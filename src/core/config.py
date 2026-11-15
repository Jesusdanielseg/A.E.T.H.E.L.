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

        env_raw = os.getenv("ENVIRONMENT", "development")
        self.ENVIRONMENT: str = (env_raw or "development").strip().lower()

        db_raw = (os.getenv("DB_PATH") or "").strip()
        db_path_obj = Path(db_raw or default_db_path).expanduser()
        if not db_path_obj.is_absolute():
            db_path_obj = project_root / db_path_obj
        self.DB_PATH: str = str(db_path_obj.resolve())

        self.AI_PROVIDER: str = (
            os.getenv("AI_PROVIDER", "gemini") or "gemini"
        ).strip()
        self.AI_API_KEY: str = (os.getenv("AI_API_KEY", "") or "").strip()
        self.AI_MODEL: str = (
            os.getenv("AI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash"
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

        if self.requires_api_key and not self.AI_API_KEY:
            errores.append(f"Falta AI_API_KEY para el entorno '{self.ENVIRONMENT}'.")

        if not self.AI_PROVIDER:
            errores.append("AI_PROVIDER no puede estar vacío.")

        if not self.AI_MODEL:
            errores.append("AI_MODEL no puede estar vacío.")

        if errores:
            raise ValueError("Error de configuración: " + "; ".join(errores))

        return True

    def as_dict(self) -> dict[str, str]:
        return {
            "PROJECT_NAME": self.PROJECT_NAME,
            "VERSION": self.VERSION,
            "ENVIRONMENT": self.ENVIRONMENT,
            "DB_PATH": self.DB_PATH,
            "AI_PROVIDER": self.AI_PROVIDER,
            "AI_API_KEY": "***" if self.AI_API_KEY else "",
            "AI_MODEL": self.AI_MODEL,
        }


config = Settings()
