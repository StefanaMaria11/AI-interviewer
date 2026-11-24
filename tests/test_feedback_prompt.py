from backend.prompts.feedback_prompts import (
    build_referenced_feedback_prompt
)

def test_feedback_prompt_numbers_answers():
    answers = [
        "I recently graduated.",
        "I built a RAG application."
    ]

    prompt = build_referenced_feedback_prompt(
        topic="Junior AI Engineer",
        answers=answers
    )

    assert "Junior AI Engineer" in prompt
    assert "[Answer 1]" in prompt
    assert "[Answer 2]" in prompt
    assert "I built a RAG application." in prompt

def test_feedback_prompt_requests_answer_references():
    prompt = build_referenced_feedback_prompt(
        topic="Junior AI Engineer",
        answers=["I used Python."]
    )

    assert '"answer_id"' in prompt
    assert '"strengths"' in prompt
    assert '"improvements"' in prompt
    assert '"overall_feedback"' in prompt
