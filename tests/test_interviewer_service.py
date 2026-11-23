import pytest
from unittest.mock import Mock

from backend.models.interview import Interview, InterviewStage, InterviewFeedback, FeedbackPoint
from backend.services.interviewer_service import InterviewerService

def test_generate_feedback(monkeypatch):
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project you built."],
        answers=["I built a FastAPI application."]
    )

    expected_feedback = InterviewFeedback(
        strengths=[
            FeedbackPoint(
                observation="Backend development experience",
                evidence="I built a FastAPI application."
            )
        ],
        improvements=[],
        overall_feedback="The candidate described backend experience."
    )

    def mock_generate_structured(prompt, response_model):
        assert "Junior AI Engineer" in prompt
        assert "I built a FastAPI application." in prompt
        assert response_model is InterviewFeedback

        return expected_feedback

    monkeypatch.setattr(
        service.llm,
        "generate_structured",
        mock_generate_structured
    )

    result = service.generate_feedback(interview)

    assert result == expected_feedback
    assert interview.feedback == expected_feedback


def test_feedback_requires_completed_interview():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.BACKGROUND
    )

    mock_generate = Mock(
        return_value=InterviewFeedback(
            strengths=[],
            improvements=[],
            overall_feedback="Test feedback"
        )
    )

    service.llm.generate_structured = mock_generate

    with pytest.raises(
        ValueError,
        match="Interview is not finished"
    ):
        service.generate_feedback(interview)

    mock_generate.assert_not_called()
    assert interview.feedback is None

def test_feedback_generated_only_once():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project you built."],
        answers=["I built a FastAPI application."]
    )

    expected_feedback = InterviewFeedback(
        strengths=[],
        improvements=[],
        overall_feedback="The candidate has backend experience."
    )

    mock_generate = Mock(return_value=expected_feedback)

    service.llm.generate_structured = mock_generate

    # Generate feedback twice
    first = service.generate_feedback(interview)
    second = service.generate_feedback(interview)

    assert first == expected_feedback
    assert second == expected_feedback
    assert interview.feedback == expected_feedback

    # Ollama should only be called once
    assert mock_generate.call_count == 1

def test_feedback_rejects_fabricated_evidence():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project you built."],
        answers=["I built a FastAPI application."]
    )

    invalid_feedback = InterviewFeedback(
        strengths=[
            FeedbackPoint(
                observation="Kubernetes deployment experience",
                evidence="I deployed Kubernetes to production."
            )
        ],
        improvements=[],
        overall_feedback="The candidate has deployment experience."
    )

    service.llm.generate_structured = Mock(
        return_value=invalid_feedback
    )

    with pytest.raises(
        ValueError,
        match="Feedback evidence not found"
    ):
        service.generate_feedback(interview)

    # Invalid feedback must not be cached
    assert interview.feedback is None