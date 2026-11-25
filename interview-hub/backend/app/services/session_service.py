import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.candidate_session import CandidateSession


SESSION_DURATION_HOURS = 12


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_candidate_session(
    db: Session,
    candidate_id: UUID
) -> str:
    raw_token = secrets.token_urlsafe(32)

    session = CandidateSession(
        candidate_id=candidate_id,
        session_hash=hash_session_token(raw_token),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(hours=SESSION_DURATION_HOURS)
        )
    )

    db.add(session)

    # The caller commits the transaction.
    return raw_token


def get_authenticated_candidate(
    db: Session,
    raw_token: str | None
) -> Candidate | None:
    if not raw_token or len(raw_token) > 256:
        return None

    session = db.scalar(
        select(CandidateSession).where(
            CandidateSession.session_hash
            == hash_session_token(raw_token)
        )
    )

    if session is None:
        return None

    now = datetime.now(timezone.utc)

    if session.revoked_at is not None:
        return None

    if session.expires_at <= now:
        return None

    candidate = db.get(Candidate, session.candidate_id)

    if candidate is None:
        return None

    if candidate.email_verified_at is None:
        return None

    return candidate


def revoke_candidate_session(
    db: Session,
    raw_token: str | None
) -> bool:
    if not raw_token or len(raw_token) > 256:
        return False

    session = db.scalar(
        select(CandidateSession)
        .where(
            CandidateSession.session_hash
            == hash_session_token(raw_token)
        )
        .with_for_update()
    )

    if session is None or session.revoked_at is not None:
        return False

    session.revoked_at = datetime.now(timezone.utc)

    # The caller commits the revocation.
    return True
