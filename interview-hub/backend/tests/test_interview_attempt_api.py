from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.main import app
from app.models.candidate import Candidate
from app.models.interview_attempt import InterviewAttempt
from app.services.session_service import create_candidate_session
from app.services.ai_engine_service import AIEngineUnavailableError

@pytest.fixture
def interview_client(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    assert engine.url.host in ("localhost", "127.0.0.1")
    assert engine.url.port == 5433

    test_engine = create_engine(
        engine.url.set(database="interviewhub_test"),
        pool_pre_ping=True,
    )

    Base.metadata.create_all(test_engine)

    connection = test_engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        transaction.rollback()
        connection.close()
        test_engine.dispose()

def login_candidate(client, db, email):
    candidate = Candidate(
        full_name="Test Candidate",
        email=email,
        age=24,
        profession="Software Engineer",
        location="Cluj-Napoca",
        email_verified_at=datetime.now(timezone.utc),
    )

    db.add(candidate)
    db.flush()

    session_token = create_candidate_session(
        db,
        candidate.id,
    )

    db.commit()

    client.cookies.clear()
    client.cookies.set(
        "interviewhub_session",
        session_token,
        path="/",
    )

    return candidate

def test_attempt_requires_authentication(interview_client):
    client, db = interview_client

    response = client.post("/interviews/attempt")

    assert response.status_code == 401

def test_current_attempt_not_found(interview_client):
    client, db = interview_client
    login_candidate(client, db, "elena@example.com")

    response = client.get("/interviews/current")

    assert response.status_code == 404

def test_repeated_requests_return_same_attempt(interview_client):
    client, db = interview_client
    candidate = login_candidate(
        client,
        db,
        "elena@example.com",
    )

    first = client.post("/interviews/attempt")
    second = client.post("/interviews/attempt")
    current = client.get("/interviews/current")

    assert first.status_code == 200
    assert second.status_code == 200
    assert current.status_code == 200

    first_id = first.json()["id"]

    assert second.json()["id"] == first_id
    assert current.json()["id"] == first_id
    assert first.json()["status"] == "pending"

    count = db.scalar(
        select(func.count())
        .select_from(InterviewAttempt)
        .where(
            InterviewAttempt.candidate_id == candidate.id
        )
    )

    assert count == 1

def test_candidates_have_separate_attempts(interview_client):
    client, db = interview_client

    login_candidate(client, db, "elena@example.com")
    elena_attempt = client.post("/interviews/attempt")

    login_candidate(client, db, "maria@example.com")
    maria_attempt = client.post("/interviews/attempt")
    maria_current = client.get("/interviews/current")

    assert elena_attempt.status_code == 200
    assert maria_attempt.status_code == 200
    assert maria_current.status_code == 200

    assert elena_attempt.json()["id"] != maria_attempt.json()["id"]
    assert maria_current.json()["id"] == maria_attempt.json()["id"]


def test_start_interview_success(
    interview_client,
    monkeypatch,
):
    client, db = interview_client
    candidate = login_candidate(
        client,
        db,
        "elena.start@example.com",
    )

    received_ids = []

    def fake_engine_start(interview_id, topic):
        received_ids.append(interview_id)

        return {
            "interview_id": str(interview_id),
            "question": "Tell me about your experience.",
            "stage": "BACKGROUND",
        }

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_engine_start,
    )

    response = client.post("/interviews/start")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "in_progress"
    assert data["stage"] == "BACKGROUND"
    assert data["question"] == "Tell me about your experience."

    attempt = db.scalar(
        select(InterviewAttempt).where(
            InterviewAttempt.candidate_id == candidate.id
        )
    )

    assert attempt.interview_id == attempt.id
    assert str(attempt.id) == data["interview_id"]
    assert attempt.started_at is not None
    assert received_ids == [attempt.id]

def test_repeated_start_reuses_interview(
    interview_client,
    monkeypatch,
):
    client, db = interview_client
    login_candidate(
        client,
        db,
        "elena.retry@example.com",
    )

    received_ids = []

    def fake_engine_start(interview_id, topic):
        received_ids.append(interview_id)

        return {
            "interview_id": str(interview_id),
            "question": "Tell me about your experience.",
            "stage": "BACKGROUND",
        }

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_engine_start,
    )

    first = client.post("/interviews/start")
    second = client.post("/interviews/start")

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["attempt_id"] == second.json()["attempt_id"]
    assert first.json()["interview_id"] == second.json()["interview_id"]

    assert len(received_ids) == 2
    assert received_ids[0] == received_ids[1]

def test_engine_failure_preserves_attempt(
    interview_client,
    monkeypatch,
):
    client, db = interview_client
    candidate = login_candidate(
        client,
        db,
        "elena.failure@example.com",
    )

    def fake_engine_failure(interview_id, topic):
        raise AIEngineUnavailableError(
            "Service unavailable"
        )

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_engine_failure,
    )

    response = client.post("/interviews/start")

    assert response.status_code == 503

    attempt = db.scalar(
        select(InterviewAttempt).where(
            InterviewAttempt.candidate_id == candidate.id
        )
    )

    assert attempt is not None
    assert attempt.status == "pending"
    assert attempt.interview_id is None
    assert attempt.started_at is None

def test_current_recovers_question_after_refresh(
    interview_client,
    monkeypatch,
):
    client, db = interview_client

    login_candidate(
        client,
        db,
        "elena.recovery@example.com",
    )

    def fake_start(interview_id, topic):
        return {
            "interview_id": str(interview_id),
            "stage": "BACKGROUND",
            "question": "Tell me about yourself.",
        }

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_start,
    )

    start_response = client.post("/interviews/start")
    assert start_response.status_code == 200

    recovered_ids = []

    def fake_get_state(interview_id):
        recovered_ids.append(interview_id)

        return {
            "stage": "BACKGROUND",
            "question": "Tell me about yourself.",
            "question_number": 1,
            "completed": False,
        }

    monkeypatch.setattr(
        "app.main.get_ai_interview_state",
        fake_get_state,
    )

    first = client.get("/interviews/current")
    second = client.get("/interviews/current")

    assert first.status_code == 200
    assert second.status_code == 200

    data = first.json()

    assert first.json() == second.json()
    assert data["status"] == "in_progress"
    assert data["stage"] == "BACKGROUND"
    assert data["question"] == "Tell me about yourself."
    assert data["question_number"] == 1
    assert data["id"] == start_response.json()["attempt_id"]
    assert len(recovered_ids) == 2
    assert recovered_ids[0] == recovered_ids[1]

def test_candidate_cannot_recover_another_attempt(
    interview_client,
    monkeypatch,
):
    client, db = interview_client

    login_candidate(
        client,
        db,
        "elena.isolation@example.com",
    )

    def fake_start(interview_id, topic):
        return {
            "interview_id": str(interview_id),
            "stage": "BACKGROUND",
            "question": "Elena's interview question.",
        }

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_start,
    )

    elena_start = client.post("/interviews/start")
    assert elena_start.status_code == 200

    login_candidate(
        client,
        db,
        "maria.isolation@example.com",
    )

    def unexpected_engine_call(interview_id):
        pytest.fail("The AI engine should not be called")

    monkeypatch.setattr(
        "app.main.get_ai_interview_state",
        unexpected_engine_call,
    )

    response = client.get("/interviews/current")

    assert response.status_code == 404

    reserved = client.post("/interviews/attempt")
    assert reserved.status_code == 200

    maria_current = client.get("/interviews/current")

    assert maria_current.status_code == 200
    assert maria_current.json()["status"] == "pending"
    assert maria_current.json()["question"] is None
    assert maria_current.json()["stage"] is None

def test_current_requires_authentication(interview_client):
    client, db = interview_client

    response = client.get("/interviews/current")

    assert response.status_code == 401

def test_answer_requires_candidate_session(interview_client):
    client, db = interview_client

    response = client.post(
        "/interviews/answer",
        json={
            "question_number": 1,
            "answer": "My answer",
        },
    )

    assert response.status_code == 401

def test_candidate_cannot_answer_before_start(interview_client):
    client, db = interview_client

    login_candidate(
        client,
        db,
        "maria.beforestart@example.com",
    )

    client.post("/interviews/attempt")

    response = client.post(
        "/interviews/answer",
        json={
            "question_number": 1,
            "answer": "My answer",
        },
    )

    assert response.status_code == 409

def test_candidate_answer_advances_interview(
    interview_client,
    monkeypatch,
):
    client, db = interview_client

    login_candidate(
        client,
        db,
        "elena.answer@example.com",
    )

    def fake_start(interview_id, topic):
        return {
            "interview_id": str(interview_id),
            "stage": "BACKGROUND",
            "question": "Tell me about yourself.",
        }

    def fake_submit(interview_id, question_number, answer):
        assert question_number == 1
        assert answer == "I build Python applications."

        return {
            "stage": "MOTIVATION",
            "question": "Why do you want this role?",
            "question_number": 2,
            "completed": False,
        }

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_start,
    )
    monkeypatch.setattr(
        "app.main.submit_ai_answer",
        fake_submit,
    )

    started = client.post("/interviews/start")
    assert started.status_code == 200

    response = client.post(
        "/interviews/answer",
        json={
            "question_number": 1,
            "answer": "I build Python applications.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["stage"] == "MOTIVATION"
    assert response.json()["question_number"] == 2

def test_final_answer_marks_attempt_completed(
    interview_client,
    monkeypatch,
):
    client, db = interview_client

    candidate = login_candidate(
        client,
        db,
        "elena.complete@example.com",
    )

    def fake_start(interview_id, topic):
        return {
            "interview_id": str(interview_id),
            "stage": "BACKGROUND",
            "question": "Question one.",
        }

    def fake_submit(interview_id, question_number, answer):
        return {
            "stage": "SUMMARY",
            "question": None,
            "question_number": None,
            "completed": True,
        }

    monkeypatch.setattr(
        "app.main.start_ai_interview",
        fake_start,
    )
    monkeypatch.setattr(
        "app.main.submit_ai_answer",
        fake_submit,
    )

    assert client.post("/interviews/start").status_code == 200

    response = client.post(
        "/interviews/answer",
        json={
            "question_number": 1,
            "answer": "Final answer",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed"] is True

    attempt = db.scalar(
        select(InterviewAttempt).where(
            InterviewAttempt.candidate_id == candidate.id
        )
    )

    assert attempt.status == "completed"
    assert attempt.completed_at is not None