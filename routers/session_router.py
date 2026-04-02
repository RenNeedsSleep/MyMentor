"""
session_router.py - API endpoints for VideoSession and SessionMaterial management.
Handles creating sessions (tutor), viewing sessions (batch members), and uploading materials.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, Batch, BatchMember, VideoSession
from batch_schemas import VideoSessionCreate, SessionMaterialCreate
from auth import decode_access_token
from services.session_service import (
    create_video_session, get_batch_sessions,
    add_session_material, get_session_materials
)

session_router = APIRouter(tags=["Video Sessions"])


# ---------------------------------------------------------------------------
# Helper: reuse the same cookie-based auth pattern from main.py
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


def _require_user(request: Request, db: Session) -> User:
    """Same as above but raises 401 if not authenticated."""
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


def _is_batch_member(db: Session, batch_id: int, user_id: int) -> bool:
    """Check if a user is a member of a given batch."""
    return db.query(BatchMember).filter(
        BatchMember.batch_id == batch_id,
        BatchMember.student_id == user_id
    ).first() is not None


# ==========================================================================
# TUTOR ENDPOINTS
# ==========================================================================

@session_router.post("/batches/{batch_id}/add-session")
async def add_session_endpoint(
    batch_id: int,
    data: VideoSessionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor adds a video session to a batch they own."""
    user = _require_user(request, db)

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    if batch.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this batch.")

    session = create_video_session(
        db=db,
        batch_id=batch_id,
        title=data.title,
        description=data.description,
        video_url=data.video_url
    )

    return JSONResponse({
        "message": "Video session added successfully.",
        "session": {
            "id": session.id,
            "batch_id": session.batch_id,
            "title": session.title,
            "description": session.description,
            "video_url": session.video_url,
            "created_at": session.created_at.isoformat()
        }
    })


@session_router.post("/sessions/{session_id}/upload-material")
async def upload_material_endpoint(
    session_id: int,
    data: SessionMaterialCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor uploads study material to a video session they own (via batch)."""
    user = _require_user(request, db)

    session_obj = db.query(VideoSession).filter(VideoSession.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Video session not found.")

    batch = db.query(Batch).filter(Batch.id == session_obj.batch_id).first()
    if not batch or batch.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this session's batch.")

    material = add_session_material(
        db=db,
        session_id=session_id,
        file_url=data.file_url,
        file_type=data.file_type
    )

    return JSONResponse({
        "message": "Material uploaded successfully.",
        "material": {
            "id": material.id,
            "session_id": material.session_id,
            "file_url": material.file_url,
            "file_type": material.file_type,
            "uploaded_at": material.uploaded_at.isoformat()
        }
    })


# ==========================================================================
# SHARED / STUDENT ENDPOINTS
# ==========================================================================

@session_router.get("/batches/{batch_id}/sessions")
async def get_sessions_endpoint(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    List video sessions for a batch.
    Accessible by: batch owner (tutor) OR enrolled students.
    """
    user = _require_user(request, db)

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    # Access check: must be the tutor OR a batch member
    is_owner = (batch.tutor_id == user.id)
    is_member = _is_batch_member(db, batch_id, user.id)

    if not is_owner and not is_member:
        raise HTTPException(
            status_code=403,
            detail="You must be enrolled in this batch to view sessions."
        )

    sessions = get_batch_sessions(db, batch_id)
    result = []
    for s in sessions:
        materials = [
            {
                "id": m.id,
                "session_id": m.session_id,
                "file_url": m.file_url,
                "file_type": m.file_type,
                "uploaded_at": m.uploaded_at.isoformat()
            }
            for m in s.materials
        ]
        result.append({
            "id": s.id,
            "batch_id": s.batch_id,
            "title": s.title,
            "description": s.description,
            "video_url": s.video_url,
            "created_at": s.created_at.isoformat(),
            "materials": materials
        })

    return JSONResponse({"sessions": result})


@session_router.get("/sessions/{session_id}/materials")
async def get_materials_endpoint(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    List materials for a video session.
    Accessible by: batch owner (tutor) OR enrolled students.
    """
    user = _require_user(request, db)

    session_obj = db.query(VideoSession).filter(VideoSession.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Video session not found.")

    batch = db.query(Batch).filter(Batch.id == session_obj.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    is_owner = (batch.tutor_id == user.id)
    is_member = _is_batch_member(db, batch_id=batch.id, user_id=user.id)

    if not is_owner and not is_member:
        raise HTTPException(
            status_code=403,
            detail="You must be enrolled in this batch to view materials."
        )

    materials = get_session_materials(db, session_id)
    result = [
        {
            "id": m.id,
            "session_id": m.session_id,
            "file_url": m.file_url,
            "file_type": m.file_type,
            "uploaded_at": m.uploaded_at.isoformat()
        }
        for m in materials
    ]

    return JSONResponse({"materials": result})
