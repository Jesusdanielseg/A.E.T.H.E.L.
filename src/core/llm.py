import logging
import math
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from src.core.exceptions import RecoverableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RespuestaLLM:
    """Respuesta del modelo junto con sus métricas de consumo."""

    contenido: str
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    coste_usd: float

    def __post_init__(self) -> None:
        """Rechaza métricas imposibles antes de registrarlas."""
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
    """Contrato que debe cumplir cualquier proveedor de modelos."""

    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        """Envía un mensaje al modelo y devuelve una respuesta estructurada."""
        ...


class GestorPresupuesto:
    """Acumula consumo de modelos y bloquea peticiones fuera del presupuesto."""

    def __init__(self, limite_usd: float) -> None:
        if not math.isfinite(limite_usd) or limite_usd < 0:
            raise ValueError("El límite debe ser un número finito no negativo.")
        self.limite_usd = limite_usd
        self.gasto_acumulado: float = 0.0
        self.tokens_totales: int = 0
        self._lock = Lock()

    def verificar_disponibilidad(self) -> None:
        """Comprueba que todavía quede presupuesto para una petición."""
        with self._lock:
            self._verificar_disponibilidad_sin_bloqueo()

    def registrar_uso(self, respuesta: RespuestaLLM) -> None:
        """Acumula tokens y coste, y registra las métricas de la petición."""
        tokens_solicitud = respuesta.tokens_entrada + respuesta.tokens_salida
        with self._lock:
            self.gasto_acumulado += respuesta.coste_usd
            self.tokens_totales += tokens_solicitud
            gasto_acumulado = self.gasto_acumulado
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
        """Comprueba el límite mientras el lock ya está adquirido."""
        if self.gasto_acumulado >= self.limite_usd:
            raise RecoverableError(
                "Presupuesto agotado "
                f"(${self.gasto_acumulado:.4f} / ${self.limite_usd:.4f} USD)."
            )
