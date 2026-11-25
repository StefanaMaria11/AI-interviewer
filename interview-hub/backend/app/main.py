from fastapi import FastAPI, Depends, HTTPException
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate
from app.schemas.email_verification import VerifyEmailRequest
from app.services.email_verification_service import create_verification_token, verify_email_token


app = FastAPI(
    title="InterviewHub API",
    description="Candidate and administrator management API",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "interview-hub"
    }

@app.get("/health/database")
def database_health(
    db: Session = Depends(get_db)
):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected"
    }

@app.post("/candidates", status_code=201)
def register_candidate(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db)
):
    candidate = Candidate(
        id=uuid4(),
        **candidate_data.model_dump()
    )

    db.add(candidate)

    try:
        # Store a verification token in the same transaction.
        create_verification_token(db, candidate.id)
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Candidate already registered"
        )

    db.refresh(candidate)

    return {
        "candidate_id": str(candidate.id),
        "message": "Candidate registered successfully",
        "email_verified": False
    }

@app.post("/auth/verify-email")
def verify_candidate_email(
    verification_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    try:
        verified = verify_email_token(
            db,
            verification_data.token
        )

        if not verified:
            db.rollback()

            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification token"
            )

        db.commit()

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Email verified successfully"
    }