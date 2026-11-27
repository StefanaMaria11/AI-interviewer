import json
import os
import tempfile

from pathlib import Path
from uuid import UUID

from backend.models.interview import Interview

DATA_FOLDER = "data/interviews"

class StorageService:
    def __init__(self):
        Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)

    def save_interview(
        self,
        interview_id: UUID,
        interview: Interview,
    ) -> None:
        folder = Path(DATA_FOLDER)
        folder.mkdir(parents=True, exist_ok=True)

        target = folder / f"interview_{interview_id}.json"
        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=folder,
                prefix=f".interview_{interview_id}_",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)

                json.dump(
                    interview.model_dump(mode="json"),
                    temporary,
                    indent=4,
                    ensure_ascii=False,
                )

                temporary.flush()
                os.fsync(temporary.fileno())

            os.replace(temporary_path, target)

        finally:
            if (
                temporary_path is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink()

    def load_interview(
        self,
        interview_id: UUID,
    ) -> Interview | None:
        path = (
            Path(DATA_FOLDER)
            / f"interview_{interview_id}.json"
        )

        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return Interview.model_validate(data)