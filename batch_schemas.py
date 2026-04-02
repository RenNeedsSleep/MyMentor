"""
batch_schemas.py - Pydantic models for Batch, VideoSession, and SessionMaterial features.
Kept separate from the original schemas.py to avoid touching existing code.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# =============================================================================
# Batch Schemas
# =============================================================================

class BatchCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scheduled_time: str
    max_students: int = 30


class BatchResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    scheduled_time: str
    max_students: int
    tutor_id: int
    tutor_name: str
    created_at: datetime
    member_count: int

    class Config:
        from_attributes = True


class BatchMemberResponse(BaseModel):
    id: int
    batch_id: int
    student_id: int
    student_name: str
    joined_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Video Session Schemas
# =============================================================================

class VideoSessionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: str


class SessionMaterialResponse(BaseModel):
    id: int
    session_id: int
    file_url: str
    file_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class VideoSessionResponse(BaseModel):
    id: int
    batch_id: int
    title: str
    description: Optional[str] = None
    video_url: str
    created_at: datetime
    materials: List[SessionMaterialResponse] = []

    class Config:
        from_attributes = True


# =============================================================================
# Session Material Schemas
# =============================================================================

class SessionMaterialCreate(BaseModel):
    file_url: str
    file_type: str = "pdf"
