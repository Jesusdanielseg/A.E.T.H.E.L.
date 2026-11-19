import logging
import sys

from src.context.manager import ContextManager
from src.context.prompt_builder import PersonaBuilder
from src.core.config import config
from src.core.controller import ControladorCentral
from src.core.exceptions import CriticalError
from src.core.health import verificar_salud
from src.core.lifecycle import LifecycleManager
from src.core.llm import GestorPresupuesto
from src.core.logger import configurar_logging
from src.infrastructure.gemini_client import GeminiClient
from src.interfaces.cli import InterfazCLI
from src.llm.base import BaseLLMProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.offline_provider import OfflineProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.router import LLMRouter

logger = logging.getLogger(__name__)


def _crear_router_llm() -> LLMRouter:
    """Construye proveedores según LLM_PROVIDER_ORDER."""
    proveedores: list[BaseLLMProvider] = []
    for provider_name in config.LLM_PROVIDER_ORDER:
        if provider_name == "gemini":
            try:
                cliente_gemini = GeminiClient(
                    modelo=config.AI_MODEL,
                    modelos_fallback=config.AI_FALLBACK_MODELS,
                )
            except CriticalError as exc:
                logger.warning("Gemini no disponible; se activarán respaldos: %s", exc)
            else:
                proveedores.append(GeminiProvider(cliente_gemini))
        elif provider_name == "ollama":
            proveedores.append(
                OllamaProvider(
                    model=config.OLLAMA_MODEL,
                    base_url=config.OLLAMA_URL,
                    timeout_seconds=config.OLLAMA_TIMEOUT_SECONDS,
                )
            )
        elif provider_name == "offline":
            proveedores.append(OfflineProvider())
        else:
            logger.warning("Proveedor LLM desconocido: %s", provider_name)
    if not proveedores:
        raise ValueError("LLM_PROVIDER_ORDER no contiene proveedores válidos.")
    return LLMRouter(proveedores)


def main() -> int:
    """Punto de entrada principal de A.E.T.H.E.L."""
    try:
        configurar_logging()
    except OSError as exc:
        logger.error("No se pudo configurar el sistema de logs: %s", exc)
        return 1

    lifecycle: LifecycleManager | None = None
    contexto: ContextManager | None = None
    exit_code = 0
    try:
        lifecycle = LifecycleManager()
        verificar_salud(strict=True)
        proveedor_llm = _crear_router_llm()
        presupuesto = GestorPresupuesto(limite_usd=0.50)
        system_prompt = PersonaBuilder(
            config.PERSONALITY_PATH,
            modo=config.PERSONALITY_MODE,
        ).build_system_prompt()
        contexto = ContextManager(
            database_path=config.DB_PATH,
            system_prompt=system_prompt,
            summarizer=proveedor_llm,
            presupuesto=presupuesto,
            encryption_key=config.CONTEXT_ENCRYPTION_KEY or None,
            retention_days=config.CONTEXT_RETENTION_DAYS,
        )
        controlador = ControladorCentral(
            proveedor_llm=proveedor_llm,
            presupuesto=presupuesto,
            contexto=contexto,
        )
        cli = InterfazCLI(controlador)
        lifecycle.iniciar()
        cli.ejecutar()
    except KeyboardInterrupt:
        logger.info("Interrupción recibida; cierre ordenado")
    except CriticalError as exc:
        logger.critical("Fallo crítico en el arranque: %s", exc)
        exit_code = 1
    except RuntimeError as exc:
        logger.error("No se pudo iniciar A.E.T.H.E.L.: %s", exc)
        exit_code = 1
    except ValueError as exc:
        logger.error("Configuración inválida: %s", exc)
        exit_code = 1
    except OSError as exc:
        logger.error("Error del sistema al iniciar A.E.T.H.E.L.: %s", exc)
        exit_code = 1
    finally:
        if lifecycle is not None:
            try:
                lifecycle.detener()
            except Exception:
                logger.exception("Error durante el apagado de A.E.T.H.E.L.")
                exit_code = 1
        if contexto is not None:
            try:
                contexto.close()
            except Exception:
                logger.exception("Error al cerrar la memoria conversacional")
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
