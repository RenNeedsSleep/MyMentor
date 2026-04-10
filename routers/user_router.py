"""
user_router.py - API endpoints for User management.
Handles user profile viewing and updating (profile image URL).
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas.user_schemas import UserProfileUpdate
from auth import decode_access_token

user_router = APIRouter(prefix="/users", tags=["Users"])


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


def _user_to_dict(user: User) -> dict:
    """Convert a User object to a response dict."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "profile_image_url": user.profile_image_url
    }


# ==========================================================================
# GET: Current user profile
# ==========================================================================

@user_router.get("/me")
async def get_my_profile(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get the current user's profile."""
    user = _require_user(request, db)
    return JSONResponse(_user_to_dict(user))


# ==========================================================================
# PUT: Update user profile (profile image URL)
# ==========================================================================

@user_router.put("/me")
async def update_my_profile(
    data: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update the current user's profile (e.g., profile image URL)."""
    user = _require_user(request, db)

    if data.profile_image_url is not None:
        user.profile_image_url = data.profile_image_url

    db.commit()
    db.refresh(user)

    return JSONResponse({
        "message": "Profile updated successfully.",
        "user": _user_to_dict(user)
    })


# ==========================================================================
# GET: View another user's public profile
# ==========================================================================

@user_router.get("/{user_id}")
async def get_user_profile(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """View a user's public profile by ID."""
    _require_user(request, db)  # Must be authenticated

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    return JSONResponse(_user_to_dict(target_user))
