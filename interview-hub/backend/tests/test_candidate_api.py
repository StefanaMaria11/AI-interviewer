from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.database import get_db


@pytest.fixture
def client_with_db():
    db = MagicMock()

    # Simulate the database assigning an ID
    db.refresh.side_effect = lambda candidate: setattr(
        candidate, "id", uuid4()
    )

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

    saved_candidate = db.add.call_args.args[0]
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
