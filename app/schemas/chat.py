"""Chat request and response schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.chat import MessageRole

NonEmptyMessage = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ChatSessionCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=100)


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ChatRequest(BaseModel):
    session_id: int
    message: NonEmptyMessage


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: MessageRole
    content: str
    created_at: datetime


class ChatExchangeResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
