from pathlib import Path

import yaml

from app.core.domain.interfaces import Question

_DATA_PATH = Path(__file__).parent / "data" / "questions.yaml"


class StaticAsyncMessagingQuestionBank:
    """Banco de perguntas estático, cobrindo SQS/SNS/Lambda."""

    def __init__(self, data_path: Path = _DATA_PATH) -> None:
        with open(data_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self._questions = [Question(**item) for item in raw]

    def next_question(self, topic: str, difficulty: int) -> Question:
        candidates = [
            q
            for q in self._questions
            if q.topic == topic and q.difficulty == difficulty
        ]
        if not candidates:
            raise ValueError(
                f"Nenhuma pergunta encontrada para topic={topic}, difficulty={difficulty}"
            )
        return candidates[0]

    def topics(self) -> list[str]:
        return sorted({q.topic for q in self._questions})
