"""
notification_router.py - API endpoints for the Notification system.
Handles listing notifications, marking as read, and marking all as read.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas.notification_schemas import NotificationMarkRead
from auth import decode_access_token
from services.notification_service import (
    get_user_notifications, get_unread_count,
    mark_notification_read, mark_all_notifications_read
)

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ---------------------------------------------------------------------------
# Helper: cookie-based auth
# ---------------------------------------------------------------------------

def _get_current_user(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("user_id")).first()


def _require_user(request: Request, db: Session) -> User:
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


# ==========================================================================
# GET: List notifications
# ==========================================================================

@notification_router.get("/")
async def list_notifications(
    request: Request,
    db: Session = Depends(get_db)
):
    """List all notifications for the current user."""
    user = _require_user(request, db)

    notifications = get_user_notifications(db, user.id)
    unread = get_unread_count(db, user.id)

    result = []
    for n in notifications:
        result.append({
            "id": n.id,
            "user_id": n.user_id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        })

    return JSONResponse({
        "notifications": result,
        "unread_count": unread
    })


# ==========================================================================
# POST: Mark a single notification as read
# ==========================================================================

@notification_router.post("/read")
async def mark_read_endpoint(
    data: NotificationMarkRead,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark a specific notification as read."""
    user = _require_user(request, db)

    result = mark_notification_read(db, data.notification_id, user.id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])

    return JSONResponse({"message": "Notification marked as read."})


# ==========================================================================
# POST: Mark all notifications as read
# ==========================================================================

@notification_router.post("/read-all")
async def mark_all_read_endpoint(
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user."""
    user = _require_user(request, db)

    count = mark_all_notifications_read(db, user.id)
    return JSONResponse({
        "message": f"Marked {count} notifications as read.",
        "count": count
    })
