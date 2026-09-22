"""Persistent student chat operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.services.mock_ai import MockAI


class ChatSessionNotFound(LookupError):
    pass


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, user_id: int, title: str) -> ChatSession:
        chat_session = ChatSession(user_id=user_id, title=title.strip() or "新对话")
        self.db.add(chat_session)
        self.db.commit()
        self.db.refresh(chat_session)
        return chat_session

    def list_sessions(self, user_id: int) -> list[ChatSession]:
        statement = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        )
        return list(self.db.scalars(statement))

    def list_messages(self, user_id: int, session_id: int) -> list[ChatMessage]:
        self._owned_session(user_id, session_id)
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        return list(self.db.scalars(statement))

    def send_message(
        self,
        user_id: int,
        session_id: int,
        content: str,
    ) -> tuple[ChatMessage, ChatMessage]:
        chat_session = self._owned_session(user_id, session_id)
        user_message = ChatMessage(session_id=session_id, role=MessageRole.USER, content=content)
        self.db.add(user_message)
        self.db.flush()

        assistant_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=MockAI.reply(content),
        )
        self.db.add(assistant_message)

        if chat_session.title == "新对话":
            chat_session.title = content[:30]

        self.db.commit()
        self.db.refresh(user_message)
        self.db.refresh(assistant_message)
        return user_message, assistant_message

    def _owned_session(self, user_id: int, session_id: int) -> ChatSession:
        chat_session = self.db.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        if chat_session is None:
            raise ChatSessionNotFound("会话不存在")
        return chat_session
