"""
performance_service.py - Business logic for the Performance Tracking system.
Handles creating records, viewing records, and computing analytics.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime
from typing import Optional

from models import PerformanceRecord, Batch, Enrollment, User
from schemas.performance_schemas import RATING_SCORE_MAP


def create_performance_record(
    db: Session,
    tutor_id: int,
    student_id: int,
    batch_id: int,
    rating: str,
    tutor_note: Optional[str],
    session_date,
) -> dict:
    """
    Tutor creates a performance record for a student in their batch.
    Validates: tutor owns the batch, student is enrolled (approved).
    """
    # Validate batch ownership
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return {"success": False, "error": "Batch not found."}
    if batch.tutor_id != tutor_id:
        return {"success": False, "error": "You do not own this batch."}

    # Validate student is enrolled and approved
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.batch_id == batch_id,
        Enrollment.status == "approved"
    ).first()
    if not enrollment:
        return {"success": False, "error": "Student is not approved in this batch."}

    # Derive score from rating
    rating_lower = rating.lower().strip()
    score = RATING_SCORE_MAP.get(rating_lower)
    if score is None:
        return {"success": False, "error": f"Invalid rating: {rating}"}

    record = PerformanceRecord(
        student_id=student_id,
        tutor_id=tutor_id,
        batch_id=batch_id,
        rating=rating_lower,
        score=score,
        tutor_note=tutor_note,
        session_date=session_date,
        created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "record": record}


def get_student_performance_records(
    db: Session, student_id: int, batch_id: Optional[int] = None
) -> list:
    """
    Get performance records for a student, optionally filtered by batch.
    """
    query = db.query(PerformanceRecord).filter(
        PerformanceRecord.student_id == student_id
    )
    if batch_id:
        query = query.filter(PerformanceRecord.batch_id == batch_id)
    return query.order_by(PerformanceRecord.session_date.desc()).all()


def get_student_analytics(db: Session, student_id: int) -> dict:
    """
    Compute graph-ready analytics for a student.
    Returns: rating_distribution, performance_trend, average_score.
    Uses efficient SQL aggregation queries.
    """
    # 1. Rating Distribution — single aggregation query
    distribution_query = db.query(
        PerformanceRecord.rating,
        func.count(PerformanceRecord.id).label("count")
    ).filter(
        PerformanceRecord.student_id == student_id
    ).group_by(
        PerformanceRecord.rating
    ).all()

    rating_distribution = {
        "excellent": 0,
        "great": 0,
        "good": 0,
        "satisfactory": 0,
    }
    for rating, count in distribution_query:
        if rating in rating_distribution:
            rating_distribution[rating] = count

    # 2. Performance Trend (time series) — ordered by date
    # Group by session_date and average the scores for that day
    trend_query = db.query(
        PerformanceRecord.session_date,
        func.avg(PerformanceRecord.score).label("avg_score")
    ).filter(
        PerformanceRecord.student_id == student_id
    ).group_by(
        PerformanceRecord.session_date
    ).order_by(
        PerformanceRecord.session_date.asc()
    ).all()

    performance_trend = []
    for session_date, avg_score in trend_query:
        date_str = session_date.isoformat() if hasattr(session_date, 'isoformat') else str(session_date)
        performance_trend.append({
            "date": date_str,
            "score": round(float(avg_score), 2)
        })

    # 3. Average Score — single aggregation
    avg_result = db.query(
        func.avg(PerformanceRecord.score)
    ).filter(
        PerformanceRecord.student_id == student_id
    ).scalar()

    average_score = round(float(avg_result), 2) if avg_result is not None else 0.0

    return {
        "student_id": student_id,
        "rating_distribution": rating_distribution,
        "performance_trend": performance_trend,
        "average_score": {"average_score": average_score}
    }
