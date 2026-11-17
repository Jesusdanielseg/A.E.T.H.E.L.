import logging
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.core.config import config

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")
_HANDLER_MARKER = "_aethel_logging_handler"
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_-]+)"
)


def _validar_request_id(request_id: str | None) -> str:
    nuevo_id = uuid.uuid4().hex[:8] if request_id is None else request_id
    if not _REQUEST_ID_PATTERN.fullmatch(nuevo_id):
        raise ValueError(
            "El request ID debe tener entre 1 y 128 caracteres "
            "alfanuméricos o contener '.', '_', ':' o '-'."
        )
    return nuevo_id


def _ocultar_secretos(texto: str) -> str:
    if config.AI_API_KEY:
        texto = texto.replace(config.AI_API_KEY, "***")
    return _SECRET_PATTERN.sub("***", texto)


def establecer_request_id(request_id: str | None = None) -> str:
    """Asigna un ID a la petición actual o genera uno corto."""
    nuevo_id = _validar_request_id(request_id)
    _request_id_ctx.set(nuevo_id)
    return nuevo_id


@contextmanager
def contexto_request_id(request_id: str | None = None) -> Iterator[str]:
    """Establece temporalmente el ID y restaura el contexto anterior al salir."""
    nuevo_id = _validar_request_id(request_id)
    token = _request_id_ctx.set(nuevo_id)
    try:
        yield nuevo_id
    finally:
        _request_id_ctx.reset(token)


class RequestIdFilter(logging.Filter):
    """Inyecta el identificador de la petición activa en cada registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _ocultar_secretos(_request_id_ctx.get())
        return True


class SecretMaskingFilter(logging.Filter):
    """Censura claves de API en el mensaje renderizado del registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        mensaje = record.getMessage()
        record.msg = _ocultar_secretos(mensaje)
        record.args = ()
        if record.exc_info:
            formatter = logging.Formatter()
            exception_text = formatter.formatException(record.exc_info)
            record.exc_text = _ocultar_secretos(exception_text)
        elif record.exc_text:
            record.exc_text = _ocultar_secretos(record.exc_text)
        if record.stack_info:
            record.stack_info = _ocultar_secretos(record.stack_info)
        return True


def configurar_logging() -> None:
    """Configura logging en consola y archivo rotativo."""
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s: %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_dir / "aethel.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handlers: tuple[logging.Handler, ...] = (
        logging.StreamHandler(),
        file_handler,
    )

    for handler in handlers:
        handler.setFormatter(formato)
        handler.addFilter(RequestIdFilter())
        handler.addFilter(SecretMaskingFilter())

    root_logger = logging.getLogger()
    try:
        for existing_handler in root_logger.handlers[:]:
            if getattr(existing_handler, _HANDLER_MARKER, False):
                root_logger.removeHandler(existing_handler)
                existing_handler.close()

        root_logger.setLevel(logging.DEBUG if config.is_development else logging.INFO)
        for handler in handlers:
            setattr(handler, _HANDLER_MARKER, True)
            root_logger.addHandler(handler)
    except BaseException:
        for handler in handlers:
            handler.close()
        raise
