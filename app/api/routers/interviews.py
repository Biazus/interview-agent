from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_candidate_id, get_interview_service
from app.api.schemas.interviews import StartInterviewRequest, SubmitAnswerRequest
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_interview(
    body: StartInterviewRequest,
    candidate_id: UUID = Depends(get_current_candidate_id),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    return await service.start_interview(
        candidate_id=candidate_id,
        domain=body.domain,
        topic=body.topic,
        difficulty=body.difficulty,
    )


@router.get("/active")
async def get_active_interview(
    candidate_id: UUID = Depends(get_current_candidate_id),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    return await service.get_active_interview(candidate_id)


@router.post("/{interview_id}/answers")
async def submit_answer(
    interview_id: UUID,
    body: SubmitAnswerRequest,
    candidate_id: UUID = Depends(get_current_candidate_id),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    return await service.submit_answer(
        candidate_id=candidate_id,
        interview_id=interview_id,
        answer=body.answer,
    )


@router.get("/{interview_id}/report")
async def get_report(
    interview_id: UUID,
    candidate_id: UUID = Depends(get_current_candidate_id),
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    return await service.get_report(candidate_id, interview_id)
