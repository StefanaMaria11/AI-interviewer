import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.candidate_login_token import CandidateLoginToken
from app.services.email_verification_service import hash_token


LOGIN_TOKEN_EXPIRATION_MINUTES = 15


def create_login_token(
    db: Session,
    candidate: Candidate,
) -> str:
    if candidate.email_verified_at is None:
        raise ValueError("Candidate email is not verified")

    raw_token = secrets.token_urlsafe(32)

    login_token = CandidateLoginToken(
        candidate_id=candidate.id,
        token_hash=hash_token(raw_token),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=LOGIN_TOKEN_EXPIRATION_MINUTES)
        ),
    )

    db.add(login_token)

    # The caller commits the transaction.
    return raw_token


def consume_login_token(
    db: Session,
    raw_token: str,
) -> Candidate | None:
    if not raw_token or len(raw_token) > 256:
        return None

    now = datetime.now(timezone.utc)

    login_token = db.scalar(
        select(CandidateLoginToken)
        .where(
            CandidateLoginToken.token_hash
            == hash_token(raw_token)
        )
        .with_for_update()
    )

    if login_token is None:
        return None

    if login_token.used_at is not None:
        return None

    if login_token.expires_at <= now:
        return None

    candidate = db.scalar(
        select(Candidate)
        .where(Candidate.id == login_token.candidate_id)
        .with_for_update()
    )

    if candidate is None:
        return None

    if candidate.email_verified_at is None:
        return None

    login_token.used_at = now

    # The caller commits token consumption and session creation.
    return candidate
