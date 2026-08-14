from app.core.domain.interfaces import Question


class StaticAsyncMessagingQuestionBank:
    """Banco de perguntas estático, cobrindo SQS/SNS/Lambda."""

    def __init__(self) -> None:
        self._questions = [
            Question(
                id="sqs-01",
                topic="dead_letter_queue",
                difficulty=1,
                prompt="O que é uma Dead Letter Queue e quando ela deveria ser usada?",
            ),
            # ... demais perguntas (15-20 no total, cobrindo os subtópicos)
        ]

    def next_question(self, topic: str, difficulty: int) -> Question:
        candidates = [
            q for q in self._questions
            if q.topic == topic and q.difficulty == difficulty
        ]
        if not candidates:
            raise ValueError(f"Nenhuma pergunta encontrada para topic={topic}, difficulty={difficulty}")
        return candidates[0]

    def topics(self) -> list[str]:
        return sorted({q.topic for q in self._questions})