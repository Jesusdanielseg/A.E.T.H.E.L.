import re

_SECRET_PATTERNS = (
    (re.compile(r"\b(?:sk|AIza)[A-Za-z0-9_-]+"), "[CREDENCIAL_OCULTA]"),
    (re.compile(r"\bAQ\.[A-Za-z0-9_-]+"), "[CREDENCIAL_OCULTA]"),
    (
        re.compile(
            r"(?i)\b(?:password|passwd|contraseña|token|api[_ -]?key)"
            r"\s*[:=]\s*\S+"
        ),
        "[DATO_SENSIBLE_OCULTO]",
    ),
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_HOME_PATH_PATTERN = re.compile(r"(?<!\w)/home/[^/\s]+(?:/[^\s]*)?")


def sanitize_text(text: str) -> str:
    """Redacta secretos, correos y rutas personales antes de persistir/enviar."""
    sanitized = text
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    sanitized = _EMAIL_PATTERN.sub("[CORREO_OCULTO]", sanitized)
    return _HOME_PATH_PATTERN.sub("~/proyecto/[RUTA_OCULTA]", sanitized)
