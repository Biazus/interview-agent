from pathlib import Path

import pytest
import yaml

from app.core.domain.interfaces import Question
from app.core.domain.static_providers import StaticQuestionBank, StaticRubricProvider


@pytest.fixture
def questions_yaml(tmp_path: Path) -> Path:
    data = [
        {"id": "q1", "topic": "beta", "difficulty": 1, "prompt": "Prompt 1?"},
        {"id": "q2", "topic": "alpha", "difficulty": 1, "prompt": "Prompt 2?"},
        {"id": "q3", "topic": "alpha", "difficulty": 1, "prompt": "Prompt 3?"},
        {"id": "q4", "topic": "alpha", "difficulty": 2, "prompt": "Prompt 4?"},
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


def test_next_question_returns_matching_candidate_from_topic_and_difficulty(
    questions_yaml: Path,
):
    bank = StaticQuestionBank(questions_yaml)

    question = bank.next_question(topic="alpha", difficulty=1)

    assert question.id in {"q2", "q3"}
    assert question.topic == "alpha"
    assert question.difficulty == 1


def test_next_question_uses_random_choice(monkeypatch, questions_yaml: Path):
    captured: list[list[Question]] = []

    def fake_choice(candidates: list[Question]) -> Question:
        captured.append(candidates)
        return candidates[0]

    monkeypatch.setattr(
        "app.core.domain.static_providers.random.choice",
        fake_choice,
    )

    bank = StaticQuestionBank(questions_yaml)

    bank.next_question(topic="alpha", difficulty=1)

    assert len(captured) == 1
    assert {q.id for q in captured[0]} == {"q2", "q3"}


def test_next_question_respects_exclude_ids(questions_yaml: Path):
    bank = StaticQuestionBank(questions_yaml)

    question = bank.next_question(topic="alpha", difficulty=1, exclude_ids={"q2"})

    assert question.id == "q3"


def test_next_question_raises_when_no_candidates(questions_yaml: Path):
    bank = StaticQuestionBank(questions_yaml)

    with pytest.raises(ValueError, match="Nenhuma pergunta encontrada"):
        bank.next_question(topic="gamma", difficulty=1)


def test_next_question_raises_when_all_candidates_excluded(questions_yaml: Path):
    bank = StaticQuestionBank(questions_yaml)

    with pytest.raises(ValueError, match="Nenhuma pergunta encontrada"):
        bank.next_question(
            topic="alpha",
            difficulty=1,
            exclude_ids={"q2", "q3"},
        )


def test_topics_returns_sorted_unique_topics(questions_yaml: Path):
    bank = StaticQuestionBank(questions_yaml)

    assert bank.topics() == ["alpha", "beta"]


def test_next_question_uses_custom_candidate_selector(questions_yaml: Path):
    def pick_last(candidates: list[Question]) -> Question:
        return candidates[-1]

    bank = StaticQuestionBank(questions_yaml, candidate_selector=pick_last)

    question = bank.next_question(topic="alpha", difficulty=1)

    assert question.id == "q3"


def test_get_rubric_returns_rubric_for_existing_topic(rubrics_yaml: Path):
    provider = StaticRubricProvider(rubrics_yaml)

    rubric = provider.get_rubric(topic="alpha")

    assert rubric.topic == "alpha"
    assert len(rubric.criteria) == 1
    assert rubric.criteria[0].description == "Criterion A"


def test_get_rubric_raises_when_topic_missing(rubrics_yaml: Path):
    provider = StaticRubricProvider(rubrics_yaml)

    with pytest.raises(ValueError, match="Nenhuma rubrica encontrada"):
        provider.get_rubric(topic="unknown")
