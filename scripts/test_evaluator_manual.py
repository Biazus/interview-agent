import asyncio

from app import bootstrap
from app.agents.evaluator import EvaluatorAgent
from app.core.domain.registry import DomainEnum, get_domain, register_domain
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
        question="O que é uma Dead Letter Queue e quando ela deveria ser usada?",
        answer="É uma fila que guarda mensagens que falharam depois de várias tentativas.",
    )

    print(f"Nível: {evaluation.level}")
    print(f"Feedback: {evaluation.feedback}")
    print(f"Provider usado: {evaluation.raw_response.provider}")
    print(f"Tokens: {evaluation.raw_response.tokens_used}")


if __name__ == "__main__":
    asyncio.run(main())
