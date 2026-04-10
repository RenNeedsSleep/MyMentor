"""
notification_schemas.py - Pydantic models for the Notification system.
"""

from pydantic import BaseModel
from datetime import datetime


class NotificationResponse(BaseModel):
    """Response schema for a notification."""
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List of notifications."""
    notifications: list[NotificationResponse]
    unread_count: int


class NotificationMarkRead(BaseModel):
    """Mark a notification as read."""
    notification_id: int
