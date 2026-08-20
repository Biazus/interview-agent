from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_candidate_id
from app.api.errors import APIError

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get("/active")
async def get_active_interview(
    _candidate_id: UUID = Depends(get_current_candidate_id),
) -> dict:
    raise APIError(
        status_code=404,
        detail="Nenhuma entrevista ativa encontrada.",
        code="NO_ACTIVE_INTERVIEW",
    )
