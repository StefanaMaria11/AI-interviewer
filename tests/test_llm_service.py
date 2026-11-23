from unittest.mock import Mock, patch

import pytest
import requests
import json

from backend.services.llm_service import LLMService, LLMServiceError
from backend.models.interview import InterviewFeedback

@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"response": "  Tell me about yourself.  "},
         "Tell me about yourself."),
        ({"response": '"What have you built?"'},
         "What have you built?"),
        ({"response": "**Describe your project.**"},
         "Describe your project."),
    ],
)
def test_generate_returns_clean_text(payload, expected):
    response = Mock()
    response.json.return_value = payload

    with patch(
        "backend.services.llm_service.requests.post",
        return_value=response,
    ):
        result = LLMService().generate("Ask one question.")

    assert result == expected


@pytest.mark.parametrize(
    "payload, expected_error",
    [
        ([], "invalid response"),
        ({}, "did not return text"),
        ({"response": None}, "did not return text"),
        ({"response": 42}, "did not return text"),
        ({"response": ""}, "empty text"),
        ({"response": "   "}, "empty text"),
        ({"response": "**"}, "empty text"),
        ({"response": '""'}, "empty text"),
    ],
)
def test_generate_rejects_invalid_output(payload, expected_error):
    response = Mock()
    response.json.return_value = payload

    with patch(
        "backend.services.llm_service.requests.post",
        return_value=response,
    ):
        with pytest.raises(LLMServiceError, match=expected_error):
            LLMService().generate("Ask one question.")


def test_generate_rejects_invalid_json():
    response = Mock()
    response.json.side_effect = ValueError("Invalid JSON")

    with patch(
        "backend.services.llm_service.requests.post",
        return_value=response,
    ):
        with pytest.raises(LLMServiceError, match="invalid JSON"):
            LLMService().generate("Ask one question.")


@pytest.mark.parametrize(
    "error",
    [
        requests.exceptions.ConnectionError("Connection failed"),
        requests.exceptions.Timeout("Request timed out"),
    ],
)
def test_generate_handles_connection_failure(error):
    with patch(
        "backend.services.llm_service.requests.post",
        side_effect=error,
    ):
        with pytest.raises(LLMServiceError, match="unavailable"):
            LLMService().generate("Ask one question.")


def test_generate_handles_http_error():
    response = Mock()
    response.raise_for_status.side_effect = (
        requests.exceptions.HTTPError("Server error")
    )

    with patch(
        "backend.services.llm_service.requests.post",
        return_value=response,
    ):
        with pytest.raises(LLMServiceError, match="unavailable"):
            LLMService().generate("Ask one question.")

    response.json.assert_not_called()

def test_generate_structured_feedback():
    feedback_data = {
        "strengths": [
            {
                "observation": "Practical API experience",
                "evidence": "I built a FastAPI application.",
                "suggestion": None
            }
        ],
        "improvements": [],
        "overall_feedback": "The candidate has backend experience."
    }

    mock_response = Mock()
    mock_response.json.return_value = {
        "response": json.dumps(feedback_data)
    }

    with patch(
        "backend.services.llm_service.requests.post",
        return_value=mock_response
    ) as mock_post:

        feedback = LLMService().generate_structured(
            prompt="Evaluate the interview.",
            response_model=InterviewFeedback
        )

    assert isinstance(feedback, InterviewFeedback)

    assert feedback.strengths[0].observation == (
        "Practical API experience"
    )

    assert feedback.overall_feedback == (
        "The candidate has backend experience."
    )

    # Verify that Ollama receives the Pydantic JSON schema
    request_data = mock_post.call_args.kwargs["json"]

    assert request_data["format"] == (
        InterviewFeedback.model_json_schema()
    )

    assert request_data["stream"] is False

@pytest.mark.parametrize(
    "raw_output",
    [
        "This is not JSON",
        '{"strengths": []}',
        '{"strengths": [], "improvements": [], "overall_feedback": 123}',
        "",
    ]
)
def test_generate_structured_rejects_invalid_data(raw_output):
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": raw_output
    }

    with patch(
        "backend.services.llm_service.requests.post",
        return_value=mock_response
    ):
        with pytest.raises(LLMServiceError):
            LLMService().generate_structured(
                prompt="Evaluate the interview.",
                response_model=InterviewFeedback
            )


def test_generate_structured_handles_connection_error():
    with patch(
        "backend.services.llm_service.requests.post",
        side_effect=requests.exceptions.ConnectionError()
    ):
        with pytest.raises(
            LLMServiceError,
            match="unavailable"
        ):
            LLMService().generate_structured(
                prompt="Evaluate the interview.",
                response_model=InterviewFeedback
            )
