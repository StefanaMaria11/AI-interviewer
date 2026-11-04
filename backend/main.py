from uuid import UUID, uuid4
from fastapi import FastAPI, Path, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.models.interview import Interview, InterviewStage
from backend.services.interviewer_service import InterviewerService
from backend.services.storage_service import StorageService
from backend.services.llm_service import LLMServiceError

app = FastAPI()

@app.exception_handler(LLMServiceError)
async def handle_llm_service_error(
    request: Request,
    exc: LLMServiceError
):
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_service = StorageService()


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
    interview_id = uuid4()

    interview = Interview(
        topic=interview_data.topic,
        stage=InterviewStage.BACKGROUND
    )

    question = interviewer_service.generate_question(interview)

    storage_service.save_interview(interview_id, interview)

    return {
        "interview_id": str(interview_id),
        "question": question,
        "stage": interview.stage
    }

@app.post("/interview/{interview_id}/answer")
def answer_interview(interview_id: UUID, answer_request: AnswerRequest):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )

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
def get_interview(interview_id: UUID = Path(..., description="ID of the interview")):
    interview = storage_service.load_interview(interview_id)

    if interview is None:   
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )
    return interview

@app.get("/interview/{interview_id}/summary")
def get_summary(interview_id: UUID):
    interview = storage_service.load_interview(interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="Interview not found"
        )

    summary = interviewer_service.generate_summary(interview)

    storage_service.save_interview(interview_id, interview)

    return {
        "summary": summary
    }