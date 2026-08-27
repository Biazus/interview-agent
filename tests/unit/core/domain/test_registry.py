import pytest

from app.core.domain.registry import (
    DomainEnum,
    DomainModule,
    DomainNotRegisteredError,
    get_domain,
    list_registered_domains,
)
from tests.fakes.retriever import FakeRAGRetriever


def test_get_domain_raises_when_not_registered():
    with pytest.raises(DomainNotRegisteredError):
        get_domain(DomainEnum.ASYNC_MESSAGING)


def test_list_registered_domains_returns_only_registered(
    registered_fake_domain: DomainModule,
):
    domains = list_registered_domains()

    assert domains == [DomainEnum.ASYNC_MESSAGING.value]


def test_get_domain_resolves_registered_domain(
    registered_fake_domain: DomainModule,
):
    domain = registered_fake_domain

    question = domain.question_bank.next_question(
        topic="dead_letter_queue", difficulty=1
    )
    assert question.id in {"sqs-01", "sqs-05"}

    rubric = domain.rubric_provider.get_rubric(topic="dead_letter_queue")
    assert len(rubric.criteria) > 0


def test_get_domain_uses_fake_retriever(registered_fake_domain: DomainModule):
    chunks = registered_fake_domain.retriever.retrieve(
        query="o que é DLQ", topic="dead_letter_queue"
    )

    assert len(chunks) > 0
    assert all(isinstance(c.source, str) for c in chunks)
    assert isinstance(registered_fake_domain.retriever, FakeRAGRetriever)
