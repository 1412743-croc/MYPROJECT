from fastapi.testclient import TestClient


STUDENT_AUTH = ("student", "student123")
ADMIN_AUTH = ("admin", "admin123")


def _create_session(client: TestClient) -> int:
    response = client.post(
        "/api/chat/sessions",
        auth=STUDENT_AUTH,
        json={"title": "我的对话"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_student_can_create_and_list_sessions(client: TestClient) -> None:
    session_id = _create_session(client)

    response = client.get("/api/chat/sessions", auth=STUDENT_AUTH)

    assert response.status_code == 200
    assert response.json()[0]["id"] == session_id
    assert response.json()[0]["title"] == "我的对话"


def test_chat_saves_user_and_assistant_messages(client: TestClient) -> None:
    session_id = _create_session(client)

    response = client.post(
        "/api/chat",
        auth=STUDENT_AUTH,
        json={"session_id": session_id, "message": "最近考试让我压力很大"},
    )

    assert response.status_code == 200
    assert response.json()["user_message"]["role"] == "user"
    assert response.json()["assistant_message"]["role"] == "assistant"
    assert "压力" in response.json()["assistant_message"]["content"]

    history = client.get(
        f"/api/chat/sessions/{session_id}/messages",
        auth=STUDENT_AUTH,
    )
    assert history.status_code == 200
    assert [message["role"] for message in history.json()] == ["user", "assistant"]
    assert history.json()[0]["content"] == "最近考试让我压力很大"


def test_high_risk_words_get_a_cautious_mock_reply(client: TestClient) -> None:
    session_id = _create_session(client)

    response = client.post(
        "/api/chat",
        auth=STUDENT_AUTH,
        json={"session_id": session_id, "message": "我想结束生命"},
    )

    assert response.status_code == 200
    reply = response.json()["assistant_message"]["content"]
    assert "立即联系当地紧急服务" in reply
    assert "信任的人" in reply


def test_admin_cannot_use_student_chat(client: TestClient) -> None:
    create_response = client.post(
        "/api/chat/sessions",
        auth=ADMIN_AUTH,
        json={"title": "不应创建"},
    )
    page_response = client.get("/student.html", auth=ADMIN_AUTH)

    assert create_response.status_code == 403
    assert page_response.status_code == 403


def test_chat_rejects_unknown_or_unowned_session(client: TestClient) -> None:
    response = client.post(
        "/api/chat",
        auth=STUDENT_AUTH,
        json={"session_id": 9999, "message": "你好"},
    )

    assert response.status_code == 404


def test_student_page_requires_login(client: TestClient) -> None:
    unauthenticated = client.get("/student.html")
    authenticated = client.get("/student.html", auth=STUDENT_AUTH)

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    assert "MindBridge 学生支持" in authenticated.text
