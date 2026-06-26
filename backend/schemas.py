from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import ApplicationStatus


# ── AUTH ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    # EmailStr validates format before it reaches any code.
    # FastAPI returns HTTP 422 automatically if the email format is wrong.
    email:     EmailStr
    password:  str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type:   str  # Always "bearer"

class UserOut(BaseModel):
    id:         int
    email:      str
    full_name:  Optional[str]
    created_at: datetime

    class Config:
        # from_attributes=True (Pydantic v2) allows creating from SQLAlchemy
        # model instances: UserOut.model_validate(db_user_object)
        from_attributes = True


# ── APPLICATIONS ──────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    # resume_file is handled separately as UploadFile, not in this schema
    job_title: str
    company:   str
    jd_text:   str

class ApplicationUpdate(BaseModel):
    # All optional — PATCH semantics (only update what's provided)
    status:    Optional[ApplicationStatus] = None
    job_title: Optional[str] = None
    company:   Optional[str] = None

class DraftOut(BaseModel):
    id:            int
    fit_analysis:  Optional[str]
    resume_rewrite: Optional[str]
    cover_letter:  Optional[str]
    interview_qa:  Optional[str]
    generated_at:  Optional[datetime]

    class Config:
        from_attributes = True

class ApplicationOut(BaseModel):
    id:              int
    job_title:       str
    company:         str
    jd_text:         str
    original_resume: str
    status:          ApplicationStatus
    created_at:      datetime
    updated_at:      datetime
    draft:           Optional[DraftOut] = None  # None if not generated yet

    class Config:
        from_attributes = True