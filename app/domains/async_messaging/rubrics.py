from app.core.domain.interfaces import Rubric, RubricCriterion


class FakeAsyncMessagingRubricProvider:
    """Implementação provisória do RubricProvider, com uma rubrica de exemplo."""

    def get_rubric(self, topic: str) -> Rubric:
        return Rubric(
            topic=topic,
            criteria=[
                RubricCriterion(
                    description="Explica o propósito de uma DLQ",
                    weak_example="Não sei, acho que guarda mensagens.",
                    medium_example="Guarda mensagens que deram erro.",
                    strong_example="Captura mensagens que excederam o número "
                    "máximo de tentativas (maxReceiveCount), "
                    "permitindo análise sem bloquear a fila principal.",
                )
            ],
        )
