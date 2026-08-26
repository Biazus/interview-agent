from unittest.mock import patch

import pytest
from fastapi import FastAPI

from app.bootstrap import bootstrap_domains
from app.core.domain.registry import (
    DomainEnum,
    clear_registry,
    get_cached_domain,
    list_registered_domains,
)


def test_run_seed_and_main_share_same_registered_domains():
    clear_registry()
    bootstrap_domains()
    bootstrap_domains_from_seed = set(list_registered_domains())

    clear_registry()
    bootstrap_domains()
    bootstrap_domains_from_main = set(list_registered_domains())

    assert (
        bootstrap_domains_from_seed
        == bootstrap_domains_from_main
        == {"async_messaging"}
    )


@pytest.mark.asyncio
async def test_lifespan_warms_only_registered_domains():
    from app.api import main as main_module

    clear_registry()
    warmed_domains: list[str] = []

    def track_warmup(domain: DomainEnum):
        warmed_domains.append(domain.value)
        return get_cached_domain(domain)

    with patch.object(main_module, "get_cached_domain", side_effect=track_warmup):
        async with main_module.lifespan(FastAPI()):
            pass

    registered = set(list_registered_domains())
    assert set(warmed_domains) == registered
    assert DomainEnum.FAKE_TEST.value not in warmed_domains
    assert DomainEnum.FAKE_TEST_TWO.value not in warmed_domains


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
