import json
from urllib import request

import pytest

from src.llm.base import BaseLLMProvider, ModelResponse, ProviderError
from src.llm.offline_provider import OfflineProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.router import LLMRouter


def test_base_provider_requires_generate_response() -> None:
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore[abstract]


def test_model_response_normalizes_to_core_contract() -> None:
    response = ModelResponse("ok", "offline", "rules", 2, 3, 0.0)

    core_response = response.to_core_response()

    assert core_response.contenido == "ok"
    assert core_response.modelo == "rules"
    assert core_response.tokens_entrada == 2
    assert core_response.tokens_salida == 3


def test_router_uses_next_provider_after_normalized_failure() -> None:
    class BrokenProvider(BaseLLMProvider):
        def generate_response(self, prompt: str, context: str | None = None):
            del prompt, context
            raise ProviderError("unavailable")

    router = LLMRouter([BrokenProvider(), OfflineProvider()])

    response = router.generar_respuesta("hola")

    assert response.modelo == "offline-rules"
    assert response.coste_usd == 0.0


def test_router_rejects_empty_provider_list() -> None:
    with pytest.raises(ValueError, match="al menos un proveedor"):
        LLMRouter([])


def test_ollama_provider_posts_prompt_and_normalizes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def read(self) -> bytes:
            return json.dumps(
                {
                    "response": "respuesta local",
                    "prompt_eval_count": 4,
                    "eval_count": 7,
                }
            ).encode()

    captured: dict[str, object] = {}

    def fake_urlopen(http_request: request.Request, timeout: int) -> FakeResponse:
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        assert isinstance(http_request.data, bytes)
        captured["body"] = json.loads(http_request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("src.llm.ollama_provider.request.urlopen", fake_urlopen)
    response = OllamaProvider("llama3.2").generate_response("hola")

    assert response.text == "respuesta local"
    assert response.provider == "ollama"
    assert response.tokens_input == 4
    assert response.tokens_output == 7
    assert captured == {
        "url": "http://127.0.0.1:11434/api/generate",
        "timeout": 30,
        "body": {"model": "llama3.2", "prompt": "hola", "stream": False},
    }
