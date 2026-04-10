"""
notification_service.py - Business logic for the Notification system.
Handles notification creation, retrieval, and marking as read.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from models import Notification


def create_notification(db: Session, user_id: int, message: str) -> Notification:
    """Create a new notification for a user."""
    notification = Notification(
        user_id=user_id,
        message=message,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_user_notifications(db: Session, user_id: int, limit: int = 50) -> list:
    """Get all notifications for a user, most recent first."""
    return db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()


def get_unread_count(db: Session, user_id: int) -> int:
    """Count unread notifications for a user."""
    return db.query(func.count(Notification.id)).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).scalar()


def mark_notification_read(db: Session, notification_id: int, user_id: int) -> dict:
    """Mark a single notification as read. User must own the notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notification:
        return {"success": False, "error": "Notification not found."}

    notification.is_read = True
    db.commit()
    return {"success": True}


def mark_all_notifications_read(db: Session, user_id: int) -> int:
    """Mark all notifications as read for a user. Returns count updated."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return count
