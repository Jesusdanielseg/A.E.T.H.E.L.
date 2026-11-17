import logging
import signal

import pytest

from src.core import lifecycle
from src.core.controller import ControladorCentral, MensajeEntrada, RespuestaSalida
from src.core.exceptions import RecoverableError
from src.core.llm import GestorPresupuesto, RespuestaLLM
from src.interfaces.cli import InterfazCLI


class FakeProvider:
    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        return RespuestaLLM(mensaje, "test-model", 1, 1, 0.0)


def _controller() -> ControladorCentral:
    return ControladorCentral(FakeProvider(), GestorPresupuesto(1.0))


def test_cli_sends_messages_until_exit_and_prints_traced_responses(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    inputs = iter(["ping", "hola", "  QUIT  "])
    received: list[MensajeEntrada] = []

    class FakeController(ControladorCentral):
        def procesar_mensaje(self, message: MensajeEntrada) -> RespuestaSalida:
            received.append(message)
            content = (
                "pong (núcleo operativo)"
                if message.contenido == "ping"
                else f"respuesta a {message.contenido}"
            )
            return RespuestaSalida("request-12345678", content)

    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    caplog.set_level(logging.INFO, logger="src.interfaces.cli")

    InterfazCLI(
        FakeController(FakeProvider(), GestorPresupuesto(1.0))
    ).ejecutar()

    output = capsys.readouterr().out
    assert "está listo" in output
    assert "Escribe 'salir'" in output
    assert "A.E.T.H.E.L. [request-12345678] > pong (núcleo operativo)" in output
    assert "A.E.T.H.E.L. [request-12345678] > respuesta a hola" in output
    assert received == [
        MensajeEntrada("ping", "cli"),
        MensajeEntrada("hola", "cli"),
    ]
    assert "Cerrando interfaz CLI por solicitud del usuario" in caplog.text


def test_cli_warns_on_recoverable_error_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    inputs = iter(["", "ping", "salir"])
    calls: list[MensajeEntrada] = []

    class FakeController(ControladorCentral):
        def procesar_mensaje(self, message: MensajeEntrada) -> RespuestaSalida:
            calls.append(message)
            if not message.contenido:
                raise RecoverableError("El mensaje no puede estar vacío.")
            return RespuestaSalida("request-ping", "pong (núcleo operativo)")

    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    caplog.set_level(logging.WARNING, logger="src.interfaces.cli")

    InterfazCLI(
        FakeController(FakeProvider(), GestorPresupuesto(1.0))
    ).ejecutar()

    assert len(calls) == 2
    output = capsys.readouterr().out
    assert "[Aviso] El mensaje no puede estar vacío." in output
    assert "Entrada rechazada: El mensaje no puede estar vacío." in caplog.text
    assert "pong (núcleo operativo)" in output


@pytest.mark.parametrize("exception", [KeyboardInterrupt, EOFError])
def test_cli_exits_cleanly_on_keyboard_interrupt_or_eof(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exception: type[BaseException],
) -> None:
    def interrupted_input(_prompt: str) -> str:
        raise exception

    monkeypatch.setattr("builtins.input", interrupted_input)

    InterfazCLI(_controller()).ejecutar()

    output = capsys.readouterr().out
    assert "está listo" in output
    assert output.endswith("\n")


def test_cli_exit_commands_are_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "  ExIt ")

    class UnexpectedController(ControladorCentral):
        def procesar_mensaje(self, _message: MensajeEntrada) -> RespuestaSalida:
            pytest.fail("No debe procesar el comando de salida")

    InterfazCLI(
        UnexpectedController(FakeProvider(), GestorPresupuesto(1.0))
    ).ejecutar()

    assert "está listo" in capsys.readouterr().out


def test_termination_signal_during_input_exits_cli_and_releases_instance_lock(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    signal_handlers: dict[int, object] = {}

    def getsignal(signum: int) -> object:
        return signal_handlers.get(signum, signal.SIG_DFL)

    def set_signal(signum: int, handler: object) -> object:
        previous = getsignal(signum)
        signal_handlers[signum] = handler
        return previous

    monkeypatch.setattr(signal, "getsignal", getsignal)
    monkeypatch.setattr(signal, "signal", set_signal)
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    manager.iniciar()

    def terminate_while_reading(_prompt: str) -> str:
        manager._manejar_senal(signal.SIGTERM, None)
        pytest.fail("The signal handler must interrupt input")

    monkeypatch.setattr("builtins.input", terminate_while_reading)
    InterfazCLI(_controller()).ejecutar()

    assert not manager.en_ejecucion
    assert manager._lock_file is None
    assert capsys.readouterr().out.endswith("\n")

    second_manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    second_manager.iniciar()
    second_manager.detener()
