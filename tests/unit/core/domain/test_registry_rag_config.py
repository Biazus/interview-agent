import pytest

from app.core.domain.rag_config import DomainRagConfig
from app.core.domain.registry import (
    DomainEnum,
    DomainModule,
    DomainNotRegisteredError,
    clear_registry,
    get_cached_domain,
    get_domain_rag_config,
    register_domain,
)


def test_register_domain_requires_rag_config(domain_module: DomainModule):
    with pytest.raises(TypeError):
        register_domain(DomainEnum.FAKE_TEST, lambda: domain_module)


def test_get_domain_rag_config_returns_registered_config(
    domain_module: DomainModule,
    fake_test_rag_config: DomainRagConfig,
):
    register_domain(
        DomainEnum.FAKE_TEST,
        lambda: domain_module,
        fake_test_rag_config,
    )

    assert get_domain_rag_config(DomainEnum.FAKE_TEST) == fake_test_rag_config


def test_get_domain_rag_config_raises_when_not_registered():
    with pytest.raises(DomainNotRegisteredError):
        get_domain_rag_config(DomainEnum.FAKE_TEST)


def test_register_domain_rejects_empty_collection_name(
    domain_module: DomainModule,
    tmp_path,
):
    seed_yaml = tmp_path / "seed.yaml"
    seed_yaml.write_text("documents: []", encoding="utf-8")
    bad_config = DomainRagConfig(
        collection_name="",
        seed_manifest_files=(str(tmp_path / "manifest.yaml"),),
        seed_yaml_path=str(seed_yaml),
    )
    (tmp_path / "manifest.yaml").write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="collection_name"):
        register_domain(DomainEnum.FAKE_TEST, lambda: domain_module, bad_config)


def test_register_domain_rejects_empty_manifest_files(
    domain_module: DomainModule,
    tmp_path,
):
    seed_yaml = tmp_path / "seed.yaml"
    seed_yaml.write_text("documents: []", encoding="utf-8")
    bad_config = DomainRagConfig(
        collection_name="fake_test",
        seed_manifest_files=(),
        seed_yaml_path=str(seed_yaml),
    )

    with pytest.raises(ValueError, match="seed_manifest_files"):
        register_domain(DomainEnum.FAKE_TEST, lambda: domain_module, bad_config)


def test_clear_registry_clears_rag_configs_and_domain_cache(
    domain_module: DomainModule,
    fake_test_rag_config: DomainRagConfig,
):
    register_domain(
        DomainEnum.FAKE_TEST,
        lambda: domain_module,
        fake_test_rag_config,
    )
    get_cached_domain(DomainEnum.FAKE_TEST)

    clear_registry()

    with pytest.raises(DomainNotRegisteredError):
        get_domain_rag_config(DomainEnum.FAKE_TEST)
    with pytest.raises(DomainNotRegisteredError):
        get_cached_domain(DomainEnum.FAKE_TEST)
