import pytest
from unittest.mock import Mock

from backend.models.interview import Interview, InterviewStage, InterviewFeedback, FeedbackPoint, FeedbackReference, GeneratedInterviewFeedback
from backend.services.interviewer_service import InterviewerService


def test_generate_feedback(monkeypatch):
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project you built."],
        answers=["I built a FastAPI application."]
    )

    generated_feedback = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Backend development experience",
                answer_id=1
            )
        ],
        improvements=[],
        overall_feedback="The candidate described backend experience."
    )

    def mock_generate_structured(prompt, response_model):
        assert "Junior AI Engineer" in prompt
        assert "[Answer 1]" in prompt
        assert "I built a FastAPI application." in prompt
        assert response_model is GeneratedInterviewFeedback

        return generated_feedback

    monkeypatch.setattr(
        service.llm,
        "generate_structured",
        mock_generate_structured
    )

    result = service.generate_feedback(interview)

    assert isinstance(result, InterviewFeedback)
    assert result.strengths[0].evidence == (
        "I built a FastAPI application."
    )
    assert result.strengths[0].observation == (
        "Backend development experience"
    )
    assert interview.feedback == result



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

def test_feedback_rejects_invalid_answer_reference():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project you built."],
        answers=["I built a FastAPI application."]
    )

    invalid_feedback = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Kubernetes deployment experience",
                answer_id=5
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
        match="Invalid feedback answer ID"
    ):
        service.generate_feedback(interview)

    # Invalid feedback must never be cached
    assert interview.feedback is None

def test_feedback_can_retry_after_invalid_reference():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project."],
        answers=["I built a FastAPI application."]
    )

    invalid_feedback = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Backend experience",
                answer_id=5
            )
        ],
        improvements=[],
        overall_feedback="Backend experience."
    )

    valid_feedback = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Backend experience",
                answer_id=1
            )
        ],
        improvements=[],
        overall_feedback="Backend experience."
    )

    mock_generate = Mock(
        side_effect=[invalid_feedback, valid_feedback]
    )
    service.llm.generate_structured = mock_generate

    # First attempt fails
    with pytest.raises(
        ValueError,
        match="Invalid feedback answer ID"
    ):
        service.generate_feedback(interview)

    assert interview.feedback is None
    assert mock_generate.call_count == 1

    # A second request succeeds
    result = service.generate_feedback(interview)

    assert result.strengths[0].evidence == (
        "I built a FastAPI application."
    )
    assert interview.feedback == result
    assert mock_generate.call_count == 2

    # Subsequent requests return cached feedback
    cached = service.generate_feedback(interview)

    assert cached == result
    assert mock_generate.call_count == 2



def test_feedback_preserves_original_answer_formatting():
    service = InterviewerService()

    original_answer = (
        "I built a FastAPI application.\n\n"
        "The application uses a RAG pipeline."
    )

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        answers=[original_answer]
    )

    generated = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Backend development experience",
                answer_id=1
            )
        ],
        improvements=[],
        overall_feedback="The candidate described an AI project."
    )

    service.llm.generate_structured = Mock(
        return_value=generated
    )

    result = service.generate_feedback(interview)

    # The evidence must match the original answer exactly
    assert result.strengths[0].evidence == original_answer

    # Preserve paragraph breaks
    assert "\n\n" in result.strengths[0].evidence

    # Save the resolved feedback
    assert interview.feedback == result


def test_resolve_feedback_references():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        answers=[
            "I recently graduated.",
            "I built a RAG application using FastAPI."
        ]
    )

    generated = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Practical AI development experience",
                answer_id=2
            )
        ],
        improvements=[],
        overall_feedback="The candidate described an AI project."
    )

    result = service._resolve_feedback_references(
        interview,
        generated
    )

    assert isinstance(result, InterviewFeedback)
    assert result.strengths[0].evidence == (
        "I built a RAG application using FastAPI."
    )
    assert result.overall_feedback == generated.overall_feedback


def test_resolve_feedback_rejects_invalid_answer_id():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        answers=["I used Python."]
    )

    generated = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Backend experience",
                answer_id=5
            )
        ],
        improvements=[],
        overall_feedback="Test feedback."
    )

    with pytest.raises(
        ValueError,
        match="Invalid feedback answer ID"
    ):
        service._resolve_feedback_references(
            interview,
            generated
        )

def test_generate_feedback_uses_answer_references():
    service = InterviewerService()

    interview = Interview(
        topic="Junior AI Engineer",
        stage=InterviewStage.END,
        questions=["Describe a project you built."],
        answers=["I built a RAG application using FastAPI."]
    )

    generated = GeneratedInterviewFeedback(
        strengths=[
            FeedbackReference(
                observation="Practical AI development experience",
                answer_id=1
            )
        ],
        improvements=[],
        overall_feedback="The candidate described an AI project."
    )

    mock_generate = Mock(return_value=generated)
    service.llm.generate_structured = mock_generate

    result = service.generate_feedback(interview)

    assert isinstance(result, InterviewFeedback)

    assert result.strengths[0].evidence == (
        "I built a RAG application using FastAPI."
    )

    assert interview.feedback == result

    assert mock_generate.call_count == 1

    # Verify that the new schema is being used
    assert mock_generate.call_args.kwargs[
        "response_model"
    ] is GeneratedInterviewFeedback

    # Verify that answers are numbered in the prompt
    assert "[Answer 1]" in (
        mock_generate.call_args.kwargs["prompt"]
    )
