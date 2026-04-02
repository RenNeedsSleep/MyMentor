"""
messaging_access.py - Batch-based messaging permission check.
A student can ONLY message a tutor if they share at least one batch.
This is a reusable function that can be called from any route or dependency.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import Batch, BatchMember


def check_batch_relationship(db: Session, student_id: int, tutor_id: int) -> bool:
    """
    Check whether a student and a tutor share at least one batch.

    A relationship exists if:
    - The tutor owns a batch AND
    - The student is a member of that same batch

    Returns True if they share at least one batch, False otherwise.
    """
    shared = db.query(Batch).join(
        BatchMember, BatchMember.batch_id == Batch.id
    ).filter(
        and_(
            Batch.tutor_id == tutor_id,
            BatchMember.student_id == student_id
        )
    ).first()

    return shared is not None
