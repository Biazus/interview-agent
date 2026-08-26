from pathlib import Path

import pytest

from app.core.domain.interfaces import RubricProvider
from app.core.domain.rag_config import DomainRagConfig
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

REPO_ROOT = Path(__file__).resolve().parents[2]


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
def async_messaging_rag_config():
    return DomainRagConfig(
        collection_name="async_messaging",
        seed_manifest_files=("app/domains/async_messaging/rag_seed.yaml",),
        seed_yaml_path=str(REPO_ROOT / "app/domains/async_messaging/rag_seed.yaml"),
    )


@pytest.fixture
def fake_test_rag_config(tmp_path):
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text("manifest-content", encoding="utf-8")
    seed_yaml = tmp_path / "rag_seed.yaml"
    seed_yaml.write_text(
        """documents:
  - id: doc_01
    topic: dead_letter_queue
    text: "test document content for fake domain seed"
""",
        encoding="utf-8",
    )
    return DomainRagConfig(
        collection_name="fake_test",
        seed_manifest_files=(str(manifest_file),),
        seed_yaml_path=str(seed_yaml),
    )


@pytest.fixture
def fake_test_two_rag_config(tmp_path):
    manifest_file = tmp_path / "manifest_two.yaml"
    manifest_file.write_text("manifest-two-content", encoding="utf-8")
    seed_yaml = tmp_path / "rag_seed_two.yaml"
    seed_yaml.write_text(
        """documents:
  - id: doc_two_01
    topic: dead_letter_queue
    text: "second fake domain seed document"
""",
        encoding="utf-8",
    )
    return DomainRagConfig(
        collection_name="fake_test_two",
        seed_manifest_files=(str(manifest_file),),
        seed_yaml_path=str(seed_yaml),
    )


@pytest.fixture
def registered_fake_domain(
    fake_retriever: FakeRAGRetriever,
    question_bank: StaticAsyncMessagingQuestionBank,
    rubric_provider: StaticAsyncMessagingRubricProvider,
    async_messaging_rag_config,
) -> DomainModule:
    def factory() -> DomainModule:
        return DomainModule(
            retriever=fake_retriever,
            question_bank=question_bank,
            rubric_provider=rubric_provider,
        )

    register_domain(
        DomainEnum.ASYNC_MESSAGING,
        factory,
        async_messaging_rag_config,
    )
    return get_domain(DomainEnum.ASYNC_MESSAGING)


@pytest.fixture
def registered_fake_domain_with_rag(
    fake_retriever: FakeRAGRetriever,
    question_bank: StaticAsyncMessagingQuestionBank,
    rubric_provider: StaticAsyncMessagingRubricProvider,
    async_messaging_rag_config,
) -> DomainModule:
    def factory() -> DomainModule:
        return DomainModule(
            retriever=fake_retriever,
            question_bank=question_bank,
            rubric_provider=rubric_provider,
        )

    register_domain(
        DomainEnum.ASYNC_MESSAGING,
        factory,
        async_messaging_rag_config,
    )

    return get_domain(DomainEnum.ASYNC_MESSAGING)


@pytest.fixture
def two_registered_domains(
    domain_module: DomainModule,
    fake_test_rag_config,
    fake_test_two_rag_config,
):
    def factory() -> DomainModule:
        return domain_module

    register_domain(DomainEnum.FAKE_TEST, factory, fake_test_rag_config)
    register_domain(DomainEnum.FAKE_TEST_TWO, factory, fake_test_two_rag_config)

    return [fake_test_rag_config, fake_test_two_rag_config]
