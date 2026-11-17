import json
from urllib import request

from src.llm.base import BaseLLMProvider, ModelResponse, ProviderError


class OllamaProvider(BaseLLMProvider):
    """Adaptador opcional para una instancia local de Ollama."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 30,
    ) -> None:
        if not model.strip():
            raise ValueError("El modelo de Ollama no puede estar vacío.")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
            raise TypeError("El timeout de Ollama debe ser un entero.")
        if timeout_seconds <= 0:
            raise ValueError("El timeout de Ollama debe ser mayor que cero.")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate_response(
        self, prompt: str, context: str | None = None
    ) -> ModelResponse:
        del context
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(
                http_request, timeout=self.timeout_seconds
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError("Ollama no está disponible.") from exc

        text = body.get("response")
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("Ollama devolvió una respuesta inválida.")
        return ModelResponse(
            text=text.strip(),
            provider="ollama",
            model=self.model,
            tokens_input=self._metric(body, "prompt_eval_count"),
            tokens_output=self._metric(body, "eval_count"),
        )

    @staticmethod
    def _metric(payload: dict[str, object], key: str) -> int:
        value = payload.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return 0
        return value
