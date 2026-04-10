"""
user_schemas.py - Pydantic models for User management.
"""

from pydantic import BaseModel
from typing import Optional


class UserResponse(BaseModel):
    """Public user response with profile image."""
    id: int
    username: str
    email: str
    role: str
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Update user profile (profile image URL)."""
    profile_image_url: Optional[str] = None


class UserListResponse(BaseModel):
    """List of users."""
    users: list[UserResponse]
