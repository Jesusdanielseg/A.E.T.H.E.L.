import logging
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from src.core.config import config
from src.core.exceptions import CriticalError

logger = logging.getLogger(__name__)
HealthStatus = Literal["healthy", "degraded", "unhealthy"]


@dataclass(frozen=True)
class HealthReport:
    """Resultado estructurado de una comprobación de salud del sistema."""

    estado: HealthStatus
    componentes: Mapping[str, bool]
    detalles: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "componentes", MappingProxyType(dict(self.componentes))
        )
        object.__setattr__(self, "detalles", MappingProxyType(dict(self.detalles)))


def _es_escribible(directorio: Path) -> bool:
    """Asegura que el directorio exista y tenga permisos de escritura."""
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        if not os.access(directorio, os.W_OK):
            return False
        with tempfile.NamedTemporaryFile(
            prefix=".aethel-health-", dir=directorio, delete=True
        ):
            return True
    except OSError:
        return False


def _tiene_espacio_disco(directorio: Path, minimo_mb: int = 100) -> bool:
    """Verifica que haya al menos `minimo_mb` libres en la partición."""
    if minimo_mb < 0:
        raise ValueError("minimo_mb no puede ser negativo")
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        _, _, libre = shutil.disk_usage(directorio)
        return libre >= minimo_mb * 1024 * 1024
    except OSError:
        return False


def verificar_salud(strict: bool = False) -> HealthReport:
    """Comprueba almacenamiento, logs y disponibilidad de la clave de IA."""
    directorio_db = Path(config.DB_PATH).parent
    directorio_logs = Path(__file__).resolve().parents[2] / "logs"
    almacenamiento_escribible = _es_escribible(directorio_db)
    almacenamiento_con_espacio = _tiene_espacio_disco(directorio_db)
    logs_escribible = _es_escribible(directorio_logs)
    cloud_provider_configured = "gemini" in config.LLM_PROVIDER_ORDER
    api_key_disponible = (
        bool(config.AI_API_KEY.strip()) if cloud_provider_configured else True
    )

    componentes = {
        "almacenamiento": (almacenamiento_escribible and almacenamiento_con_espacio),
        "logs": logs_escribible,
        "api_key": api_key_disponible,
    }
    detalles = {
        "almacenamiento": (
            "OK"
            if componentes["almacenamiento"]
            else (
                "Directorio de base de datos no escribible"
                if not almacenamiento_escribible
                else "Espacio libre insuficiente o no disponible"
            )
        ),
        "logs": "OK" if logs_escribible else "Directorio de logs no escribible",
        "api_key": ("OK" if api_key_disponible else "AI_API_KEY no está configurada"),
    }

    estado: HealthStatus
    if not componentes["almacenamiento"] or not componentes["logs"]:
        estado = "unhealthy"
    elif not componentes["api_key"]:
        estado = "degraded"
    else:
        estado = "healthy"

    if estado == "healthy":
        logger.info("Comprobación de salud: %s (%s)", estado, detalles)
    elif estado == "degraded":
        logger.warning("Comprobación de salud: %s (%s)", estado, detalles)
    else:
        logger.error("Comprobación de salud: %s (%s)", estado, detalles)
        if strict:
            raise CriticalError("Fallo crítico en comprobación de salud", str(detalles))

    return HealthReport(
        estado=estado,
        componentes=componentes,
        detalles=detalles,
    )
