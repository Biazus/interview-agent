import asyncio

from app import (  # noqa: F401 — garante que todos os domínios estejam registrados
    bootstrap,
)
from app.agents.orchestrator import InterviewNotFinishedError, OrchestratorAgent
from app.agents.selector_naive import NaiveSelector
from app.core.domain.registry import DomainEnum, get_domain
from app.core.llm.fallback import FallbackLLMProvider
from app.core.llm.providers.groq_provider import GroqProvider
from app.core.llm.providers.openrouter_provider import OpenRouterProvider

from app.core.logging import configure_logging

configure_logging("INFO")

# Respostas fixas propositalmente fracas, para forçar o NaiveSelector a
# tentar trocar de tópico. Como só há um tópico populado hoje, isso deve
# encerrar a entrevista antes de esgotar as respostas ... comportamento
# esperado, não um bug.
FIXED_ANSWERS = [
    "Uma DLQ é uma fila separada das outras,onde vão parar mensagens que falharam, permitindo reprocessamento manual ou intervenção humana para adequação ao erro.",
    "Não tenho certeza, sei la",
    "Uma DLQ é uma fila separada onde vão parar mensagens que falharam.",
    "nao sei.",
    "nao sei.",
    "nao sei.",
    "nao sei.",
    "nao sei.",
    "nao sei.",
    "nao sei.",
]


async def main() -> None:
    llm = FallbackLLMProvider([GroqProvider(), OpenRouterProvider()])
    domain = get_domain(DomainEnum.ASYNC_MESSAGING)
    selector = NaiveSelector(domain=domain)

    orchestrator = OrchestratorAgent(domain=domain, llm=llm, selector=selector)

    state = orchestrator.start(topic="dead_letter_queue", difficulty=1)
    print(f"[INÍCIO] tópico={state.topic} dificuldade={state.difficulty}")
    print(f"Pergunta 1: {state.current_question.prompt}\n")

    # Sanity check: tentar gerar relatório antes do fim deve lançar exceção.
    try:
        await orchestrator.get_report(state)
        print("[ERRO] get_report não lançou exceção com entrevista em andamento!\n")
    except InterviewNotFinishedError:
        print(
            "[OK] get_report bloqueou corretamente relatório de entrevista em andamento.\n"
        )

    for i, answer in enumerate(FIXED_ANSWERS, start=1):
        if state.finished:
            print("Entrevista encerrada antes de todas as respostas serem usadas.")
            break

        print(f"Resposta {i}: {answer}")
        state = await orchestrator.submit_answer(state, answer)

        last_question, last_evaluation = state.history[-1]
        print(f"  -> Nota avaliada: {last_evaluation.score}")
        print(f"  -> Feedback: {last_evaluation.feedback}")

        if state.finished:
            print("\n[FIM] Entrevista encerrada.")
            break

        print(f"  -> Próximo tópico: {state.topic} | dificuldade: {state.difficulty}")
        print(f"  -> Próxima pergunta: {state.current_question.prompt}\n")

    print(f"\nTotal de perguntas respondidas: {len(state.history)}")
    for idx, (question, evaluation) in enumerate(state.history, start=1):
        print(f"{idx}. [{question.topic} / nota={evaluation.score}] {question.prompt}")

    if state.finished:
        print("\n[RELATÓRIO] Gerando relatório final...\n")
        report = await orchestrator.get_report(state)
        print(f"Resumo geral: {report.overall_summary}\n")
        print("Pontos fortes:")
        for item in report.strengths:
            print(f"  - {item}")
        print("Pontos fracos:")
        for item in report.weaknesses:
            print(f"  - {item}")
        print("Sugestões:")
        for item in report.suggestions:
            print(f"  - {item}")
        print(f"\nTotal de perguntas consideradas: {report.total_questions}")

        # Chamar de novo deve reaproveitar o cache (state.report), sem nova
        # chamada de LLM — não há como confirmar isso só pelo output, mas
        # vale observar manualmente (ex: log/print dentro do LLMProvider,
        # se houver) que a segunda chamada não dispara requisição nova.
        report_again = await orchestrator.get_report(state)
        assert (
            report_again is report
        ), "get_report não reaproveitou o cache do relatório!"
        print("\n[OK] Segunda chamada a get_report reaproveitou o relatório em cache.")
    else:
        print(
            "\n[AVISO] Entrevista não terminou dentro do número de respostas fixas fornecidas."
        )


if __name__ == "__main__":
    asyncio.run(main())
