from app.core.domain.registry import DomainEnum, DomainModule, register_domain
from app.core.rag.factory import get_qdrant_retriever
from app.domains.async_messaging.question_bank import StaticAsyncMessagingQuestionBank
from app.domains.async_messaging.rag_config import build_rag_config
from app.domains.async_messaging.rubrics import StaticAsyncMessagingRubricProvider


def _build_async_messaging_domain() -> DomainModule:
    rag = build_rag_config()
    return DomainModule(
        retriever=get_qdrant_retriever(rag.collection_name),
        question_bank=StaticAsyncMessagingQuestionBank(),
        rubric_provider=StaticAsyncMessagingRubricProvider(),
    )


def register_async_messaging_domain() -> None:
    rag = build_rag_config()
    register_domain(DomainEnum.ASYNC_MESSAGING, _build_async_messaging_domain, rag)
