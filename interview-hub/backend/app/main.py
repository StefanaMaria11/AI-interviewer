import os

from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Response
from uuid import uuid4

from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.candidate import Candidate
from app.models.admin import Admin
from app.schemas.candidate import CandidateCreate
from app.schemas.admin_auth import AdminLoginRequest
from app.schemas.email_verification import VerifyEmailRequest
from app.schemas.login import LoginRequest, CompleteLoginRequest
from app.services.email_verification_service import create_verification_token, verify_email_token
from app.services.email_service import send_verification_email, send_login_email
from app.services.session_service import create_candidate_session, get_authenticated_candidate, revoke_candidate_session
from app.services.login_service import create_login_token, consume_login_token
from app.services.admin_password_service import verify_admin_password
from app.services.admin_mfa_service import verify_admin_totp
from app.services.admin_session_service import create_admin_session, get_authenticated_admin, revoke_admin_session


app = FastAPI(
    title="InterviewHub API",
    description="Candidate and administrator management API",
    version="0.1.0"
)

SESSION_COOKIE_NAME = "interviewhub_session"
SESSION_MAX_AGE = 12 * 60 * 60
ADMIN_SESSION_COOKIE_NAME = "interviewhub_admin_session"
ADMIN_SESSION_MAX_AGE = 2 * 60 * 60

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

def set_admin_session_cookie(
    response: Response,
    token: str,
) -> None:
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        value=token,
        max_age=ADMIN_SESSION_MAX_AGE,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="strict",
        path="/admin",
    )

def require_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> Admin:
    token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)
    admin = get_authenticated_admin(db, token)

    if admin is None:
        raise HTTPException(
            status_code=401,
            detail="Administrator authentication required",
        )

    return admin

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

@app.post("/auth/request-login")
def request_candidate_login(
    login_data: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    candidate = db.scalar(
        select(Candidate).where(
            Candidate.email == login_data.email
        )
    )

    if candidate is not None and candidate.email_verified_at is not None:
        try:
            raw_token = create_login_token(db, candidate)
            db.commit()
        except Exception:
            db.rollback()
            raise

        background_tasks.add_task(
            send_login_email,
            candidate.email,
            raw_token,
        )

    return {
        "message": (
            "If this email belongs to a verified account, "
            "a login message will be sent."
        )
    }

@app.post("/auth/complete-login")
def complete_candidate_login(
    login_data: CompleteLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        candidate = consume_login_token(
            db,
            login_data.token,
        )

        if candidate is None:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired login token",
            )

        raw_session_token = create_candidate_session(
            db,
            candidate.id,
        )

        # Consume the login token and create the session
        # in the same database transaction.
        db.commit()

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise

    set_session_cookie(response, raw_session_token)

    return {
        "message": "Login successful",
    }

@app.post("/admin/auth/login")
def login_admin(
    login_data: AdminLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        admin = db.scalar(
            select(Admin)
            .where(Admin.email == login_data.email)
            .with_for_update()
        )

        if (
            admin is None
            or not admin.is_active
            or admin.mfa_enabled_at is None
            or admin.totp_secret_encrypted is None
            or not verify_admin_password(
                login_data.password,
                admin.password_hash,
            )
            or not verify_admin_totp(
                admin,
                login_data.totp_code,
            )
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid administrator credentials",
            )

        verified_at = datetime.now(timezone.utc)

        raw_session_token = create_admin_session(
            db,
            admin.id,
            mfa_verified_at=verified_at,
        )

        admin.last_login_at = verified_at

        db.commit()

    except Exception:
        db.rollback()
        raise

    set_admin_session_cookie(response, raw_session_token)

    return {"message": "Administrator login successful"}

@app.get("/admin/auth/me")
def get_my_admin_profile(
    admin: Admin = Depends(require_admin),
):
    return {
        "admin_id": str(admin.id),
        "email": admin.email,
        "is_active": admin.is_active,
        "mfa_enabled": admin.mfa_enabled_at is not None,
        "last_login_at": admin.last_login_at,
    }

@app.post("/admin/auth/logout")
def logout_admin(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)

    try:
        revoked = revoke_admin_session(db, token)

        if revoked:
            db.commit()
        else:
            db.rollback()

    except Exception:
        db.rollback()
        raise

    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        path="/admin",
        secure=session_cookie_secure(),
        httponly=True,
        samesite="strict",
    )

    return {"message": "Administrator logged out successfully"}