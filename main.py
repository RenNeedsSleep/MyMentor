import os
import shutil
from typing import Optional, List, Dict
from datetime import datetime

from fastapi import (
    FastAPI, Request, Depends, HTTPException, Form,
    WebSocket, WebSocketDisconnect, Query, UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func

from database import engine, get_db, Base
from models import User, TutorProfile, AvailabilitySlot, Booking, Recording, Message
from models import Batch, BatchMember, VideoSession, SessionMaterial  # new models for table creation
from auth import hash_password, verify_password, create_access_token, decode_access_token
from services.messaging_access import check_batch_relationship
from services.batch_service import get_member_count
from services.tutor_service import check_profile_complete
from routers.batch_router import batch_router
from routers.session_router import session_router
from routers.tutor_router import tutor_router



app = FastAPI(title="MyMentor", description="Student-Tutor Matching Platform")


Base.metadata.create_all(bind=engine)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Register new feature routers (non-breaking additions) ---
app.include_router(batch_router)
app.include_router(session_router)
app.include_router(tutor_router)




def get_current_user(request: Request, db: Session) -> Optional[User]:
    """Extract user from JWT cookie. Returns None if not logged in."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    return user


                                                                            
             
                                                                            

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    full_name: str = Form(""),
    bio: str = Form(""),
    qualifications: str = Form(""),
    subjects: str = Form(""),
    experience_years: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(
        (User.email == email) | (User.username == username)
    ).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "A user with that email or username already exists."
        })

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == "tutor":
        profile = TutorProfile(
            user_id=user.id,
            full_name=full_name if full_name else None,
            bio=bio if bio else None,
            qualifications=qualifications if qualifications else None,
            subjects=subjects if subjects else None,
            experience_years=experience_years,
        )
        profile.is_profile_complete = check_profile_complete(profile)
        db.add(profile)
        db.commit()

    token = create_access_token({"user_id": user.id, "role": user.role})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return response


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password."
        })

    token = create_access_token({"user_id": user.id, "role": user.role})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


                                                                            
                  
                                                                            

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user.role == "tutor":
        return RedirectResponse(url="/tutor/dashboard", status_code=302)
    else:
        return RedirectResponse(url="/student/dashboard", status_code=302)


@app.get("/tutor/dashboard", response_class=HTMLResponse)
async def tutor_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    slots = []
    bookings = []
    if profile:
        slots = db.query(AvailabilitySlot).filter(
            AvailabilitySlot.tutor_id == profile.id
        ).order_by(AvailabilitySlot.date, AvailabilitySlot.start_time).all()

        bookings = db.query(Booking).filter(
            Booking.tutor_id == profile.id
        ).options(
            joinedload(Booking.student),
            joinedload(Booking.slot),
            joinedload(Booking.recording)
        ).order_by(Booking.id.desc()).all()

                           
    unread_count = db.query(func.count(Message.id)).filter(
        Message.receiver_id == user.id,
        Message.is_read == False
    ).scalar()

    # --- Fetch tutor's batches for the Batches tab ---
    tutor_batches = db.query(Batch).filter(Batch.tutor_id == user.id).order_by(Batch.created_at.desc()).all()
    # Enrich batches with member count and sessions
    for b in tutor_batches:
        b.member_count = get_member_count(db, b.id)
        b.sessions = db.query(VideoSession).filter(VideoSession.batch_id == b.id).order_by(VideoSession.created_at.desc()).all()
        for s in b.sessions:
            s.material_list = db.query(SessionMaterial).filter(SessionMaterial.session_id == s.id).all()

    return templates.TemplateResponse("tutor_dashboard.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "slots": slots,
        "bookings": bookings,
        "unread_count": unread_count,
        "tutor_batches": tutor_batches
    })


@app.post("/tutor/profile", response_class=HTMLResponse)
async def update_tutor_profile(
    request: Request,
    full_name: str = Form(""),
    bio: str = Form(""),
    qualifications: str = Form(""),
    subjects: str = Form(""),
    experience_years: Optional[int] = Form(None),
    profile_image_url: str = Form(""),
    teaching_mode: str = Form("both"),
    location: str = Form(""),
    certificate: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    if not profile:
        profile = TutorProfile(user_id=user.id)
        db.add(profile)

    profile.full_name = full_name if full_name else None
    profile.bio = bio if bio else None
    profile.qualifications = qualifications
    profile.subjects = subjects
    profile.experience_years = experience_years
    profile.profile_image_url = profile_image_url if profile_image_url else None
    profile.teaching_mode = teaching_mode
    profile.location = location if location else None
    profile.subscription_active = teaching_mode in ("online", "both")
    
    if certificate and certificate.filename:
        upload_dir = os.path.join("static", "uploads", "certificates")
        os.makedirs(upload_dir, exist_ok=True)
        file_name = f"tutor_{user.id}_{certificate.filename}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(certificate.file, buffer)
        profile.certificate_file_path = f"/static/uploads/certificates/{file_name}"
        
    profile.is_profile_complete = check_profile_complete(profile)
    db.commit()

    return RedirectResponse(url="/tutor/dashboard", status_code=302)


@app.post("/tutor/slot", response_class=HTMLResponse)
async def add_slot(
    request: Request,
    date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    if not profile:
        return RedirectResponse(url="/tutor/dashboard", status_code=302)

    slot = AvailabilitySlot(
        tutor_id=profile.id,
        date=date,
        start_time=start_time,
        end_time=end_time,
        is_booked=False
    )
    db.add(slot)
    db.commit()

    return RedirectResponse(url="/tutor/dashboard", status_code=302)


@app.post("/tutor/slot/delete/{slot_id}")
async def delete_slot(
    slot_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id,
        AvailabilitySlot.tutor_id == profile.id,
        AvailabilitySlot.is_booked == False
    ).first()

    if slot:
        db.delete(slot)
        db.commit()

    return RedirectResponse(url="/tutor/dashboard", status_code=302)


@app.post("/tutor/booking/{booking_id}/complete")
async def complete_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.tutor_id == profile.id
    ).first()

    if booking:
        booking.status = "completed"
        db.commit()

    return RedirectResponse(url="/tutor/dashboard", status_code=302)


@app.post("/tutor/recording")
async def add_recording(
    request: Request,
    booking_id: int = Form(...),
    video_link: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.tutor_id == profile.id,
        Booking.status == "completed"
    ).first()

    if not booking:
        return RedirectResponse(url="/tutor/dashboard", status_code=302)

    existing = db.query(Recording).filter(Recording.booking_id == booking_id).first()
    if existing:
        existing.video_link = video_link
    else:
        recording = Recording(booking_id=booking_id, video_link=video_link)
        db.add(recording)
    db.commit()

    return RedirectResponse(url="/tutor/dashboard", status_code=302)


                                                                            
                
                                                                            

@app.get("/student/dashboard", response_class=HTMLResponse)
async def student_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "student":
        return RedirectResponse(url="/login", status_code=302)

    bookings = db.query(Booking).filter(
        Booking.student_id == user.id
    ).options(
        joinedload(Booking.tutor).joinedload(TutorProfile.user),
        joinedload(Booking.slot),
        joinedload(Booking.recording)
    ).order_by(Booking.id.desc()).all()

    unread_count = db.query(func.count(Message.id)).filter(
        Message.receiver_id == user.id,
        Message.is_read == False
    ).scalar()

    # --- Fetch batch data for the Batches tab ---
    all_batches = db.query(Batch).order_by(Batch.created_at.desc()).all()
    joined_batch_ids = set()
    student_memberships = db.query(BatchMember).filter(BatchMember.student_id == user.id).all()
    for m in student_memberships:
        joined_batch_ids.add(m.batch_id)

    # Enrich batches
    for b in all_batches:
        b.member_count = get_member_count(db, b.id)
        b.tutor_user = db.query(User).filter(User.id == b.tutor_id).first()
        b.is_joined = b.id in joined_batch_ids
        if b.is_joined:
            b.sessions = db.query(VideoSession).filter(VideoSession.batch_id == b.id).order_by(VideoSession.created_at.desc()).all()
            for s in b.sessions:
                s.material_list = db.query(SessionMaterial).filter(SessionMaterial.session_id == s.id).all()
        else:
            b.sessions = []

    return templates.TemplateResponse("student_dashboard.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "unread_count": unread_count,
        "all_batches": all_batches,
        "joined_batch_ids": joined_batch_ids
    })


# =============================================================================
# BATCH HTML FORM ROUTES (server-side rendering, same pattern as existing)
# =============================================================================

@app.post("/tutor/batch/create")
async def create_batch_form(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    scheduled_time: str = Form(...),
    max_students: int = Form(30),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    # --- Soft restriction: incomplete profiles cannot create batches ---
    profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    if not profile or not profile.is_profile_complete:
        raise HTTPException(
            status_code=403,
            detail="Please complete your profile (full name, qualifications, subjects) before creating batches."
        )

    batch = Batch(
        name=name,
        description=description,
        scheduled_time=scheduled_time,
        max_students=max_students,
        tutor_id=user.id,
        created_at=datetime.utcnow()
    )
    db.add(batch)
    db.commit()
    return RedirectResponse(url="/tutor/dashboard#section-batches", status_code=302)


@app.post("/student/batch/{batch_id}/join")
async def join_batch_form(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "student":
        return RedirectResponse(url="/login", status_code=302)

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return RedirectResponse(url="/student/dashboard", status_code=302)

    # Check duplicate
    existing = db.query(BatchMember).filter(
        BatchMember.batch_id == batch_id,
        BatchMember.student_id == user.id
    ).first()
    if existing:
        return RedirectResponse(url="/student/dashboard#section-batches", status_code=302)

    # Check capacity
    current_count = get_member_count(db, batch_id)
    if current_count >= batch.max_students:
        return RedirectResponse(url="/student/dashboard#section-batches", status_code=302)

    member = BatchMember(
        batch_id=batch_id,
        student_id=user.id,
        joined_at=datetime.utcnow()
    )
    db.add(member)
    db.commit()
    return RedirectResponse(url="/student/dashboard#section-batches", status_code=302)


@app.post("/tutor/batch/{batch_id}/add-session")
async def add_session_form(
    batch_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    video_url: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    # --- Soft restriction: incomplete profiles cannot upload sessions ---
    tutor_profile = db.query(TutorProfile).filter(TutorProfile.user_id == user.id).first()
    if not tutor_profile or not tutor_profile.is_profile_complete:
        raise HTTPException(
            status_code=403,
            detail="Please complete your profile before adding video sessions."
        )

    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.tutor_id == user.id).first()
    if not batch:
        return RedirectResponse(url="/tutor/dashboard", status_code=302)

    session = VideoSession(
        batch_id=batch_id,
        title=title,
        description=description,
        video_url=video_url,
        created_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    return RedirectResponse(url="/tutor/dashboard#section-batches", status_code=302)


@app.post("/tutor/session/{session_id}/upload-material")
async def upload_material_form(
    session_id: int,
    request: Request,
    file_url: str = Form(...),
    file_type: str = Form("pdf"),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "tutor":
        return RedirectResponse(url="/login", status_code=302)

    session_obj = db.query(VideoSession).filter(VideoSession.id == session_id).first()
    if not session_obj:
        return RedirectResponse(url="/tutor/dashboard", status_code=302)

    batch = db.query(Batch).filter(Batch.id == session_obj.batch_id, Batch.tutor_id == user.id).first()
    if not batch:
        return RedirectResponse(url="/tutor/dashboard", status_code=302)

    material = SessionMaterial(
        session_id=session_id,
        file_url=file_url,
        file_type=file_type,
        uploaded_at=datetime.utcnow()
    )
    db.add(material)
    db.commit()
    return RedirectResponse(url="/tutor/dashboard#section-batches", status_code=302)


@app.get("/student/search", response_class=HTMLResponse)
async def search_tutors(
    request: Request,
    subject: str = Query(""),
    mode: str = Query(""),
    location: str = Query(""),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "student":
        return RedirectResponse(url="/login", status_code=302)

    query = db.query(TutorProfile).options(
        joinedload(TutorProfile.user),
        joinedload(TutorProfile.availability_slots)
    )

    if subject:
        query = query.filter(TutorProfile.subjects.ilike(f"%{subject}%"))
    if mode and mode != "all":
        query = query.filter(
            (TutorProfile.teaching_mode == mode) | (TutorProfile.teaching_mode == "both")
        )
    if location:
        query = query.filter(TutorProfile.location.ilike(f"%{location}%"))

    tutors = query.all()

    return templates.TemplateResponse("search_results.html", {
        "request": request,
        "user": user,
        "tutors": tutors,
        "subject": subject,
        "mode": mode,
        "location": location
    })


@app.get("/student/tutor/{tutor_id}", response_class=HTMLResponse)
async def view_tutor(
    tutor_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "student":
        return RedirectResponse(url="/login", status_code=302)

    profile = db.query(TutorProfile).options(
        joinedload(TutorProfile.user),
        joinedload(TutorProfile.availability_slots)
    ).filter(TutorProfile.id == tutor_id).first()

    if not profile:
        return RedirectResponse(url="/student/search", status_code=302)

    available_slots = [s for s in profile.availability_slots if not s.is_booked]

    return templates.TemplateResponse("tutor_detail.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "available_slots": available_slots
    })


@app.post("/student/book")
async def book_slot(
    request: Request,
    slot_id: int = Form(...),
    tutor_id: int = Form(...),
    mode: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "student":
        return RedirectResponse(url="/login", status_code=302)

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id,
        AvailabilitySlot.is_booked == False
    ).first()

    if not slot:
        return RedirectResponse(url=f"/student/tutor/{tutor_id}?error=slot_taken", status_code=302)

    slot.is_booked = True

    booking = Booking(
        student_id=user.id,
        tutor_id=tutor_id,
        slot_id=slot_id,
        mode=mode,
        status="scheduled"
    )
    db.add(booking)
    db.commit()

    return RedirectResponse(url="/student/dashboard", status_code=302)


                                                                            
                  
                                                                            

@app.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

                                          
    sent_to = db.query(Message.receiver_id).filter(Message.sender_id == user.id).distinct()
    received_from = db.query(Message.sender_id).filter(Message.receiver_id == user.id).distinct()

    partner_ids = set()
    for row in sent_to.all():
        partner_ids.add(row[0])
    for row in received_from.all():
        partner_ids.add(row[0])

    conversations = []
    for pid in partner_ids:
        partner = db.query(User).filter(User.id == pid).first()
        if not partner:
            continue
                          
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == pid),
                and_(Message.sender_id == pid, Message.receiver_id == user.id)
            )
        ).order_by(Message.timestamp.desc()).first()
                      
        unread = db.query(func.count(Message.id)).filter(
            Message.sender_id == pid,
            Message.receiver_id == user.id,
            Message.is_read == False
        ).scalar()
        conversations.append({
            "partner": partner,
            "last_message": last_msg,
            "unread": unread
        })

                                    
    conversations.sort(key=lambda c: c["last_message"].timestamp if c["last_message"] else datetime.min, reverse=True)

    return templates.TemplateResponse("messages.html", {
        "request": request,
        "user": user,
        "conversations": conversations,
        "active_chat": None,
        "messages": [],
        "chat_partner": None
    })


@app.get("/messages/{partner_id}", response_class=HTMLResponse)
async def message_thread(partner_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    partner = db.query(User).filter(User.id == partner_id).first()
    if not partner:
        return RedirectResponse(url="/messages", status_code=302)

                           
    db.query(Message).filter(
        Message.sender_id == partner_id,
        Message.receiver_id == user.id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()

                                     
    thread_messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == partner_id),
            and_(Message.sender_id == partner_id, Message.receiver_id == user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

                            
    sent_to = db.query(Message.receiver_id).filter(Message.sender_id == user.id).distinct()
    received_from = db.query(Message.sender_id).filter(Message.receiver_id == user.id).distinct()

    partner_ids = set()
    for row in sent_to.all():
        partner_ids.add(row[0])
    for row in received_from.all():
        partner_ids.add(row[0])
                                           
    partner_ids.add(partner_id)

    conversations = []
    for pid in partner_ids:
        p = db.query(User).filter(User.id == pid).first()
        if not p:
            continue
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == pid),
                and_(Message.sender_id == pid, Message.receiver_id == user.id)
            )
        ).order_by(Message.timestamp.desc()).first()
        unread = db.query(func.count(Message.id)).filter(
            Message.sender_id == pid,
            Message.receiver_id == user.id,
            Message.is_read == False
        ).scalar()
        conversations.append({
            "partner": p,
            "last_message": last_msg,
            "unread": unread
        })

    conversations.sort(key=lambda c: c["last_message"].timestamp if c["last_message"] else datetime.min, reverse=True)

    return templates.TemplateResponse("messages.html", {
        "request": request,
        "user": user,
        "conversations": conversations,
        "active_chat": partner_id,
        "messages": thread_messages,
        "chat_partner": partner
    })


@app.post("/messages/{partner_id}")
async def send_message(
    partner_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # --- Batch-based messaging restriction (backward-compatible) ---
    partner = db.query(User).filter(User.id == partner_id).first()
    if partner and user.role == "student" and partner.role == "tutor":
        if not check_batch_relationship(db, student_id=user.id, tutor_id=partner.id):
            raise HTTPException(
                status_code=403,
                detail="You can only message tutors you share a batch with."
            )

    msg = Message(
        sender_id=user.id,
        receiver_id=partner_id,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.add(msg)
    db.commit()

    return RedirectResponse(url=f"/messages/{partner_id}", status_code=302)


@app.get("/api/messages/{partner_id}")
async def api_get_messages(partner_id: int, request: Request, after: str = Query(""), db: Session = Depends(get_db)):
    """JSON API for polling new messages."""
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    query = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == partner_id),
            and_(Message.sender_id == partner_id, Message.receiver_id == user.id)
        )
    )

    if after:
        try:
            after_dt = datetime.fromisoformat(after)
            query = query.filter(Message.timestamp > after_dt)
        except ValueError:
            pass

    messages = query.order_by(Message.timestamp.asc()).all()

                                    
    db.query(Message).filter(
        Message.sender_id == partner_id,
        Message.receiver_id == user.id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()

    return JSONResponse({
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "is_mine": m.sender_id == user.id
            }
            for m in messages
        ]
    })


                                                                            
            
                                                                            

@app.get("/room/{room_id}", response_class=HTMLResponse)
async def video_room(
    room_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse("video_room.html", {
        "request": request,
        "user": user,
        "room_id": room_id
    })


                                                                            
                                  
                                                                            

class PeerInfo:
    """Tracks a WebSocket connection with metadata."""
    def __init__(self, websocket: WebSocket, peer_id: str, username: str, role: str):
        self.websocket = websocket
        self.peer_id = peer_id
        self.username = username
        self.role = role

                                         
rooms: Dict[str, List[PeerInfo]] = {}
peer_counter = 0


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    username: str = Query("Anonymous"),
    role: str = Query("student")
):
    global peer_counter
    await websocket.accept()

                           
    peer_counter += 1
    peer_id = f"peer-{peer_counter}"

    peer = PeerInfo(websocket, peer_id, username, role)

    if room_id not in rooms:
        rooms[room_id] = []

                                                
    existing_peers = []
    for p in rooms[room_id]:
        existing_peers.append({
            "peer_id": p.peer_id,
            "username": p.username,
            "role": p.role
        })
        try:
            await p.websocket.send_json({
                "type": "peer-joined",
                "peer_id": peer_id,
                "username": username,
                "role": role
            })
        except:
            pass

    rooms[room_id].append(peer)

                                                  
    await websocket.send_json({
        "type": "room-state",
        "your_peer_id": peer_id,
        "peers": existing_peers
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type in ("offer", "answer", "ice-candidate"):
                                                            
                target_id = data.get("target_id")
                if target_id:
                    for p in rooms.get(room_id, []):
                        if p.peer_id == target_id:
                            try:
                                await p.websocket.send_json({
                                    **data,
                                    "sender_id": peer_id
                                })
                            except:
                                pass
                            break
            elif msg_type == "chat":
                                                     
                for p in rooms.get(room_id, []):
                    if p.peer_id != peer_id:
                        try:
                            await p.websocket.send_json({
                                "type": "chat",
                                "sender": data.get("sender", username),
                                "message": data.get("message", ""),
                                "sender_id": peer_id
                            })
                        except:
                            pass

    except WebSocketDisconnect:
        if room_id in rooms:
            rooms[room_id] = [p for p in rooms[room_id] if p.peer_id != peer_id]

            for p in rooms[room_id]:
                try:
                    await p.websocket.send_json({
                        "type": "peer-left",
                        "peer_id": peer_id,
                        "username": username
                    })
                except:
                    pass

            if not rooms[room_id]:
                del rooms[room_id]
