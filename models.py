"""
models.py - SQLAlchemy ORM models for MyMentor
Defines all database tables: User, TutorProfile, AvailabilitySlot, Booking, Recording
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Text, DateTime, UniqueConstraint, Float
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    """
    User table - stores both students and tutors.
    The 'role' field differentiates between them.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)                        

    
    tutor_profile = relationship("TutorProfile", back_populates="user", uselist=False)
    bookings = relationship("Booking", back_populates="student")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")

    # --- New relationships for Batch system (non-breaking additions) ---
    owned_batches = relationship("Batch", back_populates="tutor")
    batch_memberships = relationship("BatchMember", back_populates="student")


class TutorProfile(Base):
    """
    TutorProfile - additional info for users who are tutors.
    Linked one-to-one with User.
    """
    __tablename__ = "tutor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    qualifications = Column(Text, nullable=True)
    subjects = Column(String(500), nullable=True)                            
    teaching_mode = Column(String(20), nullable=False, default="both")                               
    location = Column(String(255), nullable=True)                             
    subscription_active = Column(Boolean, default=False)                              

    # --- New fields for tutor safety / quality (non-breaking additions) ---
    full_name = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    experience_years = Column(Integer, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    certificate_file_path = Column(String(500), nullable=True)
    is_profile_complete = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    total_students = Column(Integer, default=0)

    
    user = relationship("User", back_populates="tutor_profile")
    availability_slots = relationship("AvailabilitySlot", back_populates="tutor")
    bookings = relationship("Booking", back_populates="tutor")


class AvailabilitySlot(Base):
    """
    AvailabilitySlot - time blocks when a tutor is available.
    Tutors create these; students book them.
    """
    __tablename__ = "availability_slots"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("tutor_profiles.id"), nullable=False)
    date = Column(String(20), nullable=False)                     
    start_time = Column(String(10), nullable=False)                
    end_time = Column(String(10), nullable=False)                
    is_booked = Column(Boolean, default=False)

    
    tutor = relationship("TutorProfile", back_populates="availability_slots")
    booking = relationship("Booking", back_populates="slot", uselist=False)


class Booking(Base):
    """
    Booking - a confirmed session between a student and tutor.
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tutor_id = Column(Integer, ForeignKey("tutor_profiles.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("availability_slots.id"), nullable=False)
    mode = Column(String(20), nullable=False)  
    status = Column(String(20), default="scheduled")  

    
    student = relationship("User", back_populates="bookings")
    tutor = relationship("TutorProfile", back_populates="bookings")
    slot = relationship("AvailabilitySlot", back_populates="booking")
    recording = relationship("Recording", back_populates="booking", uselist=False)


class Recording(Base):
    """
    Recording - link to a recorded session.
    Tutors add these after completing an online session.
    """
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    video_link = Column(String(500), nullable=False)

    
    booking = relationship("Booking", back_populates="recording")


class Message(Base):
    """
    Message - direct messages between users (tutor-student communication).
    Used for pre-session queries and doubt solving.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_read = Column(Boolean, default=False)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


# =============================================================================
# NEW MODELS — Batch System, Video Sessions, Study Materials
# =============================================================================

class Batch(Base):
    """
    Batch - a scheduled class group created by a tutor.
    Students can browse and join batches.
    """
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_time = Column(String(100), nullable=False)
    max_students = Column(Integer, nullable=False, default=30)
    tutor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tutor = relationship("User", back_populates="owned_batches")
    members = relationship("BatchMember", back_populates="batch", cascade="all, delete-orphan")
    video_sessions = relationship("VideoSession", back_populates="batch", cascade="all, delete-orphan")


class BatchMember(Base):
    """
    BatchMember - tracks which students have joined which batches.
    A student cannot join the same batch twice (unique constraint).
    """
    __tablename__ = "batch_members"
    __table_args__ = (
        UniqueConstraint("batch_id", "student_id", name="uq_batch_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("Batch", back_populates="members")
    student = relationship("User", back_populates="batch_memberships")


class VideoSession(Base):
    """
    VideoSession - a recorded/live session linked to a batch.
    Replaces the concept of standalone recordings for batch-based content.
    """
    __tablename__ = "video_sessions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("Batch", back_populates="video_sessions")
    materials = relationship("SessionMaterial", back_populates="session", cascade="all, delete-orphan")


class SessionMaterial(Base):
    """
    SessionMaterial - study resources (PDFs, docs, etc.) attached to a video session.
    """
    __tablename__ = "session_materials"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("video_sessions.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False, default="pdf")
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("VideoSession", back_populates="materials")
