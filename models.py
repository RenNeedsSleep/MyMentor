"""
models.py - SQLAlchemy ORM models for MyMentor
Defines all database tables: User, TutorProfile, AvailabilitySlot, Booking, Recording,
Message, Batch, Enrollment, PerformanceRecord, Notification, VideoSession, SessionMaterial
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Text, DateTime,
    UniqueConstraint, Float, Date, Index
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
    role = Column(String(20), nullable=False)  # "student" or "tutor"
    profile_image_url = Column(String(500), nullable=True)

    # Relationships
    tutor_profile = relationship("TutorProfile", back_populates="user", uselist=False)
    bookings = relationship("Booking", back_populates="student")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")

    # Batch system relationships
    owned_batches = relationship("Batch", back_populates="tutor")
    batch_memberships = relationship("BatchMember", back_populates="student")

    # Enrollment system relationships
    enrollments = relationship("Enrollment", back_populates="student", foreign_keys="Enrollment.student_id")

    # Performance relationships
    performance_records_as_student = relationship(
        "PerformanceRecord", back_populates="student",
        foreign_keys="PerformanceRecord.student_id"
    )
    performance_records_as_tutor = relationship(
        "PerformanceRecord", back_populates="tutor",
        foreign_keys="PerformanceRecord.tutor_id"
    )

    # Notification relationships
    notifications = relationship("Notification", back_populates="user")


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
    teaching_mode = Column(String(20), nullable=False, default="both")  # online/offline/both
    location = Column(String(255), nullable=True)
    subscription_active = Column(Boolean, default=False)

    # Extended profile fields
    full_name = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    experience_years = Column(Integer, nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    certificate_file_path = Column(String(500), nullable=True)
    is_profile_complete = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    total_students = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="tutor_profile")
    availability_slots = relationship("AvailabilitySlot", back_populates="tutor")
    bookings = relationship("Booking", back_populates="tutor")


class AvailabilitySlot(Base):
    """
    AvailabilitySlot - time blocks when a tutor is available.
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
    """
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    video_link = Column(String(500), nullable=False)

    booking = relationship("Booking", back_populates="recording")


class Message(Base):
    """
    Message - direct messages between users (tutor-student communication).
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
# BATCH SYSTEM — Updated with subject, base_fee, mode, is_active
# =============================================================================

class Batch(Base):
    """
    Batch - a scheduled class group created by a tutor.
    Central entity for the enrollment-based learning system.
    """
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    schedule = Column(Text, nullable=True)  # TEXT for flexible schedule representation
    scheduled_time = Column(String(100), nullable=True)  # legacy compat
    base_fee = Column(Float, nullable=False, default=0.0)
    mode = Column(String(20), nullable=False, default="both")  # "online", "offline", "both"
    max_students = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tutor = relationship("User", back_populates="owned_batches")
    members = relationship("BatchMember", back_populates="batch", cascade="all, delete-orphan")
    video_sessions = relationship("VideoSession", back_populates="batch", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="batch", cascade="all, delete-orphan")
    performance_records = relationship("PerformanceRecord", back_populates="batch", cascade="all, delete-orphan")


class BatchMember(Base):
    """
    BatchMember - legacy membership tracking (kept for backward compat).
    New enrollment flow uses Enrollment model instead.
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


# =============================================================================
# ENROLLMENT SYSTEM — Approval-based with fee override
# =============================================================================

class Enrollment(Base):
    """
    Enrollment - approval-based enrollment for students in batches.
    Students request to join, tutors approve/reject.
    Supports per-student fee customization.
    """
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "batch_id", name="uq_enrollment_student_batch"),
        Index("ix_enrollment_student_id", "student_id"),
        Index("ix_enrollment_batch_id", "batch_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected
    fee_override = Column(Float, nullable=True)  # custom fee per student per batch
    fee_locked = Column(Boolean, default=False)  # prevent further fee edits
    request_status = Column(String(20), nullable=False, default="pending")  # none, pending, approved, rejected
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student = relationship("User", back_populates="enrollments", foreign_keys=[student_id])
    batch = relationship("Batch", back_populates="enrollments")

    @property
    def final_fee(self):
        """Computed: returns fee_override if set, otherwise the batch base_fee."""
        if self.fee_override is not None:
            return self.fee_override
        if self.batch:
            return self.batch.base_fee
        return 0.0


# =============================================================================
# PERFORMANCE TRACKING SYSTEM
# =============================================================================

class PerformanceRecord(Base):
    """
    PerformanceRecord - tutor-assigned student performance records.
    Tracks ratings, scores, and tutor notes per session date.
    """
    __tablename__ = "performance_records"
    __table_args__ = (
        Index("ix_perf_student_id", "student_id"),
        Index("ix_perf_batch_id", "batch_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tutor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    rating = Column(String(20), nullable=False)  # excellent, great, good, satisfactory
    score = Column(Integer, nullable=False)  # 4, 3, 2, 1 (derived from rating)
    tutor_note = Column(Text, nullable=True)
    session_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student = relationship("User", back_populates="performance_records_as_student", foreign_keys=[student_id])
    tutor = relationship("User", back_populates="performance_records_as_tutor", foreign_keys=[tutor_id])
    batch = relationship("Batch", back_populates="performance_records")


# =============================================================================
# NOTIFICATION SYSTEM
# =============================================================================

class Notification(Base):
    """
    Notification - simple notification system for enrollment events.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")


# =============================================================================
# VIDEO SESSION & STUDY MATERIALS (existing, preserved)
# =============================================================================

class VideoSession(Base):
    """
    VideoSession - a recorded/live session linked to a batch.
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
    SessionMaterial - study resources attached to a video session.
    """
    __tablename__ = "session_materials"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("video_sessions.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False, default="pdf")
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("VideoSession", back_populates="materials")
