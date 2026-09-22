"""Application HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import current_user
from app.models.user import User
from app.schemas.auth import ProfileResponse

router = APIRouter()


def _profile(user: User) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@router.post("/api/auth/login", response_model=ProfileResponse, tags=["authentication"])
def login(user: Annotated[User, Depends(current_user)]) -> ProfileResponse:
    """Validate HTTP Basic credentials and return the current profile."""
    return _profile(user)


@router.get("/api/profile", response_model=ProfileResponse, tags=["authentication"])
def profile(user: Annotated[User, Depends(current_user)]) -> ProfileResponse:
    """Return the authenticated user's public profile."""
    return _profile(user)
