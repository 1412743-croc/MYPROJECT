"""Persistent student chat operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.risk import RiskAssessment, RiskCase, RiskLevel
from app.services.ai import AIProvider, ChatTurn, build_ai_provider
from app.services.risk import assess_risk


class ChatSessionNotFound(LookupError):
    pass


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

    def send_message(
        self,
        user_id: int,
        session_id: int,
        content: str,
    ) -> tuple[ChatMessage, ChatMessage]:
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

        assistant_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=self.ai_provider.generate(content, risk_result.level, history),
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
