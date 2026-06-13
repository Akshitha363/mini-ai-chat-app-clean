# Mini AI Chat Application

A ChatGPT-style chat app with FastAPI backend, SQLite + SQLAlchemy storage,
Streamlit frontend, and Groq LLM integration with universal cross-thread memory.

## Project Structure
```
project/
  backend/
    app.py
    database.py
    models.py
    schemas.py
    llm.py
    requirements.txt
    .env.example
  frontend/
    main.py
    requirements.txt
```

## Setup & Run

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # then edit .env and add your GROQ_API_KEY
uvicorn app:app --reload --port 8000
```

### 2. Frontend
In a separate terminal:
```bash
cd frontend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run main.py
```

The Streamlit app will open at http://localhost:8501 and connects to the
backend at http://localhost:8000.

## Features
- Multiple chat threads (create, rename, delete, switch)
- Full per-thread message history stored in SQLite
- Universal memory: facts shared in one thread are recalled in others
- Groq LLM (default model: llama-3.3-70b-versatile)

## API Endpoints
- `POST /threads` - create thread
- `GET /threads` - list threads
- `GET /threads/{id}` - get thread + messages
- `PUT /threads/{id}` - rename thread
- `DELETE /threads/{id}` - delete thread
- `POST /chat` - send message, get AI response
