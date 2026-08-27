from pathlib import Path

import pytest
import yaml

from app.core.domain.interfaces import Question, Rubric, RubricCriterion
from app.core.domain.yaml_loaders import (
    load_questions_from_yaml,
    load_rubrics_from_yaml,
)


@pytest.fixture
def questions_yaml(tmp_path: Path) -> Path:
    data = [
        {"id": "q1", "topic": "beta", "difficulty": 1, "prompt": "Prompt 1?"},
        {"id": "q2", "topic": "alpha", "difficulty": 1, "prompt": "Prompt 2?"},
        {"id": "q3", "topic": "alpha", "difficulty": 2, "prompt": "Prompt 3?"},
    ]
    path = tmp_path / "questions.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


@pytest.fixture
def rubrics_yaml(tmp_path: Path) -> Path:
    data = [
        {
            "topic": "alpha",
            "criteria": [
                {
                    "description": "Criterion A",
                    "weak_example": "weak",
                    "medium_example": "medium",
                    "strong_example": "strong",
                }
            ],
        },
        {
            "topic": "beta",
            "criteria": [
                {
                    "description": "Criterion B",
                    "weak_example": "weak",
                    "medium_example": "medium",
                    "strong_example": "strong",
                }
            ],
        },
    ]
    path = tmp_path / "rubrics.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_load_questions_from_yaml_returns_questions(questions_yaml: Path):
    questions = load_questions_from_yaml(questions_yaml)

    assert len(questions) == 3
    assert all(isinstance(q, Question) for q in questions)
    assert questions[0].id == "q1"
    assert questions[0].topic == "beta"
    assert questions[0].difficulty == 1
    assert questions[0].prompt == "Prompt 1?"


def test_load_questions_from_yaml_raises_when_file_missing(tmp_path: Path):
    missing = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_questions_from_yaml(missing)


def test_load_questions_from_yaml_raises_when_not_a_list(tmp_path: Path):
    path = tmp_path / "questions.yaml"
    path.write_text(yaml.dump({"id": "q1"}), encoding="utf-8")

    with pytest.raises(TypeError):
        load_questions_from_yaml(path)


def test_load_questions_from_yaml_raises_when_item_missing_required_field(
    tmp_path: Path,
):
    path = tmp_path / "questions.yaml"
    path.write_text(yaml.dump([{"id": "q1", "topic": "alpha"}]), encoding="utf-8")

    with pytest.raises(TypeError):
        load_questions_from_yaml(path)


def test_load_rubrics_from_yaml_returns_rubric_dict(rubrics_yaml: Path):
    rubrics = load_rubrics_from_yaml(rubrics_yaml)

    assert set(rubrics.keys()) == {"alpha", "beta"}
    assert all(isinstance(r, Rubric) for r in rubrics.values())
    alpha = rubrics["alpha"]
    assert alpha.topic == "alpha"
    assert len(alpha.criteria) == 1
    assert isinstance(alpha.criteria[0], RubricCriterion)
    assert alpha.criteria[0].description == "Criterion A"


def test_load_rubrics_from_yaml_raises_when_file_missing(tmp_path: Path):
    missing = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_rubrics_from_yaml(missing)


def test_load_rubrics_from_yaml_raises_when_not_a_list(tmp_path: Path):
    path = tmp_path / "rubrics.yaml"
    path.write_text(yaml.dump({"topic": "alpha"}), encoding="utf-8")

    with pytest.raises(TypeError):
        load_rubrics_from_yaml(path)


def test_load_rubrics_from_yaml_raises_when_item_missing_topic(tmp_path: Path):
    path = tmp_path / "rubrics.yaml"
    path.write_text(
        yaml.dump(
            [
                {
                    "criteria": [
                        {
                            "description": "x",
                            "weak_example": "w",
                            "medium_example": "m",
                            "strong_example": "s",
                        }
                    ]
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        load_rubrics_from_yaml(path)
