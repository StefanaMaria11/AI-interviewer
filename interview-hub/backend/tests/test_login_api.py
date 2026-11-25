from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


@pytest.fixture
def login_client(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)

def make_candidate(verified=True):
    return SimpleNamespace(
        id=uuid4(),
        email="elena.popescu@example.com",
        email_verified_at=(
            datetime.now(timezone.utc) if verified else None
        ),
    )

def test_request_login_for_verified_candidate(login_client):
    client, db = login_client
    candidate = make_candidate()
    db.scalar.return_value = candidate

    with (
        patch(
            "app.main.create_login_token",
            return_value="test-login-token",
        ) as create_token,
        patch("app.main.send_login_email") as send_email,
    ):
        response = client.post(
            "/auth/request-login",
            json={"email": "Elena.Popescu@Example.com"},
        )

    assert response.status_code == 200

    create_token.assert_called_once_with(db, candidate)
    send_email.assert_called_once_with(
        candidate.email,
        "test-login-token",
    )
    db.commit.assert_called_once()

def test_request_login_for_unknown_email(login_client):
    client, db = login_client
    db.scalar.return_value = None

    with patch("app.main.send_login_email") as send_email:
        response = client.post(
            "/auth/request-login",
            json={"email": "unknown@example.com"},
        )

    assert response.status_code == 200
    send_email.assert_not_called()
    db.commit.assert_not_called()

def test_request_login_for_unverified_candidate(login_client):
    client, db = login_client
    db.scalar.return_value = make_candidate(verified=False)

    with patch("app.main.send_login_email") as send_email:
        response = client.post(
            "/auth/request-login",
            json={"email": "elena.popescu@example.com"},
        )

    assert response.status_code == 200
    send_email.assert_not_called()
    db.commit.assert_not_called()

def test_unknown_and_verified_responses_match(login_client):
    client, db = login_client
    candidate = make_candidate()

    with (
        patch(
            "app.main.create_login_token",
            return_value="test-login-token",
        ),
        patch("app.main.send_login_email"),
    ):
        db.scalar.return_value = candidate
        known = client.post(
            "/auth/request-login",
            json={"email": candidate.email},
        )

        db.scalar.return_value = None
        unknown = client.post(
            "/auth/request-login",
            json={"email": "unknown@example.com"},
        )

    assert known.status_code == unknown.status_code
    assert known.json() == unknown.json()

def test_complete_login_success(login_client):
    client, db = login_client
    candidate = make_candidate()

    with (
        patch(
            "app.main.consume_login_token",
            return_value=candidate,
        ) as consume,
        patch(
            "app.main.create_candidate_session",
            return_value="new-session-token",
        ) as create_session,
    ):
        response = client.post(
            "/auth/complete-login",
            json={"token": "valid-login-token"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"

    consume.assert_called_once_with(db, "valid-login-token")
    create_session.assert_called_once_with(db, candidate.id)
    db.commit.assert_called_once()

    cookie = response.headers["set-cookie"]
    assert "interviewhub_session=new-session-token" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=strict" in cookie.lower()

def test_complete_login_rejects_invalid_token(login_client):
    client, db = login_client

    with patch(
        "app.main.consume_login_token",
        return_value=None,
    ):
        response = client.post(
            "/auth/complete-login",
            json={"token": "invalid-token"},
        )

    assert response.status_code == 400
    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_complete_login_rejects_empty_token(login_client):
    client, db = login_client

    response = client.post(
        "/auth/complete-login",
        json={"token": ""},
    )

    assert response.status_code == 422
    db.commit.assert_not_called()

def test_complete_login_rolls_back_on_failure(login_client):
    client, db = login_client
    candidate = make_candidate()
    db.commit.side_effect = RuntimeError("Database failure")

    with (
        patch(
            "app.main.consume_login_token",
            return_value=candidate,
        ),
        patch(
            "app.main.create_candidate_session",
            return_value="new-session-token",
        ),
    ):
        with pytest.raises(RuntimeError, match="Database failure"):
            client.post(
                "/auth/complete-login",
                json={"token": "valid-login-token"},
            )

    db.rollback.assert_called_once()