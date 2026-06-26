from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class ApplicationStatus(str, enum.Enum):
    """
    str + enum.Enum means values are stored as strings in the DB.
    This lets you compare status == "applied" in templates without .value.
    The 5 statuses map to the typical job application lifecycle.
    """
    not_yet    = "not_yet"
    applied    = "applied"
    interviewed = "interviewed"
    rejected   = "rejected"
    offer      = "offer"


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(255))
    created_at      = Column(DateTime, default=datetime.utcnow)

    # One user → many applications
    # cascade="all, delete-orphan": deleting the user auto-deletes their applications
    applications = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_title       = Column(String(500), nullable=False)
    company         = Column(String(500), nullable=False)
    jd_text         = Column(Text, nullable=False)
    # Text has no length limit in SQLite (unlike String(N)).
    # Resumes can be 3000+ characters — use Text, not String.
    original_resume = Column(Text, nullable=False)
    status          = Column(Enum(ApplicationStatus), default=ApplicationStatus.not_yet)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user  = relationship("User", back_populates="applications")
    # uselist=False = one Application has exactly one Draft (1:1 not 1:many)
    # cascade = deleting application auto-deletes its draft
    draft = relationship(
        "Draft",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Draft(Base):
    __tablename__ = "drafts"

    id             = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    # All 4 agent outputs stored as Text (JSON strings).
    # json.dumps() when writing, json.loads() when reading.
    fit_analysis   = Column(Text)  # JSON: {match_score, matching_requirements, ...}
    resume_rewrite = Column(Text)  # JSON: {text: "...", changes: [{original, rewritten, reason}]}
    cover_letter   = Column(Text)  # Plain text — no JSON wrapper needed
    interview_qa   = Column(Text)  # JSON: [{type, question, sample_answer, tip}, ...]
    generated_at   = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="draft")