import logging
from typing import Any
from uuid import UUID


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def error_type(exc: BaseException | None) -> str:
    if exc is None:
        return "Unknown"
    return type(exc).__name__


def interview_extra(
    interview_id: UUID,
    candidate_id: UUID,
    **fields: Any,
) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "interview_id": str(interview_id),
        "candidate_id": str(candidate_id),
    }
    extra.update(fields)
    return extra
