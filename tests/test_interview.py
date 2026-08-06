import pytest
from fastapi.testclient import TestClient
from backend.main import app, interviewer_service

client = TestClient(app)

def fake_generate_question(interview):
    return "Fake interview question?"

def fake_generate_summary(interview):
    return "Fake summary"

@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
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
    response = client.get( "/interview/999999")

    assert response.status_code == 200
    assert response.json()=={
        "error":
        "Interview not found"
    }

def test_summary():
    start = client.post("/start-interview",
                        json={
                            "topic":"AI Engineering Intern"
                            })

    interview_id = (start.json()["interview_id"])

    response = client.get( f"/interview/{interview_id}/summary")

    assert response.status_code == 200
    assert response.json()=={
        "summary":
        "Fake summary"
    }