from dataclasses import FrozenInstanceError

import pytest

from src.core import controller
from src.core.exceptions import RecoverableError


def test_process_message_trims_input_and_returns_simulated_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(controller, "establecer_request_id", lambda: "request-123")
    controlador = controller.ControladorCentral()

    respuesta = controlador.procesar_mensaje(
        controller.MensajeEntrada("  Hola A.E.T.H.E.L.  ")
    )

    assert respuesta.request_id == "request-123"
    assert respuesta.contenido == (
        "[A.E.T.H.E.L. - Simulación] Procesado: 'Hola A.E.T.H.E.L.'"
    )
    assert respuesta.simulada is True


@pytest.mark.parametrize("contenido", ["", " ", "\n\t"])
def test_empty_message_raises_recoverable_error(contenido: str) -> None:
    controlador = controller.ControladorCentral()

    with pytest.raises(RecoverableError, match="no puede estar vacío"):
        controlador.procesar_mensaje(controller.MensajeEntrada(contenido))


def test_message_over_limit_raises_recoverable_error() -> None:
    controlador = controller.ControladorCentral()
    contenido = "x" * (controlador.MAX_CARACTERES + 1)

    with pytest.raises(RecoverableError, match="excede el límite de 2000 caracteres"):
        controlador.procesar_mensaje(controller.MensajeEntrada(contenido))


@pytest.mark.parametrize("contenido", ["ping", "PING", " Ping "])
def test_ping_returns_core_health_response(contenido: str) -> None:
    controlador = controller.ControladorCentral()

    respuesta = controlador.procesar_mensaje(
        controller.MensajeEntrada(contenido)
    )

    assert respuesta.contenido == "pong (núcleo operativo)"


def test_message_at_maximum_length_is_accepted() -> None:
    controlador = controller.ControladorCentral()
    contenido = "x" * controlador.MAX_CARACTERES

    respuesta = controlador.procesar_mensaje(controller.MensajeEntrada(contenido))

    assert respuesta.simulada
    assert contenido in respuesta.contenido


def test_message_contracts_are_immutable() -> None:
    entrada = controller.MensajeEntrada("hola")
    salida = controller.RespuestaSalida("request-123", "respuesta")

    with pytest.raises(FrozenInstanceError):
        entrada.contenido = "cambiado"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        salida.contenido = "cambiado"  # type: ignore[misc]
