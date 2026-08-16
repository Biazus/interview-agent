from app.core.domain.registry import DomainEnum, DomainModule, register_domain
from app.core.rag.qdrant_receiver import QdrantRetriever
from app.domains.async_messaging.question_bank import \
    StaticAsyncMessagingQuestionBank
from app.domains.async_messaging.rubrics import \
    StaticAsyncMessagingRubricProvider


def _build_async_messaging_domain() -> DomainModule:
    return DomainModule(
        retriever=QdrantRetriever("async_messaging"),
        question_bank=StaticAsyncMessagingQuestionBank(),
        rubric_provider=StaticAsyncMessagingRubricProvider(),
    )


def register_async_messaging_domain() -> None:
    register_domain(DomainEnum.ASYNC_MESSAGING, _build_async_messaging_domain)
