import requests
from backend.config import OLLAMA_URL, OLLAMA_MODEL

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
