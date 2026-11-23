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
            "enjoy", "like", "love", "interesting",
            "excited", "successful", "learned",
            "improved", "motivated"
        }

        negative_words = {
            "failed", "frustrating", "blocked",
            "stuck", "impossible", "disappointed"
        }

        negation_words = {
            "not", "never", "no", "cannot",
            "don't", "didn't", "doesn't",
            "can't", "won't", "wasn't",
            "isn't", "aren't", "weren't"
        }

        text = " ".join(answers).lower()

        # Preserve contractions such as "don't"
        words = re.findall(
            r"\b[a-z]+(?:'[a-z]+)?\b",
            text
        )

        positive_score = 0
        negative_score = 0

        for index, word in enumerate(words):
            is_negated = (
                index > 0
                and words[index - 1] in negation_words
            )

            if word in positive_words:
                if is_negated:
                    negative_score += 1
                else:
                    positive_score += 1

            elif word in negative_words:
                if not is_negated:
                    negative_score += 1

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