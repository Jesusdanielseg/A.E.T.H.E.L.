from src.core.controller import ControladorCentral
from src.core.llm import GestorPresupuesto, RespuestaLLM
from src.interfaces.cli import InterfazCLI


class FakeProvider:
    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        return RespuestaLLM(mensaje, "test", 1, 1, 0.0)


def test_cli_supports_memory_model_and_status_commands(
    monkeypatch, capsys, tmp_path
) -> None:
    inputs = iter(["/memoria", "/modelo", "/estado", "/limpiar", "salir"])
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
    assert "[Estado]" in output
    assert "tokens=0" in output
    assert "coste=$0.0000 / $1.0000" in output
    assert "Sesión limpiada" in output
    context.close()
