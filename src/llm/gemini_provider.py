from src.infrastructure.gemini_client import GeminiClient
from src.llm.base import BaseLLMProvider, ModelResponse, ProviderError


class GeminiProvider(BaseLLMProvider):
    """Adaptador que traduce GeminiClient al contrato abstracto."""

    def __init__(self, client: GeminiClient) -> None:
        self.client = client

    def generate_response(
        self, prompt: str, context: str | None = None
    ) -> ModelResponse:
        del context
        try:
            response = self.client.generar_respuesta(prompt)
        except Exception as exc:
            raise ProviderError("El proveedor Gemini no está disponible.") from exc
        return ModelResponse(
            text=response.contenido,
            provider="gemini",
            model=response.modelo,
            tokens_input=response.tokens_entrada,
            tokens_output=response.tokens_salida,
            cost_usd=response.coste_usd,
        )
