from pathlib import Path
from unittest.mock import patch

from app.core.domain.registry import clear_registry, list_registered_domains

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_main_lifespan_imports_app_bootstrap():
    # Contrato estático: após Green, lifespan delega registro a app.bootstrap
    # e não chama register_async_messaging_domain diretamente no bloco startup.
    main_source = (REPO_ROOT / "app/api/main.py").read_text(encoding="utf-8")
    lifespan_section = main_source.split("async def lifespan", maxsplit=1)[1]
    startup_body = lifespan_section.split("yield", maxsplit=1)[0]

    assert "app.bootstrap" in startup_body
    assert "register_async_messaging_domain" not in startup_body


def test_run_seed_and_main_share_same_registered_domains():
    run_seed_source = (REPO_ROOT / "scripts/run_seed.py").read_text(encoding="utf-8")
    main_source = (REPO_ROOT / "app/api/main.py").read_text(encoding="utf-8")

    assert "app.bootstrap" in run_seed_source
    assert "app.bootstrap" in main_source

    clear_registry()
    import app.bootstrap  # noqa: F401 — registra domínios ao importar

    bootstrap_domains = set(list_registered_domains())

    clear_registry()
    from app.domains.async_messaging.bootstrap import register_async_messaging_domain

    register_async_messaging_domain()
    main_style_domains = set(list_registered_domains())

    assert bootstrap_domains == main_style_domains
    assert bootstrap_domains == {"async_messaging"}


def test_run_seed_calls_ingest_for_each_registered_domain(two_registered_domains):
    ingested_collection_names: list[str] = []

    def capture_ingest(config):
        ingested_collection_names.append(config.collection_name)

    expected_collections = [config.collection_name for config in two_registered_domains]

    with (
        patch("app.core.rag.qdrant_wait.wait_for_qdrant"),
        patch(
            "scripts.run_seed.list_registered_domains",
            return_value=expected_collections,
        ),
        patch(
            "scripts.run_seed.ingest_domain_seed",
            side_effect=capture_ingest,
        ),
    ):
        from scripts.run_seed import main

        main()

    assert set(ingested_collection_names) == set(expected_collections)
    assert len(ingested_collection_names) == len(expected_collections)
