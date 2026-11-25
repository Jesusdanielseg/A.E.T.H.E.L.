from src.llm.base import BaseLLMProvider, ModelResponse


class OfflineProvider(BaseLLMProvider):
    """Último respaldo determinista que no requiere red ni dependencias."""

    def generate_response(
        self, prompt: str, context: str | None = None
    ) -> ModelResponse:
        del context
        normalized = prompt.strip().lower()
        if normalized in {"hola", "hola aethel", "hello"}:
            text = "Hola. A.E.T.H.E.L. está funcionando en modo offline."
        elif normalized.endswith("?") or normalized.startswith(
            ("qué ", "que ", "cómo ", "como ", "por qué ", "porque ")
        ):
            text = (
                "No puedo consultar un modelo ahora. La pregunta quedó "
                "recibida y puede reintentarse cuando haya un proveedor disponible."
            )
        else:
            text = (
                "A.E.T.H.E.L. recibió tu mensaje, pero los proveedores de IA "
                "no están disponibles en este momento."
            )
        return ModelResponse(
            text=text,
            provider="offline",
            model="offline-rules",
        )
