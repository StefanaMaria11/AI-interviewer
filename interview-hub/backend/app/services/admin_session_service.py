import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import Admin
from app.models.admin_session import AdminSession


ADMIN_SESSION_DURATION_HOURS = 12


def hash_admin_session_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_admin_session(db: Session, admin_id: UUID, *, mfa_verified_at: datetime) -> str:
    now = datetime.now(timezone.utc)

    if (
        mfa_verified_at.tzinfo is None
        or mfa_verified_at.utcoffset() is None
        or not (
            now - timedelta(minutes=1)
            <= mfa_verified_at
            <= now
        )
    ):
        raise ValueError("Recent MFA verification required")

    raw_token = secrets.token_urlsafe(32)

    admin_session = AdminSession(
        admin_id=admin_id,
        session_hash=hash_admin_session_token(raw_token),
        mfa_verified_at=mfa_verified_at,
        expires_at=(
            now + timedelta(hours=ADMIN_SESSION_DURATION_HOURS)
        ),
    )

    db.add(admin_session)

    # The caller commits after successful authentication.
    return raw_token


def get_authenticated_admin(db: Session, raw_token: str | None) -> Admin | None:
    if not raw_token or len(raw_token) > 256:
        return None

    session = db.scalar(
        select(AdminSession).where(
            AdminSession.session_hash
            == hash_admin_session_token(raw_token)
        )
    )

    if session is None:
        return None

    now = datetime.now(timezone.utc)

    if session.revoked_at is not None:
        return None

    if session.expires_at <= now:
        return None

    if session.mfa_verified_at is None:
        return None

    admin = db.get(Admin, session.admin_id)

    if admin is None or not admin.is_active:
        return None

    return admin

def revoke_admin_session(db: Session, raw_token: str | None) -> bool:
    if not raw_token or len(raw_token) > 256:
        return False

    session = db.scalar(
        select(AdminSession)
        .where(
            AdminSession.session_hash
            == hash_admin_session_token(raw_token)
        )
        .with_for_update()
    )

    if session is None or session.revoked_at is not None:
        return False

    session.revoked_at = datetime.now(timezone.utc)

    # The caller commits the revocation.
    return True
