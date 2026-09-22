"""Read-only administrator reporting queries."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.risk import RiskAssessment, RiskCase
from app.models.user import User


class AdminReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def cases(self) -> list[dict[str, Any]]:
        statement = (
            select(RiskCase, ChatMessage, ChatSession, User)
            .join(ChatMessage, ChatMessage.id == RiskCase.message_id)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(User, User.id == RiskCase.user_id)
            .order_by(RiskCase.created_at.desc(), RiskCase.id.desc())
        )
        return [
            {
                "id": case.id,
                "message_id": message.id,
                "session_id": session.id,
                "username": user.username,
                "content": message.content,
                "level": case.level,
                "reason": case.reason,
                "status": case.status,
                "created_at": case.created_at,
            }
            for case, message, session, user in self.db.execute(statement)
        ]

    def reports(self) -> list[dict[str, Any]]:
        statement = (
            select(RiskAssessment, ChatMessage, ChatSession, User)
            .join(ChatMessage, ChatMessage.id == RiskAssessment.message_id)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(User, User.id == ChatSession.user_id)
            .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
        )
        return [
            {
                "id": assessment.id,
                "message_id": message.id,
                "session_id": session.id,
                "username": user.username,
                "content": message.content,
                "level": assessment.level,
                "matched_rules": assessment.matched_rules,
                "reason": assessment.reason,
                "created_at": assessment.created_at,
            }
            for assessment, message, session, user in self.db.execute(statement)
        ]
