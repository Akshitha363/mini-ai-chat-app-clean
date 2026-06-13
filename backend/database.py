"""
Database configuration module.
Sets up the SQLAlchemy engine, session, and declarative base for SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database file lives alongside this module
SQLALCHEMY_DATABASE_URL = "sqlite:///./chat_app.db"

# check_same_thread=False is required for SQLite when used with FastAPI's
# threaded request handling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a database session and
    ensures it is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
