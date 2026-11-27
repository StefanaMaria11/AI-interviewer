from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.interview_attempt import InterviewAttempt

def get_or_create_attempt(
    db: Session,
    candidate_id: UUID,
) -> InterviewAttempt:
    statement = (
        insert(InterviewAttempt)
        .values(
            id=uuid4(),
            candidate_id=candidate_id,
            status="pending",
        )
        .on_conflict_do_nothing(
            constraint="uq_interview_attempt_candidate"
        )
    )

    db.execute(statement)

    attempt = db.scalar(
        select(InterviewAttempt).where(
            InterviewAttempt.candidate_id == candidate_id
        )
    )

    if attempt is None:
        raise RuntimeError("Could not retrieve interview attempt")

    return attempt

def get_candidate_attempt(
    db: Session,
    candidate_id: UUID,
) -> InterviewAttempt | None:
    return db.scalar(
        select(InterviewAttempt).where(
            InterviewAttempt.candidate_id == candidate_id
        )
    )