import asyncio
import json
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.evaluator import EvaluatorAgent
from app.core.domain.interfaces import Chunk
from app.core.llm.interfaces import LLMResponse
from app.domains.async_messaging.rubrics import StaticAsyncMessagingRubricProvider
from tests.fakes.retriever import FakeRAGRetriever


@pytest.fixture
def rubric_provider() -> StaticAsyncMessagingRubricProvider:
    return StaticAsyncMessagingRubricProvider()


@pytest.fixture
def evaluator(
    fake_retriever: FakeRAGRetriever,
    rubric_provider: StaticAsyncMessagingRubricProvider,
) -> EvaluatorAgent:
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(
            text=json.dumps({"score": 85, "feedback": "Boa resposta."}),
            provider="test",
            model="test",
        )
    )
    return EvaluatorAgent(
        llm=llm, retriever=fake_retriever, rubric_provider=rubric_provider
    )


@pytest.mark.asyncio
async def test_evaluate_returns_parsed_evaluation(
    evaluator: EvaluatorAgent,
):
    result = await evaluator.evaluate(
        topic="dead_letter_queue",
        question="O que é uma DLQ?",
        answer="Fila para mensagens que falharam após retries.",
    )

    assert result.topic == "dead_letter_queue"
    assert result.score == 85
    assert result.feedback == "Boa resposta."
    assert result.raw_response.provider == "test"


@pytest.mark.asyncio
async def test_evaluate_does_not_block_event_loop(
    rubric_provider: StaticAsyncMessagingRubricProvider,
):
    gate = threading.Event()

    class BlockingRetriever:
        def retrieve(self, query: str, topic: str, top_k: int = 5) -> list[Chunk]:
            gate.wait(timeout=2)
            return [Chunk(text="ctx", source="s", topic=topic)]

    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(
            text=json.dumps({"score": 55, "feedback": "ok"}),
            provider="test",
            model="test",
        )
    )
    agent = EvaluatorAgent(
        llm=llm, retriever=BlockingRetriever(), rubric_provider=rubric_provider
    )

    evaluate_task = asyncio.create_task(
        agent.evaluate("dead_letter_queue", "pergunta", "resposta")
    )
    await asyncio.sleep(0.05)

    parallel_ran = False

    async def parallel_work() -> None:
        nonlocal parallel_ran
        parallel_ran = True

    await asyncio.wait_for(parallel_work(), timeout=0.5)
    assert parallel_ran

    gate.set()
    result = await evaluate_task
    assert result.score == 55
    assert result.feedback == "ok"
