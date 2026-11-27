import os
from uuid import UUID

import httpx

class AIEngineUnavailableError(Exception):
    pass

class AIEngineConflictError(Exception):
    pass

def start_ai_interview(
    interview_id: UUID,
    topic: str,
) -> dict:
    base_url = os.getenv(
        "AI_ENGINE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    api_key = os.getenv("AI_ENGINE_INTERNAL_KEY")

    if not api_key:
        raise AIEngineUnavailableError(
            "AI engine credentials are not configured"
        )

    try:
        response = httpx.post(
            f"{base_url}/internal/interviews/"
            f"{interview_id}/start",
            json={"topic": topic},
            headers={
                "X-Internal-API-Key": api_key,
            },
            timeout=httpx.Timeout(
                150.0,
                connect=5.0,
            ),
        )

        response.raise_for_status()
        payload = response.json()

    except (httpx.HTTPError, ValueError) as exc:
        raise AIEngineUnavailableError(
            "AI interview service is unavailable"
        ) from exc

    if not isinstance(payload, dict):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid response"
        )

    if payload.get("interview_id") != str(interview_id):
        raise AIEngineUnavailableError(
            "AI engine returned the wrong interview"
        )

    stage = payload.get("stage")
    question = payload.get("question")

    if not isinstance(stage, str):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid stage"
        )

    if question is not None and not isinstance(question, str):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid question"
        )

    return payload

def get_ai_interview_state(interview_id: UUID) -> dict:
    base_url = os.getenv(
        "AI_ENGINE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    api_key = os.getenv("AI_ENGINE_INTERNAL_KEY")

    if not api_key:
        raise AIEngineUnavailableError(
            "AI engine credentials are not configured"
        )

    try:
        response = httpx.get(
            f"{base_url}/internal/interviews/"
            f"{interview_id}/state",
            headers={
                "X-Internal-API-Key": api_key,
            },
            timeout=httpx.Timeout(
                10.0,
                connect=3.0,
            ),
        )

        response.raise_for_status()
        payload = response.json()

    except (httpx.HTTPError, ValueError) as exc:
        raise AIEngineUnavailableError(
            "Could not retrieve AI interview state"
        ) from exc

    if not isinstance(payload, dict):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid response"
        )

    if payload.get("interview_id") != str(interview_id):
        raise AIEngineUnavailableError(
            "AI engine returned the wrong interview"
        )

    valid_stages = {
        "START",
        "BACKGROUND",
        "MOTIVATION",
        "EXPERIENCE",
        "TECHNICAL_FOUNDATION",
        "PROBLEM_SOLVING",
        "SUMMARY",
        "END",
    }

    stage = payload.get("stage")
    question = payload.get("question")
    question_number = payload.get("question_number")
    completed = payload.get("completed")

    if stage not in valid_stages:
        raise AIEngineUnavailableError(
            "AI engine returned an invalid stage"
        )

    if question is not None and not isinstance(question, str):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid question"
        )

    if not isinstance(completed, bool):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid completion state"
        )

    if completed and question is not None:
        raise AIEngineUnavailableError(
            "Completed interview has an active question"
        )

    if question is None:
        if question_number is not None:
            raise AIEngineUnavailableError(
                "AI engine returned an invalid question number"
            )
    elif (
        type(question_number) is not int
        or question_number < 1
    ):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid question number"
        )
    
    return {
        "stage": stage,
        "question": question,
        "question_number": question_number,
        "completed": completed,
    }

def submit_ai_answer(
    interview_id: UUID,
    question_number: int,
    answer: str,
) -> dict:
    base_url = os.getenv(
        "AI_ENGINE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    api_key = os.getenv("AI_ENGINE_INTERNAL_KEY")

    if not api_key:
        raise AIEngineUnavailableError(
            "AI engine credentials are not configured"
        )

    try:
        response = httpx.post(
            f"{base_url}/internal/interviews/"
            f"{interview_id}/answer",
            json={
                "question_number": question_number,
                "answer": answer,
            },
            headers={
                "X-Internal-API-Key": api_key,
            },
            timeout=httpx.Timeout(
                150.0,
                connect=5.0,
            ),
        )

        response.raise_for_status()
        payload = response.json()

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            raise AIEngineConflictError(
                "Question cannot be answered again"
            ) from exc

        raise AIEngineUnavailableError(
            "AI interview service is unavailable"
        ) from exc

    except (httpx.HTTPError, ValueError) as exc:
        raise AIEngineUnavailableError(
            "AI interview service is unavailable"
        ) from exc

    if not isinstance(payload, dict):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid response"
        )

    if payload.get("interview_id") != str(interview_id):
        raise AIEngineUnavailableError(
            "AI engine returned the wrong interview"
        )

    stage = payload.get("stage")
    question = payload.get("question")
    next_number = payload.get("question_number")
    completed = payload.get("completed")

    valid_stages = {
        "BACKGROUND",
        "MOTIVATION",
        "EXPERIENCE",
        "TECHNICAL_FOUNDATION",
        "PROBLEM_SOLVING",
        "SUMMARY",
        "END",
    }

    if stage not in valid_stages or type(completed) is not bool:
        raise AIEngineUnavailableError(
            "AI engine returned invalid interview progress"
        )

    if completed != (stage in {"SUMMARY", "END"}):
        raise AIEngineUnavailableError(
            "AI engine returned inconsistent completion state"
        )

    if completed:
        if question is not None or next_number is not None:
            raise AIEngineUnavailableError(
                "Completed interview has an active question"
            )
    elif (
        not isinstance(question, str)
        or not question.strip()
        or type(next_number) is not int
        or next_number < 1
    ):
        raise AIEngineUnavailableError(
            "AI engine returned an invalid next question"
        )

    return {
        "stage": stage,
        "question": question,
        "question_number": next_number,
        "completed": completed,
    }

def get_ai_interview_transcript(interview_id: UUID) -> dict:
    base_url = os.getenv(
        "AI_ENGINE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    api_key = os.getenv("AI_ENGINE_INTERNAL_KEY")

    if not api_key:
        raise AIEngineUnavailableError(
            "AI engine credentials are not configured"
        )

    try:
        response = httpx.get(
            f"{base_url}/internal/interviews/"
            f"{interview_id}/transcript",
            headers={
                "X-Internal-API-Key": api_key,
            },
            timeout=httpx.Timeout(
                10.0,
                connect=3.0,
            ),
        )

        response.raise_for_status()
        payload = response.json()

    except (httpx.HTTPError, ValueError) as exc:
        raise AIEngineUnavailableError(
            "Could not retrieve interview transcript"
        ) from exc

    if not isinstance(payload, dict):
        raise AIEngineUnavailableError(
            "Invalid interview transcript response"
        )

    if payload.get("interview_id") != str(interview_id):
        raise AIEngineUnavailableError(
            "AI engine returned the wrong interview"
        )

    if payload.get("stage") not in {"SUMMARY", "END"}:
        raise AIEngineUnavailableError(
            "Interview is not completed"
        )

    topic = payload.get("topic")
    transcript = payload.get("transcript")

    if not isinstance(topic, str) or not topic.strip():
        raise AIEngineUnavailableError(
            "Invalid interview topic"
        )

    if not isinstance(transcript, list):
        raise AIEngineUnavailableError(
            "Invalid interview transcript"
        )

    for number, item in enumerate(transcript, start=1):
        if not isinstance(item, dict):
            raise AIEngineUnavailableError(
                "Invalid transcript entry"
            )

        if (
            type(item.get("question_number")) is not int
            or item["question_number"] != number
            or not isinstance(item.get("question"), str)
            or not item["question"].strip()
            or not isinstance(item.get("answer"), str)
            or not item["answer"].strip()
        ):
            raise AIEngineUnavailableError(
                "Invalid transcript entry"
            )

    return {
        "topic": topic,
        "stage": payload["stage"],
        "transcript": transcript,
    }