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

        self.AI_PROVIDER: str = (os.getenv("AI_PROVIDER", "gemini") or "gemini").strip()
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
            os.getenv("OLLAMA_MODEL", "llama3.2") or "llama3.2"
        ).strip()
        ollama_timeout_raw = os.getenv("OLLAMA_TIMEOUT_SECONDS", "120") or "120"
        try:
            self.OLLAMA_TIMEOUT_SECONDS: int = int(ollama_timeout_raw)
        except ValueError:
            self.OLLAMA_TIMEOUT_SECONDS = 0
        provider_order_raw = (
            os.getenv("LLM_PROVIDER_ORDER", "gemini,ollama,offline") or ""
        )
        self.LLM_PROVIDER_ORDER: tuple[str, ...] = tuple(
            provider.strip().lower()
            for provider in provider_order_raw.split(",")
            if provider.strip()
        )
        retention_raw = os.getenv("CONTEXT_RETENTION_DAYS", "30") or "30"
        try:
            self.CONTEXT_RETENTION_DAYS: int = int(retention_raw)
        except ValueError:
            self.CONTEXT_RETENTION_DAYS = 0
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

        if not self.AI_PROVIDER:
            errores.append("AI_PROVIDER no puede estar vacío.")

        if "gemini" in self.LLM_PROVIDER_ORDER and not self.AI_MODEL:
            errores.append("AI_MODEL no puede estar vacío.")

        if self.OLLAMA_TIMEOUT_SECONDS <= 0:
            errores.append("OLLAMA_TIMEOUT_SECONDS debe ser mayor que cero.")

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
            "AI_PROVIDER": self.AI_PROVIDER,
            "AI_API_KEY": "***" if self.AI_API_KEY else "",
            "AI_MODEL": self.AI_MODEL,
            "AI_FALLBACK_MODELS": ",".join(self.AI_FALLBACK_MODELS),
            "OLLAMA_URL": self.OLLAMA_URL,
            "OLLAMA_MODEL": self.OLLAMA_MODEL,
            "OLLAMA_TIMEOUT_SECONDS": str(self.OLLAMA_TIMEOUT_SECONDS),
            "LLM_PROVIDER_ORDER": ",".join(self.LLM_PROVIDER_ORDER),
            "CONTEXT_RETENTION_DAYS": str(self.CONTEXT_RETENTION_DAYS),
            "CONTEXT_ENCRYPTION_KEY": "***" if self.CONTEXT_ENCRYPTION_KEY else "",
        }


config = Settings()
