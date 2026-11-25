from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.candidate import Candidate
from app.models.candidate_login_token import CandidateLoginToken
from app.services.email_verification_service import hash_token
from app.services.login_service import create_login_token, consume_login_token



def make_candidate(verified=True):
    return Candidate(
        id=uuid4(),
        full_name="Elena Popescu",
        email="elena.popescu@example.com",
        age=24,
        profession="Software Engineer",
        location="Cluj-Napoca",
        email_verified_at=(
            datetime.now(timezone.utc) if verified else None
        ),
    )

def make_login_token(candidate_id, expired=False, used=False):
    now = datetime.now(timezone.utc)

    return CandidateLoginToken(
        candidate_id=candidate_id,
        token_hash=hash_token("test-login-token"),
        expires_at=now + (
            timedelta(minutes=-1)
            if expired else timedelta(minutes=15)
        ),
        used_at=now if used else None,
    )

def test_create_login_token():
    db = MagicMock()
    candidate = make_candidate()

    raw_token = create_login_token(db, candidate)

    saved = db.add.call_args.args[0]

    assert isinstance(saved, CandidateLoginToken)
    assert saved.candidate_id == candidate.id
    assert saved.token_hash == hash_token(raw_token)
    assert saved.token_hash != raw_token
    assert saved.expires_at > datetime.now(timezone.utc)

    db.commit.assert_not_called()

def test_reject_unverified_login_request():
    db = MagicMock()
    candidate = make_candidate(verified=False)

    with pytest.raises(ValueError, match="not verified"):
        create_login_token(db, candidate)

    db.add.assert_not_called()

def test_consume_valid_login_token():
    db = MagicMock()
    candidate = make_candidate()
    token = make_login_token(candidate.id)

    db.scalar.side_effect = [token, candidate]

    result = consume_login_token(db, "test-login-token")

    assert result is candidate
    assert token.used_at is not None
    db.commit.assert_not_called()

def test_reject_unknown_login_token():
    db = MagicMock()
    db.scalar.return_value = None

    assert consume_login_token(db, "unknown-token") is None

def test_reject_expired_login_token():
    db = MagicMock()
    candidate = make_candidate()
    token = make_login_token(candidate.id, expired=True)

    db.scalar.return_value = token

    assert consume_login_token(db, "test-login-token") is None
    assert token.used_at is None

def test_reject_used_login_token():
    db = MagicMock()
    candidate = make_candidate()
    token = make_login_token(candidate.id, used=True)

    db.scalar.return_value = token

    assert consume_login_token(db, "test-login-token") is None

def test_reject_login_for_unverified_candidate():
    db = MagicMock()
    candidate = make_candidate(verified=False)
    token = make_login_token(candidate.id)

    db.scalar.side_effect = [token, candidate]

    assert consume_login_token(db, "test-login-token") is None
    assert token.used_at is None