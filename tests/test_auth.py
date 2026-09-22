from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def test_profile_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


def test_student_can_log_in(client: TestClient) -> None:
    response = client.post("/api/auth/login", auth=("student", "student123"))

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "username": "student",
        "display_name": "演示学生",
        "role": "student",
    }


def test_admin_profile_has_admin_role(client: TestClient) -> None:
    response = client.get("/api/profile", auth=("admin", "admin123"))

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "admin"


def test_wrong_password_is_rejected(client: TestClient) -> None:
    response = client.post("/api/auth/login", auth=("student", "wrong-password"))

    assert response.status_code == 401


def test_demo_passwords_are_hashed(db_session: Session) -> None:
    student = db_session.scalar(select(User).where(User.username == "student"))

    assert student is not None
    assert student.password_hash != "student123"
    assert verify_password("student123", student.password_hash)
