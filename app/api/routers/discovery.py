from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_discovery_service
from app.services.discovery_service import DiscoveryService

router = APIRouter(tags=["discovery"])


@router.get("/domains")
def list_domains(
    discovery_service: DiscoveryService = Depends(get_discovery_service),
) -> list[str]:
    return discovery_service.list_domains()


@router.get("/topics")
def list_topics(
    domain: str | None = Query(default=None),
    discovery_service: DiscoveryService = Depends(get_discovery_service),
) -> list[str]:
    return discovery_service.list_topics(domain)
