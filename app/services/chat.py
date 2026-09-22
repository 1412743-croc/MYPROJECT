"""Persistent student chat operations."""

from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.risk import RiskAssessment, RiskCase, RiskLevel
from app.services.ai import AIProvider, AIProviderError, ChatTurn, build_ai_provider
from app.services.risk import RiskAssessmentResult, assess_risk


class ChatSessionNotFound(LookupError):
    pass


@dataclass(frozen=True)
class ChatStreamEvent:
    event: str
    content: str = ""
    message_id: int | None = None


class ChatService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        ai_provider: AIProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.ai_provider = ai_provider or build_ai_provider(self.settings)

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

    def ensure_session(self, user_id: int, session_id: int) -> None:
        self._owned_session(user_id, session_id)

    def send_message(
        self,
        user_id: int,
        session_id: int,
        content: str,
    ) -> tuple[ChatMessage, ChatMessage]:
        user_message, risk_result, history = self._record_user_message(
            user_id,
            session_id,
            content,
        )
        reply = self.ai_provider.generate(content, risk_result.level, history)
        assistant_message = self._save_assistant_message(session_id, reply)
        return user_message, assistant_message

    def stream_message(
        self,
        user_id: int,
        session_id: int,
        content: str,
    ) -> Iterator[ChatStreamEvent]:
        _, risk_result, history = self._record_user_message(user_id, session_id, content)
        chunks: list[str] = []
        for chunk in self.ai_provider.stream(content, risk_result.level, history):
            if not chunk:
                continue
            chunks.append(chunk)
            yield ChatStreamEvent(event="token", content=chunk)

        reply = "".join(chunks).strip()
        if not reply:
            raise AIProviderError("provider returned an empty stream")
        assistant_message = self._save_assistant_message(session_id, reply)
        yield ChatStreamEvent(event="done", message_id=assistant_message.id)

    def _record_user_message(
        self,
        user_id: int,
        session_id: int,
        content: str,
    ) -> tuple[ChatMessage, RiskAssessmentResult, list[ChatTurn]]:
        chat_session = self._owned_session(user_id, session_id)
        history = self._recent_history(session_id)
        risk_result = assess_risk(content)
        user_message = ChatMessage(session_id=session_id, role=MessageRole.USER, content=content)
        self.db.add(user_message)
        self.db.flush()

        self.db.add(
            RiskAssessment(
                message_id=user_message.id,
                level=risk_result.level,
                matched_rules=list(risk_result.matched_rules),
                reason=risk_result.reason,
            )
        )
        if risk_result.level == RiskLevel.HIGH:
            self.db.add(
                RiskCase(
                    user_id=user_id,
                    message_id=user_message.id,
                    level=risk_result.level,
                    reason=risk_result.reason,
                    status="open",
                )
            )
        if chat_session.title == "新对话":
            chat_session.title = content[:30]

        self.db.commit()
        self.db.refresh(user_message)
        return user_message, risk_result, history

    def _save_assistant_message(self, session_id: int, content: str) -> ChatMessage:
        assistant_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
        )
        self.db.add(assistant_message)
        self.db.commit()
        self.db.refresh(assistant_message)
        return assistant_message

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

    def _recent_history(self, session_id: int) -> list[ChatTurn]:
        if self.settings.ai_history_limit == 0:
            return []
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(self.settings.ai_history_limit)
        )
        messages = reversed(list(self.db.scalars(statement)))
        return [ChatTurn(role=item.role.value, content=item.content) for item in messages]
