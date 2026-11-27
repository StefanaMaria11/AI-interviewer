from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

class CandidateAnswerRequest(BaseModel):
    question_number: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=10000)

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        answer = value.strip()

        if not answer:
            raise ValueError("Answer cannot be empty")

        return answer

class InterviewAnswerResponse(BaseModel):
    attempt_id: UUID
    status: Literal["in_progress", "completed"]
    stage: str
    question: str | None
    question_number: int | None
    completed: bool