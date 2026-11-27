from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

class InterviewAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: Literal["pending", "in_progress", "completed"]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None