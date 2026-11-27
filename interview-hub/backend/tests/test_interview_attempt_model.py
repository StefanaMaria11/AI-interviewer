from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models.candidate import Candidate
from app.models.interview_attempt import InterviewAttempt

@pytest.fixture
def db():
    test_engine = create_engine(
        engine.url.set(database="interviewhub_test"),
        pool_pre_ping=True,
    )

    Base.metadata.create_all(test_engine)

    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        test_engine.dispose()

def make_candidate(email):
    return Candidate(
        full_name="Test Candidate",
        email=email,
        age=24,
        profession="Software Engineer",
        location="Cluj-Napoca",
    )

def test_candidate_can_have_one_attempt(db):
    candidate = make_candidate("elena@example.com")
    db.add(candidate)
    db.flush()

    attempt = InterviewAttempt(candidate_id=candidate.id)
    db.add(attempt)
    db.flush()

    assert attempt.id is not None
    assert attempt.status == "pending"
    assert attempt.candidate_id == candidate.id

def test_cannot_create_second_attempt(db):
    candidate = make_candidate("elena@example.com")
    db.add(candidate)
    db.flush()

    first = InterviewAttempt(candidate_id=candidate.id)
    db.add(first)
    db.flush()

    second = InterviewAttempt(candidate_id=candidate.id)
    db.add(second)

    with pytest.raises(IntegrityError):
        db.flush()

def test_different_candidates_can_have_attempts(db):
    elena = make_candidate("elena@example.com")
    maria = make_candidate("maria@example.com")

    db.add_all([elena, maria])
    db.flush()

    db.add_all([
        InterviewAttempt(candidate_id=elena.id),
        InterviewAttempt(candidate_id=maria.id),
    ])

    db.flush()

def test_cannot_reuse_interview_id(db):
    elena = make_candidate("elena@example.com")
    maria = make_candidate("maria@example.com")

    db.add_all([elena, maria])
    db.flush()

    interview_id = uuid4()

    db.add(
        InterviewAttempt(
            candidate_id=elena.id,
            interview_id=interview_id,
        )
    )
    db.flush()

    db.add(
        InterviewAttempt(
            candidate_id=maria.id,
            interview_id=interview_id,
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()