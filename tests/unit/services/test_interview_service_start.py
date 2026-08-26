import importlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.domain.registry import DomainEnum, register_domain
from app.core.exceptions import InvalidDomain
from app.services.interview_service import InterviewService


@pytest.fixture
def interview_service_setup(
    registered_fake_domain_with_rag, async_messaging_rag_config
):
    candidate_id = uuid4()
    interview_id = uuid4()

    repo = MagicMock()
    repo.get_active_by_candidate = AsyncMock(return_value=None)
    repo.create_interview = AsyncMock(return_value=interview_id)

    question = registered_fake_domain_with_rag.question_bank.next_question(
        topic="dead_letter_queue", difficulty=1
    )
    interview_row = MagicMock(
        id=interview_id,
        domain=DomainEnum.ASYNC_MESSAGING.value,
        topic="dead_letter_queue",
        difficulty=1,
        status="active",
        questions_answered=0,
        current_question_id=question.id,
        current_question_topic=question.topic,
        current_question_difficulty=question.difficulty,
        current_question_prompt=question.prompt,
    )
    repo.get_by_id_for_candidate = AsyncMock(return_value=interview_row)

    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    orchestrator = MagicMock()
    state = MagicMock()
    state.topic = "dead_letter_queue"
    state.difficulty = 1
    state.current_question = question
    orchestrator.start.return_value = state

    orchestrator_factory = MagicMock(return_value=orchestrator)
    rag_check = MagicMock()

    service = InterviewService(
        repository=repo,
        session=session,
        orchestrator_factory=orchestrator_factory,
        rag_readiness_check=rag_check,
    )

    return service, rag_check, candidate_id, async_messaging_rag_config


@pytest.mark.asyncio
async def test_start_interview_uses_registry_rag_config_not_importlib(
    interview_service_setup,
):
    service, rag_check, candidate_id, async_messaging_rag_config = (
        interview_service_setup
    )

    with patch.object(importlib, "import_module") as mock_import_module:
        await service.start_interview(
            candidate_id,
            "async_messaging",
            "dead_letter_queue",
            1,
        )

    mock_import_module.assert_not_called()
    rag_check.assert_called_once_with(
        async_messaging_rag_config.collection_name,
        async_messaging_rag_config.seed_manifest_files,
    )


@pytest.mark.asyncio
async def test_start_interview_raises_invalid_domain_for_unregistered(
    domain_module,
    fake_test_rag_config,
):
    register_domain(
        DomainEnum.ASYNC_MESSAGING,
        lambda: domain_module,
        fake_test_rag_config,
    )

    repo = MagicMock()
    repo.get_active_by_candidate = AsyncMock(return_value=None)
    session = MagicMock()
    rag_check = MagicMock()
    orchestrator_factory = MagicMock()

    service = InterviewService(
        repository=repo,
        session=session,
        orchestrator_factory=orchestrator_factory,
        rag_readiness_check=rag_check,
    )

    with pytest.raises(InvalidDomain, match="não registrado"):
        await service.start_interview(
            uuid4(),
            DomainEnum.FAKE_TEST.value,
            "dead_letter_queue",
            1,
        )

    rag_check.assert_not_called()
