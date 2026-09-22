"""Student chat routes and protected student page."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_student
from app.models.user import User
from app.schemas.chat import (
    ChatExchangeResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatSessionCreate,
    ChatSessionResponse,
)
from app.services.chat import ChatService, ChatSessionNotFound

router = APIRouter()
student_page = Path(__file__).resolve().parents[1] / "pages" / "student.html"


@router.get("/student.html", include_in_schema=False)
def student_html(_: Annotated[User, Depends(require_student)]) -> FileResponse:
    return FileResponse(student_page)


@router.post(
    "/api/chat/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["chat"],
)
def create_chat_session(
    request: ChatSessionCreate,
    user: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionResponse:
    return ChatSessionResponse.model_validate(ChatService(db).create_session(user.id, request.title))


@router.get("/api/chat/sessions", response_model=list[ChatSessionResponse], tags=["chat"])
def list_chat_sessions(
    user: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChatSessionResponse]:
    return [
        ChatSessionResponse.model_validate(item)
        for item in ChatService(db).list_sessions(user.id)
    ]


@router.get(
    "/api/chat/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
    tags=["chat"],
)
def list_chat_messages(
    session_id: int,
    user: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChatMessageResponse]:
    try:
        messages = ChatService(db).list_messages(user.id, session_id)
    except ChatSessionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return [ChatMessageResponse.model_validate(item) for item in messages]


@router.post("/api/chat", response_model=ChatExchangeResponse, tags=["chat"])
def send_chat_message(
    request: ChatRequest,
    user: Annotated[User, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatExchangeResponse:
    try:
        user_message, assistant_message = ChatService(db).send_message(
            user.id,
            request.session_id,
            request.message,
        )
    except ChatSessionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ChatExchangeResponse(
        user_message=ChatMessageResponse.model_validate(user_message),
        assistant_message=ChatMessageResponse.model_validate(assistant_message),
    )
