from types import SimpleNamespace

import pytest

from src.core.exceptions import CriticalError, ExternalServiceError
from src.infrastructure import gemini_client


def _client(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[object],
    timeout_segundos: int = 30,
    max_reintentos: int = 3,
    espera_base: float = 1.5,
    espera_maxima: float = 30.0,
    jitter: float = 0.0,
) -> gemini_client.GeminiClient:
    class FakeModels:
        def generate_content(self, **_kwargs: object) -> object:
            response = responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            return response

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gemini_client.config, "AI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_client.config, "AI_FALLBACK_MODELS", ())
    monkeypatch.setattr(gemini_client.genai, "Client", lambda **_kwargs: FakeClient())
    return gemini_client.GeminiClient(
        modelo="gemini-2.5-flash",
        timeout_segundos=timeout_segundos,
        max_reintentos=max_reintentos,
        espera_base=espera_base,
        espera_maxima=espera_maxima,
        jitter=jitter,
    )


def _response(
    text: str, prompt_tokens: int = 10, output_tokens: int = 5
) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=output_tokens,
        ),
    )


def test_gemini_client_builds_structured_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch, [_response(" Hola ")])

    response = client.generar_respuesta("saluda")

    assert response.contenido == "Hola"
    assert response.modelo == "gemini-2.5-flash"
    assert response.tokens_entrada == 10
    assert response.tokens_salida == 5
    assert response.coste_usd == 0.000005


def test_gemini_client_retries_transient_api_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = gemini_client.APIError(503, {"error": {"message": "temporal"}})
    waits: list[float] = []
    monkeypatch.setattr(gemini_client.time, "sleep", waits.append)
    client = _client(monkeypatch, [error, error, _response("ok")])

    response = client.generar_respuesta("hola")

    assert response.contenido == "ok"
    assert waits == [1.5, 3.0]


def test_gemini_client_does_not_retry_invalid_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = gemini_client.APIError(401, {"error": {"message": "unauthorized"}})
    client = _client(monkeypatch, [error])

    with pytest.raises(CriticalError, match="Credenciales"):
        client.generar_respuesta("hola")


def test_gemini_client_translates_exhausted_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []
    monkeypatch.setattr(gemini_client.time, "sleep", waits.append)
    client = _client(
        monkeypatch,
        [TimeoutError("timeout"), TimeoutError("timeout"), TimeoutError("timeout")],
    )

    with pytest.raises(ExternalServiceError, match="Tiempo de espera"):
        client.generar_respuesta("hola")
    assert waits == [1.5, 3.0]


def test_gemini_client_rejects_empty_response_and_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch, [_response("   ")])

    with pytest.raises(ExternalServiceError, match="respuesta vacía"):
        client.generar_respuesta("hola")
    with pytest.raises(ValueError, match="mensaje"):
        client.generar_respuesta("  ")


@pytest.mark.parametrize("message", [None, 42])
def test_gemini_client_rejects_non_text_messages(
    monkeypatch: pytest.MonkeyPatch, message: object
) -> None:
    client = _client(monkeypatch, [])

    with pytest.raises(TypeError, match="texto"):
        client.generar_respuesta(message)  # type: ignore[arg-type]


def test_gemini_client_rejects_invalid_usage_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(
        monkeypatch,
        [_response("ok", prompt_tokens=-1, output_tokens=1)],
    )

    with pytest.raises(ExternalServiceError, match="métricas"):
        client.generar_respuesta("hola")


def test_gemini_client_validates_constructor_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_values = [
        ("timeout", 0, ValueError),
        ("retries", 0, ValueError),
        ("wait", -1.0, ValueError),
        ("timeout", True, TypeError),
        ("retries", True, TypeError),
    ]
    for option, value, error_type in invalid_values:
        with pytest.raises(error_type):
            if option == "timeout":
                _client(monkeypatch, [], timeout_segundos=value)  # type: ignore[arg-type]
            elif option == "retries":
                _client(monkeypatch, [], max_reintentos=value)  # type: ignore[arg-type]
            else:
                _client(monkeypatch, [], espera_base=value)  # type: ignore[arg-type]


def test_gemini_client_uses_fallback_after_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeModels:
        def generate_content(self, **kwargs: object) -> object:
            calls.append(str(kwargs["model"]))
            if len(calls) == 1:
                raise gemini_client.APIError(503, {"error": {"message": "busy"}})
            return _response("fallback ok")

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gemini_client.config, "AI_API_KEY", "test-key")
    monkeypatch.setattr(
        gemini_client.genai, "Client", lambda **_kwargs: FakeClient()
    )
    client = gemini_client.GeminiClient(
        modelo="primary",
        modelos_fallback=("fallback",),
        max_reintentos=1,
        jitter=0,
    )

    response = client.generar_respuesta("hola")

    assert response.modelo == "fallback"
    assert calls == ["primary", "fallback"]


def test_gemini_client_caps_backoff_and_adds_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waits: list[float] = []
    monkeypatch.setattr(gemini_client.time, "sleep", waits.append)
    monkeypatch.setattr(gemini_client.random, "uniform", lambda _a, _b: 0.25)
    client = _client(
        monkeypatch,
        [
            gemini_client.APIError(503, {"error": {"message": "busy"}}),
            gemini_client.APIError(503, {"error": {"message": "busy"}}),
            gemini_client.APIError(503, {"error": {"message": "busy"}}),
            gemini_client.APIError(503, {"error": {"message": "busy"}}),
        ],
        max_reintentos=4,
        espera_maxima=2.0,
        jitter=0.5,
    )

    with pytest.raises(ExternalServiceError):
        client.generar_respuesta("hola")

    assert waits == [1.75, 2.25, 2.25]
