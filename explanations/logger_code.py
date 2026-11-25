"""Copia didáctica de src/core/logger.py; no es el módulo importado.

Estado 04.5: el patrón _SECRET_PATTERN de esta copia no incluye el prefijo
AQ. que sí redacta el código actual. Ver
explanations/14-auditoria-explanations-04-5.md.
"""

import logging
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.core.config import config

# ContextVar separa el ID entre contextos async/hilos, a diferencia de una global.
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")

# Marca los handlers que creó este módulo para poder reemplazarlos al reconfigurar.
_HANDLER_MARKER = "_aethel_logging_handler"

# La primera regex limita formato y tamaño; la segunda encuentra claves conocidas.
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_SECRET_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]+)")


def _validar_request_id(request_id: str | None) -> str:
    """Valida un ID proporcionado o genera uno breve si no se pasó ninguno."""
    nuevo_id = uuid.uuid4().hex[:8] if request_id is None else request_id
    if not _REQUEST_ID_PATTERN.fullmatch(nuevo_id):
        # Rechazar saltos de línea evita falsificar entradas en el log.
        raise ValueError(
            "El request ID debe tener entre 1 y 128 caracteres "
            "alfanuméricos o contener '.', '_', ':' o '-'."
        )
    return nuevo_id


def _ocultar_secretos(texto: str) -> str:
    """Redacta la clave configurada y formatos externos reconocidos."""
    if config.AI_API_KEY:
        texto = texto.replace(config.AI_API_KEY, "***")
    return _SECRET_PATTERN.sub("***", texto)


def establecer_request_id(request_id: str | None = None) -> str:
    """Fija el ID en el contexto actual hasta que se reemplace."""
    nuevo_id = _validar_request_id(request_id)
    _request_id_ctx.set(nuevo_id)
    return nuevo_id


@contextmanager
def contexto_request_id(request_id: str | None = None) -> Iterator[str]:
    """Fija temporalmente un ID y siempre restaura el valor previo al salir."""
    nuevo_id = _validar_request_id(request_id)
    token = _request_id_ctx.set(nuevo_id)
    try:
        yield nuevo_id
    finally:
        # El token permite restaurar el contexto aunque el bloque lance excepción.
        _request_id_ctx.reset(token)


class RequestIdFilter(logging.Filter):
    """Agrega el ID del contexto al record que consumen los formatters."""

    def filter(self, record: logging.LogRecord) -> bool:
        # El ID también se censura por si coincide con un patrón de secreto.
        record.request_id = _ocultar_secretos(_request_id_ctx.get())
        return True


class SecretMaskingFilter(logging.Filter):
    """Censura secretos en mensajes, tracebacks y stack traces."""

    def filter(self, record: logging.LogRecord) -> bool:
        # getMessage aplica los %s y argumentos antes de censurar el texto final.
        mensaje = record.getMessage()
        record.msg = _ocultar_secretos(mensaje)
        record.args = ()

        if record.exc_info:
            # Se genera texto desde la excepción y se censura antes de formatear.
            formatter = logging.Formatter()
            exception_text = formatter.formatException(record.exc_info)
            record.exc_text = _ocultar_secretos(exception_text)
        elif record.exc_text:
            # Puede venir precalculado por un handler o filtro anterior.
            record.exc_text = _ocultar_secretos(record.exc_text)

        if record.stack_info:
            record.stack_info = _ocultar_secretos(record.stack_info)
        return True


def configurar_logging() -> None:
    """Instala salida a consola y archivo rotativo en el logger raíz."""
    # parents[2] apunta a la raíz del proyecto desde src/core/logger.py.
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s: %(message)s"
    )

    # El archivo tiene límite de 5 MiB y guarda tres archivos antiguos.
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

    # Filtros en cada handler: cubren tanto consola como archivo.
    for handler in handlers:
        handler.setFormatter(formato)
        handler.addFilter(RequestIdFilter())
        handler.addFilter(SecretMaskingFilter())

    root_logger = logging.getLogger()
    try:
        # Quitamos únicamente handlers nuestros; no borramos config de terceros.
        for existing_handler in root_logger.handlers[:]:
            if getattr(existing_handler, _HANDLER_MARKER, False):
                root_logger.removeHandler(existing_handler)
                existing_handler.close()

        # En producción INFO evita el volumen de DEBUG.
        root_logger.setLevel(logging.DEBUG if config.is_development else logging.INFO)
        for handler in handlers:
            setattr(handler, _HANDLER_MARKER, True)
            root_logger.addHandler(handler)
    except BaseException:
        # Si la instalación falla, cerramos los handlers recién abiertos.
        for handler in handlers:
            handler.close()
        raise
