from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.models.candidate import Candidate
from app.models.candidate_session import CandidateSession
from app.services.session_service import create_candidate_session, get_authenticated_candidate, hash_session_token, revoke_candidate_session


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


def make_session(candidate_id, expired=False, revoked=False):
    now = datetime.now(timezone.utc)

    return CandidateSession(
        candidate_id=candidate_id,
        session_hash=hash_session_token("test-session-token"),
        expires_at=now + (
            timedelta(minutes=-1)
            if expired else timedelta(hours=12)
        ),
        revoked_at=now if revoked else None,
    )


def test_create_candidate_session():
    db = MagicMock()
    candidate_id = uuid4()

    raw_token = create_candidate_session(db, candidate_id)

    saved = db.add.call_args.args[0]

    assert isinstance(saved, CandidateSession)
    assert saved.candidate_id == candidate_id
    assert saved.session_hash == hash_session_token(raw_token)
    assert saved.session_hash != raw_token
    assert saved.expires_at > datetime.now(timezone.utc)
    db.commit.assert_not_called()


def test_get_authenticated_candidate():
    db = MagicMock()
    candidate = make_candidate()

    db.scalar.return_value = make_session(candidate.id)
    db.get.return_value = candidate

    result = get_authenticated_candidate(
        db, "test-session-token"
    )

    assert result is candidate
    db.get.assert_called_once_with(Candidate, candidate.id)


def test_reject_missing_session():
    db = MagicMock()
    db.scalar.return_value = None

    assert get_authenticated_candidate(
        db, "unknown-session"
    ) is None


def test_reject_expired_session():
    db = MagicMock()
    candidate = make_candidate()

    db.scalar.return_value = make_session(
        candidate.id, expired=True
    )

    assert get_authenticated_candidate(
        db, "test-session-token"
    ) is None

    db.get.assert_not_called()


def test_reject_revoked_session():
    db = MagicMock()
    candidate = make_candidate()

    db.scalar.return_value = make_session(
        candidate.id, revoked=True
    )

    assert get_authenticated_candidate(
        db, "test-session-token"
    ) is None


def test_reject_unverified_candidate():
    db = MagicMock()
    candidate = make_candidate(verified=False)

    db.scalar.return_value = make_session(candidate.id)
    db.get.return_value = candidate

    assert get_authenticated_candidate(
        db, "test-session-token"
    ) is None


def test_reject_empty_session_token():
    db = MagicMock()

    assert get_authenticated_candidate(db, None) is None
    assert get_authenticated_candidate(db, "") is None

    db.scalar.assert_not_called()


def test_revoke_session():
    db = MagicMock()
    candidate = make_candidate()
    session = make_session(candidate.id)

    db.scalar.return_value = session

    assert revoke_candidate_session(
        db, "test-session-token"
    ) is True

    assert session.revoked_at is not None
    db.commit.assert_not_called()


def test_cannot_revoke_session_twice():
    db = MagicMock()
    candidate = make_candidate()

    db.scalar.return_value = make_session(
        candidate.id, revoked=True
    )

    assert revoke_candidate_session(
        db, "test-session-token"
    ) is False
