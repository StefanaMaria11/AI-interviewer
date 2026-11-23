import pytest
from pydantic import ValidationError

from backend.models.interview import (
    Interview,
    InterviewStage,
    InterviewFeedback,
    FeedbackPoint
)

def test_feedback_serialization():
    feedback = InterviewFeedback(
        strengths=[
            FeedbackPoint(
                observation="Practical API development experience",
                evidence="I built a FastAPI application."
            )
        ],
        improvements=[
            FeedbackPoint(
                observation="Limited explanation of error handling",
                evidence="I connected the backend to an LLM.",
                suggestion="Explain how API failures are handled."
            )
        ],
        overall_feedback="The candidate demonstrated practical experience."
    )

    interview = Interview(
        topic="AI Engineering Intern",
        stage=InterviewStage.END,
        feedback=feedback
    )

    # Convert the interview to JSON and restore it
    restored = Interview.model_validate_json(
        interview.model_dump_json()
    )

    assert restored.feedback == feedback
    assert restored.feedback.strengths[0].evidence == (
        "I built a FastAPI application."
    )

def test_feedback_requires_evidence():
    with pytest.raises(ValidationError):
        FeedbackPoint(
            observation="Good backend knowledge"
        )

def test_feedback_requires_overall_feedback():
    with pytest.raises(ValidationError):
        InterviewFeedback(
            strengths=[],
            improvements=[]
        )