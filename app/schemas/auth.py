"""Authentication response schemas."""

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: UserRole
