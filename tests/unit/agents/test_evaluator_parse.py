import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.evaluator import EvaluatorAgent
from app.core.llm.exceptions import StructuredOutputError
from app.core.llm.interfaces import LLMResponse
from app.domains.async_messaging.rubrics import StaticAsyncMessagingRubricProvider
from tests.fakes.retriever import FakeRAGRetriever


@pytest.mark.asyncio
async def test_evaluate_raises_structured_output_error_on_invalid_json():
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(
            text="Resposta sem JSON válido.",
            provider="test",
            model="test",
        )
    )
    agent = EvaluatorAgent(
        llm=llm,
        retriever=FakeRAGRetriever(),
        rubric_provider=StaticAsyncMessagingRubricProvider(),
    )

    with pytest.raises(StructuredOutputError):
        await agent.evaluate(
            topic="dead_letter_queue",
            question="O que é uma DLQ?",
            answer="Não sei.",
        )


@pytest.mark.asyncio
async def test_evaluate_raises_structured_output_error_on_empty_response():
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(text="", provider="test", model="test")
    )
    agent = EvaluatorAgent(
        llm=llm,
        retriever=FakeRAGRetriever(),
        rubric_provider=StaticAsyncMessagingRubricProvider(),
    )

    with pytest.raises(StructuredOutputError):
        await agent.evaluate(
            topic="dead_letter_queue",
            question="O que é uma DLQ?",
            answer="Não sei.",
        )


@pytest.mark.asyncio
async def test_evaluate_raises_structured_output_error_on_schema_violation():
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(
            text=json.dumps({"score": 0, "feedback": "fora da faixa"}),
            provider="test",
            model="test",
        )
    )
    agent = EvaluatorAgent(
        llm=llm,
        retriever=FakeRAGRetriever(),
        rubric_provider=StaticAsyncMessagingRubricProvider(),
    )

    with pytest.raises(StructuredOutputError):
        await agent.evaluate(
            topic="dead_letter_queue",
            question="O que é uma DLQ?",
            answer="Não sei.",
        )
