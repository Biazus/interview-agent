from pathlib import Path

import yaml

from app.core.domain.interfaces import Rubric, RubricCriterion

_DATA_PATH = Path(__file__).parent / "data" / "rubrics.yaml"


class StaticPythonBasicsRubricProvider:
    """Provider de rubricas estático para fundamentos de Python."""

    def __init__(self, data_path: Path = _DATA_PATH) -> None:
        with open(data_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self._rubrics = {
            item["topic"]: Rubric(
                topic=item["topic"],
                criteria=[RubricCriterion(**c) for c in item["criteria"]],
            )
            for item in raw
        }

    def get_rubric(self, topic: str) -> Rubric:
        rubric = self._rubrics.get(topic)
        if rubric is None:
            raise ValueError(f"Nenhuma rubrica encontrada para topic={topic}")
        return rubric
