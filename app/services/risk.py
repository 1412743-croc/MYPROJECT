"""Deterministic and explainable first-pass risk assessment."""

import re
from dataclasses import dataclass

from app.models.risk import RiskLevel


@dataclass(frozen=True)
class RiskAssessmentResult:
    level: RiskLevel
    matched_rules: tuple[str, ...]
    reason: str


HIGH_RISK_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "explicit_self_harm_intent",
        re.compile(r"(?:我|自己).{0,8}(?:想|要|准备|计划).{0,8}(?:自杀|结束生命|伤害自己|割腕|跳楼)"),
    ),
    (
        "self_harm_plan",
        re.compile(r"(?:自杀|结束生命|割腕|跳楼).{0,8}(?:计划|方法|时间|今晚|现在)"),
    ),
    (
        "cannot_stay_alive",
        re.compile(r"(?:我|自己).{0,8}(?:不想活了|活不下去了)"),
    ),
    (
        "explicit_self_harm_intent_en",
        re.compile(r"\b(?:i want to die|i plan to kill myself|i'm going to kill myself)\b", re.IGNORECASE),
    ),
)

MEDIUM_RISK_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "severe_distress",
        re.compile(r"压力(?:很大|太大)|焦虑|恐慌|失眠|很难过|情绪低落|绝望|崩溃|撑不下去|活着没意思"),
    ),
    (
        "ambiguous_death_thought",
        re.compile(r"不想活|想消失|没有希望"),
    ),
)


def assess_risk(message: str) -> RiskAssessmentResult:
    """Classify a message using conservative, auditable rules."""
    normalized = " ".join(message.casefold().split())
    high_risk_text = re.sub(
        r"(?:不想|没有想过|没想过|不会|不准备|没打算)(?:要)?(?:自杀|结束生命|伤害自己)",
        "",
        normalized,
    )
    high_matches = tuple(code for code, pattern in HIGH_RISK_RULES if pattern.search(high_risk_text))
    if high_matches:
        return RiskAssessmentResult(
            level=RiskLevel.HIGH,
            matched_rules=high_matches,
            reason="检测到明确的自伤或自杀意图、计划或即时危险信号",
        )

    medium_matches = tuple(code for code, pattern in MEDIUM_RISK_RULES if pattern.search(normalized))
    if medium_matches:
        return RiskAssessmentResult(
            level=RiskLevel.MEDIUM,
            matched_rules=medium_matches,
            reason="检测到明显压力、情绪困扰或含义不明确的消极表达",
        )

    return RiskAssessmentResult(
        level=RiskLevel.LOW,
        matched_rules=(),
        reason="未检测到明确的中高风险规则信号",
    )
