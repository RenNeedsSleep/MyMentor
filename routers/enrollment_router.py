"""
enrollment_router.py - API endpoints for the Enrollment system.
Handles enrollment requests, approvals, rejections, fee overrides, and fee locking.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, Batch, Enrollment
from schemas.enrollment_schemas import (
    EnrollmentRequest, EnrollmentAction, FeeOverrideUpdate, FeeLockUpdate
)
from auth import decode_access_token
from services.enrollment_service import (
    request_enrollment, process_enrollment_action,
    update_fee_override, update_fee_lock,
    get_batch_enrollments, get_student_enrollments,
    get_pending_enrollments_for_tutor, get_approved_enrollment_count
)

enrollment_router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


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


def _build_enrollment_response(enrollment: Enrollment, db: Session) -> dict:
    """Build a response dict for an enrollment, including computed fields."""
    student = db.query(User).filter(User.id == enrollment.student_id).first()
    batch = db.query(Batch).filter(Batch.id == enrollment.batch_id).first()

    # Compute final_fee
    final_fee = enrollment.fee_override if enrollment.fee_override is not None else (
        batch.base_fee if batch else 0.0
    )

    return {
        "id": enrollment.id,
        "student_id": enrollment.student_id,
        "student_username": student.username if student else None,
        "student_profile_image_url": student.profile_image_url if student else None,
        "batch_id": enrollment.batch_id,
        "batch_name": batch.name if batch else None,
        "status": enrollment.status,
        "fee_override": enrollment.fee_override,
        "fee_locked": enrollment.fee_locked,
        "final_fee": final_fee,
        "request_status": enrollment.request_status,
        "joined_at": enrollment.joined_at.isoformat()
    }


# ==========================================================================
# STUDENT: Request enrollment
# ==========================================================================

@enrollment_router.post("/request")
async def request_enrollment_endpoint(
    data: EnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Student requests to join a batch. Tutor will be notified."""
    user = _require_user(request, db)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can request enrollment.")

    result = request_enrollment(db, user.id, data.batch_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    enrollment = result["enrollment"]
    return JSONResponse({
        "message": "Enrollment request submitted. Waiting for tutor approval.",
        "enrollment": _build_enrollment_response(enrollment, db)
    })


# ==========================================================================
# STUDENT: View my enrollments
# ==========================================================================

@enrollment_router.get("/my")
async def get_my_enrollments(
    request: Request,
    db: Session = Depends(get_db)
):
    """Student views all their enrollment records."""
    user = _require_user(request, db)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can view their enrollments.")

    enrollments = get_student_enrollments(db, user.id)
    result = [_build_enrollment_response(e, db) for e in enrollments]
    return JSONResponse({"enrollments": result, "total": len(result)})


# ==========================================================================
# TUTOR: View pending enrollment requests
# ==========================================================================

@enrollment_router.get("/pending")
async def get_pending_enrollments(
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor views all pending enrollment requests for their batches."""
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can view pending enrollments.")

    enrollments = get_pending_enrollments_for_tutor(db, user.id)
    result = [_build_enrollment_response(e, db) for e in enrollments]
    return JSONResponse({"enrollments": result, "total": len(result)})


# ==========================================================================
# TUTOR: View enrollments for a specific batch
# ==========================================================================

@enrollment_router.get("/batch/{batch_id}")
async def get_batch_enrollments_endpoint(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor views all enrollments for a specific batch they own."""
    user = _require_user(request, db)

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    if batch.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this batch.")

    enrollments = get_batch_enrollments(db, batch_id)
    result = [_build_enrollment_response(e, db) for e in enrollments]
    return JSONResponse({"enrollments": result, "total": len(result)})


# ==========================================================================
# TUTOR: Approve / Reject enrollment
# ==========================================================================

@enrollment_router.post("/action")
async def enrollment_action_endpoint(
    data: EnrollmentAction,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor approves or rejects an enrollment request."""
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can approve/reject enrollments.")

    result = process_enrollment_action(db, data.enrollment_id, user.id, data.action)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    enrollment = result["enrollment"]
    action_word = "approved" if data.action == "approve" else "rejected"
    return JSONResponse({
        "message": f"Enrollment {action_word} successfully.",
        "enrollment": _build_enrollment_response(enrollment, db)
    })


# ==========================================================================
# TUTOR: Set fee override
# ==========================================================================

@enrollment_router.put("/fee-override")
async def set_fee_override_endpoint(
    data: FeeOverrideUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor sets/updates a custom fee for a student in a batch."""
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can set fee overrides.")

    result = update_fee_override(db, data.enrollment_id, user.id, data.fee_override)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    enrollment = result["enrollment"]
    return JSONResponse({
        "message": "Fee override updated successfully.",
        "enrollment": _build_enrollment_response(enrollment, db)
    })


# ==========================================================================
# TUTOR: Lock/unlock fee
# ==========================================================================

@enrollment_router.put("/fee-lock")
async def set_fee_lock_endpoint(
    data: FeeLockUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Tutor locks or unlocks the fee for a student enrollment."""
    user = _require_user(request, db)
    if user.role != "tutor":
        raise HTTPException(status_code=403, detail="Only tutors can lock/unlock fees.")

    result = update_fee_lock(db, data.enrollment_id, user.id, data.fee_locked)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    enrollment = result["enrollment"]
    lock_word = "locked" if data.fee_locked else "unlocked"
    return JSONResponse({
        "message": f"Fee {lock_word} successfully.",
        "enrollment": _build_enrollment_response(enrollment, db)
    })
