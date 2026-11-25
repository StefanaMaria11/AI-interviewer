from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from urllib import response
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)


def make_candidate():
    return MagicMock(
        id=uuid4(),
        full_name="Elena Popescu",
        email="elena.popescu@example.com",
        profession="Software Engineer",
        location="Cluj-Napoca",
        email_verified_at=datetime.now(timezone.utc),
    )


def test_profile_requires_authentication(auth_client):
    client, db = auth_client

    with patch(
        "app.main.get_authenticated_candidate",
        return_value=None,
    ):
        response = client.get("/auth/me")

    assert response.status_code == 401


def test_candidate_can_access_own_profile(auth_client):
    client, db = auth_client
    candidate = make_candidate()

    client.cookies.set(
        "interviewhub_session",
        "valid-session-token",
    )

    with patch(
        "app.main.get_authenticated_candidate",
        return_value=candidate,
    ) as authenticate:
        response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["candidate_id"] == str(candidate.id)
    assert response.json()["email"] == candidate.email

    authenticate.assert_called_once_with(
        db, "valid-session-token"
    )


def test_logout_revokes_session(auth_client):
    client, db = auth_client

    client.cookies.set(
        "interviewhub_session",
        "valid-session-token",
    )

    with patch(
        "app.main.revoke_candidate_session",
        return_value=True,
    ) as revoke:
        response = client.post("/auth/logout")

    assert response.status_code == 200

    revoke.assert_called_once_with(
        db, "valid-session-token"
    )

    db.commit.assert_called_once()

    cookie_header = response.headers["set-cookie"]

    assert "interviewhub_session=" in cookie_header
    assert "max-age=0" in cookie_header.lower()
    assert "httponly" in cookie_header.lower()



def test_logout_without_session(auth_client):
    client, db = auth_client

    with patch(
        "app.main.revoke_candidate_session",
        return_value=False,
    ):
        response = client.post("/auth/logout")

    assert response.status_code == 200
    db.commit.assert_not_called()
