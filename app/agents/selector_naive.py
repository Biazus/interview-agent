from app.core.domain.interfaces import (
    Evaluation,
    InterviewState,
    SelectorDecision,
)
from app.core.domain.registry import DomainModule

_LOW_BAND_MAX = 30
_MID_BAND_MAX = 69
_HIGH_BAND_MIN = 70
_SAME_BAND_STREAK = 2


def _score_band(score: int) -> str:
    if score <= _LOW_BAND_MAX:
        return "low"
    if score <= _MID_BAND_MAX:
        return "mid"
    return "high"


class NaiveSelector:
    """Troca de tópico quando o tópico atual esgota as perguntas disponíveis,
    ou quando o candidato emite N respostas seguidas na mesma faixa de nota no
    tópico atual. Calibra dificuldade de forma simplista dentro do tópico."""

    def __init__(self, domain: DomainModule) -> None:
        self._domain = domain

    def decide(self, state: InterviewState, evaluation: Evaluation) -> SelectorDecision:
        next_difficulty = self._next_difficulty(state.difficulty, evaluation.score)

        if self._should_switch_topic(state):
            next_topic = self._pick_next_topic(state)
            return SelectorDecision(next_topic=next_topic, next_difficulty=1)

        return SelectorDecision(next_topic=state.topic, next_difficulty=next_difficulty)

    def _next_difficulty(self, current: int, score: int) -> int:
        if score <= _LOW_BAND_MAX:
            return max(current - 1, 1)
        if score >= _HIGH_BAND_MIN:
            return min(current + 1, 5)
        return current

    def _should_switch_topic(self, state: InterviewState) -> bool:
        same_topic = [(q, e) for q, e in state.history if q.topic == state.topic]
        if len(same_topic) < _SAME_BAND_STREAK:
            return False
        last_bands = [_score_band(e.score) for _, e in same_topic[-_SAME_BAND_STREAK:]]
        return len(set(last_bands)) == 1

    def _pick_next_topic(self, state: InterviewState) -> str:
        visited = {q.topic for q, _ in state.history}
        remaining = [t for t in self._domain.question_bank.topics() if t not in visited]
        if not remaining:
            raise ValueError("Nenhum outro tópico disponível.")
        return remaining[0]  # estratégia ingênua: primeiro disponível
