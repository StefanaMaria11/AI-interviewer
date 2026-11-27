from app.schemas.interview_attempt import InterviewAttemptResponse

class CurrentInterviewResponse(InterviewAttemptResponse):
    stage: str | None = None
    question: str | None = None
    question_number: int | None = None