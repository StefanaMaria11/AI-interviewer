from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.database import get_db


@pytest.fixture
def client_with_db():
    db = MagicMock()

    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)

def test_register_candidate_success(client_with_db):
    client, db = client_with_db

    response = client.post(
        "/candidates",
        json={
            "full_name": "Elena Popescu",
            "email": "Elena.Popescu@Example.com",
            "age": 24,
            "profession": "Software Engineer",
            "location": "Cluj-Napoca"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["candidate_id"]
    assert data["email_verified"] is False

    saved_candidate = db.add.call_args_list[0].args[0]
    saved_token = db.add.call_args_list[1].args[0]

    assert saved_token.candidate_id == saved_candidate.id
    assert len(saved_token.token_hash) == 64
    assert "token" not in data
    assert saved_candidate.email == "elena.popescu@example.com"

    db.commit.assert_called_once()

def test_register_duplicate_email(client_with_db):
    client, db = client_with_db

    db.commit.side_effect = IntegrityError(
        "INSERT INTO candidates",
        {},
        Exception("duplicate email")
    )

    response = client.post(
        "/candidates",
        json={
            "full_name": "Elena Popescu",
            "email": "elena.popescu@example.com",
            "age": 24,
            "profession": "Software Engineer",
            "location": "Cluj-Napoca"
        }
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Candidate already registered"
    )

    db.rollback.assert_called_once()

def test_register_invalid_email(client_with_db):
    client, db = client_with_db

    response = client.post(
        "/candidates",
        json={
            "full_name": "Elena Popescu",
            "email": "invalid-email",
            "age": 24,
            "profession": "Software Engineer",
            "location": "Cluj-Napoca"
        }
    )

    assert response.status_code == 422
    db.add.assert_not_called()

def test_verify_email_success(client_with_db):
    client, db = client_with_db

    with patch(
        "app.main.verify_email_token",
        return_value=True
    ) as verifier:
        response = client.post(
            "/auth/verify-email",
            json={"token": "valid-test-token"}
        )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Email verified successfully"
    )

    verifier.assert_called_once_with(db, "valid-test-token")
    db.commit.assert_called_once()


def test_verify_email_invalid_token(client_with_db):
    client, db = client_with_db

    with patch(
        "app.main.verify_email_token",
        return_value=False
    ):
        response = client.post(
            "/auth/verify-email",
            json={"token": "invalid-token"}
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid or expired verification token"
    )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_verify_email_empty_token(client_with_db):
    client, db = client_with_db

    response = client.post(
        "/auth/verify-email",
        json={"token": ""}
    )

    assert response.status_code == 422
    db.commit.assert_not_called()


def test_verify_email_commit_failure(client_with_db):
    client, db = client_with_db
    db.commit.side_effect = RuntimeError("Database failure")

    with patch(
        "app.main.verify_email_token",
        return_value=True
    ):
        with pytest.raises(RuntimeError, match="Database failure"):
            client.post(
                "/auth/verify-email",
                json={"token": "valid-test-token"}
            )

    db.rollback.assert_called_once()
