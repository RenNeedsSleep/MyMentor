"""
tutor_router.py - API endpoints for Tutor profile management.
Provides GET /tutor/me and PUT /tutor/profile (JSON API).
These are non-breaking additions alongside the existing HTML form routes in main.py.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, TutorProfile
from auth import decode_access_token
from tutor_schemas import TutorProfileUpdate
from services.tutor_service import (
    update_tutor_profile,
    get_tutor_profile_response,
)

tutor_router = APIRouter(prefix="/tutor", tags=["Tutor Profile"])


# ---------------------------------------------------------------------------
# Helper: cookie-based auth (same pattern as batch_router.py)
# ---------------------------------------------------------------------------

def _get_current_user(request: Request, db: Session):
    """Extract user from JWT cookie. Returns None if not logged in."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    return user


def _require_tutor(request: Request, db: Session) -> User:
    """Require an authenticated tutor. Raises 401/403 otherwise."""
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can access this endpoint.")
    return user


# ==========================================================================
# GET /tutor/me — fetch current tutor's profile
# ==========================================================================

@tutor_router.get("/me")
async def get_my_profile(
    request: Request,
    db: Session = Depends(get_db),
):
    """Return the currently authenticated tutor's full profile."""
    user = _require_tutor(request, db)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    if not profile:
        # Auto-create an empty profile if one doesn't exist yet
        profile = TutorProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return JSONResponse(get_tutor_profile_response(profile, user))


# ==========================================================================
# PUT /tutor/profile — update tutor profile (JSON API with Pydantic validation)
# ==========================================================================

@tutor_router.put("/profile")
async def update_profile(
    data: TutorProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Update the authenticated tutor's profile.
    Validates inputs via TutorProfileUpdate schema.
    Automatically recalculates is_profile_complete.
    """
    user = _require_tutor(request, db)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    if not profile:
        profile = TutorProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    updated = update_tutor_profile(
        db,
        profile,
        full_name=data.full_name,
        bio=data.bio,
        qualifications=data.qualifications,
        subjects=data.subjects,
        experience_years=data.experience_years,
        profile_image_url=data.profile_image_url,
        teaching_mode=data.teaching_mode,
        location=data.location,
    )

    return JSONResponse({
        "message": "Profile updated successfully.",
        "profile": get_tutor_profile_response(updated, user),
    })
