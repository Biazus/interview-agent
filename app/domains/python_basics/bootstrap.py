from app.core.domain.registry import DomainEnum, DomainModule, register_domain
from app.core.rag.factory import get_qdrant_retriever
from app.domains.python_basics.question_bank import StaticPythonBasicsQuestionBank
from app.domains.python_basics.rag_config import build_rag_config
from app.domains.python_basics.rubrics import StaticPythonBasicsRubricProvider


def _build_python_basics_domain() -> DomainModule:
    rag = build_rag_config()
    return DomainModule(
        retriever=get_qdrant_retriever(rag.collection_name),
        question_bank=StaticPythonBasicsQuestionBank(),
        rubric_provider=StaticPythonBasicsRubricProvider(),
    )


def register_python_basics_domain() -> None:
    rag = build_rag_config()
    register_domain(DomainEnum.PYTHON_BASICS, _build_python_basics_domain, rag)
