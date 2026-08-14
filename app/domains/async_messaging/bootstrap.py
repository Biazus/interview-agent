from app.core.domain.registry import DomainEnum, DomainModule, register_domain
from app.domains.async_messaging.question_bank import \
    StaticAsyncMessagingQuestionBank
from app.domains.async_messaging.retriever import FakeAsyncMessagingRetriever
from app.domains.async_messaging.rubrics import \
    FakeAsyncMessagingRubricProvider


def _build_async_messaging_domain() -> DomainModule:
    return DomainModule(
        retriever=FakeAsyncMessagingRetriever(),
        question_bank=StaticAsyncMessagingQuestionBank(),
        rubric_provider=FakeAsyncMessagingRubricProvider(),
    )


def register_async_messaging_domain() -> None:
    register_domain(DomainEnum.ASYNC_MESSAGING, _build_async_messaging_domain)
