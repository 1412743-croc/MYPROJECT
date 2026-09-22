import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.chat import ChatMessage, MessageRole
from app.models.risk import RiskLevel
from app.services.ai import AIProviderError, ChatTurn, get_ai_provider

STUDENT_AUTH = ("student", "student123")
ADMIN_AUTH = ("admin", "admin123")


def _create_session(client: TestClient) -> int:
    response = client.post(
        "/api/chat/sessions",
        auth=STUDENT_AUTH,
        json={"title": "流式测试"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    parsed = []
    for block in body.strip().replace("\r\n", "\n").split("\n\n"):
        lines = block.splitlines()
        event = next(line[7:] for line in lines if line.startswith("event: "))
        data = next(line[6:] for line in lines if line.startswith("data: "))
        parsed.append((event, json.loads(data)))
    return parsed


def test_stream_emits_tokens_then_done_and_saves_one_assistant(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = _create_session(client)

    response = client.post(
        "/api/chat/stream",
        auth=STUDENT_AUTH,
        json={"session_id": session_id, "message": "最近考试压力很大"},
    )
    events = _parse_sse(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert events[-1][0] == "done"
    token_text = "".join(data["content"] for event, data in events if event == "token")
    assert token_text
    assert events[-1][1]["message_id"] > 0

    messages = list(
        db_session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        )
    )
    assistants = [message for message in messages if message.role == MessageRole.ASSISTANT]
    assert len(messages) == 2
    assert len(assistants) == 1
    assert assistants[0].content == token_text


def test_stream_error_is_friendly_and_does_not_save_partial_assistant(
    client: TestClient,
    db_session: Session,
) -> None:
    class FailingProvider:
        name = "failing-test-provider"

        def generate(self, message: str, risk_level: RiskLevel, history: list[ChatTurn]) -> str:
            raise AIProviderError("internal test failure")

        def stream(self, message: str, risk_level: RiskLevel, history: list[ChatTurn]):
            raise AIProviderError("internal test failure")
            yield  # pragma: no cover

    app.dependency_overrides[get_ai_provider] = lambda: FailingProvider()
    session_id = _create_session(client)

    response = client.post(
        "/api/chat/stream",
        auth=STUDENT_AUTH,
        json={"session_id": session_id, "message": "测试错误处理"},
    )
    events = _parse_sse(response.text)

    assert events == [("error", {"message": "回复生成失败，请稍后重试。"})]
    messages = list(
        db_session.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id))
    )
    assert [message.role for message in messages] == [MessageRole.USER]
    assert "internal test failure" not in response.text


def test_admin_cannot_start_streaming_chat(client: TestClient) -> None:
    response = client.post(
        "/api/chat/stream",
        auth=ADMIN_AUTH,
        json={"session_id": 1, "message": "不应发送"},
    )

    assert response.status_code == 403
