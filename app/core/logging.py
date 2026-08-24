import logging
from typing import Any
from uuid import UUID

_RESERVED_LOG_RECORD_KEYS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None, None).__dict__
) | frozenset({"message", "asctime"})


class ExtraFieldsFormatter(logging.Formatter):
    """Appends user-defined ``extra`` fields to the log line."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        suffix = _format_extra_suffix(record)
        if not suffix:
            return base
        return f"{base} {suffix}"


def _format_extra_suffix(record: logging.LogRecord) -> str:
    parts: list[str] = []
    for key in sorted(record.__dict__):
        if key in _RESERVED_LOG_RECORD_KEYS:
            continue
        value = record.__dict__[key]
        if value is None:
            continue
        parts.append(f"{key}={_format_extra_value(value)}")
    return " ".join(parts)


def _format_extra_value(value: Any) -> str:
    if isinstance(value, str) and (" " in value or "=" in value):
        return repr(value)
    return str(value)


def configure_logging(level: str = "INFO") -> None:
    formatter = ExtraFieldsFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(
        level=level.upper(),
        handlers=[handler],
        force=True,
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


def llm_extra(
    tokens_used: int | None,
    provider: str,
    model: str,
    **fields: Any,
) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "tokens_used": tokens_used,
        "provider": provider,
        "model": model,
    }
    extra.update(fields)
    return extra
