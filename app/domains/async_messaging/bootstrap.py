from app.core.domain.registry import DomainEnum, DomainModule, register_domain
from app.domains.async_messaging.question_bank import \
    StaticAsyncMessagingQuestionBank
from app.domains.async_messaging.retriever import FakeAsyncMessagingRetriever
from app.domains.async_messaging.rubrics import \
    FakeAsyncMessagingRubricProvider


def _build_async_messaging_domain() -> DomainModule:
    return DomainModule(
        retriever=QdrantRetriever("async_messaging"),
        question_bank=None,  # StaticAsyncMessagingQuestionBank(),
        rubric_provider=None,  # FakeAsyncMessagingRubricProvider(),
    )


def register_async_messaging_domain() -> None:
    register_domain(DomainEnum.ASYNC_MESSAGING, _build_async_messaging_domain)
