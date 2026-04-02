"""
session_service.py - Business logic for VideoSession and SessionMaterial management.
Handles creating sessions, listing them, and attaching study materials.
"""

from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from models import VideoSession, SessionMaterial, Batch


def create_video_session(db: Session, batch_id: int, title: str,
                         description: str, video_url: str) -> VideoSession:
    """Create a new video session linked to a batch."""
    session = VideoSession(
        batch_id=batch_id,
        title=title,
        description=description,
        video_url=video_url,
        created_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_batch_sessions(db: Session, batch_id: int) -> list:
    """Return all video sessions for a batch, including their materials."""
    sessions = db.query(VideoSession).filter(
        VideoSession.batch_id == batch_id
    ).options(
        joinedload(VideoSession.materials)
    ).order_by(VideoSession.created_at.desc()).all()
    return sessions


def add_session_material(db: Session, session_id: int, file_url: str,
                         file_type: str) -> SessionMaterial:
    """Attach a study material (PDF, doc, etc.) to a video session."""
    material = SessionMaterial(
        session_id=session_id,
        file_url=file_url,
        file_type=file_type,
        uploaded_at=datetime.utcnow()
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def get_session_materials(db: Session, session_id: int) -> list:
    """Return all materials for a given session."""
    return db.query(SessionMaterial).filter(
        SessionMaterial.session_id == session_id
    ).order_by(SessionMaterial.uploaded_at.asc()).all()
