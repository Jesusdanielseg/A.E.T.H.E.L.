from src.core.controller import ControladorCentral
from src.core.llm import GestorPresupuesto, RespuestaLLM
from src.interfaces.cli import InterfazCLI


class FakeProvider:
    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        return RespuestaLLM(mensaje, "test", 1, 1, 0.0)


def test_cli_supports_memory_and_model_commands(monkeypatch, capsys, tmp_path) -> None:
    inputs = iter(["/memoria", "/modelo", "/limpiar", "salir"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    from src.context.manager import ContextManager

    context = ContextManager(tmp_path / "memory.db", "Regla")
    controller = ControladorCentral(
        FakeProvider(), GestorPresupuesto(1.0), contexto=context
    )

    InterfazCLI(controller).ejecutar()

    output = capsys.readouterr().out
    assert "[Memoria]" in output
    assert "[Modelo]" in output
    assert "Sesión limpiada" in output
    context.close()
