import pytest

from app.core.domain.interfaces import RubricProvider
from app.core.domain.registry import (
    DomainEnum,
    DomainModule,
    clear_registry,
    get_domain,
    register_domain,
)
from app.domains.async_messaging.question_bank import StaticAsyncMessagingQuestionBank
from app.domains.async_messaging.rubrics import StaticAsyncMessagingRubricProvider
from tests.fakes.retriever import FakeRAGRetriever


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def fake_retriever() -> FakeRAGRetriever:
    return FakeRAGRetriever()


@pytest.fixture
def question_bank() -> StaticAsyncMessagingQuestionBank:
    return StaticAsyncMessagingQuestionBank()


@pytest.fixture
def rubric_provider() -> StaticAsyncMessagingRubricProvider:
    return StaticAsyncMessagingRubricProvider()


@pytest.fixture
def domain_module(
    fake_retriever: FakeRAGRetriever,
    question_bank: StaticAsyncMessagingQuestionBank,
    rubric_provider: RubricProvider,
) -> DomainModule:
    return DomainModule(
        retriever=fake_retriever,
        question_bank=question_bank,
        rubric_provider=rubric_provider,
    )


@pytest.fixture
def registered_fake_domain(
    fake_retriever: FakeRAGRetriever,
    question_bank: StaticAsyncMessagingQuestionBank,
    rubric_provider: StaticAsyncMessagingRubricProvider,
) -> DomainModule:
    def factory() -> DomainModule:
        return DomainModule(
            retriever=fake_retriever,
            question_bank=question_bank,
            rubric_provider=rubric_provider,
        )

    register_domain(DomainEnum.ASYNC_MESSAGING, factory)
    return get_domain(DomainEnum.ASYNC_MESSAGING)
