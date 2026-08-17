from app.agents.evaluator import EvaluatorAgent
from app.core.domain.interfaces import InterviewState, Selector
from app.core.domain.registry import DomainModule
from app.core.llm.interfaces import LLMProvider

_MAX_QUESTIONS = 10


class OrchestratorAgent:
    """Conduz uma sessão de entrevista: abre com uma pergunta, recebe respostas,
    aciona o Avaliador, consulta o Seletor para a próxima pergunta/tópico, e
    decide quando encerrar (limite de perguntas, ou nenhum tópico restante)."""

    def __init__(
        self, domain: DomainModule, llm: LLMProvider, selector: Selector
    ) -> None:
        self._domain = domain
        self._selector = selector
        self._evaluator = EvaluatorAgent(
            llm=llm,
            retriever=domain.retriever,
            rubric_provider=domain.rubric_provider,
        )

    def start(self, topic: str, difficulty: int = 1) -> InterviewState:
        question = self._domain.question_bank.next_question(topic, difficulty)
        return InterviewState(
            topic=topic, difficulty=difficulty, current_question=question
        )

    async def submit_answer(self, state: InterviewState, answer: str) -> InterviewState:
        evaluation = await self._evaluator.evaluate(
            topic=state.topic,
            question=state.current_question.prompt,
            answer=answer,
        )
        state.history.append((state.current_question, evaluation))

        if len(state.history) >= _MAX_QUESTIONS:
            state.finished = True
            return state

        try:
            decision = self._selector.decide(state, evaluation)
        except ValueError:
            # Selector não encontrou próximo tópico: não há mais material disponível.
            state.finished = True
            return state

        asked_ids = {q.id for q, _ in state.history} | {state.current_question.id}
        try:
            state.current_question = self._domain.question_bank.next_question(
                decision.next_topic, decision.next_difficulty, exclude_ids=asked_ids
            )
            state.topic = decision.next_topic
            state.difficulty = decision.next_difficulty
        except ValueError:
            state.finished = (
                True  # tópico escolhido também não tem pergunta nesse nível
            )

        return state
