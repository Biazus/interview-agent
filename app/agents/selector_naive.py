from app.core.domain.interfaces import (
    Evaluation,
    InterviewState,
    SelectorDecision,
)
from app.core.domain.registry import DomainModule

_SAME_LEVEL_STREAK = 2


class NaiveSelector:
    """Troca de tópico quando o tópico atual esgota as perguntas disponíveis,
    ou quando o candidato emite N respostas seguidas do mesmo nível no
    tópico atual. Calibra dificuldade de forma simplista dentro do tópico."""

    def __init__(self, domain: DomainModule) -> None:
        self._domain = domain

    def decide(self, state: InterviewState, evaluation: Evaluation) -> SelectorDecision:
        next_difficulty = self._next_difficulty(state.difficulty, evaluation.level)

        if self._should_switch_topic(state):
            next_topic = self._pick_next_topic(state.topic)
            return SelectorDecision(next_topic=next_topic, next_difficulty=1)

        return SelectorDecision(next_topic=state.topic, next_difficulty=next_difficulty)

    def _next_difficulty(self, current: int, level: str) -> int:
        if level == "strong":
            return min(current + 1, 5)
        if level == "weak":
            return max(current - 1, 1)
        return current

    def _should_switch_topic(self, state: InterviewState) -> bool:
        same_topic = [(q, e) for q, e in state.history if q.topic == state.topic]
        if len(same_topic) < _SAME_LEVEL_STREAK:
            return False
        last_levels = [e.level for _, e in same_topic[-_SAME_LEVEL_STREAK:]]
        return len(set(last_levels)) == 1  # todas iguais entre si

    def _pick_next_topic(self, current_topic: str) -> str:
        topics = self._domain.question_bank.topics()
        remaining = [t for t in topics if t != current_topic]
        if not remaining:
            raise ValueError("Nenhum outro tópico disponível.")
        return remaining[0]  # estratégia ingênua: primeiro disponível
