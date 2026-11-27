import pytest
from fastapi.testclient import TestClient
from backend.main import app, interviewer_service
from backend.models.interview import InterviewStage, InterviewFeedback, FeedbackPoint

client = TestClient(
    app,
    headers={
        "X-Internal-API-Key": "test-internal-secret",
    },
)

def fake_generate_question(interview):
    return "Fake interview question?"

def fake_generate_summary(interview):
    interview.summary = "Fake summary"
    interview.stage = InterviewStage.END
    return interview.summary


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setenv(
        "AI_ENGINE_INTERNAL_KEY",
        "test-internal-secret",
    )
    
    monkeypatch.setattr(
        interviewer_service,
        "generate_question",
        fake_generate_question
    )

    monkeypatch.setattr(
        interviewer_service,
        "generate_summary",
        fake_generate_summary
    )

def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "AI Interviewer API running"
    }

def test_start_interview():
    response = client.post("/start-interview", 
                           json={
                               "topic":"AI Engineering Intern"
                           })

    assert response.status_code == 200

    data = response.json()

    assert "interview_id" in data
    assert data["question"] == ("Fake interview question?")
    assert data["stage"] == "BACKGROUND"

def test_get_interview():
    start = client.post("/start-interview", 
                        json={
                            "topic":"AI Engineering Intern"
                            })
    interview_id = (start.json()["interview_id"])

    response = client.get(f"/interview/{interview_id}")

    assert response.status_code == 200

    data=response.json()

    assert data["topic"] == ("AI Engineering Intern")
    assert data["stage"] == "BACKGROUND"

def test_answer_interview():
    start = client.post("/start-interview",
                        json={
                            "topic":"AI Engineering Intern"
                            })

    interview_id = (start.json()["interview_id"])

    response = client.post(
        f"/interview/{interview_id}/answer",
        json={
            "answer":"I am a computer science graduate."
        }
    )

    assert response.status_code == 200

    data=response.json()

    assert "question" in data
    assert "stage" in data


def test_missing_interview():
    missing_id = "00000000-0000-4000-8000-000000000000"

    response = client.get(f"/interview/{missing_id}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Interview not found"
    }


def test_invalid_interview_id():
    response = client.get("/interview/not-a-uuid")

    assert response.status_code == 422



def test_summary():
    start = client.post(
        "/start-interview",
        json={"topic": "AI Engineering Intern"}
    )

    interview_id = start.json()["interview_id"]

    for _ in range(5):
        response = client.post(
            f"/interview/{interview_id}/answer",
            json={"answer": "Test answer"}
        )
        assert response.status_code == 200

    response = client.get(
        f"/interview/{interview_id}/summary"
    )

    assert response.status_code == 200
    assert response.json() == {
        "summary": "Fake summary"
    }



def test_summary_before_interview_completion():
    start = client.post(
        "/start-interview",
        json={"topic": "AI Engineering Intern"}
    )

    interview_id = start.json()["interview_id"]

    response = client.get(
        f"/interview/{interview_id}/summary"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Interview is not finished"
    }

def test_cannot_answer_completed_interview():
    start = client.post(
        "/start-interview",
        json={"topic": "AI Engineering Intern"}
    )

    interview_id = start.json()["interview_id"]

    # Complete all five interview stages
    for _ in range(5):
        response = client.post(
            f"/interview/{interview_id}/answer",
            json={"answer": "Test answer"}
        )
        assert response.status_code == 200

    # Generate the final summary
    summary_response = client.get(
        f"/interview/{interview_id}/summary"
    )

    assert summary_response.status_code == 200

    # Attempt to answer after completion
    response = client.post(
        f"/interview/{interview_id}/answer",
        json={"answer": "Another answer"}
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Interview is already finished"
    }

def test_summary_generated_only_once(monkeypatch):
    call_count = 0

    def tracked_generate_summary(interview):
        nonlocal call_count
        call_count += 1
        return fake_generate_summary(interview)

    monkeypatch.setattr(
        interviewer_service,
        "generate_summary",
        tracked_generate_summary
    )

    start = client.post(
        "/start-interview",
        json={"topic": "AI Engineering Intern"}
    )

    interview_id = start.json()["interview_id"]

    # Complete the interview
    for _ in range(5):
        response = client.post(
            f"/interview/{interview_id}/answer",
            json={"answer": "Test answer"}
        )
        assert response.status_code == 200

    # Request summary twice
    first = client.get(
        f"/interview/{interview_id}/summary"
    )

    second = client.get(
        f"/interview/{interview_id}/summary"
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json() == second.json()

    # The LLM should only be called once
    assert call_count == 1

def test_feedback_endpoint(monkeypatch):
    expected_feedback = InterviewFeedback(
        strengths=[
            FeedbackPoint(
                observation="Backend experience",
                evidence="I built a FastAPI application."
            )
        ],
        improvements=[],
        overall_feedback="The candidate demonstrated backend experience."
    )

    def fake_generate_feedback(interview):
        interview.feedback = expected_feedback
        return expected_feedback

    monkeypatch.setattr(
        interviewer_service,
        "generate_feedback",
        fake_generate_feedback
    )

    start = client.post(
        "/start-interview",
        json={"topic": "Junior AI Engineer"}
    )
    interview_id = start.json()["interview_id"]

    # Complete the interview
    for _ in range(5):
        client.post(
            f"/interview/{interview_id}/answer",
            json={"answer": "I built a FastAPI application."}
        )

    client.get(f"/interview/{interview_id}/summary")

    # Request feedback
    response = client.post(
        f"/interview/{interview_id}/feedback"
    )

    assert response.status_code == 200
    assert response.json()["feedback"] == expected_feedback.model_dump()

    # Verify persistence
    saved = client.get(f"/interview/{interview_id}")

    assert saved.json()["feedback"] == expected_feedback.model_dump()

def test_feedback_endpoint_handles_invalid_evidence(monkeypatch):
    start = client.post(
        "/start-interview",
        json={"topic": "Junior AI Engineer"}
    )

    interview_id = start.json()["interview_id"]

    for _ in range(5):
        client.post(
            f"/interview/{interview_id}/answer",
            json={"answer": "I built a FastAPI application."}
        )

    client.get(f"/interview/{interview_id}/summary")

    def invalid_feedback(interview):
        raise ValueError("Feedback evidence not found")

    monkeypatch.setattr(
        interviewer_service,
        "generate_feedback",
        invalid_feedback
    )

    response = client.post(
        f"/interview/{interview_id}/feedback"
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "AI feedback could not be validated"
    }

    saved = client.get(f"/interview/{interview_id}")
    assert saved.json()["feedback"] is None