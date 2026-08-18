import pytest

from app.agents.orchestrator import OrchestratorAgent
from app.core.domain.interfaces import Evaluation, InterviewState
from app.core.domain.registry import DomainModule
from app.core.llm.interfaces import LLMResponse
from app.domains.async_messaging.question_bank import StaticAsyncMessagingQuestionBank


@pytest.fixture
def orchestrator(domain_module: DomainModule) -> OrchestratorAgent:
    return OrchestratorAgent(domain=domain_module, llm=None, selector=None)  # type: ignore[arg-type]


def test_resolve_falls_back_to_higher_difficulty_same_topic(
    orchestrator: OrchestratorAgent, question_bank: StaticAsyncMessagingQuestionBank
):
    exclude = {"sqs-01", "sqs-05"}  # esgota dificuldade 1 em dead_letter_queue
    question = orchestrator._resolve_next_question(
        "dead_letter_queue", 1, exclude_ids=exclude
    )
    assert question is not None
    assert question.topic == "dead_letter_queue"
    assert question.difficulty == 2
    assert question.id not in exclude


def test_resolve_falls_back_to_other_topic(
    orchestrator: OrchestratorAgent, question_bank: StaticAsyncMessagingQuestionBank
):
    dlq_ids = {q.id for q in question_bank._questions if q.topic == "dead_letter_queue"}
    question = orchestrator._resolve_next_question(
        "dead_letter_queue", 1, exclude_ids=dlq_ids
    )
    assert question is not None
    assert question.topic != "dead_letter_queue"


def test_resolve_returns_none_when_all_questions_used(
    orchestrator: OrchestratorAgent, question_bank: StaticAsyncMessagingQuestionBank
):
    all_ids = {q.id for q in question_bank._questions}
    question = orchestrator._resolve_next_question(
        "dead_letter_queue", 1, exclude_ids=all_ids
    )
    assert question is None


def test_resolve_exhausted_difficulty_one_finds_same_topic_level_two(
    orchestrator: OrchestratorAgent,
):
    # batch_processing tem só 1 pergunta em d=1; fallback deve subir para d=2
    exclude = {"lambda-10"}
    question = orchestrator._resolve_next_question(
        "batch_processing", 1, exclude_ids=exclude
    )
    assert question is not None
    assert question.topic == "batch_processing"
    assert question.difficulty == 2


def test_resolve_skips_excluded_topics_when_cross_topic_fallback(
    orchestrator: OrchestratorAgent, question_bank: StaticAsyncMessagingQuestionBank
):
    batch_ids = {
        q.id for q in question_bank._questions if q.topic == "batch_processing"
    }
    question = orchestrator._resolve_next_question(
        "batch_processing",
        1,
        exclude_ids=batch_ids,
        exclude_topics={"dead_letter_queue", "batch_processing"},
    )
    assert question is not None
    assert question.topic not in {"dead_letter_queue", "batch_processing"}


def test_selector_pick_next_topic_skips_visited_topics(
    question_bank: StaticAsyncMessagingQuestionBank,
    domain_module: DomainModule,
):
    from app.agents.selector_naive import NaiveSelector

    selector = NaiveSelector(domain=domain_module)

    dlq_q = question_bank.next_question("dead_letter_queue", 1)
    ev = Evaluation(
        topic="dead_letter_queue",
        level="weak",
        feedback="fb",
        raw_response=LLMResponse(text="", provider="t", model="t"),
    )
    state = InterviewState(
        topic="dead_letter_queue",
        difficulty=1,
        current_question=dlq_q,
        history=[(dlq_q, ev), (dlq_q, ev)],
    )

    next_topic = selector._pick_next_topic(state)
    assert next_topic != "dead_letter_queue"
    assert next_topic == "batch_processing"
