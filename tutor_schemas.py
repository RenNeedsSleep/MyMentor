"""
tutor_schemas.py - Pydantic models for Tutor profile update and response.
Kept separate from existing schemas to avoid touching legacy code.
"""

from pydantic import BaseModel, field_validator
from typing import Optional


class TutorProfileUpdate(BaseModel):
    """Schema for updating a tutor's extended profile via PUT /tutor/profile."""

    full_name: str
    bio: Optional[str] = None
    qualifications: str
    subjects: str
    experience_years: Optional[int] = None
    profile_image_url: Optional[str] = None
    teaching_mode: str = "both"
    location: Optional[str] = None

    # --- Validation rules ---

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Full name must not be empty.")
        return v.strip()

    @field_validator("qualifications")
    @classmethod
    def qualifications_min_length(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Qualifications must not be empty.")
        words = v.strip().split()
        if len(words) < 3:
            raise ValueError("Qualifications should be at least a few words (minimum 3 words).")
        return v.strip()

    @field_validator("subjects")
    @classmethod
    def subjects_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Subjects must not be empty.")
        return v.strip()

    @field_validator("experience_years")
    @classmethod
    def experience_years_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Experience years cannot be negative.")
        return v

    @field_validator("teaching_mode")
    @classmethod
    def valid_teaching_mode(cls, v: str) -> str:
        allowed = {"online", "offline", "both"}
        if v not in allowed:
            raise ValueError(f"Teaching mode must be one of: {', '.join(allowed)}")
        return v


class TutorProfileResponse(BaseModel):
    """Schema for GET /tutor/me response."""

    id: int
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    qualifications: Optional[str] = None
    subjects: Optional[str] = None
    experience_years: Optional[int] = None
    profile_image_url: Optional[str] = None
    teaching_mode: str = "both"
    location: Optional[str] = None
    is_profile_complete: bool = False
    rating: float = 0.0
    total_students: int = 0

    class Config:
        from_attributes = True
