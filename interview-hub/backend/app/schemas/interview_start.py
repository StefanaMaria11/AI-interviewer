from typing import Literal
from uuid import UUID

from pydantic import BaseModel

class InterviewStartResponse(BaseModel):
    attempt_id: UUID
    interview_id: UUID
    status: Literal["in_progress"]
    stage: str
    question: str | None