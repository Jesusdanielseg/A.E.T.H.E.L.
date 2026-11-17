from dataclasses import FrozenInstanceError

import pytest

from src.core import controller
from src.core.exceptions import RecoverableError
from src.core.llm import GestorPresupuesto, RespuestaLLM


class FakeProvider:
    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        return RespuestaLLM(f"[test] {mensaje}", "test-model", 1, 1, 0.0)


def _controller() -> controller.ControladorCentral:
    return controller.ControladorCentral(
        proveedor_llm=FakeProvider(),
        presupuesto=GestorPresupuesto(1.0),
    )


def test_process_message_trims_input_and_uses_injected_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(controller, "establecer_request_id", lambda: "request-123")
    controlador = _controller()

    respuesta = controlador.procesar_mensaje(
        controller.MensajeEntrada("  Hola A.E.T.H.E.L.  ")
    )

    assert respuesta.request_id == "request-123"
    assert respuesta.contenido == "[test] Hola A.E.T.H.E.L."
    assert respuesta.simulada is False


@pytest.mark.parametrize("contenido", ["", " ", "\n\t"])
def test_empty_message_raises_recoverable_error(contenido: str) -> None:
    controlador = _controller()

    with pytest.raises(RecoverableError, match="no puede estar vacío"):
        controlador.procesar_mensaje(controller.MensajeEntrada(contenido))


def test_message_over_limit_raises_recoverable_error() -> None:
    controlador = _controller()
    contenido = "x" * (controlador.MAX_CARACTERES + 1)

    with pytest.raises(RecoverableError, match="excede el límite de 2000 caracteres"):
        controlador.procesar_mensaje(controller.MensajeEntrada(contenido))


@pytest.mark.parametrize("contenido", ["ping", "PING", " Ping "])
def test_ping_returns_core_health_response(contenido: str) -> None:
    controlador = _controller()

    respuesta = controlador.procesar_mensaje(
        controller.MensajeEntrada(contenido)
    )

    assert respuesta.contenido == "pong (núcleo operativo)"


def test_message_at_maximum_length_is_accepted() -> None:
    controlador = _controller()
    contenido = "x" * controlador.MAX_CARACTERES

    respuesta = controlador.procesar_mensaje(controller.MensajeEntrada(contenido))

    assert respuesta.simulada is False
    assert contenido in respuesta.contenido


def test_message_contracts_are_immutable() -> None:
    entrada = controller.MensajeEntrada("hola")
    salida = controller.RespuestaSalida("request-123", "respuesta")

    with pytest.raises(FrozenInstanceError):
        entrada.contenido = "cambiado"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        salida.contenido = "cambiado"  # type: ignore[misc]


def test_controller_uses_injected_llm_for_non_ping_messages() -> None:
    controlador = controller.ControladorCentral(
        FakeProvider(), GestorPresupuesto(1.0)
    )

    respuesta = controlador.procesar_mensaje(controller.MensajeEntrada("hola"))

    assert respuesta.contenido == "[test] hola"
    assert respuesta.simulada is False


def test_controller_keeps_ping_local_with_an_injected_llm() -> None:
    class UnexpectedProvider:
        def generar_respuesta(self, _mensaje: str):
            pytest.fail("ping no debe consumir la API")

    respuesta = controller.ControladorCentral(
        UnexpectedProvider(), GestorPresupuesto(1.0)
    ).procesar_mensaje(controller.MensajeEntrada("ping"))

    assert respuesta.contenido == "pong (núcleo operativo)"
    assert respuesta.simulada is True


def test_controller_checks_and_registers_budget_for_real_messages() -> None:
    presupuesto = GestorPresupuesto(1.0)
    controlador = controller.ControladorCentral(FakeProvider(), presupuesto)

    controlador.procesar_mensaje(controller.MensajeEntrada("hola"))

    assert presupuesto.tokens_totales == 2
    assert presupuesto.gasto_acumulado == 0.0


def test_controller_rejects_message_when_budget_is_exhausted() -> None:
    class UnexpectedProvider:
        def generar_respuesta(self, _mensaje: str):
            pytest.fail("No debe consultar el proveedor sin presupuesto")

    controlador = controller.ControladorCentral(
        UnexpectedProvider(), GestorPresupuesto(0.0)
    )

    with pytest.raises(RecoverableError, match="Presupuesto agotado"):
        controlador.procesar_mensaje(controller.MensajeEntrada("hola"))
