from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app

@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)

def make_admin(active=True, mfa_enabled=True):
    return SimpleNamespace(
        id=uuid4(),
        email="admin@interviewer.com",
        password_hash="stored-hash",
        is_active=active,
        mfa_enabled_at=(
            datetime.now(timezone.utc)
            if mfa_enabled else None
        ),
        totp_secret_encrypted=(
            "encrypted-secret" if mfa_enabled else None
        ),
        last_login_at=None,
    )

def login_payload():
    return {
        "email": "admin@interviewer.com",
        "password": "test-password",
        "totp_code": "123456",
    }

def test_admin_login_success(admin_client):
    client, db = admin_client
    admin = make_admin()
    db.scalar.return_value = admin

    with (
        patch(
            "app.main.verify_admin_password",
            return_value=True,
        ) as password_check,
        patch(
            "app.main.verify_admin_totp",
            return_value=True,
        ) as mfa_check,
        patch(
            "app.main.create_admin_session",
            return_value="test-admin-session",
        ) as create_session,
    ):
        response = client.post(
            "/admin/auth/login",
            json=login_payload(),
        )

    assert response.status_code == 200
    password_check.assert_called_once()
    mfa_check.assert_called_once()
    create_session.assert_called_once()

    assert admin.last_login_at is not None
    db.commit.assert_called_once()

    cookie = response.headers["set-cookie"]
    assert "interviewhub_admin_session=test-admin-session" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=strict" in cookie.lower()
    assert "path=/admin" in cookie.lower()

def test_admin_login_rejects_wrong_password(admin_client):
    client, db = admin_client
    db.scalar.return_value = make_admin()

    with (
        patch(
            "app.main.verify_admin_password",
            return_value=False,
        ),
        patch("app.main.verify_admin_totp") as mfa_check,
        patch("app.main.create_admin_session") as create_session,
    ):
        response = client.post(
            "/admin/auth/login",
            json=login_payload(),
        )

    assert response.status_code == 401
    mfa_check.assert_not_called()
    create_session.assert_not_called()
    db.commit.assert_not_called()

def test_admin_login_rejects_wrong_mfa(admin_client):
    client, db = admin_client
    db.scalar.return_value = make_admin()

    with (
        patch(
            "app.main.verify_admin_password",
            return_value=True,
        ),
        patch(
            "app.main.verify_admin_totp",
            return_value=False,
        ),
        patch("app.main.create_admin_session") as create_session,
    ):
        response = client.post(
            "/admin/auth/login",
            json=login_payload(),
        )

    assert response.status_code == 401
    create_session.assert_not_called()
    db.commit.assert_not_called()

def test_admin_login_rejects_unknown_email(admin_client):
    client, db = admin_client
    db.scalar.return_value = None

    response = client.post(
        "/admin/auth/login",
        json=login_payload(),
    )

    assert response.status_code == 401
    db.commit.assert_not_called()

def test_admin_login_rejects_inactive_admin(admin_client):
    client, db = admin_client
    db.scalar.return_value = make_admin(active=False)

    response = client.post(
        "/admin/auth/login",
        json=login_payload(),
    )

    assert response.status_code == 401
    db.commit.assert_not_called()

def test_admin_login_requires_mfa_enrollment(admin_client):
    client, db = admin_client
    db.scalar.return_value = make_admin(mfa_enabled=False)

    response = client.post(
        "/admin/auth/login",
        json=login_payload(),
    )

    assert response.status_code == 401
    db.commit.assert_not_called()

def test_admin_profile_requires_authentication(admin_client):
    client, db = admin_client

    with patch(
        "app.main.get_authenticated_admin",
        return_value=None,
    ):
        response = client.get("/admin/auth/me")

    assert response.status_code == 401

def test_admin_can_access_own_profile(admin_client):
    client, db = admin_client
    admin = make_admin()

    client.cookies.set(
        "interviewhub_admin_session",
        "valid-admin-token",
        path="/admin",
    )

    with patch(
        "app.main.get_authenticated_admin",
        return_value=admin,
    ) as authenticate:
        response = client.get("/admin/auth/me")

    assert response.status_code == 200
    assert response.json()["admin_id"] == str(admin.id)
    assert response.json()["email"] == admin.email

    authenticate.assert_called_once_with(
        db, "valid-admin-token"
    )

def test_candidate_cookie_cannot_access_admin(admin_client):
    client, db = admin_client

    client.cookies.set(
        "interviewhub_session",
        "candidate-session-token",
    )

    with patch(
        "app.main.get_authenticated_admin",
        return_value=None,
    ) as authenticate:
        response = client.get("/admin/auth/me")

    assert response.status_code == 401
    authenticate.assert_called_once_with(db, None)

def test_admin_logout_revokes_session(admin_client):
    client, db = admin_client

    client.cookies.set(
        "interviewhub_admin_session",
        "valid-admin-token",
        path="/admin",
    )

    with patch(
        "app.main.revoke_admin_session",
        return_value=True,
    ) as revoke:
        response = client.post("/admin/auth/logout")

    assert response.status_code == 200
    revoke.assert_called_once_with(
        db, "valid-admin-token"
    )
    db.commit.assert_called_once()

    cookie = response.headers["set-cookie"]
    assert "interviewhub_admin_session=" in cookie
    assert "max-age=0" in cookie.lower()
    assert "path=/admin" in cookie.lower()

def test_admin_logout_without_session(admin_client):
    client, db = admin_client

    with patch(
        "app.main.revoke_admin_session",
        return_value=False,
    ):
        response = client.post("/admin/auth/logout")

    assert response.status_code == 200
    db.commit.assert_not_called()