import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk import RiskAssessment, RiskCase, RiskLevel
from app.services.risk import assess_risk

STUDENT_AUTH = ("student", "student123")
ADMIN_AUTH = ("admin", "admin123")


@pytest.mark.parametrize(
    ("message", "expected_level"),
    [
        ("今天和朋友一起吃了午饭", RiskLevel.LOW),
        ("最近考试压力很大，我经常焦虑失眠", RiskLevel.MEDIUM),
        ("我已经计划今晚结束生命", RiskLevel.HIGH),
    ],
)
def test_rule_based_risk_levels(message: str, expected_level: RiskLevel) -> None:
    result = assess_risk(message)

    assert result.level == expected_level
    assert result.reason
    if expected_level != RiskLevel.LOW:
        assert result.matched_rules


def test_exam_stress_is_not_classified_as_high() -> None:
    result = assess_risk("这周考试很多，我压力很大，心情也比较低落")

    assert result.level == RiskLevel.MEDIUM


def test_negated_self_harm_statement_is_not_classified_as_high() -> None:
    result = assess_risk("我不想自杀，只是最近压力很大")

    assert result.level == RiskLevel.MEDIUM


def test_each_user_message_is_assessed_and_high_creates_case(
    client: TestClient,
    db_session: Session,
) -> None:
    session_response = client.post(
        "/api/chat/sessions",
        auth=STUDENT_AUTH,
        json={"title": "风险评估测试"},
    )
    session_id = session_response.json()["id"]

    for message in ("今天还不错", "最近压力很大", "我已经计划今晚结束生命"):
        response = client.post(
            "/api/chat",
            auth=STUDENT_AUTH,
            json={"session_id": session_id, "message": message},
        )
        assert response.status_code == 200

    assessments = list(db_session.scalars(select(RiskAssessment).order_by(RiskAssessment.id)))
    cases = list(db_session.scalars(select(RiskCase)))

    assert [item.level for item in assessments] == [
        RiskLevel.LOW,
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
    ]
    assert len(cases) == 1
    assert cases[0].level == RiskLevel.HIGH
    assert cases[0].status == "open"


def test_high_risk_reply_contains_safety_guidance_without_fake_phone_number(
    client: TestClient,
) -> None:
    session_id = client.post(
        "/api/chat/sessions",
        auth=STUDENT_AUTH,
        json={"title": "安全回复测试"},
    ).json()["id"]

    response = client.post(
        "/api/chat",
        auth=STUDENT_AUTH,
        json={"session_id": session_id, "message": "我想结束生命"},
    )

    reply = response.json()["assistant_message"]["content"]
    assert "立即联系当地紧急服务" in reply
    assert "信任的人" in reply
    assert "校园" in reply
    assert re.search(r"\d{3,}", reply) is None


def test_admin_can_view_cases_and_reports(client: TestClient) -> None:
    session_id = client.post(
        "/api/chat/sessions",
        auth=STUDENT_AUTH,
        json={"title": "管理员报告测试"},
    ).json()["id"]
    client.post(
        "/api/chat",
        auth=STUDENT_AUTH,
        json={"session_id": session_id, "message": "我已经计划今晚结束生命"},
    )

    cases = client.get("/api/admin/cases", auth=ADMIN_AUTH)
    reports = client.get("/api/admin/reports", auth=ADMIN_AUTH)
    page = client.get("/admin.html", auth=ADMIN_AUTH)

    assert cases.status_code == 200
    assert cases.json()[0]["level"] == "high"
    assert cases.json()[0]["username"] == "student"
    assert reports.status_code == 200
    assert reports.json()[0]["matched_rules"]
    assert page.status_code == 200
    assert "MindBridge 管理后台" in page.text


def test_student_cannot_access_admin_views(client: TestClient) -> None:
    assert client.get("/api/admin/cases", auth=STUDENT_AUTH).status_code == 403
    assert client.get("/api/admin/reports", auth=STUDENT_AUTH).status_code == 403
    assert client.get("/admin.html", auth=STUDENT_AUTH).status_code == 403
