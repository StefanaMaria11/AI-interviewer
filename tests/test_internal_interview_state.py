from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import main as engine_api
from backend.models.interview import Interview
from backend.models.interview import InterviewStage
from backend.services import storage_service as storage_module

@pytest.fixture
def state_client(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "AI_ENGINE_INTERNAL_KEY",
        "test-internal-secret",
    )

    monkeypatch.setattr(
        storage_module,
        "DATA_FOLDER",
        str(tmp_path),
    )

    with TestClient(engine_api.app) as client:
        yield client

def test_state_requires_internal_authentication(state_client):
    response = state_client.get(
        f"/internal/interviews/{uuid4()}/state"
    )

    assert response.status_code == 403

def test_state_recovers_unanswered_question(state_client):
    interview_id = uuid4()

    interview = Interview(
        topic="Software Engineering",
        stage=InterviewStage.MOTIVATION,
        questions=[
            "Tell me about yourself.",
            "Why do you want this role?",
        ],
        answers=[
            "I am a software engineer.",
        ],
    )

    engine_api.storage_service.save_interview(
        interview_id,
        interview,
    )

    response = state_client.get(
        f"/internal/interviews/{interview_id}/state",
        headers={
            "X-Internal-API-Key": "test-internal-secret",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "interview_id": str(interview_id),
        "stage": "MOTIVATION",
        "question": "Why do you want this role?",
        "question_number": 2,
        "completed": False,
    }

def test_completed_state_has_no_active_question(state_client):
    interview_id = uuid4()

    interview = Interview(
        topic="Software Engineering",
        stage=InterviewStage.END,
        questions=["Tell me about yourself."],
        answers=["I am a software engineer."],
        summary="Interview completed.",
    )

    engine_api.storage_service.save_interview(
        interview_id,
        interview,
    )

    response = state_client.get(
        f"/internal/interviews/{interview_id}/state",
        headers={
            "X-Internal-API-Key": "test-internal-secret",
        },
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "END"
    assert response.json()["question"] is None
    assert "summary" not in response.json()
    assert "answers" not in response.json()