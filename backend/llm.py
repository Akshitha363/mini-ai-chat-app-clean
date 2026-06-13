"""
LLM helper module.

Provides a reusable interface to the Groq LLM API and implements the
"Universal Memory" feature: relevant information from messages across
ALL threads is retrieved and injected into the prompt context so the
assistant can recall facts shared in other conversations.
"""

import os
from typing import List

from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import desc

import models

# Load environment variables (in case dotenv hasn't been loaded by app.py yet)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Maximum number of historical messages (across all threads) to pull
# into the universal memory context.
MAX_MEMORY_MESSAGES = 50

# Maximum number of most-recent messages from the CURRENT thread to
# include as direct conversation context.
MAX_THREAD_MESSAGES = 20


_client = None


def get_client() -> Groq:
    """Lazily initialize and return the Groq client."""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Please configure it in your .env file."
            )
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def build_universal_memory_context(db: Session, current_thread_id: int) -> str:
    """
    Build a textual memory summary from messages across ALL OTHER threads.

    This allows the assistant to recall facts/preferences shared by the
    user in different conversation threads (e.g. "My favorite language
    is Python" in Thread A should be recallable in Thread B).
    """
    # Fetch the most recent messages from other threads (most recent first)
    other_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.thread_id != current_thread_id)
        .order_by(desc(models.ChatMessage.created_at))
        .limit(MAX_MEMORY_MESSAGES)
        .all()
    )

    if not other_messages:
        return ""

    # Reverse to chronological order for readability
    other_messages = list(reversed(other_messages))

    lines = []
    for msg in other_messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role_label}: {msg.content}")

    memory_text = "\n".join(lines)

    return (
        "The following is a record of relevant information shared by the "
        "user in OTHER conversation threads. Use this to recall facts, "
        "preferences, or context about the user when relevant to the "
        "current conversation:\n\n"
        f"{memory_text}\n\n"
        "---\n"
        "Now continue the current conversation below, using the memory "
        "above when it helps answer the user's question."
    )


def get_thread_messages(db: Session, thread_id: int) -> List[models.ChatMessage]:
    """Return all messages for a given thread in chronological order."""
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.thread_id == thread_id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )


def generate_response(db: Session, thread_id: int, user_message: str) -> str:
    """
    Generate an AI response for the given thread and user message.

    Steps:
    1. Build universal memory context from other threads.
    2. Load current thread's conversation history.
    3. Construct the full message list (system + memory + history + new message).
    4. Call the Groq LLM API and return the response text.
    """
    client = get_client()

    system_prompt = (
        "You are a helpful, friendly AI assistant in a chat application. "
        "You have access to a memory of the user's previous conversations "
        "across different chat threads. Use that memory to provide "
        "personalized, context-aware answers. Be concise and accurate."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Inject universal memory context (if any) as a system-level message
    memory_context = build_universal_memory_context(db, thread_id)
    if memory_context:
        messages.append({"role": "system", "content": memory_context})

    # Add current thread's conversation history (most recent N messages)
    history = get_thread_messages(db, thread_id)
    if len(history) > MAX_THREAD_MESSAGES:
        history = history[-MAX_THREAD_MESSAGES:]

    for msg in history:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.content})

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc
