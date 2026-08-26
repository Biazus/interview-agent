import asyncio

import app.bootstrap  # noqa: F401 — registra domínios antes de get_domain
from app.agents.evaluator import EvaluatorAgent
from app.core.domain.registry import DomainEnum, get_domain
from app.core.llm.fallback import FallbackLLMProvider
from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.providers.openrouter_provider import OpenRouterProvider


async def main() -> None:
    llm = FallbackLLMProvider([GroqProvider(), OpenRouterProvider()])
    domain = get_domain(DomainEnum.ASYNC_MESSAGING)

    agent = EvaluatorAgent(
        llm=llm,
        retriever=domain.retriever,
        rubric_provider=domain.rubric_provider,
    )

    evaluation = await agent.evaluate(
        topic="dead_letter_queue",  # ajuste para o tópico que você populou
        question="O que é o parâmetro BatchSize na configuração de um Event Source Mapping entre SQS e Lambda?",
        answer="O parâmetro BatchSize define o número máximo de mensagens que o poller do AWS Lambda lê de uma fila do Amazon SQS em uma única operação e envia de uma só vez para a sua função Lambda",
    )

    print(f"Nota: {evaluation.score}")
    print(f"Feedback: {evaluation.feedback}")
    print(f"Provider usado: {evaluation.raw_response.provider}")
    print(f"Tokens: {evaluation.raw_response.tokens_used}")


if __name__ == "__main__":
    asyncio.run(main())
