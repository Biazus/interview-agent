from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.evaluator import EvaluatorAgent
from app.core.llm.interfaces import LLMResponse
from app.domains.async_messaging.rubrics import StaticAsyncMessagingRubricProvider
from tests.fakes.retriever import FakeRAGRetriever


@pytest.mark.asyncio
async def test_parse_raises_evaluation_parse_error_when_nivel_missing():
    pytest.importorskip(
        "app.agents.evaluator",
        reason="EvaluationParseError ainda não implementado",
    )
    from app.agents.evaluator import EvaluationParseError  # noqa: E402

    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(
            text="Resposta sem o formato NIVEL/FEEDBACK.",
            provider="test",
            model="test",
        )
    )
    agent = EvaluatorAgent(
        llm=llm,
        retriever=FakeRAGRetriever(),
        rubric_provider=StaticAsyncMessagingRubricProvider(),
    )

    with pytest.raises(EvaluationParseError):
        await agent.evaluate(
            topic="dead_letter_queue",
            question="O que é uma DLQ?",
            answer="Não sei.",
        )
