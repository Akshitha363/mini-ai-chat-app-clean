"""
Streamlit frontend for the Mini AI Chat Application.

A ChatGPT-style interface that connects to the FastAPI backend.
Run the backend first:  uvicorn app:app --reload --port 8000
Then run this:           streamlit run main.py
"""

import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Mini AI Chat", page_icon="💬", layout="wide")

# ---------------------------------------------------------------------------
# Custom CSS for a clean, modern ChatGPT-style look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stChatMessage { padding: 0.5rem 0; }
    .block-container { padding-top: 2rem; }
    .thread-title { font-weight: 600; }
    div[data-testid="stSidebar"] button { width: 100%; text-align: left; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

if "rename_target" not in st.session_state:
    st.session_state.rename_target = None


# ---------------------------------------------------------------------------
# API Helper Functions
# ---------------------------------------------------------------------------

def api_get(path):
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def api_post(path, json_data):
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", json=json_data, timeout=60)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        try:
            detail = resp.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail


def api_put(path, json_data):
    try:
        resp = requests.put(f"{BACKEND_URL}{path}", json=json_data, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        try:
            detail = resp.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail


def api_delete(path):
    try:
        resp = requests.delete(f"{BACKEND_URL}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        try:
            detail = resp.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail


# ---------------------------------------------------------------------------
# Sidebar: Thread Management
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("💬 Mini AI Chat")

    if st.button("➕ New Chat", use_container_width=True):
        data, err = api_post("/threads", {"title": "New Chat"})
        if err:
            st.error(f"Failed to create thread: {err}")
        else:
            st.session_state.current_thread_id = data["id"]
            st.success("New chat created!")
            st.rerun()

    st.markdown("---")
    st.subheader("Your Chats")

    threads, err = api_get("/threads")
    if err:
        st.error(f"Could not load threads. Is the backend running?\n\n{err}")
        threads = []

    if not threads:
        st.caption("No chats yet. Start a new one above!")

    for thread in threads:
        thread_id = thread["id"]
        is_active = thread_id == st.session_state.current_thread_id

        cols = st.columns([5, 1, 1])
        with cols[0]:
            label = ("🟢 " if is_active else "") + thread["title"]
            if st.button(label, key=f"select_{thread_id}", use_container_width=True):
                st.session_state.current_thread_id = thread_id
                st.session_state.rename_target = None
                st.rerun()
        with cols[1]:
            if st.button("✏️", key=f"rename_btn_{thread_id}"):
                st.session_state.rename_target = thread_id
                st.rerun()
        with cols[2]:
            if st.button("🗑️", key=f"delete_{thread_id}"):
                _, derr = api_delete(f"/threads/{thread_id}")
                if derr:
                    st.error(f"Failed to delete thread: {derr}")
                else:
                    if st.session_state.current_thread_id == thread_id:
                        st.session_state.current_thread_id = None
                    st.success("Thread deleted")
                    st.rerun()

        # Inline rename form
        if st.session_state.rename_target == thread_id:
            new_title = st.text_input(
                "New title", value=thread["title"], key=f"rename_input_{thread_id}"
            )
            rcols = st.columns(2)
            with rcols[0]:
                if st.button("Save", key=f"save_rename_{thread_id}"):
                    _, uerr = api_put(f"/threads/{thread_id}", {"title": new_title})
                    if uerr:
                        st.error(f"Rename failed: {uerr}")
                    else:
                        st.session_state.rename_target = None
                        st.success("Thread renamed")
                        st.rerun()
            with rcols[1]:
                if st.button("Cancel", key=f"cancel_rename_{thread_id}"):
                    st.session_state.rename_target = None
                    st.rerun()


# ---------------------------------------------------------------------------
# Main Area: Conversation
# ---------------------------------------------------------------------------
st.header("Mini AI Chat Application")

if st.session_state.current_thread_id is None:
    st.info("👈 Select a chat thread or create a new one to get started.")
else:
    thread_data, err = api_get(f"/threads/{st.session_state.current_thread_id}")

    if err:
        st.error(f"Failed to load thread: {err}")
    else:
        st.markdown(f"### {thread_data['title']}")
        st.caption(f"Created: {thread_data['created_at']}")
        st.markdown("---")

        # Display full message history
        for msg in thread_data["messages"]:
            role = msg["role"]
            with st.chat_message("user" if role == "user" else "assistant"):
                st.markdown(msg["content"])

        # Message input
        user_input = st.chat_input("Type your message here...")

        if user_input:
            # Display the user's message immediately
            with st.chat_message("user"):
                st.markdown(user_input)

            # Get AI response with a loading spinner
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    data, err = api_post(
                        "/chat",
                        {"thread_id": st.session_state.current_thread_id, "message": user_input},
                    )
                if err:
                    st.error(f"Error generating response: {err}")
                else:
                    st.markdown(data["response"])

            if not err:
                st.rerun()
