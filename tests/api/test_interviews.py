from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.constants import MAX_ANSWER_LENGTH
from tests.fakes.llm import DeterministicLLM, FailingEvaluationLLM

_START_PAYLOAD = {
    "domain": "async_messaging",
    "topic": "dead_letter_queue",
    "difficulty": 1,
}


@pytest.fixture
async def interview_client(authenticated_client: AsyncClient) -> AsyncClient:
    fake_llm = DeterministicLLM()
    with patch("app.api.dependencies.get_llm_chain", lambda: fake_llm):
        yield authenticated_client


async def _start_interview(client: AsyncClient) -> UUID:
    response = await client.post("/interviews", json=_START_PAYLOAD)
    assert response.status_code == 201
    return UUID(response.json()["interview_id"])


@pytest.mark.asyncio
async def test_happy_path_start_answer_report(interview_client: AsyncClient):
    with patch("app.agents.orchestrator._MAX_QUESTIONS", 1):
        interview_id = await _start_interview(interview_client)

        answer_response = await interview_client.post(
            f"/interviews/{interview_id}/answers",
            json={"answer": "DLQ armazena mensagens que falharam após retries."},
        )

        assert answer_response.status_code == 200
        answer_body = answer_response.json()
        assert answer_body["finished"] is True
        assert answer_body["questions_answered"] == 1
        assert "current_question" not in answer_body
        assert "level" not in answer_body
        assert "feedback" not in answer_body

        report_response = await interview_client.get(
            f"/interviews/{interview_id}/report"
        )

        assert report_response.status_code == 200
        report_body = report_response.json()
        assert report_body["interview_id"] == str(interview_id)
        assert report_body["overall_summary"]
        assert isinstance(report_body["strengths"], list)
        assert report_body["total_questions"] == 1


@pytest.mark.asyncio
async def test_second_active_interview_returns_409(interview_client: AsyncClient):
    await _start_interview(interview_client)

    second = await interview_client.post("/interviews", json=_START_PAYLOAD)

    assert second.status_code == 409
    assert second.json()["code"] == "ACTIVE_INTERVIEW_EXISTS"


@pytest.mark.asyncio
async def test_get_active_after_start(interview_client: AsyncClient):
    interview_id = await _start_interview(interview_client)

    active = await interview_client.get("/interviews/active")

    assert active.status_code == 200
    body = active.json()
    assert body["interview_id"] == str(interview_id)
    assert body["finished"] is False
    assert body["current_question"]["id"]


@pytest.mark.asyncio
async def test_submit_answer_response_omits_evaluation_fields(
    interview_client: AsyncClient,
):
    interview_id = await _start_interview(interview_client)

    response = await interview_client.post(
        f"/interviews/{interview_id}/answers",
        json={"answer": "Resposta com conteúdo suficiente para avaliação."},
    )

    assert response.status_code == 200
    body = response.json()
    assert "level" not in body
    assert "feedback" not in body
    assert "evaluation_level" not in body
    assert "evaluation_feedback" not in body


@pytest.mark.asyncio
async def test_submit_on_finished_interview_returns_409(interview_client: AsyncClient):
    with patch("app.agents.orchestrator._MAX_QUESTIONS", 1):
        interview_id = await _start_interview(interview_client)

        first = await interview_client.post(
            f"/interviews/{interview_id}/answers",
            json={"answer": "Resposta que encerra a entrevista."},
        )
        assert first.status_code == 200
        assert first.json()["finished"] is True

        second = await interview_client.post(
            f"/interviews/{interview_id}/answers",
            json={"answer": "Tentativa após finalização."},
        )

        assert second.status_code == 409
        assert second.json()["code"] == "INTERVIEW_ALREADY_FINISHED"


@pytest.mark.asyncio
async def test_report_while_in_progress_returns_409(interview_client: AsyncClient):
    interview_id = await _start_interview(interview_client)

    response = await interview_client.get(f"/interviews/{interview_id}/report")

    assert response.status_code == 409
    assert response.json()["code"] == "INTERVIEW_NOT_FINISHED"


@pytest.mark.asyncio
async def test_empty_answer_returns_422(interview_client: AsyncClient):
    interview_id = await _start_interview(interview_client)

    response = await interview_client.post(
        f"/interviews/{interview_id}/answers",
        json={"answer": ""},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "EMPTY_ANSWER"


@pytest.mark.asyncio
async def test_whitespace_only_answer_returns_422(interview_client: AsyncClient):
    interview_id = await _start_interview(interview_client)

    response = await interview_client.post(
        f"/interviews/{interview_id}/answers",
        json={"answer": "   "},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "EMPTY_ANSWER"


@pytest.mark.asyncio
async def test_answer_too_long_returns_422(interview_client: AsyncClient):
    interview_id = await _start_interview(interview_client)

    response = await interview_client.post(
        f"/interviews/{interview_id}/answers",
        json={"answer": "x" * (MAX_ANSWER_LENGTH + 1)},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "ANSWER_TOO_LONG"
    assert str(MAX_ANSWER_LENGTH) in body["detail"]


@pytest.mark.asyncio
async def test_llm_failure_returns_503_without_extra_turn(
    interview_client: AsyncClient,
):
    with patch("app.api.dependencies.get_llm_chain", lambda: FailingEvaluationLLM()):
        interview_id = await _start_interview(interview_client)

        fail = await interview_client.post(
            f"/interviews/{interview_id}/answers",
            json={"answer": "Resposta válida que não será persistida."},
        )

        assert fail.status_code == 503
        assert fail.json()["code"] == "LLM_UNAVAILABLE"

        active = await interview_client.get("/interviews/active")
        assert active.status_code == 200
        assert active.json()["questions_answered"] == 0
