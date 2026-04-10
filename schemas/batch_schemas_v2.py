"""
batch_schemas_v2.py - Updated Pydantic models for the Batch system.
Includes new fields: subject, base_fee, mode, is_active, schedule.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class BatchCreateV2(BaseModel):
    """Create a new batch with the v2 schema (enrollment-based)."""
    name: str
    subject: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    base_fee: float = 0.0
    mode: str = "both"  # online, offline, both
    max_students: int = 30

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"online", "offline", "both"}
        if v not in allowed:
            raise ValueError(f"Mode must be one of: {', '.join(allowed)}")
        return v

    @field_validator("base_fee")
    @classmethod
    def fee_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Base fee cannot be negative.")
        return v

    @field_validator("max_students")
    @classmethod
    def max_students_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Max students must be at least 1.")
        return v


class BatchResponseV2(BaseModel):
    """Response schema for a batch with v2 fields."""
    id: int
    tutor_id: int
    tutor_username: Optional[str] = None
    tutor_profile_image_url: Optional[str] = None
    name: str
    subject: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    base_fee: float
    mode: str
    max_students: int
    is_active: bool
    created_at: datetime
    enrolled_count: int = 0

    class Config:
        from_attributes = True


class BatchUpdateV2(BaseModel):
    """Update batch fields."""
    name: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    base_fee: Optional[float] = None
    mode: Optional[str] = None
    max_students: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v is not None:
            allowed = {"online", "offline", "both"}
            if v not in allowed:
                raise ValueError(f"Mode must be one of: {', '.join(allowed)}")
        return v
