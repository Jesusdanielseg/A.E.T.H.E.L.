from pathlib import Path

from src.context.manager import ContextManager
from src.context.prompt_builder import PersonaBuilder
from src.core.llm import RespuestaLLM

PERSONA_PATH = Path(__file__).parents[1] / "prompts" / "persona.yaml"


class FakeSummarizer:
    def generar_respuesta(self, _prompt: str) -> RespuestaLLM:
        return RespuestaLLM("resumen de prueba", "offline", 1, 1, 0.0)


def test_long_conversation_compacts_and_persists_summary(tmp_path) -> None:
    database = tmp_path / "memory.db"
    context = ContextManager(
        database,
        "Regla permanente",
        max_messages=6,
        max_estimated_tokens=10000,
        summarizer=FakeSummarizer(),
    )
    for index in range(20):
        role = "user" if index % 2 == 0 else "assistant"
        context.add_message(role, f"turno {index}")
    session_id = context.session_id
    context.close()

    reopened = ContextManager(
        database,
        "Regla permanente",
        max_messages=6,
        max_estimated_tokens=10000,
    )

    assert reopened.session_id == session_id
    assert reopened.summary == "resumen de prueba"
    assert len(reopened.messages) <= 6
    prompt = reopened.build_prompt("última pregunta")
    assert "[RESUMEN_PREVIO]" in prompt
    assert "turno 19" in prompt
    reopened.close()


def test_contradictory_user_claims_remain_available_in_context(tmp_path) -> None:
    context = ContextManager(tmp_path / "memory.db", "Regla")
    context.add_message("user", "Mi color favorito es azul.")
    context.add_message("assistant", "Anotado: azul.")
    context.add_message("user", "En realidad, mi color favorito es rojo.")

    prompt = context.build_prompt("¿Cuál es mi color favorito?")

    assert "azul" in prompt
    assert "rojo" in prompt
    context.close()


def test_personality_prompt_includes_uncertainty_guidance() -> None:
    prompt = PersonaBuilder(PERSONA_PATH).build_system_prompt()

    assert "No inventes datos" in prompt
    assert "incertidumbre" in prompt
    assert "No puedo garantizarlo" in prompt
