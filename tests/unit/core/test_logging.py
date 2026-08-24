import logging

from app.core.logging import ExtraFieldsFormatter, configure_logging


def test_extra_fields_formatter_appends_custom_fields():
    formatter = ExtraFieldsFormatter(
        fmt="%(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.tokens_used = 42
    record.provider = "groq"

    assert formatter.format(record) == "INFO hello provider=groq tokens_used=42"


def test_extra_fields_formatter_omits_none_values():
    formatter = ExtraFieldsFormatter(fmt="%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.tokens_used = None
    record.provider = "groq"

    assert formatter.format(record) == "hello provider=groq"


def test_extra_fields_formatter_quotes_strings_with_spaces():
    formatter = ExtraFieldsFormatter(fmt="%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.reason = "max questions reached"

    assert formatter.format(record) == "hello reason='max questions reached'"


def test_configure_logging_uses_extra_fields_formatter():
    configure_logging("INFO")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, ExtraFieldsFormatter)


def test_configure_logging_force_replaces_existing_handlers():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    try:
        stale_handler = logging.StreamHandler()
        stale_handler.setFormatter(logging.Formatter("STALE %(message)s"))
        root.handlers.clear()
        root.addHandler(stale_handler)
        root.setLevel(logging.WARNING)

        configure_logging("INFO")

        assert len(root.handlers) == 1
        assert root.handlers[0] is not stale_handler
        assert isinstance(root.handlers[0].formatter, ExtraFieldsFormatter)
        assert root.level == logging.INFO
    finally:
        root.handlers.clear()
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)
