import requests
from backend.config import OLLAMA_URL, OLLAMA_MODEL

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
                }
            )

            response.raise_for_status()
            question = response.json()["response"].strip()
            question = question.strip('"')
            question = question.strip("'")
            question = question.strip("“")
            question = question.strip("”")
            question = question.replace("**", "")

            return question
        except requests.exceptions.RequestException as e:
            return f"Failed to communicate with Ollama: {e}"
    