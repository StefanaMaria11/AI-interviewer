from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import main as engine_api
from backend.models.interview import InterviewStage
from backend.services import storage_service as storage_module
from backend.services.llm_service import LLMServiceError

HEADERS = {
    "X-Internal-API-Key": "test-internal-secret",
}

@pytest.fixture
def answer_client(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "AI_ENGINE_INTERNAL_KEY",
        "test-internal-secret",
    )
    monkeypatch.setattr(
        storage_module,
        "DATA_FOLDER",
        str(tmp_path),
    )

    generated = []

    def fake_generate_question(interview):
        question = f"Question for {interview.stage.value}"
        generated.append(question)
        interview.questions.append(question)
        return question

    monkeypatch.setattr(
        engine_api.interviewer_service,
        "generate_question",
        fake_generate_question,
    )

    with TestClient(engine_api.app) as client:
        yield client, generated

def create_interview(client):
    interview_id = uuid4()

    response = client.post(
        f"/internal/interviews/{interview_id}/start",
        headers=HEADERS,
        json={"topic": "Software Engineering"},
    )

    assert response.status_code == 200
    return interview_id

def submit_answer(client, interview_id, number, answer):
    return client.post(
        f"/internal/interviews/{interview_id}/answer",
        headers=HEADERS,
        json={
            "question_number": number,
            "answer": answer,
        },
    )

def test_answer_requires_internal_authentication(answer_client):
    client, generated = answer_client
    interview_id = create_interview(client)

    response = client.post(
        f"/internal/interviews/{interview_id}/answer",
        json={
            "question_number": 1,
            "answer": "My answer",
        },
    )

    assert response.status_code == 403

def test_answer_advances_stage(answer_client):
    client, generated = answer_client
    interview_id = create_interview(client)

    response = submit_answer(
        client,
        interview_id,
        1,
        "I build Python applications.",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["stage"] == "MOTIVATION"
    assert data["question_number"] == 2
    assert data["completed"] is False

    saved = engine_api.storage_service.load_interview(
        interview_id
    )

    assert saved.answers == [
        "I build Python applications."
    ]
    assert len(saved.questions) == 2

def test_duplicate_answer_does_not_advance_twice(answer_client):
    client, generated = answer_client
    interview_id = create_interview(client)

    first = submit_answer(
        client,
        interview_id,
        1,
        "I build Python applications.",
    )

    second = submit_answer(
        client,
        interview_id,
        1,
        "I build Python applications.",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(generated) == 2

    saved = engine_api.storage_service.load_interview(
        interview_id
    )

    assert len(saved.answers) == 1
    assert len(saved.questions) == 2

def test_different_answer_for_same_question_is_rejected(answer_client):
    client, generated = answer_client
    interview_id = create_interview(client)

    first = submit_answer(
        client,
        interview_id,
        1,
        "My original answer.",
    )

    second = submit_answer(
        client,
        interview_id,
        1,
        "A different answer.",
    )

    assert first.status_code == 200
    assert second.status_code == 409

def test_answer_survives_llm_failure(
    answer_client,
    monkeypatch,
):
    client, generated = answer_client
    interview_id = create_interview(client)

    original_generate = (
        engine_api.interviewer_service.generate_question
    )

    def fail_on_next_question(interview):
        if interview.stage == InterviewStage.MOTIVATION:
            raise LLMServiceError("Simulated Ollama failure")

        return original_generate(interview)

    monkeypatch.setattr(
        engine_api.interviewer_service,
        "generate_question",
        fail_on_next_question,
    )

    failed = submit_answer(
        client,
        interview_id,
        1,
        "My experience is in Python.",
    )

    assert failed.status_code == 503

    saved = engine_api.storage_service.load_interview(
        interview_id
    )

    assert len(saved.answers) == 1
    assert len(saved.questions) == 1
    assert saved.stage == InterviewStage.MOTIVATION

    monkeypatch.setattr(
        engine_api.interviewer_service,
        "generate_question",
        original_generate,
    )

    retried = submit_answer(
        client,
        interview_id,
        1,
        "My experience is in Python.",
    )

    assert retried.status_code == 200
    assert retried.json()["question_number"] == 2

    saved = engine_api.storage_service.load_interview(
        interview_id
    )

    assert len(saved.answers) == 1
    assert len(saved.questions) == 2

def test_final_answer_completes_interview(answer_client):
    client, generated = answer_client
    interview_id = create_interview(client)

    response = None

    for question_number in range(1, 6):
        response = submit_answer(
            client,
            interview_id,
            question_number,
            f"Answer number {question_number}",
        )

        assert response.status_code == 200

    assert response.json()["stage"] == "SUMMARY"
    assert response.json()["completed"] is True
    assert response.json()["question"] is None
    assert response.json()["question_number"] is None

    saved = engine_api.storage_service.load_interview(
        interview_id
    )

    assert len(saved.answers) == 5
    assert saved.stage == InterviewStage.SUMMARY

    retried = submit_answer(
        client,
        interview_id,
        5,
        "Answer number 5",
    )

    assert retried.status_code == 200
    assert retried.json()["completed"] is True
    assert len(generated) == 5