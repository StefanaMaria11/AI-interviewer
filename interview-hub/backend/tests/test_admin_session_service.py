from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.admin_session import AdminSession
from app.services.admin_session_service import create_admin_session, get_authenticated_admin, hash_admin_session_token, revoke_admin_session


def make_admin(active=True):
    return SimpleNamespace(
        id=uuid4(),
        is_active=active,
    )

def make_session(admin_id, expired=False, revoked=False):
    now = datetime.now(timezone.utc)

    return AdminSession(
        admin_id=admin_id,
        session_hash=hash_admin_session_token("test-token"),
        mfa_verified_at=now,
        expires_at=(
            now - timedelta(minutes=1)
            if expired
            else now + timedelta(hours=2)
        ),
        revoked_at=now if revoked else None,
    )

def test_create_admin_session():
    db = MagicMock()
    admin = make_admin()

    verified_at = datetime.now(timezone.utc)

    token = create_admin_session(
        db,
        admin.id,
        mfa_verified_at=verified_at,
    )

    session = db.add.call_args.args[0]

    assert isinstance(session, AdminSession)
    assert session.admin_id == admin.id
    assert session.session_hash == hash_admin_session_token(token)
    assert session.session_hash != token
    assert session.mfa_verified_at == verified_at
    assert session.expires_at > datetime.now(timezone.utc)

    db.commit.assert_not_called()

def test_reject_stale_mfa_verification():
    db = MagicMock()

    with pytest.raises(ValueError):
        create_admin_session(
            db,
            uuid4(),
            mfa_verified_at=(
                datetime.now(timezone.utc)
                - timedelta(minutes=5)
            ),
        )

    db.add.assert_not_called()

def test_get_authenticated_admin():
    db = MagicMock()
    admin = make_admin()
    session = make_session(admin.id)

    db.scalar.return_value = session
    db.get.return_value = admin

    result = get_authenticated_admin(db, "test-token")

    assert result is admin

def test_reject_expired_admin_session():
    db = MagicMock()
    admin = make_admin()

    db.scalar.return_value = make_session(
        admin.id,
        expired=True,
    )

    assert get_authenticated_admin(db, "test-token") is None

def test_reject_revoked_admin_session():
    db = MagicMock()
    admin = make_admin()

    db.scalar.return_value = make_session(
        admin.id,
        revoked=True,
    )

    assert get_authenticated_admin(db, "test-token") is None

def test_reject_inactive_admin():
    db = MagicMock()
    admin = make_admin(active=False)

    db.scalar.return_value = make_session(admin.id)
    db.get.return_value = admin

    assert get_authenticated_admin(db, "test-token") is None

def test_revoke_admin_session():
    db = MagicMock()
    admin = make_admin()
    session = make_session(admin.id)

    db.scalar.return_value = session

    assert revoke_admin_session(db, "test-token")
    assert session.revoked_at is not None
    db.commit.assert_not_called()

def test_cannot_revoke_twice():
    db = MagicMock()
    admin = make_admin()

    db.scalar.return_value = make_session(
        admin.id,
        revoked=True,
    )

    assert not revoke_admin_session(db, "test-token")