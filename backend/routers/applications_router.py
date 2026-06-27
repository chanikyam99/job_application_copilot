from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
import json

from database import get_db
import models
import schemas
import auth
from utils.pdf_parser import extract_text_from_pdf
from utils.docx_generator import generate_cover_letter_docx, generate_resume_docx
from agents.orchestrator import (
    run_pipeline, run_fit_analyst, run_resume_writer,
    run_cover_letter_writer, run_interviewer
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("/", response_model=List[schemas.ApplicationOut])
def list_applications(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all applications for the current user, newest first.
    user_id filter ensures users can only see their OWN applications.
    This is a critical security boundary — never omit this filter.
    """
    return (
        db.query(models.Application)
        .filter(models.Application.user_id == current_user.id)
        .order_by(models.Application.created_at.desc())
        .all()
    )


@router.post("/", response_model=schemas.ApplicationOut, status_code=201)
async def create_application(
    job_title:   str = Form(...),
    company:     str = Form(...),
    jd_text:     str = Form(...),
    resume_file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates application record (without generating AI artifacts).
    Uses Form() + File() instead of JSON body because file uploads
    require multipart/form-data encoding, not application/json.
    """
    if not resume_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await resume_file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    resume_text = extract_text_from_pdf(file_bytes)
    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from this PDF. Try a text-based PDF (not a scanned image)."
        )

    application = models.Application(
        user_id=current_user.id,
        job_title=job_title.strip(),
        company=company.strip(),
        jd_text=jd_text.strip(),
        original_resume=resume_text,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.post("/{app_id}/generate", response_model=schemas.ApplicationOut)
async def generate_artifacts(
    app_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Runs the 4-agent pipeline and saves all artifacts.
    This endpoint takes ~15–30 seconds.
    """
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    results = await run_pipeline(
        resume_text=application.original_resume,
        jd_text=application.jd_text,
        job_title=application.job_title,
        company=application.company,
    )

    # Upsert draft — create if doesn't exist, update if it does
    draft = application.draft
    if not draft:
        draft = models.Draft(application_id=application.id)
        db.add(draft)

    draft.fit_analysis   = json.dumps(results["fit_analysis"])
    draft.resume_rewrite = json.dumps({
        "text":    results["resume_rewrite"],
        "changes": results["resume_changes"]
    })
    draft.cover_letter = results["cover_letter"]
    draft.interview_qa = json.dumps(results["interview_qa"])

    db.commit()
    db.refresh(application)
    return application


@router.get("/{app_id}", response_model=schemas.ApplicationOut)
def get_application(
    app_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch("/{app_id}/status", response_model=schemas.ApplicationOut)
def update_status(
    app_id: int,
    update: schemas.ApplicationUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Updates application status and/or metadata."""
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if update.status    is not None: application.status    = update.status
    if update.job_title is not None: application.job_title = update.job_title
    if update.company   is not None: application.company   = update.company

    db.commit()
    db.refresh(application)
    return application


@router.post("/{app_id}/regenerate/{section}", response_model=schemas.ApplicationOut)
async def regenerate_section(
    app_id:  int,
    section: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerates a single section without re-running the full pipeline.
    Valid sections: fit_analysis | resume | cover_letter | interview

    WHY this endpoint? LLM output is non-deterministic. If the generated
    cover letter sounds generic, the user can re-run just that agent (~5s)
    instead of waiting for the full 30-second pipeline.
    """
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    draft = application.draft
    if not draft:
        draft = models.Draft(application_id=application.id)
        db.add(draft)
        db.flush()

    fit_analysis = json.loads(draft.fit_analysis) if draft.fit_analysis else {}

    if section == "fit_analysis":
        result = await run_fit_analyst(application.original_resume, application.jd_text)
        draft.fit_analysis = json.dumps(result)

    elif section == "resume":
        if not fit_analysis:
            fit_analysis = await run_fit_analyst(application.original_resume, application.jd_text)
            draft.fit_analysis = json.dumps(fit_analysis)
        result = await run_resume_writer(application.original_resume, application.jd_text, fit_analysis)
        draft.resume_rewrite = json.dumps({"text": result["rewritten_resume"], "changes": result["changes"]})

    elif section == "cover_letter":
        if not fit_analysis:
            fit_analysis = await run_fit_analyst(application.original_resume, application.jd_text)
            draft.fit_analysis = json.dumps(fit_analysis)
        result = await run_cover_letter_writer(
            application.original_resume, application.jd_text,
            fit_analysis, application.job_title, application.company
        )
        draft.cover_letter = result

    elif section == "interview":
        if not fit_analysis:
            fit_analysis = await run_fit_analyst(application.original_resume, application.jd_text)
            draft.fit_analysis = json.dumps(fit_analysis)
        result = await run_interviewer(application.original_resume, application.jd_text, fit_analysis)
        draft.interview_qa = json.dumps(result)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section '{section}'. Use: fit_analysis, resume, cover_letter, interview"
        )

    db.commit()
    db.refresh(application)
    return application


@router.get("/{app_id}/download/cover-letter")
def download_cover_letter(
    app_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the cover letter as a downloadable .docx file."""
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application or not application.draft or not application.draft.cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not generated yet")

    docx_bytes = generate_cover_letter_docx(
        application.draft.cover_letter,
        application.job_title,
        application.company
    )

    # Sanitize filename — remove special chars that break Content-Disposition
    safe = lambda s: "".join(c for c in s if c.isalnum() or c in " _-")[:30]
    filename = f"cover_{safe(application.company)}_{safe(application.job_title)}.docx".replace(" ", "_")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{app_id}/download/resume")
def download_resume(
    app_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the AI-rewritten resume as a downloadable .docx file."""
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application or not application.draft or not application.draft.resume_rewrite:
        raise HTTPException(status_code=404, detail="Resume rewrite not generated yet")

    rewrite_data = json.loads(application.draft.resume_rewrite)
    resume_text  = rewrite_data.get("text", application.original_resume)

    docx_bytes = generate_resume_docx(resume_text, application.job_title, application.company)

    safe = lambda s: "".join(c for c in s if c.isalnum() or c in " _-")[:30]
    filename = f"resume_{safe(application.company)}_{safe(application.job_title)}.docx".replace(" ", "_")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.delete("/{app_id}", status_code=204)
def delete_application(
    app_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(models.Application).filter(
        models.Application.id == app_id,
        models.Application.user_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(application)
    db.commit()