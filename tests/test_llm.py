from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from src.core.exceptions import RecoverableError
from src.core.llm import GestorPresupuesto, RespuestaLLM


def test_llm_response_is_immutable() -> None:
    respuesta = RespuestaLLM("respuesta", "modelo-test", 10, 5, 0.001)

    with pytest.raises(FrozenInstanceError):
        respuesta.contenido = "modificada"  # type: ignore[misc]


def test_budget_starts_empty_and_accepts_usage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="src.core.llm")
    gestor = GestorPresupuesto(1.0)
    respuesta = RespuestaLLM("respuesta", "modelo-test", 10, 5, 0.25)

    gestor.verificar_disponibilidad()
    gestor.registrar_uso(respuesta)

    assert gestor.gasto_acumulado == pytest.approx(0.25)
    assert gestor.tokens_totales == 15
    assert "modelo-test" in caplog.text
    assert "acumulado=$0.2500 / $1.0000 USD" in caplog.text


def test_budget_rejects_usage_when_limit_is_reached() -> None:
    gestor = GestorPresupuesto(0.25)
    gestor.registrar_uso(RespuestaLLM("respuesta", "modelo-test", 1, 1, 0.25))

    with pytest.raises(RecoverableError, match="Presupuesto agotado"):
        gestor.verificar_disponibilidad()


def test_budget_allows_usage_below_limit() -> None:
    gestor = GestorPresupuesto(0.25)
    gestor.registrar_uso(RespuestaLLM("respuesta", "modelo-test", 1, 1, 0.2499))

    gestor.verificar_disponibilidad()


@pytest.mark.parametrize("limit", [-1.0, inf, nan])
def test_budget_rejects_invalid_limits(limit: float) -> None:
    with pytest.raises(ValueError, match="límite"):
        GestorPresupuesto(limit)


@pytest.mark.parametrize(
    ("tokens_entrada", "tokens_salida", "coste"),
    [(-1, 0, 0.0), (0, -1, 0.0), (0, 0, -0.01), (0, 0, inf), (0, 0, nan)],
)
def test_llm_response_rejects_invalid_metrics(
    tokens_entrada: int, tokens_salida: int, coste: float
) -> None:
    with pytest.raises(ValueError):
        RespuestaLLM(
            "respuesta",
            "modelo-test",
            tokens_entrada,
            tokens_salida,
            coste,
        )


@pytest.mark.parametrize(
    ("contenido", "modelo"),
    [("", "modelo-test"), ("respuesta", ""), ("   ", "modelo-test")],
)
def test_llm_response_requires_content_and_model(
    contenido: str, modelo: str
) -> None:
    with pytest.raises(ValueError):
        RespuestaLLM(contenido, modelo, 0, 0, 0.0)
