from datetime import datetime, timezone

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.main import app
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.models.candidate import Candidate
from app.services.admin_password_service import hash_admin_password
from app.services.admin_mfa_service import encrypt_totp_secret
from app.services.session_service import create_candidate_session

TEST_PASSWORD = "Integration-Test-Password-2026"

@pytest.fixture(scope="module")
def test_engine():
    assert engine.url.host in ("localhost", "127.0.0.1")
    assert engine.url.port == 5433

    url = engine.url.set(database="interviewhub_test")
    isolated_engine = create_engine(url, pool_pre_ping=True)

    Base.metadata.create_all(isolated_engine)

    yield isolated_engine

    isolated_engine.dispose()

@pytest.fixture
def integration_client(test_engine, monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    connection = test_engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        transaction.rollback()
        connection.close()

def create_test_admin(db):
    secret = pyotp.random_base32()

    admin = Admin(
        email="integration-admin@example.com",
        password_hash=hash_admin_password(TEST_PASSWORD),
        is_active=True,
        totp_secret_encrypted=encrypt_totp_secret(secret),
        mfa_enabled_at=datetime.now(timezone.utc),
    )

    db.add(admin)
    db.commit()

    return admin, secret

def make_login_payload(secret):
    return {
        "email": "integration-admin@example.com",
        "password": TEST_PASSWORD,
        "totp_code": pyotp.TOTP(secret).now(),
    }

def test_real_admin_login_and_logout(integration_client):
    client, db = integration_client
    admin, secret = create_test_admin(db)

    response = client.post(
        "/admin/auth/login",
        json=make_login_payload(secret),
    )

    assert response.status_code == 200

    profile = client.get("/admin/auth/me")

    assert profile.status_code == 200
    assert profile.json()["admin_id"] == str(admin.id)

    logout = client.post("/admin/auth/logout")

    assert logout.status_code == 200
    assert client.get("/admin/auth/me").status_code == 401

    sessions = db.scalars(
        select(AdminSession).where(
            AdminSession.admin_id == admin.id
        )
    ).all()

    assert len(sessions) == 1
    assert sessions[0].revoked_at is not None

def test_reject_replayed_totp_code(integration_client):
    client, db = integration_client
    admin, secret = create_test_admin(db)

    payload = make_login_payload(secret)

    first = client.post(
        "/admin/auth/login",
        json=payload,
    )

    second = client.post(
        "/admin/auth/login",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 401

    sessions = db.scalars(
        select(AdminSession).where(
            AdminSession.admin_id == admin.id
        )
    ).all()

    assert len(sessions) == 1

def test_invalid_mfa_creates_no_session(integration_client):
    client, db = integration_client
    admin, secret = create_test_admin(db)

    payload = make_login_payload(secret)

    payload["totp_code"] = (
        "000000"
        if payload["totp_code"] != "000000"
        else "000001"
    )

    response = client.post(
        "/admin/auth/login",
        json=payload,
    )

    assert response.status_code == 401

    sessions = db.scalars(
        select(AdminSession).where(
            AdminSession.admin_id == admin.id
        )
    ).all()

    assert len(sessions) == 0

def test_candidate_session_cannot_access_admin(integration_client):
    client, db = integration_client

    candidate = Candidate(
        full_name="Elena Popescu",
        email="elena.integration@example.com",
        age=24,
        profession="Software Engineer",
        location="Cluj-Napoca",
        email_verified_at=datetime.now(timezone.utc),
    )

    db.add(candidate)
    db.flush()

    candidate_token = create_candidate_session(
        db,
        candidate.id,
    )

    db.commit()

    client.cookies.set(
        "interviewhub_session",
        candidate_token,
        path="/",
    )

    response = client.get("/admin/auth/me")

    assert response.status_code == 401