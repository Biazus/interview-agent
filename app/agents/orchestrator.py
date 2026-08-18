from app.agents.evaluator import EvaluatorAgent
from app.agents.reporting import ReportingAgent
from app.core.domain.interfaces import CandidateReport, InterviewState, Question, Selector
from app.core.domain.registry import DomainModule
from app.core.llm.interfaces import LLMProvider

_MAX_QUESTIONS = 10
_MAX_DIFFICULTY = 5


class InterviewNotFinishedError(Exception):
    """Levantada ao tentar gerar relatório de uma entrevista ainda em andamento."""


class OrchestratorAgent:
    def __init__(self, domain: DomainModule, llm: LLMProvider, selector: Selector) -> None:
        self._domain = domain
        self._selector = selector
        self._evaluator = EvaluatorAgent(
            llm=llm,
            retriever=domain.retriever,
            rubric_provider=domain.rubric_provider,
        )
        self.reporting_agent = ReportingAgent(llm=llm)

    def _used_question_ids(self, state: InterviewState) -> set[str]:
        return {question.id for question, _ in state.history}

    def _visited_topics(self, state: InterviewState) -> set[str]:
        return {question.topic for question, _ in state.history}

    def _difficulty_fallback_order(self, preferred: int) -> list[int]:
        higher = list(range(preferred, _MAX_DIFFICULTY + 1))
        lower = list(range(preferred - 1, 0, -1))
        return higher + lower

    def _resolve_next_question(
        self,
        topic: str,
        difficulty: int,
        exclude_ids: set[str],
        exclude_topics: set[str] | None = None,
    ) -> Question | None:
        """Tenta a combinação pedida pelo seletor; se esgotada, sobe dificuldade
        no mesmo tópico e depois tenta outros tópicos antes de desistir."""
        bank = self._domain.question_bank
        blocked_topics = exclude_topics or set()

        for d in self._difficulty_fallback_order(difficulty):
            try:
                return bank.next_question(topic, d, exclude_ids=exclude_ids)
            except ValueError:
                continue

        for other_topic in bank.topics():
            if other_topic == topic or other_topic in blocked_topics:
                continue
            for d in range(1, _MAX_DIFFICULTY + 1):
                try:
                    return bank.next_question(other_topic, d, exclude_ids=exclude_ids)
                except ValueError:
                    continue

        return None

    def start(self, topic: str, difficulty: int = 1) -> InterviewState:
        question = self._domain.question_bank.next_question(topic, difficulty)
        return InterviewState(topic=topic, difficulty=difficulty, current_question=question)

    async def submit_answer(self, state: InterviewState, answer: str) -> InterviewState:
        evaluation = await self._evaluator.evaluate(
            topic=state.topic,
            question=state.current_question.prompt,
            answer=answer,
        )
        state.history.append((state.current_question, evaluation))

        if len(state.history) >= _MAX_QUESTIONS:
            print("Atingiu o número máximo de perguntas. Encerrando a entrevista.")
            state.finished = True
            return state

        try:
            decision = self._selector.decide(state, evaluation)
        except ValueError:
            state.finished = True
            return state

        visited = self._visited_topics(state)
        exclude_topics = visited - {decision.next_topic}

        question = self._resolve_next_question(
            decision.next_topic,
            decision.next_difficulty,
            self._used_question_ids(state),
            exclude_topics=exclude_topics,
        )
        if question is None:
            print("Não foi possível encontrar uma próxima pergunta. Encerrando a entrevista.")
            state.finished = True
            return state

        state.current_question = question
        state.topic = question.topic
        state.difficulty = question.difficulty
        return state

    async def get_report(self, state: InterviewState) -> CandidateReport:
        """Gera (ou reaproveita) o relatório final."""
        if not state.finished:
            raise InterviewNotFinishedError(
                "Não é possível gerar relatório: a entrevista ainda está em andamento."
            )
        if state.report is None:
            state.report = await self.reporting_agent.generate_report(state)
        return state.report
