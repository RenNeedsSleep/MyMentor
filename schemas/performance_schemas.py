"""
performance_schemas.py - Pydantic models for the Performance Tracking system.
Covers performance record creation, viewing, and analytics responses.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


# Score mapping: rating string → integer score
RATING_SCORE_MAP = {
    "excellent": 4,
    "great": 3,
    "good": 2,
    "satisfactory": 1,
}

VALID_RATINGS = list(RATING_SCORE_MAP.keys())


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class PerformanceRecordCreate(BaseModel):
    """Tutor creates a performance record for a student in a batch."""
    student_id: int
    batch_id: int
    rating: str
    tutor_note: Optional[str] = None
    session_date: date

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower not in VALID_RATINGS:
            raise ValueError(f"Rating must be one of: {', '.join(VALID_RATINGS)}")
        return v_lower


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class PerformanceRecordResponse(BaseModel):
    """Response schema for a single performance record."""
    id: int
    student_id: int
    tutor_id: int
    batch_id: int
    batch_name: Optional[str] = None
    rating: str
    score: int
    tutor_note: Optional[str] = None
    session_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class PerformanceListResponse(BaseModel):
    """List of performance records."""
    records: list[PerformanceRecordResponse]
    total: int


# =============================================================================
# ANALYTICS RESPONSE SCHEMAS (Graph-Ready)
# =============================================================================

class RatingDistribution(BaseModel):
    """Count of each rating category."""
    excellent: int = 0
    great: int = 0
    good: int = 0
    satisfactory: int = 0


class PerformanceTrendPoint(BaseModel):
    """Single data point in the performance trend time series."""
    date: str  # YYYY-MM-DD
    score: float


class AverageScore(BaseModel):
    """Average score across all performance records."""
    average_score: float


class StudentAnalyticsResponse(BaseModel):
    """Complete analytics response for a student (graph-ready)."""
    student_id: int
    rating_distribution: RatingDistribution
    performance_trend: list[PerformanceTrendPoint]
    average_score: AverageScore
