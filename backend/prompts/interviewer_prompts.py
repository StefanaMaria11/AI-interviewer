"""Public prompt builders used by InterviewerService and tests.

The prompt text lives in focused modules; importing from this module keeps
existing callers compatible without changing service code.
"""

from backend.models.interview import InterviewStage
from backend.prompts.question_prompts import (
    INTERVIEWER_ROLE,
    QUESTION_RULES,
    STAGE_INSTRUCTIONS,
)
from backend.prompts.summary_prompts import SUMMARY_PROMPT
from backend.prompts.feedback_prompts import build_feedback_prompt


def build_interview_prompt(
    stage: InterviewStage,
    context: str = ""
) -> str:

    if stage == InterviewStage.SUMMARY:
        return f"""
{SUMMARY_PROMPT}

{context}
"""

    return f"""
{INTERVIEWER_ROLE}

{QUESTION_RULES}

Current stage:
{stage.value}

Stage instructions:
{STAGE_INSTRUCTIONS[stage]}

Previous conversation:
{context}

Generate the next interview question.
"""
