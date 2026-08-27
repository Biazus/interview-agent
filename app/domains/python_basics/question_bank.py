from pathlib import Path

from app.core.domain.static_providers import StaticQuestionBank

_DATA_PATH = Path(__file__).parent / "data" / "questions.yaml"


class StaticPythonBasicsQuestionBank(StaticQuestionBank):
    """Banco de perguntas estático para fundamentos de Python."""

    def __init__(self, data_path: Path = _DATA_PATH) -> None:
        super().__init__(data_path)
