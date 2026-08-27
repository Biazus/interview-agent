from pathlib import Path

import yaml

from app.core.domain.interfaces import Question, Rubric, RubricCriterion


def load_questions_from_yaml(data_path: Path) -> list[Question]:
    with open(data_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, list):
        raise TypeError(f"Expected a list in {data_path}, got {type(raw).__name__}")
    return [Question(**item) for item in raw]


def load_rubrics_from_yaml(data_path: Path) -> dict[str, Rubric]:
    with open(data_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, list):
        raise TypeError(f"Expected a list in {data_path}, got {type(raw).__name__}")
    return {
        item["topic"]: Rubric(
            topic=item["topic"],
            criteria=[RubricCriterion(**c) for c in item["criteria"]],
        )
        for item in raw
    }
