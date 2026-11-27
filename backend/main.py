import logging
import fcntl
import hmac
import os

from uuid import UUID, uuid4
from pathlib import Path as FilePath
from fastapi import FastAPI, Path, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from backend.models.interview import Interview, InterviewStage
from backend.services import storage_service as storage_module
from backend.services.interviewer_service import InterviewerService
from backend.services.storage_service import StorageService
from backend.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(LLMServiceError)
async def handle_llm_service_error(
    request: Request,
    exc: LLMServiceError
):
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)}
    )

storage_service = StorageService()


interviewer_service = InterviewerService()

class StartInterview(BaseModel):
    topic: str

def require_internal_key(
    api_key: str | None = Header(
        default=None,
        alias="X-Internal-API-Key",
    ),
) -> None:
    expected = os.getenv("AI_ENGINE_INTERNAL_KEY")

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Internal API is not configured",
        )

    if (
        api_key is None
        or not hmac.compare_digest(api_key, expected)
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

class AnswerRequest(BaseModel):
    answer: str

class InternalAnswerRequest(BaseModel):
    question_number: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=10000)

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        answer = value.strip()

        if not answer:
            raise ValueError("Answer cannot be empty")

        return answer

def build_interview_progress(
    interview_id: UUID,
    interview: Interview,
) -> dict:
    completed = interview.stage in (
        InterviewStage.SUMMARY,
        InterviewStage.END,
    )

    has_unanswered_question = (
        not completed
        and len(interview.questions) > len(interview.answers)
    )

    return {
        "interview_id": str(interview_id),
        "stage": interview.stage.value,
        "question": (
            interview.questions[-1]
            if has_unanswered_question
            else None
        ),
        "question_number": (
            len(interview.questions)
            if has_unanswered_question
            else None
        ),
        "completed": completed,
    }

@app.get("/")
def index():
    return {
        "message": "AI Interviewer API running"
    }


@app.post(
    "/start-interview",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def start_interview(interview_data: StartInterview):
    interview_id = uuid4()

    interview = Interview(
        topic=interview_data.topic,
        stage=InterviewStage.BACKGROUND
    )

    question = interviewer_service.generate_question(interview)

    storage_service.save_interview(interview_id, interview)

    return {
        "interview_id": str(interview_id),
        "question": question,
        "stage": interview.stage
    }

@app.post(
    "/internal/interviews/{interview_id}/start",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def start_reserved_interview(
    interview_id: UUID,
    interview_data: StartInterview,
):
    data_folder = FilePath(storage_module.DATA_FOLDER)
    data_folder.mkdir(parents=True, exist_ok=True)

    lock_path = data_folder / f".interview_{interview_id}.lock"

    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        existing = storage_service.load_interview(
            interview_id
        )

        if existing is not None:
            if existing.topic != interview_data.topic:
                raise HTTPException(
                    status_code=409,
                    detail="Interview topic mismatch",
                )

            question = None

            if len(existing.questions) > len(existing.answers):
                question = existing.questions[-1]

            return {
                "interview_id": str(interview_id),
                "question": question,
                "stage": existing.stage,
            }

        interview = Interview(
            topic=interview_data.topic,
            stage=InterviewStage.BACKGROUND,
        )

        question = interviewer_service.generate_question(
            interview
        )

        storage_service.save_interview(
            interview_id,
            interview,
        )

        return {
            "interview_id": str(interview_id),
            "question": question,
            "stage": interview.stage,
        }

@app.post(
    "/interview/{interview_id}/answer",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def answer_interview(interview_id: UUID, answer_request: AnswerRequest):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )
    
    if interview.stage in (
        InterviewStage.SUMMARY,
        InterviewStage.END
    ):
        raise HTTPException(
            status_code=409,
            detail="Interview is already finished"
        )

    interviewer_service.add_answer(interview, answer_request.answer)

    storage_service.save_interview(interview_id, interview)

    if interview.stage == InterviewStage.SUMMARY:
        return {
            "message": "interview completed",
            "summary_available": True
        }

    question = interviewer_service.generate_question(interview)

    storage_service.save_interview(interview_id, interview)


    return {
        "question": question,
        "stage": interview.stage
    }

@app.get(
    "/interview/{interview_id}",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def get_interview(interview_id: UUID = Path(..., description="ID of the interview")):
    interview = storage_service.load_interview(interview_id)

    if interview is None:   
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )
    return interview

@app.get(
    "/interview/{interview_id}/summary",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def get_summary(interview_id: UUID):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )

    if interview.stage not in (
        InterviewStage.SUMMARY,
        InterviewStage.END
    ):
        raise HTTPException(
            status_code=409,
            detail="Interview is not finished"
        )

    if interview.stage == InterviewStage.END:
        return {"summary": interview.summary}

    summary = interviewer_service.generate_summary(interview)

    storage_service.save_interview(interview_id, interview)

    return {"summary": summary}

@app.post(
    "/interview/{interview_id}/feedback",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def get_feedback(interview_id: UUID):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )

    if interview.stage != InterviewStage.END:
        raise HTTPException(
            status_code=409,
            detail="Interview is not finished"
        )

    try:
        feedback = interviewer_service.generate_feedback(interview)

    except ValueError as e:
        logger.warning(
            "Feedback validation failed for interview %s: %s",
            interview_id,
            e
        )
        
        raise HTTPException(
            status_code=502,
            detail="AI feedback could not be validated"
        ) from e

    storage_service.save_interview(interview_id, interview)

    return {"feedback": feedback.model_dump()}

@app.get(
    "/internal/interviews/{interview_id}/state",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def get_internal_interview_state(interview_id: UUID):
    data_folder = FilePath(storage_module.DATA_FOLDER)
    data_folder.mkdir(parents=True, exist_ok=True)

    lock_path = data_folder / f".interview_{interview_id}.lock"

    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_SH)

        interview = storage_service.load_interview(
            interview_id
        )

        if interview is None:
            raise HTTPException(
                status_code=404,
                detail="Interview not found",
            )

        question = None

        if len(interview.questions) > len(interview.answers):
            question = interview.questions[-1]

        return build_interview_progress(
            interview_id,
            interview,
        )
    
@app.post(
    "/internal/interviews/{interview_id}/answer",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def submit_internal_answer(
    interview_id: UUID,
    submission: InternalAnswerRequest,
):
    data_folder = FilePath(storage_module.DATA_FOLDER)
    data_folder.mkdir(parents=True, exist_ok=True)

    lock_path = data_folder / f".interview_{interview_id}.lock"

    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        interview = storage_service.load_interview(
            interview_id
        )

        if interview is None:
            raise HTTPException(
                status_code=404,
                detail="Interview not found",
            )

        number = submission.question_number
        answer = submission.answer

        if number <= len(interview.answers):
            # The question has already been answered.
            if interview.answers[number - 1] != answer:
                raise HTTPException(
                    status_code=409,
                    detail="Question already has a different answer",
                )

        else:
            expected_number = len(interview.answers) + 1

            if (
                number != expected_number
                or number != len(interview.questions)
                or interview.stage in (
                    InterviewStage.SUMMARY,
                    InterviewStage.END,
                )
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Question is not awaiting an answer",
                )

            interviewer_service.add_answer(
                interview,
                answer,
            )

            # Save the accepted answer before calling Ollama.
            storage_service.save_interview(
                interview_id,
                interview,
            )

        # A previous request may have saved its answer
        # but failed while generating the next question.
        if (
            interview.stage not in (
                InterviewStage.SUMMARY,
                InterviewStage.END,
            )
            and len(interview.questions) == len(interview.answers)
        ):
            interviewer_service.generate_question(
                interview
            )

            storage_service.save_interview(
                interview_id,
                interview,
            )

        return build_interview_progress(
            interview_id,
            interview,
        )

@app.get(
    "/internal/interviews/{interview_id}/transcript",
    dependencies=[Depends(require_internal_key)],
    include_in_schema=False,
)
def get_internal_interview_transcript(interview_id: UUID):
    data_folder = FilePath(storage_module.DATA_FOLDER)
    data_folder.mkdir(parents=True, exist_ok=True)

    lock_path = data_folder / f".interview_{interview_id}.lock"

    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_SH)

        interview = storage_service.load_interview(
            interview_id
        )

        if interview is None:
            raise HTTPException(
                status_code=404,
                detail="Interview not found",
            )

        if interview.stage not in (
            InterviewStage.SUMMARY,
            InterviewStage.END,
        ):
            raise HTTPException(
                status_code=409,
                detail="Interview is not completed",
            )

        if len(interview.questions) != len(interview.answers):
            raise HTTPException(
                status_code=409,
                detail="Interview transcript is incomplete",
            )

        transcript = [
            {
                "question_number": number,
                "question": question,
                "answer": answer,
            }
            for number, (question, answer) in enumerate(
                zip(interview.questions, interview.answers),
                start=1,
            )
        ]

        return {
            "interview_id": str(interview_id),
            "topic": interview.topic,
            "stage": interview.stage.value,
            "transcript": transcript,
        }
