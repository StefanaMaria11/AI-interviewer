import pytest
from pydantic import ValidationError

from app.schemas.candidate import CandidateCreate

def test_valid_candidate_registration():
    candidate = CandidateCreate(
        full_name="Elena Popescu",
        email="Elena.Popescu@Example.com",
        age=24,
        profession="Software Engineer",
        location="Cluj-Napoca"
    )

    assert candidate.full_name == "Elena Popescu"
    assert candidate.email == "elena.popescu@example.com"
    assert candidate.age == 24

def test_invalid_candidate_email():
    with pytest.raises(ValidationError):
        CandidateCreate(
            full_name="Elena Popescu",
            email="invalid-email",
            age=24,
            profession="Software Engineer",
            location="Cluj-Napoca"
        )

def test_candidate_under_minimum_age():
    with pytest.raises(ValidationError):
        CandidateCreate(
            full_name="Elena Popescu",
            email="elena.popescu@example.com",
            age=17,
            profession="Software Engineer",
            location="Cluj-Napoca"
        )
