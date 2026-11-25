import math
import os
from pathlib import Path
from typing import IO, ClassVar

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover

    def load_dotenv(
        dotenv_path: str | os.PathLike[str] | None = None,
        stream: IO[str] | None = None,
        verbose: bool = False,
        override: bool = False,
        interpolate: bool = True,
        encoding: str | None = "utf-8",
    ) -> bool:
        del dotenv_path, stream, verbose, override, interpolate, encoding
        return False


def _env_int(name: str, default: int) -> int:
    """Lee un entero de entorno; devuelve 0 si el valor no es válido."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return 0


def _env_bool(name: str, default: bool) -> bool:
    """Interpreta valores habituales de verdad sin aceptar falsos positivos."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on", "si", "sí"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


class Settings:
    """Configuración global del sistema A.E.T.H.E.L."""

    PROJECT_NAME: str = "A.E.T.H.E.L."
    VERSION: str = "0.3.0"
    ALLOWED_ENVIRONMENTS: ClassVar[frozenset[str]] = frozenset(
        {"development", "production", "test", "local"}
    )

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")

        default_db_path = project_root / "database" / "aethel.db"
        default_persona_path = project_root / "prompts" / "persona.yaml"

        env_raw = os.getenv("ENVIRONMENT", "development")
        self.ENVIRONMENT: str = (env_raw or "development").strip().lower()

        db_raw = (os.getenv("DB_PATH") or "").strip()
        db_path_obj = Path(db_raw or default_db_path).expanduser()
        if not db_path_obj.is_absolute():
            db_path_obj = project_root / db_path_obj
        self.DB_PATH: str = str(db_path_obj.resolve())
        persona_raw = (os.getenv("PERSONALITY_PATH") or "").strip()
        persona_path = Path(persona_raw or default_persona_path).expanduser()
        if not persona_path.is_absolute():
            persona_path = project_root / persona_path
        self.PERSONALITY_PATH: str = str(persona_path.resolve())
        self.PERSONALITY_MODE: str = (
            (os.getenv("PERSONALITY_MODE", "enfoque") or "enfoque").strip().lower()
        )

        self.AI_API_KEY: str = (os.getenv("AI_API_KEY", "") or "").strip()
        self.AI_MODEL: str = (
            os.getenv("AI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash"
        ).strip()
        fallbacks_raw = os.getenv("AI_FALLBACK_MODELS", "") or ""
        self.AI_FALLBACK_MODELS: tuple[str, ...] = tuple(
            modelo.strip() for modelo in fallbacks_raw.split(",") if modelo.strip()
        )
        self.OLLAMA_URL: str = (
            os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
            or "http://127.0.0.1:11434"
        ).strip()
        self.OLLAMA_MODEL: str = (
            os.getenv("OLLAMA_MODEL", "gemma3:4b") or "gemma3:4b"
        ).strip()
        self.OLLAMA_THINK: bool = _env_bool("OLLAMA_THINK", False)
        self.OLLAMA_NUM_CTX: int = _env_int("OLLAMA_NUM_CTX", 8192)
        self.OLLAMA_NUM_PREDICT: int = _env_int("OLLAMA_NUM_PREDICT", 512)
        self.OLLAMA_KEEP_ALIVE: str = (
            os.getenv("OLLAMA_KEEP_ALIVE", "30m") or "30m"
        ).strip()
        self.OLLAMA_TIMEOUT_SECONDS: int = _env_int("OLLAMA_TIMEOUT_SECONDS", 120)
        provider_order_raw = (
            os.getenv("LLM_PROVIDER_ORDER", "ollama,gemini,offline") or ""
        )
        self.LLM_PROVIDER_ORDER: tuple[str, ...] = tuple(
            provider.strip().lower()
            for provider in provider_order_raw.split(",")
            if provider.strip()
        )
        budget_raw = (os.getenv("LLM_BUDGET_USD", "0.50") or "0.50").strip()
        try:
            self.LLM_BUDGET_USD: float = float(budget_raw)
        except ValueError:
            self.LLM_BUDGET_USD = -1.0
        self.CONTEXT_RETENTION_DAYS: int = _env_int("CONTEXT_RETENTION_DAYS", 30)
        self.CONTEXT_ENCRYPTION_KEY: str = (
            os.getenv("CONTEXT_ENCRYPTION_KEY", "") or ""
        ).strip()

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def requires_api_key(self) -> bool:
        return self.ENVIRONMENT in {"production", "test"}

    def validar(self) -> bool:
        """Valida las variables críticas de configuración."""
        errores: list[str] = []

        if not self.ENVIRONMENT:
            errores.append("ENVIRONMENT no puede estar vacío.")
        elif self.ENVIRONMENT not in self.ALLOWED_ENVIRONMENTS:
            errores.append(
                f"ENVIRONMENT desconocido: '{self.ENVIRONMENT}'. "
                "Se espera development, production, test o local."
            )

        if (
            self.requires_api_key
            and "gemini" in self.LLM_PROVIDER_ORDER
            and not self.AI_API_KEY
        ):
            errores.append(f"Falta AI_API_KEY para el entorno '{self.ENVIRONMENT}'.")

        if "gemini" in self.LLM_PROVIDER_ORDER and not self.AI_MODEL:
            errores.append("AI_MODEL no puede estar vacío.")

        if not self.OLLAMA_MODEL:
            errores.append("OLLAMA_MODEL no puede estar vacío.")
        if self.OLLAMA_TIMEOUT_SECONDS <= 0:
            errores.append("OLLAMA_TIMEOUT_SECONDS debe ser mayor que cero.")
        if self.OLLAMA_NUM_CTX <= 0:
            errores.append("OLLAMA_NUM_CTX debe ser mayor que cero.")
        if self.OLLAMA_NUM_PREDICT <= 0:
            errores.append("OLLAMA_NUM_PREDICT debe ser mayor que cero.")
        if not self.OLLAMA_KEEP_ALIVE:
            errores.append("OLLAMA_KEEP_ALIVE no puede estar vacío.")

        if not math.isfinite(self.LLM_BUDGET_USD) or self.LLM_BUDGET_USD < 0:
            errores.append("LLM_BUDGET_USD debe ser un número finito no negativo.")

        if self.CONTEXT_RETENTION_DAYS <= 0:
            errores.append("CONTEXT_RETENTION_DAYS debe ser mayor que cero.")

        if not self.PERSONALITY_PATH:
            errores.append("PERSONALITY_PATH no puede estar vacío.")
        if self.PERSONALITY_MODE not in {"enfoque", "codigo", "casual"}:
            errores.append("PERSONALITY_MODE debe ser enfoque, codigo o casual.")

        valid_providers = {"gemini", "ollama", "offline"}
        if not self.LLM_PROVIDER_ORDER or any(
            provider not in valid_providers for provider in self.LLM_PROVIDER_ORDER
        ):
            errores.append("LLM_PROVIDER_ORDER debe contener gemini, ollama u offline.")

        if errores:
            raise ValueError("Error de configuración: " + "; ".join(errores))

        return True

    def as_dict(self) -> dict[str, str]:
        return {
            "PROJECT_NAME": self.PROJECT_NAME,
            "VERSION": self.VERSION,
            "ENVIRONMENT": self.ENVIRONMENT,
            "DB_PATH": self.DB_PATH,
            "PERSONALITY_PATH": self.PERSONALITY_PATH,
            "PERSONALITY_MODE": self.PERSONALITY_MODE,
            "AI_API_KEY": "***" if self.AI_API_KEY else "",
            "AI_MODEL": self.AI_MODEL,
            "AI_FALLBACK_MODELS": ",".join(self.AI_FALLBACK_MODELS),
            "OLLAMA_URL": self.OLLAMA_URL,
            "OLLAMA_MODEL": self.OLLAMA_MODEL,
            "OLLAMA_THINK": str(self.OLLAMA_THINK).lower(),
            "OLLAMA_NUM_CTX": str(self.OLLAMA_NUM_CTX),
            "OLLAMA_NUM_PREDICT": str(self.OLLAMA_NUM_PREDICT),
            "OLLAMA_KEEP_ALIVE": self.OLLAMA_KEEP_ALIVE,
            "OLLAMA_TIMEOUT_SECONDS": str(self.OLLAMA_TIMEOUT_SECONDS),
            "LLM_PROVIDER_ORDER": ",".join(self.LLM_PROVIDER_ORDER),
            "LLM_BUDGET_USD": str(self.LLM_BUDGET_USD),
            "CONTEXT_RETENTION_DAYS": str(self.CONTEXT_RETENTION_DAYS),
            "CONTEXT_ENCRYPTION_KEY": "***" if self.CONTEXT_ENCRYPTION_KEY else "",
        }


config = Settings()
