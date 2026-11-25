"""Copia didáctica de src/core/llm.py; no es el módulo ejecutado."""

import logging
import math
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from src.core.exceptions import RecoverableError

# El logger permite observar consumo sin imprimir directamente en consola.
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RespuestaLLM:
    """DTO inmutable con texto y métricas de una respuesta del modelo."""

    contenido: str
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    coste_usd: float

    def __post_init__(self) -> None:
        """Impide registrar respuestas con métricas imposibles."""
        if not self.contenido.strip():
            raise ValueError("La respuesta del LLM no puede estar vacía.")
        if not self.modelo.strip():
            raise ValueError("El modelo del LLM no puede estar vacío.")
        if not isinstance(self.tokens_entrada, int) or not isinstance(
            self.tokens_salida, int
        ):
            raise TypeError("Los tokens deben ser enteros.")
        if self.tokens_entrada < 0 or self.tokens_salida < 0:
            raise ValueError("Los tokens no pueden ser negativos.")
        if not math.isfinite(self.coste_usd) or self.coste_usd < 0:
            raise ValueError("El coste debe ser un número finito no negativo.")


class ProveedorLLM(Protocol):
    """Contrato estructural independiente del SDK del proveedor."""

    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        """Envía un mensaje y devuelve texto junto con métricas."""
        ...


class GestorPresupuesto:
    """Acumula consumo y bloquea peticiones cuando se agota el límite."""

    def __init__(self, limite_usd: float) -> None:
        # NaN e infinito romperían cualquier comparación fiable del presupuesto.
        if not math.isfinite(limite_usd) or limite_usd < 0:
            raise ValueError("El límite debe ser un número finito no negativo.")
        self.limite_usd = limite_usd
        self.gasto_acumulado: float = 0.0
        self.tokens_totales: int = 0
        # El estado puede ser consultado por más de un flujo del proceso.
        self._lock = Lock()

    def verificar_disponibilidad(self) -> None:
        """Lanza un error recuperable si no queda presupuesto."""
        with self._lock:
            self._verificar_disponibilidad_sin_bloqueo()

    def registrar_uso(self, respuesta: RespuestaLLM) -> None:
        """Suma métricas de uso y deja una traza operativa."""
        tokens_solicitud = respuesta.tokens_entrada + respuesta.tokens_salida
        with self._lock:
            self.gasto_acumulado += respuesta.coste_usd
            self.tokens_totales += tokens_solicitud
            gasto_acumulado = self.gasto_acumulado

        # El logging ocurre fuera del lock para no retenerlo durante handlers.
        logger.info(
            "Uso LLM registrado: modelo=%s, tokens=%d, coste=$%.4f, "
            "acumulado=$%.4f / $%.4f USD",
            respuesta.modelo,
            tokens_solicitud,
            respuesta.coste_usd,
            gasto_acumulado,
            self.limite_usd,
        )
        if gasto_acumulado > self.limite_usd:
            logger.warning(
                "El uso registrado supera el presupuesto: $%.4f / $%.4f USD",
                gasto_acumulado,
                self.limite_usd,
            )

    def _verificar_disponibilidad_sin_bloqueo(self) -> None:
        """Comprueba el estado suponiendo que el lock ya está adquirido."""
        if self.gasto_acumulado >= self.limite_usd:
            raise RecoverableError(
                "Presupuesto agotado "
                f"(${self.gasto_acumulado:.4f} / ${self.limite_usd:.4f} USD)."
            )
