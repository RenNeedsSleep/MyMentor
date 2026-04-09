"""
messaging_access.py - Batch-based messaging permission check.
Updated to support mode-based access control:
- If batch.mode == "online": allow ONLY if enrollment.status == "approved"
- If batch.mode == "offline" or "both": allow regardless of enrollment
- Tutors can always reply to anyone who messages them
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import Batch, Enrollment


def check_batch_relationship(db: Session, student_id: int, tutor_id: int) -> bool:
    """
    Check whether a student can message a tutor based on batch enrollment rules.

    Rules:
    - If ANY shared batch has mode == "offline" or "both": messaging is allowed.
    - If ALL shared batches have mode == "online": student must be "approved" in
      at least one of them.
    - If no shared batches at all: messaging is NOT allowed.
    """
    # Get all batches owned by the tutor
    tutor_batches = db.query(Batch).filter(Batch.tutor_id == tutor_id).all()
    if not tutor_batches:
        return False

    for batch in tutor_batches:
        # Check if student has any enrollment in this batch
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.batch_id == batch.id
        ).first()

        if batch.mode in ("offline", "both"):
            # Messaging allowed regardless of enrollment status
            if enrollment is not None:
                return True
        elif batch.mode == "online":
            # Messaging allowed only if approved
            if enrollment and enrollment.status == "approved":
                return True

    # Fallback: check legacy BatchMember table for backward compat
    from models import BatchMember
    legacy_shared = db.query(Batch).join(
        BatchMember, BatchMember.batch_id == Batch.id
    ).filter(
        and_(
            Batch.tutor_id == tutor_id,
            BatchMember.student_id == student_id
        )
    ).first()

    return legacy_shared is not None
