"""
batch_service.py - Business logic for Batch management.
Handles batch creation, listing, joining, and membership queries.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from models import Batch, BatchMember, User


def create_batch(db: Session, tutor_id: int, name: str, description: str,
                 scheduled_time: str, max_students: int) -> Batch:
    """Create a new batch owned by the given tutor."""
    batch = Batch(
        name=name,
        description=description,
        scheduled_time=scheduled_time,
        max_students=max_students,
        tutor_id=tutor_id,
        created_at=datetime.utcnow()
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def get_tutor_batches(db: Session, tutor_id: int) -> list:
    """Return all batches created by a specific tutor, with member counts."""
    batches = db.query(Batch).filter(Batch.tutor_id == tutor_id).order_by(
        Batch.created_at.desc()
    ).all()
    return batches


def get_all_batches(db: Session) -> list:
    """Return all batches (for student browsing)."""
    batches = db.query(Batch).order_by(Batch.created_at.desc()).all()
    return batches


def join_batch(db: Session, batch_id: int, student_id: int) -> dict:
    """
    Try to add a student to a batch. Returns a dict with status info.

    Checks:
    1. Batch exists
    2. Student hasn't already joined
    3. Batch is not full
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return {"success": False, "error": "Batch not found."}

    # Check for duplicate membership
    existing = db.query(BatchMember).filter(
        BatchMember.batch_id == batch_id,
        BatchMember.student_id == student_id
    ).first()
    if existing:
        return {"success": False, "error": "You have already joined this batch."}

    # Check slot availability
    current_count = db.query(func.count(BatchMember.id)).filter(
        BatchMember.batch_id == batch_id
    ).scalar()
    if current_count >= batch.max_students:
        return {"success": False, "error": "This batch is full."}

    member = BatchMember(
        batch_id=batch_id,
        student_id=student_id,
        joined_at=datetime.utcnow()
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"success": True, "member": member}


def get_batch_members(db: Session, batch_id: int) -> list:
    """Return all members of a batch."""
    members = db.query(BatchMember).filter(
        BatchMember.batch_id == batch_id
    ).order_by(BatchMember.joined_at.asc()).all()
    return members


def get_member_count(db: Session, batch_id: int) -> int:
    """Return the number of students in a batch."""
    return db.query(func.count(BatchMember.id)).filter(
        BatchMember.batch_id == batch_id
    ).scalar()
