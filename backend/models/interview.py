from enum import Enum
from pydantic import BaseModel, Field

class InterviewStage(str, Enum):
    START = "START"
    BACKGROUND = "BACKGROUND"
    MOTIVATION = "MOTIVATION"
    EXPERIENCE = "EXPERIENCE"
    TECHNICAL_FOUNDATION = "TECHNICAL_FOUNDATION"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    SUMMARY = "SUMMARY"
    END = "END"

class Interview(BaseModel):
    topic: str = Field(
        description="The position/topic of the interview"
    )

    stage: InterviewStage = Field(
        default=InterviewStage.START,
        description="Current stage of the interview"
    )

    questions: list[str] = Field(
        default_factory=list,
        description="Questions asked by the AI interviewer"
    )

    answers: list[str] = Field(
        default_factory=list,
        description="Answers provided by the candidate"
    )

    summary: str = Field(
        default="",
        description="Final AI-generated interview summary"
    )

    analysis: dict = Field(
        default_factory=dict,
        description="Automatic interview analysis"
    )