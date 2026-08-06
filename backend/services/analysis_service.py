from collections import Counter
import re

class AnalysisService:

    TECHNICAL_TERMS = {
                "python",
                "java",
                "javascript",
                "typescript",
                "backend",
                "frontend",
                "database",
                "docker",
                "api",
                "llm",
                "rag",
                "embedding",
                "embeddings",
                "vector",
                "machine",
                "learning",
                "model",
                "prompt",
                "retrieval",
                "cloud"
            }

    def extract_keywords(self, answers: list[str], limit: int = 5):
        text = " ".join(answers).lower()
        words = re.findall(
            r"\b[a-zA-Z]{4,}\b",
            text
        )

        ignored_words = {
            "that",
            "this",
            "with",
            "have",
            "from",
            "were",
            "used",
            "using",
            "into",
            "about",
            "what",
            "when",
            "where",
            "which",
            "their",
            "because",
            "different",
            "ai",
            "artificial",
            "intelligence",
            "would",

            # generic words
            "system",
            "application",
            "project",
            "development",
            "experience",
            "process",
            "problem",
            "answer",

            # interview words
            "candidate",
            "question",
            "interview"
        }

        filtered = [
            word
            for word in words
            if word not in ignored_words
        ]

        counter = Counter(filtered)

        scores = {}

        for word, count in counter.items():
            score = count

            # prioritize technical concepts
            if word in self.TECHNICAL_TERMS:
                score += 5

            scores[word] = score

        ranked_words = sorted(scores, key=scores.get, reverse=True)

        return ranked_words[:limit]

    def analyze_sentiment(self, answers: list[str]):
        positive_words = {
            "enjoy",
            "like",
            "love",
            "interesting",
            "excited",
            "successful",
            "learned",
            "improved",
            "motivated"
        }

        negative_words = {
            "failed",
            "frustrating",
            "blocked",
            "stuck",
            "impossible",
            "disappointed"
        }

        text = " ".join(answers).lower()

        positive_score = sum(
            text.count(word)
            for word in positive_words
        )

        negative_score = sum(
            text.count(word)
            for word in negative_words
        )

        if positive_score > negative_score:
            sentiment = "positive"

        elif negative_score > positive_score:
            sentiment = "challenging"

        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "positive_score": positive_score,
            "negative_score": negative_score
        }