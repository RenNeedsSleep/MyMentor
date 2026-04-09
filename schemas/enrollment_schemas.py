"""
enrollment_schemas.py - Pydantic models for the Enrollment system.
Covers enrollment requests, approvals, rejections, and fee overrides.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class EnrollmentRequest(BaseModel):
    """Student requests to join a batch."""
    batch_id: int


class EnrollmentAction(BaseModel):
    """Tutor approves or rejects an enrollment request."""
    enrollment_id: int
    action: str  # "approve" or "reject"

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("Action must be 'approve' or 'reject'.")
        return v


class FeeOverrideUpdate(BaseModel):
    """Tutor sets/updates a custom fee for a student in a batch."""
    enrollment_id: int
    fee_override: float

    @field_validator("fee_override")
    @classmethod
    def fee_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Fee override cannot be negative.")
        return v


class FeeLockUpdate(BaseModel):
    """Tutor locks the fee for a student enrollment (prevents further edits)."""
    enrollment_id: int
    fee_locked: bool


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class EnrollmentResponse(BaseModel):
    """Response schema for an enrollment record."""
    id: int
    student_id: int
    student_username: Optional[str] = None
    student_profile_image_url: Optional[str] = None
    batch_id: int
    batch_name: Optional[str] = None
    status: str
    fee_override: Optional[float] = None
    fee_locked: bool = False
    final_fee: float
    request_status: str
    joined_at: datetime

    class Config:
        from_attributes = True


class EnrollmentListResponse(BaseModel):
    """Paginated list of enrollments."""
    enrollments: list[EnrollmentResponse]
    total: int
