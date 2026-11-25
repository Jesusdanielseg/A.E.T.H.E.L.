"""Copia didáctica de src/core/health.py; no es el módulo importado.

Estado 04.5: verificar_salud() está desactualizado; el código actual solo
exige AI_API_KEY cuando Gemini está en LLM_PROVIDER_ORDER. Ver
explanations/14-auditoria-explanations-04-5.md.
"""

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

# El logger por módulo permite filtrar o identificar el origen de cada mensaje.
logger = logging.getLogger(__name__)

# Literal limita el estado a estos tres valores conocidos por el programa.
HealthStatus = Literal["healthy", "degraded", "unhealthy"]


@dataclass(frozen=True)
class HealthReport:
    """Reporte inmutable con resultado, componentes y diagnóstico legible."""

    estado: HealthStatus
    componentes: Mapping[str, bool]
    detalles: Mapping[str, str]

    def __post_init__(self) -> None:
        # frozen=True bloquea reasignar atributos, pero no congela los dict
        # recibidos. Copiamos y envolvemos cada mapping para hacerlo de solo lectura.
        object.__setattr__(
            self, "componentes", MappingProxyType(dict(self.componentes))
        )
        object.__setattr__(self, "detalles", MappingProxyType(dict(self.detalles)))


def _es_escribible(directorio: Path) -> bool:
    """Crea el directorio si falta y prueba escritura con un archivo temporal."""
    try:
        directorio.mkdir(parents=True, exist_ok=True)

        # os.access es una primera señal, pero no garantiza una escritura real.
        if not os.access(directorio, os.W_OK):
            return False

        # Crear el archivo comprueba escritura efectiva; with lo cierra y elimina.
        with tempfile.NamedTemporaryFile(
            prefix=".aethel-health-", dir=directorio, delete=True
        ):
            return True
    except OSError:
        # Errores de filesystem se convierten en el resultado "no saludable".
        return False


def _tiene_espacio_disco(directorio: Path, minimo_mb: int = 100) -> bool:
    """Comprueba que el volumen tenga al menos el mínimo de MiB libres."""
    if minimo_mb < 0:
        # Un umbral negativo es un error de programación, no un fallo del disco.
        raise ValueError("minimo_mb no puede ser negativo")

    try:
        directorio.mkdir(parents=True, exist_ok=True)
        _, _, libre = shutil.disk_usage(directorio)
        return libre >= minimo_mb * 1024 * 1024
    except OSError:
        return False


def verificar_salud(strict: bool = False) -> HealthReport:
    """Evalúa almacenamiento, logs y presencia de la clave de IA."""
    directorio_db = Path(config.DB_PATH).parent
    directorio_logs = Path(__file__).resolve().parents[2] / "logs"

    # Cada comprobación se calcula una sola vez y luego se construye el reporte.
    almacenamiento_escribible = _es_escribible(directorio_db)
    almacenamiento_con_espacio = _tiene_espacio_disco(directorio_db)
    logs_escribible = _es_escribible(directorio_logs)
    api_key_disponible = bool(config.AI_API_KEY.strip())

    componentes = {
        "almacenamiento": (
            almacenamiento_escribible and almacenamiento_con_espacio
        ),
        "logs": logs_escribible,
        "api_key": api_key_disponible,
    }

    # Los detalles explican por qué un componente no pasó la comprobación.
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
        "api_key": "OK" if api_key_disponible else "AI_API_KEY no está configurada",
    }

    # Disco o logs fallidos son críticos; sin API key el estado es degradado.
    estado: HealthStatus
    if not componentes["almacenamiento"] or not componentes["logs"]:
        estado = "unhealthy"
    elif not componentes["api_key"]:
        estado = "degraded"
    else:
        estado = "healthy"

    # El nivel de log refleja la severidad; no se registra el valor de la clave.
    if estado == "healthy":
        logger.info("Comprobación de salud: %s (%s)", estado, detalles)
    elif estado == "degraded":
        logger.warning("Comprobación de salud: %s (%s)", estado, detalles)
    else:
        logger.error("Comprobación de salud: %s (%s)", estado, detalles)
        if strict:
            # El llamador, por ejemplo main(), puede decidir no continuar.
            raise CriticalError(
                "Fallo crítico en comprobación de salud", str(detalles)
            )

    # El reporte copia los diccionarios y los hace inmutables en __post_init__.
    return HealthReport(
        estado=estado,
        componentes=componentes,
        detalles=detalles,
    )
