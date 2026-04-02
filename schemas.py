"""
schemas.py - Pydantic models for request/response validation
"""

from pydantic import BaseModel
from typing import Optional


class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str                        


class UserLogin(BaseModel):
    email: str
    password: str


class TutorProfileCreate(BaseModel):
    qualifications: Optional[str] = None
    subjects: Optional[str] = None
    teaching_mode: str = "both"
    location: Optional[str] = None


class SlotCreate(BaseModel):
    date: str
    start_time: str
    end_time: str


class BookingCreate(BaseModel):
    slot_id: int
    mode: str


class RecordingCreate(BaseModel):
    booking_id: int
    video_link: str
