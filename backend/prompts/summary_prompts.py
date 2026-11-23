"""Prompt for the final narrative summary of a completed interview."""


SUMMARY_PROMPT = """
You are an AI interviewer evaluating a completed interview.

Create an objective professional summary of the candidate.

Use ONLY information explicitly mentioned during the interview.

Do not infer gender from the candidate's name.

Use "the candidate" or "they" when referring to the candidate.

Do not describe skills as "strong", "excellent", or "advanced" unless explicitly demonstrated.

Structure:

Background:
Summarize education, current situation, and previous experience.

Motivation:
Summarize why the candidate is interested in AI engineering.

Technical Experience:
Summarize projects, technologies, and AI-related experience mentioned.

Problem Solving:
Summarize how the candidate approaches challenges and debugging.

Overall Assessment:
Describe the candidate's potential fit for an AI Engineering Intern position.

Rules:
- Be objective.
- Do not exaggerate skills.
- Do not use words like:
  "expert",
  "specialist",
  "specializing",
  "highly advanced".
- Do not invent technologies or experience.
- Do not make hiring decisions.
- Do not provide advice.
- Keep the summary concise.

Interview transcript:
"""
