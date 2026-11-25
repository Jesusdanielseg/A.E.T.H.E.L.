import pytest

from src.core import config as config_module
from src.core.config import Settings


def test_defaults_prefer_ollama_and_disable_thinking(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "load_dotenv", lambda *_args, **_kwargs: False)
    for name in (
        "LLM_PROVIDER_ORDER",
        "OLLAMA_MODEL",
        "OLLAMA_THINK",
        "LLM_BUDGET_USD",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings()

    assert settings.LLM_PROVIDER_ORDER == ("ollama", "gemini", "offline")
    assert settings.OLLAMA_MODEL == "gemma3:4b"
    assert settings.OLLAMA_THINK is False
    assert settings.OLLAMA_NUM_CTX == 8192
    assert settings.LLM_BUDGET_USD == pytest.approx(0.50)


def test_settings_reads_ollama_performance_options(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "ollama,offline")
    monkeypatch.setenv("OLLAMA_THINK", "false")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "2048")
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "128")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "5m")
    monkeypatch.setenv("LLM_BUDGET_USD", "1.25")

    settings = Settings()

    assert settings.OLLAMA_THINK is False
    assert settings.OLLAMA_NUM_CTX == 2048
    assert settings.OLLAMA_NUM_PREDICT == 128
    assert settings.OLLAMA_KEEP_ALIVE == "5m"
    assert settings.LLM_BUDGET_USD == pytest.approx(1.25)
    assert settings.validar() is True


def test_settings_rejects_invalid_budget(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "ollama,offline")
    monkeypatch.setenv("LLM_BUDGET_USD", "no-es-un-numero")

    with pytest.raises(ValueError, match="LLM_BUDGET_USD"):
        Settings().validar()


def test_settings_rejects_invalid_ollama_limits(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "ollama,offline")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "0")

    with pytest.raises(ValueError, match="OLLAMA_NUM_CTX"):
        Settings().validar()
