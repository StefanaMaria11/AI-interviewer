import json
import os
from uuid import UUID
from backend.models.interview import Interview


DATA_FOLDER = "data/interviews"


class StorageService:

    def __init__(self):
        os.makedirs(DATA_FOLDER, exist_ok=True)


    def save_interview(self, interview_id: UUID, interview: Interview):

        file_path = f"{DATA_FOLDER}/interview_{interview_id}.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(
                interview.model_dump(),
                file,
                indent=4,
                default=str
            )


    def load_interview(self, interview_id: UUID):

        file_path = f"{DATA_FOLDER}/interview_{interview_id}.json"

        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return Interview(**data)