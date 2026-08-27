from collections.abc import Callable
from pathlib import Path

from app.core.domain.interfaces import Question, Rubric
from app.core.domain.yaml_loaders import (
    load_questions_from_yaml,
    load_rubrics_from_yaml,
)


class StaticQuestionBank:
    def __init__(
        self,
        data_path: Path,
        *,
        candidate_selector: Callable[[list[Question]], Question] | None = None,
    ) -> None:
        self._questions = load_questions_from_yaml(data_path)
        self._candidate_selector = candidate_selector or (
            lambda candidates: candidates[0]
        )

    def next_question(
        self, topic: str, difficulty: int, exclude_ids: set[str] | None = None
    ) -> Question:
        candidates = [
            q
            for q in self._questions
            if q.topic == topic
            and q.difficulty == difficulty
            and (exclude_ids is None or q.id not in exclude_ids)
        ]
        if not candidates:
            raise ValueError(
                f"Nenhuma pergunta encontrada para topic={topic}, difficulty={difficulty}"
            )
        return self._candidate_selector(candidates)

    def topics(self) -> list[str]:
        return sorted({q.topic for q in self._questions})


class StaticRubricProvider:
    def __init__(self, data_path: Path) -> None:
        self._rubrics = load_rubrics_from_yaml(data_path)

    def get_rubric(self, topic: str) -> Rubric:
        rubric = self._rubrics.get(topic)
        if rubric is None:
            raise ValueError(f"Nenhuma rubrica encontrada para topic={topic}")
        return rubric
