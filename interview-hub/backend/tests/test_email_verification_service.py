import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.models.candidate import Candidate
from app.models.email_verification import EmailVerificationToken
from app.services.email_verification_service import (
    create_verification_token,
    hash_token,
    verify_email_token,
)

def make_candidate():
    return Candidate(
        id=uuid4(),
        full_name="Elena Popescu",
        email="elena.popescu@example.com",
        age=24,
        profession="Software Engineer",
        location="Cluj-Napoca",
        email_verified_at=None,
    )

def make_token(candidate_id, expires_at=None, used_at=None):
    return EmailVerificationToken(
        candidate_id=candidate_id,
        token_hash=hash_token("test-secret"),
        expires_at=expires_at or (
            datetime.now(timezone.utc) + timedelta(minutes=30)
        ),
        used_at=used_at,
    )

def test_create_verification_token():
    db = MagicMock()
    candidate_id = uuid4()

    raw_token = create_verification_token(db, candidate_id)

    saved = db.add.call_args.args[0]

    assert isinstance(saved, EmailVerificationToken)
    assert saved.candidate_id == candidate_id
    assert saved.token_hash == hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()
    assert raw_token != saved.token_hash
    assert saved.expires_at > datetime.now(timezone.utc)

    db.commit.assert_not_called()

def test_verify_valid_token():
    db = MagicMock()
    candidate = make_candidate()
    verification = make_token(candidate.id)

    db.scalar.side_effect = [verification, candidate]

    result = verify_email_token(db, "test-secret")

    assert result is candidate
    assert verification.used_at is not None
    assert candidate.email_verified_at is not None
    assert verification.used_at == candidate.email_verified_at
    db.commit.assert_not_called()

def test_reject_unknown_token():
    db = MagicMock()
    db.scalar.return_value = None

    assert verify_email_token(db, "unknown-token") is None

def test_reject_expired_token():
    db = MagicMock()
    verification = make_token(
        uuid4(),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    db.scalar.return_value = verification

    assert verify_email_token(db, "test-secret") is None
    assert verification.used_at is None
    db.scalar.assert_called_once()

def test_reject_used_token():
    db = MagicMock()
    verification = make_token(
        uuid4(),
        used_at=datetime.now(timezone.utc),
    )

    db.scalar.return_value = verification

    assert verify_email_token(db, "test-secret") is None

def test_reject_already_verified_candidate():
    db = MagicMock()
    candidate = make_candidate()
    candidate.email_verified_at = datetime.now(timezone.utc)
    verification = make_token(candidate.id)

    db.scalar.side_effect = [verification, candidate]

    assert verify_email_token(db, "test-secret") is None
    assert verification.used_at is None