"""Password hashing and HTTP Basic authentication."""

import base64
import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole

PBKDF2_ITERATIONS = 600_000
basic_auth = HTTPBasic(auto_error=False)


def hash_password(password: str) -> str:
    """Return a salted PBKDF2-SHA256 password hash."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without leaking timing information."""
    try:
        algorithm, iterations_text, salt_text, expected_text = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_text.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return secrets.compare_digest(actual, expected)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="用户名或密码错误",
        headers={"WWW-Authenticate": "Basic"},
    )


def current_user(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Authenticate the request and return its user."""
    if credentials is None:
        raise _unauthorized()

    user = db.scalar(select(User).where(User.username == credentials.username))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise _unauthorized()
    return user


def require_student(user: Annotated[User, Depends(current_user)]) -> User:
    """Allow student-only pages and APIs."""
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅学生账号可以使用聊天功能",
        )
    return user
