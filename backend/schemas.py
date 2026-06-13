"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- ChatMessage Schemas ----------

class ChatMessageBase(BaseModel):
    role: str
    content: str


class ChatMessageOut(ChatMessageBase):
    id: int
    thread_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- ChatThread Schemas ----------

class ChatThreadCreate(BaseModel):
    title: Optional[str] = Field(default="New Chat")


class ChatThreadUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ChatThreadOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatThreadDetailOut(ChatThreadOut):
    messages: List[ChatMessageOut] = []

    class Config:
        from_attributes = True


# ---------- Chat Endpoint Schemas ----------

class ChatRequest(BaseModel):
    thread_id: int
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
