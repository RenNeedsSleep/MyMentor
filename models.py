"""
models.py - SQLAlchemy ORM models for MyMentor
Defines all database tables: User, TutorProfile, AvailabilitySlot, Booking, Recording
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Text, DateTime
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
