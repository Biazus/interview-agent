import asyncio

from app import (  # noqa: F401 — garante que todos os domínios estejam registrados
    bootstrap,
)
from app.agents.orchestrator import OrchestratorAgent
from app.agents.selector_naive import NaiveSelector
from app.core.domain.registry import DomainEnum, get_domain
from app.core.llm.fallback import FallbackLLMProvider
from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.providers.openrouter_provider import OpenRouterProvider

# Respostas fixas propositalmente fracas, para forçar o NaiveSelector a
# detectar "2 respostas do mesmo nível no mesmo tópico" e tentar trocar de
# tópico. Como hoje só existe um tópico populado (dead_letter_queue), a troca
# deve falhar por falta de tópico disponível, encerrando a entrevista — esse
# é o comportamento esperado a validar neste teste, não um bug.
FIXED_ANSWERS = [
    "Não sei bem, acho que é algo relacionado a erro.",
    "Não tenho certeza, sei la",
    "Uma DLQ é uma fila separada onde vão parar mensagens que falharam.",
]


async def main() -> None:
    llm = FallbackLLMProvider([GroqProvider(), OpenRouterProvider()])
    domain = get_domain(DomainEnum.ASYNC_MESSAGING)
    selector = NaiveSelector(domain=domain)

    orchestrator = OrchestratorAgent(domain=domain, llm=llm, selector=selector)

    state = orchestrator.start(topic="dead_letter_queue", difficulty=1)
    print(f"[INÍCIO] tópico={state.topic} dificuldade={state.difficulty}")
    print(f"Pergunta 1: {state.current_question.prompt}\n")

    for i, answer in enumerate(FIXED_ANSWERS, start=1):
        if state.finished:
            print("Entrevista encerrada antes de todas as respostas serem usadas.")
            break

        print(f"Resposta {i}: {answer}")
        state = await orchestrator.submit_answer(state, answer)

        last_question, last_evaluation = state.history[-1]
        print(f"  -> Nível avaliado: {last_evaluation.level}")
        print(f"  -> Feedback: {last_evaluation.feedback}")

        if state.finished:
            print("\n[FIM] Entrevista encerrada.")
            break

        print(f"  -> Próximo tópico: {state.topic} | dificuldade: {state.difficulty}")
        print(f"  -> Próxima pergunta: {state.current_question.prompt}\n")

    print(f"\nTotal de perguntas respondidas: {len(state.history)}")
    for idx, (question, evaluation) in enumerate(state.history, start=1):
        print(f"{idx}. [{question.topic} / nível={evaluation.level}] {question.prompt}")


if __name__ == "__main__":
    asyncio.run(main())
