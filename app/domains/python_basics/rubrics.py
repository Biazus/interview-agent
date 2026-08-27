from pathlib import Path

from app.core.domain.static_providers import StaticRubricProvider

_DATA_PATH = Path(__file__).parent / "data" / "rubrics.yaml"


class StaticPythonBasicsRubricProvider(StaticRubricProvider):
    """Provider de rubricas estático para fundamentos de Python."""

    def __init__(self, data_path: Path = _DATA_PATH) -> None:
        super().__init__(data_path)
