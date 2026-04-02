"""
tutor_service.py - Business logic for Tutor profile management.
Handles profile completeness checks and profile updates.
"""

from sqlalchemy.orm import Session
from models import TutorProfile, User


def check_profile_complete(profile: TutorProfile) -> bool:
    """
    Determine if a tutor profile is complete.
    A profile is complete if full_name, qualifications, and subjects are provided.
    """
    if not profile:
        return False
    if not profile.full_name or not profile.full_name.strip():
        return False
    if not profile.qualifications or not profile.qualifications.strip():
        return False
    if not profile.subjects or not profile.subjects.strip():
        return False
    return True


def update_tutor_profile(
    db: Session,
    profile: TutorProfile,
    *,
    full_name: str,
    bio: str | None,
    qualifications: str,
    subjects: str,
    experience_years: int | None,
    profile_image_url: str | None,
    teaching_mode: str,
    location: str | None,
) -> TutorProfile:
    """
    Update a tutor's profile fields and recalculate is_profile_complete.
    """
    profile.full_name = full_name
    profile.bio = bio
    profile.qualifications = qualifications
    profile.subjects = subjects
    profile.experience_years = experience_years
    profile.profile_image_url = profile_image_url
    profile.teaching_mode = teaching_mode
    profile.location = location if location else None
    profile.subscription_active = teaching_mode in ("online", "both")

    # Recalculate completeness flag
    profile.is_profile_complete = check_profile_complete(profile)

    db.commit()
    db.refresh(profile)
    return profile


def get_tutor_profile_response(profile: TutorProfile, user: User) -> dict:
    """
    Build a JSON-serialisable dict for a tutor profile response.
    """
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "username": user.username,
        "email": user.email,
        "full_name": profile.full_name,
        "bio": profile.bio,
        "qualifications": profile.qualifications,
        "subjects": profile.subjects,
        "experience_years": profile.experience_years,
        "profile_image_url": profile.profile_image_url,
        "teaching_mode": profile.teaching_mode,
        "location": profile.location,
        "is_profile_complete": profile.is_profile_complete,
        "rating": profile.rating or 0.0,
        "total_students": profile.total_students or 0,
    }
