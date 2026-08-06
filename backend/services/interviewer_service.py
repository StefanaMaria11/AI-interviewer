from backend.models.interview import Interview, InterviewStage
from backend.prompts.interviewer_prompts import build_interview_prompt
from backend.services.llm_service import LLMService
from backend.services.analysis_service import AnalysisService

class InterviewerService:
    def __init__(self):
        self.llm = LLMService()
        self.analysis_service = AnalysisService()

    def generate_question(self, interview: Interview) -> str:
        context = self._build_context(interview)

        prompt = build_interview_prompt(
            stage=interview.stage,
            context=context
        )

        question = self.llm.generate(prompt)

        interview.questions.append(question)

        return question

    def add_answer(self, interview: Interview, answer: str):
        interview.answers.append(answer)

        self._advance_stage(interview)

    def generate_summary(self, interview: Interview) -> str:
        interview.analysis = {
            "keywords":
                self.analysis_service.extract_keywords(
                    interview.answers
                ),

            "sentiment":
                self.analysis_service.analyze_sentiment(
                    interview.answers
                )
        }

        context = self._build_context(interview)

        prompt = build_interview_prompt(
            stage=InterviewStage.SUMMARY,
            context=context
        )

        summary = self.llm.generate(prompt)

        interview.summary = summary
        interview.stage = InterviewStage.END

        return summary

    def _build_context(self, interview: Interview) -> str:
        conversation = "" 

        for question, answer in zip(interview.questions,interview.answers): 
            conversation += f"""
Interviewer:
{question}

Candidate:
{answer}
"""
        return conversation

    def _advance_stage(self, interview: Interview):
        stages = [
            InterviewStage.BACKGROUND,
            InterviewStage.MOTIVATION,
            InterviewStage.EXPERIENCE,
            InterviewStage.TECHNICAL_FOUNDATION,
            InterviewStage.PROBLEM_SOLVING,
            InterviewStage.SUMMARY
        ]

        current_index = stages.index(interview.stage)

        if current_index < len(stages) - 1:
            interview.stage = stages[current_index + 1]
