"""
enrollment_service.py - Business logic for the Enrollment system.
Handles enrollment requests, approvals, rejections, fee overrides, and fee locking.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional

from models import Enrollment, Batch, User, Notification


def request_enrollment(db: Session, student_id: int, batch_id: int) -> dict:
    """
    Student requests to join a batch.
    Checks: batch exists, batch is active, no duplicate enrollment, batch not full.
    Creates a notification for the tutor.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return {"success": False, "error": "Batch not found."}

    if not batch.is_active:
        return {"success": False, "error": "This batch is no longer active."}

    # Check duplicate enrollment
    existing = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.batch_id == batch_id
    ).first()
    if existing:
        return {"success": False, "error": "You have already requested to join this batch."}

    # Check capacity (count only approved enrollments)
    approved_count = db.query(func.count(Enrollment.id)).filter(
        Enrollment.batch_id == batch_id,
        Enrollment.status == "approved"
    ).scalar()
    if approved_count >= batch.max_students:
        return {"success": False, "error": "This batch is full."}

    enrollment = Enrollment(
        student_id=student_id,
        batch_id=batch_id,
        status="pending",
        request_status="pending",
        joined_at=datetime.utcnow()
    )
    db.add(enrollment)

    # Notify the tutor
    student = db.query(User).filter(User.id == student_id).first()
    student_name = student.username if student else "A student"
    notification = Notification(
        user_id=batch.tutor_id,
        message=f"{student_name} has requested to join your batch '{batch.name}'.",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notification)

    db.commit()
    db.refresh(enrollment)
    return {"success": True, "enrollment": enrollment}


def process_enrollment_action(
    db: Session, enrollment_id: int, tutor_id: int, action: str
) -> dict:
    """
    Tutor approves or rejects an enrollment request.
    Only the batch owner can perform this action.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        return {"success": False, "error": "Enrollment not found."}

    batch = db.query(Batch).filter(Batch.id == enrollment.batch_id).first()
    if not batch:
        return {"success": False, "error": "Batch not found."}

    if batch.tutor_id != tutor_id:
        return {"success": False, "error": "You do not own this batch."}

    if enrollment.status != "pending":
        return {"success": False, "error": f"Enrollment is already '{enrollment.status}'."}

    if action == "approve":
        # Check capacity before approving
        approved_count = db.query(func.count(Enrollment.id)).filter(
            Enrollment.batch_id == enrollment.batch_id,
            Enrollment.status == "approved"
        ).scalar()
        if approved_count >= batch.max_students:
            return {"success": False, "error": "Batch is full. Cannot approve more students."}

        enrollment.status = "approved"
        enrollment.request_status = "approved"

        # Notify the student
        notification = Notification(
            user_id=enrollment.student_id,
            message=f"Your request to join batch '{batch.name}' has been approved!",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notification)

    elif action == "reject":
        enrollment.status = "rejected"
        enrollment.request_status = "rejected"

        # Notify the student
        notification = Notification(
            user_id=enrollment.student_id,
            message=f"Your request to join batch '{batch.name}' has been rejected.",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notification)

    db.commit()
    db.refresh(enrollment)
    return {"success": True, "enrollment": enrollment}


def update_fee_override(
    db: Session, enrollment_id: int, tutor_id: int, fee_override: float
) -> dict:
    """
    Tutor sets or updates a custom fee for a student in a batch.
    Cannot update if fee is locked.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        return {"success": False, "error": "Enrollment not found."}

    batch = db.query(Batch).filter(Batch.id == enrollment.batch_id).first()
    if not batch or batch.tutor_id != tutor_id:
        return {"success": False, "error": "You do not own this batch."}

    if enrollment.fee_locked:
        return {"success": False, "error": "Fee is locked and cannot be modified."}

    enrollment.fee_override = fee_override
    db.commit()
    db.refresh(enrollment)

    # Notify the student about fee change
    notification = Notification(
        user_id=enrollment.student_id,
        message=f"Your fee for batch '{batch.name}' has been updated to {fee_override}.",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()

    return {"success": True, "enrollment": enrollment}


def update_fee_lock(
    db: Session, enrollment_id: int, tutor_id: int, fee_locked: bool
) -> dict:
    """
    Tutor locks or unlocks the fee for a student enrollment.
    """
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        return {"success": False, "error": "Enrollment not found."}

    batch = db.query(Batch).filter(Batch.id == enrollment.batch_id).first()
    if not batch or batch.tutor_id != tutor_id:
        return {"success": False, "error": "You do not own this batch."}

    enrollment.fee_locked = fee_locked
    db.commit()
    db.refresh(enrollment)
    return {"success": True, "enrollment": enrollment}


def get_batch_enrollments(db: Session, batch_id: int) -> list:
    """Get all enrollments for a batch."""
    return db.query(Enrollment).filter(
        Enrollment.batch_id == batch_id
    ).order_by(Enrollment.joined_at.desc()).all()


def get_student_enrollments(db: Session, student_id: int) -> list:
    """Get all enrollments for a student."""
    return db.query(Enrollment).filter(
        Enrollment.student_id == student_id
    ).order_by(Enrollment.joined_at.desc()).all()


def get_pending_enrollments_for_tutor(db: Session, tutor_id: int) -> list:
    """Get all pending enrollment requests for batches owned by the tutor."""
    return db.query(Enrollment).join(
        Batch, Batch.id == Enrollment.batch_id
    ).filter(
        Batch.tutor_id == tutor_id,
        Enrollment.status == "pending"
    ).order_by(Enrollment.joined_at.desc()).all()


def get_approved_enrollment_count(db: Session, batch_id: int) -> int:
    """Count approved enrollments for a batch."""
    return db.query(func.count(Enrollment.id)).filter(
        Enrollment.batch_id == batch_id,
        Enrollment.status == "approved"
    ).scalar()


def is_student_approved_in_batch(db: Session, student_id: int, batch_id: int) -> bool:
    """Check if a student has an approved enrollment in a batch."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.batch_id == batch_id,
        Enrollment.status == "approved"
    ).first()
    return enrollment is not None
