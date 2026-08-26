import pytest

from app.agents.selector_naive import (
    _HIGH_BAND_MIN,
    _LOW_BAND_MAX,
    _MID_BAND_MAX,
    _SAME_BAND_STREAK,
    NaiveSelector,
)
from app.core.domain.interfaces import Evaluation, InterviewState, Question
from app.core.domain.registry import DomainModule
from app.core.llm.interfaces import LLMResponse


def test_score_band_constants():
    assert _LOW_BAND_MAX == 30
    assert _MID_BAND_MAX == 69
    assert _HIGH_BAND_MIN == 70
    assert _SAME_BAND_STREAK == 2


def _evaluation(score: int, topic: str = "dead_letter_queue") -> Evaluation:
    return Evaluation(
        topic=topic,
        score=score,
        feedback="feedback de teste",
        raw_response=LLMResponse(text="", provider="test", model="test"),
    )


def _question(
    question_id: str,
    topic: str = "dead_letter_queue",
    difficulty: int = 1,
) -> Question:
    return Question(
        id=question_id,
        topic=topic,
        difficulty=difficulty,
        prompt=f"Pergunta {question_id}",
    )


def _state_with_scores(
    scores: list[int],
    *,
    topic: str = "dead_letter_queue",
    difficulty: int = 1,
) -> InterviewState:
    history: list[tuple[Question, Evaluation]] = []
    for index, score in enumerate(scores):
        question = _question(f"q-{index}", topic=topic, difficulty=difficulty)
        history.append((question, _evaluation(score, topic=topic)))

    return InterviewState(
        topic=topic,
        difficulty=difficulty,
        current_question=_question("current", topic=topic, difficulty=difficulty),
        history=history,
    )


@pytest.fixture
def selector(domain_module: DomainModule) -> NaiveSelector:
    return NaiveSelector(domain=domain_module)


@pytest.mark.parametrize(
    ("current", "score", "expected", "case"),
    [
        (1, 30, 1, "fronteira baixa, já no mínimo"),
        (1, 31, 1, "30→31 estável"),
        (1, 69, 1, "média alta estável"),
        (1, 70, 2, "69→70 sobe"),
        (5, 30, 4, "desce no topo"),
        (5, 31, 5, "estável no topo"),
        (5, 70, 5, "capped em 5"),
        (3, 29, 2, "baixa genérica"),
        (3, 32, 3, "média genérica"),
        (3, 71, 4, "alta genérica"),
    ],
)
def test_next_difficulty(
    selector: NaiveSelector,
    current: int,
    score: int,
    expected: int,
    case: str,
):
    assert selector._next_difficulty(current, score) == expected, case


@pytest.mark.parametrize(
    ("scores", "bands", "should_switch"),
    [
        ([25, 28], "low, low", True),
        ([35, 40], "mid, mid", True),
        ([75, 80], "high, high", True),
        ([25, 35], "low, mid", False),
        ([30, 31], "low, mid", False),
        ([69, 70], "mid, high", False),
        ([15], "—", False),
        ([50, 50, 50], "mid×3, últimas 2", True),
    ],
)
def test_should_switch_topic(
    selector: NaiveSelector,
    scores: list[int],
    bands: str,
    should_switch: bool,
):
    state = _state_with_scores(scores)
    assert selector._should_switch_topic(state) is should_switch, bands
