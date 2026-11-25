from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.exceptions import ExternalServiceError
from src.core.llm import RespuestaLLM


class ProviderError(ExternalServiceError):
    """Error normalizado producido por cualquier proveedor de modelos."""


@dataclass(frozen=True)
class ModelResponse:
    """Respuesta pública normalizada de la capa de abstracción."""

    text: str
    provider: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0

    def to_core_response(self) -> RespuestaLLM:
        return RespuestaLLM(
            contenido=self.text,
            modelo=self.model,
            tokens_entrada=self.tokens_input,
            tokens_salida=self.tokens_output,
            coste_usd=self.cost_usd,
        )


class BaseLLMProvider(ABC):
    """Contrato común para adaptadores cloud, locales y offline."""

    @abstractmethod
    def generate_response(
        self, prompt: str, context: str | None = None
    ) -> ModelResponse:
        """Genera una respuesta normalizada."""
        raise NotImplementedError

    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        """Compatibilidad con el contrato actual del núcleo."""
        return self.generate_response(mensaje).to_core_response()
