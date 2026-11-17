import io
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from src.core import logger


@pytest.fixture
def isolated_root_logger():
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    for handler in original_handlers:
        root_logger.removeHandler(handler)
    try:
        yield root_logger
    finally:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)


def test_secret_filter_masks_configured_and_provider_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(logger.config, "AI_API_KEY", "my-private-key")
    record = logging.LogRecord(
        "test",
        logging.ERROR,
        __file__,
        1,
        "keys=%s %s %s %s",
        (
            "my-private-key",
            "sk-openai_key-123",
            "AIzaGemini_key-456",
            "AQ.secret_header-789",
        ),
        None,
    )

    assert logger.SecretMaskingFilter().filter(record)
    assert record.getMessage() == "keys=*** *** *** ***"
    assert record.args == ()


def test_secret_filter_masks_exception_traceback_and_stack_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(logger.config, "AI_API_KEY", "private-key")

    try:
        raise RuntimeError("failed with private-key and sk-secret-123")
    except RuntimeError as error:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            __file__,
            1,
            "operation failed",
            (),
            (type(error), error, error.__traceback__),
            sinfo="stack contains AIzaSecret-123",
        )
        record.stack_info = "stack contains AIzaSecret-123"

    assert logger.SecretMaskingFilter().filter(record)
    formatted = logging.Formatter().format(record)
    assert "private-key" not in formatted
    assert "sk-secret-123" not in formatted
    assert "AIzaSecret-123" not in formatted
    assert formatted.count("***") >= 3


def test_request_id_rejects_log_injection_and_masks_secret_values() -> None:
    with pytest.raises(ValueError, match="request ID"):
        logger.establecer_request_id("request\nforged")

    logger.establecer_request_id("sk-private-123")
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    logger.RequestIdFilter().filter(record)

    assert record.__dict__["request_id"] == "***"


def test_request_id_context_restores_previous_value() -> None:
    previous = logger.establecer_request_id("outer-request")

    with logger.contexto_request_id("inner-request") as active:
        assert active == "inner-request"
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "", (), None)
        logger.RequestIdFilter().filter(record)
        assert record.__dict__["request_id"] == "inner-request"

    restored = logging.LogRecord("test", logging.INFO, __file__, 1, "", (), None)
    logger.RequestIdFilter().filter(restored)
    assert restored.__dict__["request_id"] == previous


def test_configure_logging_sets_request_id_masks_secrets_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_root_logger: logging.Logger,
) -> None:
    project_dir = tmp_path / "project"
    fake_module = project_dir / "src" / "core" / "logger.py"
    monkeypatch.setattr(logger, "__file__", str(fake_module))
    monkeypatch.setattr(logger.config, "AI_API_KEY", "private-config-key")
    monkeypatch.setattr(logger.config, "ENVIRONMENT", "development")
    logger.establecer_request_id("request-42")

    logger.configurar_logging()
    logger.configurar_logging()

    handlers = [
        handler
        for handler in isolated_root_logger.handlers
        if getattr(handler, logger._HANDLER_MARKER, False)
    ]
    assert len(handlers) == 2
    assert isolated_root_logger.level == logging.DEBUG

    console_handler = next(
        handler
        for handler in handlers
        if isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
    )
    file_handler = next(
        handler for handler in handlers if isinstance(handler, RotatingFileHandler)
    )
    assert file_handler.maxBytes == 5 * 1024 * 1024
    assert file_handler.backupCount == 3
    assert file_handler.encoding == "utf-8"
    assert file_handler.baseFilename == str(project_dir / "logs" / "aethel.log")

    output = io.StringIO()
    console_handler.setStream(output)
    isolated_root_logger.info(
        "secret values: %s %s %s",
        "private-config-key",
        "sk-openai-123",
        "AIzaGemini-456",
    )

    console_output = output.getvalue()
    file_output = (project_dir / "logs" / "aethel.log").read_text(encoding="utf-8")
    for log_output in (console_output, file_output):
        assert "[request-42]" in log_output
        assert "secret values: *** *** ***" in log_output
        assert "private-config-key" not in log_output
        assert "sk-openai-123" not in log_output
        assert "AIzaGemini-456" not in log_output
