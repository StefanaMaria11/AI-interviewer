import os

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Response
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate
from app.schemas.email_verification import VerifyEmailRequest
from app.services.email_verification_service import create_verification_token, verify_email_token
from app.services.email_service import send_verification_email
from app.services.session_service import create_candidate_session, get_authenticated_candidate, revoke_candidate_session


app = FastAPI(
    title="InterviewHub API",
    description="Candidate and administrator management API",
    version="0.1.0"
)

SESSION_COOKIE_NAME = "interviewhub_session"
SESSION_MAX_AGE = 12 * 60 * 60

def session_cookie_secure() -> bool:
    # Secure by default. Allow HTTP only when explicitly
    # configured for local development.
    return os.getenv(
        "SESSION_COOKIE_SECURE", "true"
    ).lower() != "false"


def set_session_cookie(
    response: Response,
    token: str,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="strict",
        path="/",
    )


def require_candidate(
    request: Request,
    db: Session = Depends(get_db),
) -> Candidate:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    candidate = get_authenticated_candidate(db, token)

    if candidate is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    return candidate


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "interview-hub"
    }

@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected"
    }


@app.post("/candidates", status_code=201)
def register_candidate(candidate_data: CandidateCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    candidate = Candidate(
        id=uuid4(),
        **candidate_data.model_dump()
    )

    db.add(candidate)

    try:
        raw_token = create_verification_token(
            db,
            candidate.id
        )

        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Candidate already registered"
        )

    db.refresh(candidate)

    background_tasks.add_task(
        send_verification_email,
        candidate.email,
        raw_token
    )

    return {
        "candidate_id": str(candidate.id),
        "message": "Candidate registered successfully",
        "email_verified": False
    }

@app.post("/auth/verify-email")
def verify_candidate_email(
    verification_data: VerifyEmailRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        candidate = verify_email_token(
            db,
            verification_data.token,
        )

        if candidate is None:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification token",
            )

        raw_session_token = create_candidate_session(
            db,
            candidate.id,
        )

        # Commit verification and session creation together.
        db.commit()

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise

    # Send the session cookie only after a successful commit.
    set_session_cookie(response, raw_session_token)

    return {
        "message": "Email verified successfully",
    }

@app.get("/auth/me")
def get_my_profile(
    candidate: Candidate = Depends(require_candidate),
):
    return {
        "candidate_id": str(candidate.id),
        "full_name": candidate.full_name,
        "email": candidate.email,
        "profession": candidate.profession,
        "location": candidate.location,
        "email_verified": candidate.email_verified_at is not None,
    }


@app.post("/auth/logout")
def logout_candidate(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)

    try:
        revoked = revoke_candidate_session(db, token)

        if revoked:
            db.commit()
        else:
            db.rollback()

    except Exception:
        db.rollback()
        raise

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=session_cookie_secure(),
        httponly=True,
        samesite="strict",
    )

    return {"message": "Logged out successfully"}