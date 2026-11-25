from pathlib import Path

import pytest

from src.context.prompt_builder import PersonaBuilder, PersonaConfigError

PERSONA_PATH = Path(__file__).parents[1] / "prompts" / "persona.yaml"


def test_persona_prompt_contains_identity_style_and_serious_override() -> None:
    prompt = PersonaBuilder(PERSONA_PATH).build_system_prompt()

    assert "A.E.T.H.E.L." in prompt
    assert "Modo activo: enfoque." in prompt
    assert "Regla de situación seria:" in prompt
    assert "el humor" in prompt.lower()
    assert "Copiloto técnico" in prompt


def test_persona_mode_can_be_overridden_without_editing_yaml() -> None:
    builder = PersonaBuilder(PERSONA_PATH)

    assert "Modo activo: codigo." in builder.build_system_prompt("codigo")


def test_persona_renders_format_flags_as_natural_instructions() -> None:
    prompt = PersonaBuilder(PERSONA_PATH).build_system_prompt()

    assert "Primera línea directa: True" not in prompt
    assert "Brevedad por defecto: True" not in prompt
    assert "Empieza con una respuesta directa" in prompt
    assert "Sé breve por defecto" in prompt
    assert "No inventes listados de archivos" in prompt
    assert "No inventes precios" in prompt
    assert "No puedo ver tu escritorio" in prompt
    assert "Reconoce los datos que el usuario comparte" in prompt
    assert "Operativa." not in prompt


@pytest.mark.parametrize("mode", ["", "irreverente", "serio"])
def test_persona_rejects_unknown_modes(mode: str) -> None:
    with pytest.raises(PersonaConfigError, match="modo"):
        PersonaBuilder(PERSONA_PATH, modo=mode)


def test_persona_rejects_invalid_profile(tmp_path) -> None:
    profile = tmp_path / "persona.yaml"
    profile.write_text("identidad: []\n", encoding="utf-8")

    with pytest.raises(PersonaConfigError):
        PersonaBuilder(profile)
