"""Administrator risk report schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.models.risk import RiskLevel


class RiskReportResponse(BaseModel):
    id: int
    message_id: int
    session_id: int
    username: str
    content: str
    level: RiskLevel
    matched_rules: list[str]
    reason: str
    created_at: datetime


class RiskCaseResponse(BaseModel):
    id: int
    message_id: int
    session_id: int
    username: str
    content: str
    level: RiskLevel
    reason: str
    status: str
    created_at: datetime
