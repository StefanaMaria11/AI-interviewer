import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.email_verification import EmailVerificationToken


TOKEN_EXPIRATION_MINUTES = 30


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_verification_token(
    db: Session,
    candidate_id: UUID
) -> str:
    raw_token = secrets.token_urlsafe(32)

    verification = EmailVerificationToken(
        candidate_id=candidate_id,
        token_hash=hash_token(raw_token),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
        )
    )

    db.add(verification)

    # The caller commits the transaction.
    return raw_token

def verify_email_token(db: Session, raw_token: str) -> bool:
    if not raw_token:
        return False

    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    verification = db.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == token_hash)
        .with_for_update()
    )

    if verification is None:
        return False

    if verification.used_at is not None:
        return False

    if verification.expires_at <= now:
        return False

    candidate = db.scalar(
        select(Candidate)
        .where(Candidate.id == verification.candidate_id)
        .with_for_update()
    )

    if candidate is None or candidate.email_verified_at is not None:
        return False

    verification.used_at = now
    candidate.email_verified_at = now

    # The caller commits both updates in one transaction.
    return True
