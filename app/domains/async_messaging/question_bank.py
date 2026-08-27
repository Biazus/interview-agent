from pathlib import Path

from app.core.domain.static_providers import StaticQuestionBank

_DATA_PATH = Path(__file__).parent / "data" / "questions.yaml"


class StaticAsyncMessagingQuestionBank(StaticQuestionBank):
    """Banco de perguntas estático, cobrindo SQS/SNS/Lambda."""

    def __init__(self, data_path: Path = _DATA_PATH) -> None:
        super().__init__(data_path)
