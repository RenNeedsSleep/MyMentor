"""
batch_router.py - API endpoints for Batch management.
Handles batch creation (tutor), browsing (student), joining (student), and membership viewing.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, Batch, BatchMember
from batch_schemas import BatchCreate, BatchResponse, BatchMemberResponse
from auth import decode_access_token
from services.batch_service import (
    create_batch, get_tutor_batches, get_all_batches,
    join_batch, get_batch_members, get_member_count
)

batch_router = APIRouter(tags=["Batches"])


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


# ==========================================================================
# TUTOR ENDPOINTS
# ==========================================================================

@batch_router.post("/batches/create")
async def create_batch_endpoint(
    data: BatchCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor creates a new batch."""
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can create batches.")

    batch = create_batch(
        db=db,
        tutor_id=user.id,
        name=data.name,
        description=data.description,
        scheduled_time=data.scheduled_time,
        max_students=data.max_students
    )

    return JSONResponse({
        "message": "Batch created successfully.",
        "batch": {
            "id": batch.id,
            "name": batch.name,
            "description": batch.description,
            "scheduled_time": batch.scheduled_time,
            "max_students": batch.max_students,
            "tutor_id": batch.tutor_id,
            "created_at": batch.created_at.isoformat()
        }
    })


@batch_router.get("/batches/my")
async def get_my_batches(
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor views all batches they created."""
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can view their own batches.")

    batches = get_tutor_batches(db, user.id)
    result = []
    for b in batches:
        count = get_member_count(db, b.id)
        result.append({
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "scheduled_time": b.scheduled_time,
            "max_students": b.max_students,
            "tutor_id": b.tutor_id,
            "tutor_name": user.username,
            "created_at": b.created_at.isoformat(),
            "member_count": count
        })

    return JSONResponse({"batches": result})


@batch_router.get("/batches/{batch_id}/members")
async def get_members_endpoint(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor (batch owner) views members of a batch."""
    user = _require_user(request, db)

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    if batch.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this batch.")

    members = get_batch_members(db, batch_id)
    result = []
    for m in members:
        student = db.query(User).filter(User.id == m.student_id).first()
        result.append({
            "id": m.id,
            "batch_id": m.batch_id,
            "student_id": m.student_id,
            "student_name": student.username if student else "Unknown",
            "joined_at": m.joined_at.isoformat()
        })

    return JSONResponse({"members": result})


# ==========================================================================
# STUDENT ENDPOINTS
# ==========================================================================

@batch_router.get("/batches/all")
async def get_all_batches_endpoint(
    request: Request,
    db: Session = Depends(get_db)
):
    """Student browses all available batches."""
    user = _require_user(request, db)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can browse batches.")

    batches = get_all_batches(db)
    result = []
    for b in batches:
        tutor = db.query(User).filter(User.id == b.tutor_id).first()
        count = get_member_count(db, b.id)
        result.append({
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "scheduled_time": b.scheduled_time,
            "max_students": b.max_students,
            "tutor_id": b.tutor_id,
            "tutor_name": tutor.username if tutor else "Unknown",
            "created_at": b.created_at.isoformat(),
            "member_count": count
        })

    return JSONResponse({"batches": result})


@batch_router.post("/batches/{batch_id}/join")
async def join_batch_endpoint(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Student joins a batch (with slot limit and duplicate checks)."""
    user = _require_user(request, db)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can join batches.")

    result = join_batch(db, batch_id, user.id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    member = result["member"]
    return JSONResponse({
        "message": "Successfully joined the batch.",
        "membership": {
            "id": member.id,
            "batch_id": member.batch_id,
            "student_id": member.student_id,
            "joined_at": member.joined_at.isoformat()
        }
    })
