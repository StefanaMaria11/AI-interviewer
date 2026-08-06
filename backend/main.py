from fastapi import FastAPI, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.models.interview import Interview, InterviewStage
from backend.services.interviewer_service import InterviewerService
from backend.services.storage_service import StorageService

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_service = StorageService()

interview_counter = 1

interviewer_service = InterviewerService()

class StartInterview(BaseModel):
    topic: str

class AnswerRequest(BaseModel):
    answer: str

@app.get("/")
def index():
    return {
        "message": "AI Interviewer API running"
    }

@app.post("/start-interview")
def start_interview(interview_data: StartInterview):
    global interview_counter

    interview = Interview(
        topic=interview_data.topic,
        stage=InterviewStage.BACKGROUND
    )

    question = interviewer_service.generate_question(interview)

    storage_service.save_interview(interview_counter, interview)

    response = {
        "interview_id": interview_counter,
        "question": question,
        "stage": interview.stage
    }

    interview_counter += 1

    return response

@app.post("/interview/{interview_id}/answer")
def answer_interview(interview_id: int, answer_request: AnswerRequest):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        return {
            "error": "Interview not found"
        }

    interviewer_service.add_answer(interview, answer_request.answer)

    storage_service.save_interview(interview_id, interview)

    if interview.stage == InterviewStage.SUMMARY:
        return {
            "message": "interview completed",
            "summary_available": True
        }

    question = interviewer_service.generate_question(interview)

    storage_service.save_interview(interview_id, interview)


    return {
        "question": question,
        "stage": interview.stage
    }

@app.get("/interview/{interview_id}")
def get_interview(interview_id: int = Path(..., description="ID of the interview", gt=0)):
    interview = storage_service.load_interview(interview_id)

    if interview is None:   
        return {
            "error": "Interview not found"
        }
    return interview

@app.get("/interview/{interview_id}/summary")
def get_summary(interview_id: int):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        return {
            "error": "Interview not found"
        }

    summary = interviewer_service.generate_summary(interview)

    storage_service.save_interview(interview_id, interview)

    return {
        "summary": summary
    }