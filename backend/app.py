"""
FastAPI backend for the Mini AI Chat Application.

Endpoints:
- POST   /threads             Create a new thread
- GET    /threads              Return all threads
- GET    /threads/{thread_id}  Return thread + messages
- PUT    /threads/{thread_id}  Rename thread
- DELETE /threads/{thread_id}  Delete thread
- POST   /chat                 Send a message and get AI response
"""

from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
import llm
from database import engine, get_db, Base

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini AI Chat Application", version="1.0.0")

# Allow the Streamlit frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Mini AI Chat Application API is running"}


# ---------------------------------------------------------------------------
# Thread Endpoints
# ---------------------------------------------------------------------------

@app.post("/threads", response_model=schemas.ChatThreadOut)
def create_thread(thread: schemas.ChatThreadCreate, db: Session = Depends(get_db)):
    """Create a new chat thread."""
    title = thread.title.strip() if thread.title and thread.title.strip() else "New Chat"
    new_thread = models.ChatThread(title=title, created_at=datetime.utcnow())
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    return new_thread


@app.get("/threads", response_model=list[schemas.ChatThreadOut])
def list_threads(db: Session = Depends(get_db)):
    """Return all chat threads, most recently created first."""
    threads = (
        db.query(models.ChatThread)
        .order_by(models.ChatThread.created_at.desc())
        .all()
    )
    return threads


@app.get("/threads/{thread_id}", response_model=schemas.ChatThreadDetailOut)
def get_thread(thread_id: int, db: Session = Depends(get_db)):
    """Return a single thread along with its full message history."""
    thread = db.query(models.ChatThread).filter(models.ChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@app.put("/threads/{thread_id}", response_model=schemas.ChatThreadOut)
def rename_thread(
    thread_id: int, update: schemas.ChatThreadUpdate, db: Session = Depends(get_db)
):
    """Rename an existing thread."""
    thread = db.query(models.ChatThread).filter(models.ChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    new_title = update.title.strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    thread.title = new_title
    db.commit()
    db.refresh(thread)
    return thread


@app.delete("/threads/{thread_id}")
def delete_thread(thread_id: int, db: Session = Depends(get_db)):
    """Delete a thread and all of its messages."""
    thread = db.query(models.ChatThread).filter(models.ChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    db.delete(thread)
    db.commit()
    return {"status": "success", "message": f"Thread {thread_id} deleted"}


# ---------------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=schemas.ChatResponse)
def chat(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """
    Handle a chat message:
    1. Validate the thread exists.
    2. Save the user's message.
    3. Generate an AI response (with universal memory context).
    4. Save the AI response.
    5. Return the AI response text.
    """
    thread = db.query(models.ChatThread).filter(models.ChatThread.id == request.thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_message_text = request.message.strip()
    if not user_message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Save user message
    user_msg = models.ChatMessage(
        thread_id=thread.id,
        role="user",
        content=user_message_text,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Generate AI response (uses universal memory + thread history)
    try:
        ai_response_text = llm.generate_response(db, thread.id, user_message_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Save assistant message
    assistant_msg = models.ChatMessage(
        thread_id=thread.id,
        role="assistant",
        content=ai_response_text,
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Auto-title the thread based on the first user message
    if thread.title == "New Chat":
        title_preview = user_message_text[:50]
        thread.title = title_preview + ("..." if len(user_message_text) > 50 else "")
        db.commit()

    return schemas.ChatResponse(response=ai_response_text)
