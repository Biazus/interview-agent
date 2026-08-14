from app.core.domain.registry import DomainEnum, get_domain
from app.domains.async_messaging.bootstrap import register_async_messaging_domain


def test_registry_resolves_async_messaging_domain():
    register_async_messaging_domain()
    domain = get_domain(DomainEnum.ASYNC_MESSAGING)

    question = domain.question_bank.next_question(topic="dead_letter_queue", difficulty=1)
    assert question.id == "sqs-01"

    chunks = domain.retriever.retrieve(query="o que é DLQ")
    assert len(chunks) > 0

    rubric = domain.rubric_provider.get_rubric(topic="dead_letter_queue")
    assert len(rubric.criteria) > 0