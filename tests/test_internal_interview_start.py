from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import main as engine_api
from backend.services import storage_service as storage_module

@pytest.fixture
def engine_client(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "AI_ENGINE_INTERNAL_KEY",
        "test-internal-secret",
    )

    monkeypatch.setattr(
        storage_module,
        "DATA_FOLDER",
        str(tmp_path),
    )

    generated_questions = []

    def fake_generate_question(interview):
        question = "Tell me about your experience."
        generated_questions.append(question)
        interview.questions.append(question)
        return question

    monkeypatch.setattr(
        engine_api.interviewer_service,
        "generate_question",
        fake_generate_question,
    )

    with TestClient(engine_api.app) as client:
        yield client, generated_questions

def test_internal_start_requires_authentication(engine_client):
    client, generated = engine_client

    response = client.post(
        f"/internal/interviews/{uuid4()}/start",
        json={"topic": "Software Engineering"},
    )

    assert response.status_code == 403
    assert len(generated) == 0

def test_repeated_start_reuses_interview(engine_client):
    client, generated = engine_client
    interview_id = uuid4()

    url = f"/internal/interviews/{interview_id}/start"

    headers = {
        "X-Internal-API-Key": "test-internal-secret",
    }

    first = client.post(
        url,
        headers=headers,
        json={"topic": "Software Engineering"},
    )

    second = client.post(
        url,
        headers=headers,
        json={"topic": "Software Engineering"},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json() == second.json()
    assert first.json()["interview_id"] == str(interview_id)
    assert first.json()["stage"] == "BACKGROUND"
    assert len(generated) == 1

def test_reject_different_topic_for_existing_interview(
    engine_client,
):
    client, generated = engine_client
    interview_id = uuid4()

    url = f"/internal/interviews/{interview_id}/start"

    headers = {
        "X-Internal-API-Key": "test-internal-secret",
    }

    first = client.post(
        url,
        headers=headers,
        json={"topic": "Software Engineering"},
    )

    second = client.post(
        url,
        headers=headers,
        json={"topic": "Data Science"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(generated) == 1