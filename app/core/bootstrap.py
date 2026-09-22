"""Database initialization and development seed data."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.security import hash_password
from app.models import User, UserRole


def initialize_database() -> None:
    settings = get_settings()
    settings.project_root.joinpath("data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def seed_demo_users(db: Session) -> None:
    """Create development users only when the user table is empty."""
    user_count = db.scalar(select(func.count()).select_from(User))
    if user_count:
        return

    db.add_all(
        [
            User(
                username="student",
                password_hash=hash_password("student123"),
                display_name="演示学生",
                role=UserRole.STUDENT,
            ),
            User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="演示管理员",
                role=UserRole.ADMIN,
            ),
        ]
    )
    db.commit()
