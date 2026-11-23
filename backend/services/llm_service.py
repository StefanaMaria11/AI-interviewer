import requests
from backend.config import OLLAMA_URL, OLLAMA_MODEL
from typing import TypeVar
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)

class LLMServiceError(Exception):
    pass

class LLMService:
    def __init__(self):
        self.url = OLLAMA_URL
        self.model = OLLAMA_MODEL

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=(5, 120)
            )

            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as e:
                raise LLMServiceError(
                    "The AI service returned invalid JSON."
                ) from e

            if not isinstance(payload, dict):
                raise LLMServiceError(
                    "The AI service returned an invalid response."
                )

            question = payload.get("response")

            if not isinstance(question, str):
                raise LLMServiceError(
                    "The AI service did not return text."
                )

            question = question.strip()
            question = question.strip('"')
            question = question.strip("'")
            question = question.strip("“")
            question = question.strip("”")
            question = question.replace("**", "")

            if not question.strip():
                raise LLMServiceError(
                    "The AI service returned empty text."
                )

            return question
        
        except requests.exceptions.RequestException as e:
            raise LLMServiceError(
                "The AI service is currently unavailable."
            ) from e


    def generate_structured(self, prompt: str, response_model: type[ModelT]) -> ModelT:
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": response_model.model_json_schema(),
                    "options": {"temperature": 0.3}
                },
                timeout=(5, 120)
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            raise LLMServiceError(
                "The AI service is currently unavailable."
            ) from e

        try:
            payload = response.json()
        except ValueError as e:
            raise LLMServiceError(
                "The AI service returned invalid JSON."
            ) from e

        if not isinstance(payload, dict):
            raise LLMServiceError(
                "The AI service returned an invalid response."
            )

        raw_output = payload.get("response")

        if not isinstance(raw_output, str) or not raw_output.strip():
            raise LLMServiceError(
                "The AI service returned empty or invalid text."
            )

        try:
            return response_model.model_validate_json(raw_output)

        except ValidationError as e:
            raise LLMServiceError(
                "The AI service returned invalid structured data."
            ) from e