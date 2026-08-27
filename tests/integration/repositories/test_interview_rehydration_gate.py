import pytest

from app.agents.orchestrator import OrchestratorAgent
from app.agents.selector_naive import NaiveSelector
from app.core.domain.static_providers import StaticQuestionBank
from app.core.domain.registry import (
    DomainEnum,
    DomainModule,
    clear_registry,
    get_domain,
    register_domain,
)
from app.domains.async_messaging.question_bank import _DATA_PATH
from app.domains.async_messaging.rag_config import build_rag_config
from app.domains.async_messaging.rubrics import StaticAsyncMessagingRubricProvider
from app.repositories import interview_mapper
from tests.fakes.llm import DeterministicLLM
from tests.fakes.retriever import FakeRAGRetriever


@pytest.fixture
def registered_fake_domain() -> DomainModule:
    clear_registry()
    retriever = FakeRAGRetriever()
    question_bank = StaticQuestionBank(
        _DATA_PATH,
        candidate_selector=lambda candidates: candidates[0],
    )
    rubric_provider = StaticAsyncMessagingRubricProvider()

    def factory() -> DomainModule:
        return DomainModule(
            retriever=retriever,
            question_bank=question_bank,
            rubric_provider=rubric_provider,
        )

    register_domain(DomainEnum.ASYNC_MESSAGING, factory, build_rag_config())
    return get_domain(DomainEnum.ASYNC_MESSAGING)


@pytest.fixture
def orchestrator(registered_fake_domain: DomainModule) -> OrchestratorAgent:
    return OrchestratorAgent(
        domain=registered_fake_domain,
        llm=DeterministicLLM(),
        selector=NaiveSelector(domain=registered_fake_domain),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_persist_reload_matches_memory_state(
    orchestrator: OrchestratorAgent,
    interview_repository_with_candidate,
    require_postgres,
):
    repository, candidate_id = interview_repository_with_candidate
    memory_state = orchestrator.start("dead_letter_queue", difficulty=1)

    interview_id = await repository.create_interview(
        candidate_id=candidate_id,
        domain="async_messaging",
        topic=memory_state.topic,
        difficulty=memory_state.difficulty,
        current_question_id=memory_state.current_question.id,
        current_question_topic=memory_state.current_question.topic,
        current_question_difficulty=memory_state.current_question.difficulty,
        current_question_prompt=memory_state.current_question.prompt,
    )

    interview = await repository.get_by_id_for_candidate(interview_id, candidate_id)
    turns = await repository.get_turns(interview_id)
    reloaded = interview_mapper.to_state(interview, turns)

    assert reloaded.finished == memory_state.finished
    assert reloaded.topic == memory_state.topic
    assert reloaded.difficulty == memory_state.difficulty
    assert reloaded.current_question == memory_state.current_question
    assert reloaded.history == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_submit_answer_after_reload_matches_memory_flow(
    orchestrator: OrchestratorAgent,
    interview_repository_with_candidate,
    require_postgres,
):
    repository, candidate_id = interview_repository_with_candidate
    answer = "DLQ armazena mensagens que falharam após retries."

    memory_state = orchestrator.start("dead_letter_queue", difficulty=1)

    interview_id = await repository.create_interview(
        candidate_id=candidate_id,
        domain="async_messaging",
        topic=memory_state.topic,
        difficulty=memory_state.difficulty,
        current_question_id=memory_state.current_question.id,
        current_question_topic=memory_state.current_question.topic,
        current_question_difficulty=memory_state.current_question.difficulty,
        current_question_prompt=memory_state.current_question.prompt,
    )

    memory_after = await orchestrator.submit_answer(memory_state, answer)

    interview = await repository.get_by_id_for_candidate(interview_id, candidate_id)
    turns = await repository.get_turns(interview_id)
    reloaded = interview_mapper.to_state(interview, turns)

    db_after = await orchestrator.submit_answer(reloaded, answer)

    assert len(db_after.history) == len(memory_after.history)
    assert db_after.finished == memory_after.finished
    assert db_after.topic == memory_after.topic
    assert db_after.difficulty == memory_after.difficulty
    assert db_after.current_question.id == memory_after.current_question.id
    assert db_after.history[0][0].id == memory_after.history[0][0].id
    assert db_after.history[0][1].score == memory_after.history[0][1].score
    assert db_after.history[0][1].feedback == memory_after.history[0][1].feedback
