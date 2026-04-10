"""
performance_router.py - API endpoints for Performance Tracking and Analytics.
Handles creating performance records (tutor), viewing records (student),
and computing graph-ready analytics.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import User, Batch, PerformanceRecord
from schemas.performance_schemas import PerformanceRecordCreate
from auth import decode_access_token
from services.performance_service import (
    create_performance_record,
    get_student_performance_records,
    get_student_analytics
)

performance_router = APIRouter(tags=["Performance"])


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


def _build_record_response(record: PerformanceRecord, db: Session) -> dict:
    """Build a response dict for a performance record."""
    batch = db.query(Batch).filter(Batch.id == record.batch_id).first()
    return {
        "id": record.id,
        "student_id": record.student_id,
        "tutor_id": record.tutor_id,
        "batch_id": record.batch_id,
        "batch_name": batch.name if batch else None,
        "rating": record.rating,
        "score": record.score,
        "tutor_note": record.tutor_note,
        "session_date": record.session_date.isoformat() if record.session_date else None,
        "created_at": record.created_at.isoformat()
    }


# ==========================================================================
# TUTOR: Create performance record
# ==========================================================================

@performance_router.post("/performance")
async def create_performance_endpoint(
    data: PerformanceRecordCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Tutor creates a performance record for a student in their batch.
    Only the batch owner can create records.
    """
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can create performance records.")

    result = create_performance_record(
        db=db,
        tutor_id=user.id,
        student_id=data.student_id,
        batch_id=data.batch_id,
        rating=data.rating,
        tutor_note=data.tutor_note,
        session_date=data.session_date
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    record = result["record"]
    return JSONResponse({
        "message": "Performance record created successfully.",
        "record": _build_record_response(record, db)
    })


# ==========================================================================
# STUDENT: View own performance records
# ==========================================================================

@performance_router.get("/performance/my")
async def get_my_performance(
    request: Request,
    batch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Student views their own performance records.
    Optionally filter by batch_id.
    """
    user = _require_user(request, db)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can view their performance.")

    records = get_student_performance_records(db, user.id, batch_id)
    result = [_build_record_response(r, db) for r in records]
    return JSONResponse({"records": result, "total": len(result)})


# ==========================================================================
# TUTOR: View performance records for a student in their batch
# ==========================================================================

@performance_router.get("/performance/batch/{batch_id}/student/{student_id}")
async def get_student_performance_in_batch(
    batch_id: int,
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Tutor views performance records for a student in a specific batch they own.
    """
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can view student performance.")

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    if batch.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this batch.")

    records = get_student_performance_records(db, student_id, batch_id)
    result = [_build_record_response(r, db) for r in records]
    return JSONResponse({"records": result, "total": len(result)})


# ==========================================================================
# ANALYTICS: Graph-ready endpoint
# ==========================================================================

@performance_router.get("/students/{student_id}/analytics")
async def get_analytics_endpoint(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    GET /students/{student_id}/analytics

    Returns graph-ready analytics for a student:
    1. Rating Distribution: {"excellent": count, "great": count, ...}
    2. Performance Trend: [{"date": "YYYY-MM-DD", "score": number}, ...]
    3. Average Score: {"average_score": float}

    Access: The student themselves, or a tutor who has a batch with this student.
    """
    user = _require_user(request, db)

    # Access control: student can view own, tutor can view enrolled students
    if user.role == "student" and user.id != student_id:
        raise HTTPException(
            status_code=403,
            detail="Students can only view their own analytics."
        )

    if user.role == "tutor":
        # Verify the tutor has at least one batch with this student
        from models import Enrollment
        has_student = db.query(Enrollment).join(
            Batch, Batch.id == Enrollment.batch_id
        ).filter(
            Batch.tutor_id == user.id,
            Enrollment.student_id == student_id,
            Enrollment.status == "approved"
        ).first()
        if not has_student:
            raise HTTPException(
                status_code=403,
                detail="You can only view analytics for students enrolled in your batches."
            )

    analytics = get_student_analytics(db, student_id)
    return JSONResponse(analytics)
