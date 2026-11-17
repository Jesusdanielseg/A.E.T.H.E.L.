import logging
import time
from collections.abc import Sequence

from src.core.llm import RespuestaLLM
from src.llm.base import BaseLLMProvider, ProviderError

logger = logging.getLogger(__name__)


class LLMRouter(BaseLLMProvider):
    """Intenta proveedores en orden y devuelve el primer resultado válido."""

    def __init__(self, providers: Sequence[BaseLLMProvider]) -> None:
        self.providers = tuple(providers)
        if not self.providers:
            raise ValueError("El router necesita al menos un proveedor.")
        self.last_provider = ""
        self.last_latency_ms = 0.0

    def generate_response(self, prompt: str, context: str | None = None):
        last_error: ProviderError | None = None
        for provider in self.providers:
            started = time.perf_counter()
            try:
                response = provider.generate_response(prompt, context)
            except ProviderError as exc:
                last_error = exc
                latency_ms = (time.perf_counter() - started) * 1000
                logger.warning(
                    "Proveedor %s no disponible en %.1f ms; probando el siguiente",
                    provider.__class__.__name__,
                    latency_ms,
                )
            else:
                self.last_provider = response.provider
                self.last_latency_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "Proveedor LLM seleccionado: %s (%s) en %.1f ms",
                    response.provider,
                    response.model,
                    self.last_latency_ms,
                )
                return response
        raise ProviderError(
            "Todos los proveedores de modelos fallaron."
        ) from last_error

    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        return super().generar_respuesta(mensaje)
