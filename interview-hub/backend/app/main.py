from fastapi import FastAPI, Depends, HTTPException

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate

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
        **candidate_data.model_dump()
    )

    db.add(candidate)

    try:
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