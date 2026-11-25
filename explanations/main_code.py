"""Copia didáctica de src/main.py; no es el punto de entrada importado.

Estado 04.5: copia desactualizada. No incluye _crear_router_llm(), el router,
el contexto, config.validar(), sqlite3.Error ni LLM_BUDGET_USD. Ver
explanations/14-auditoria-explanations-04-5.md.
"""

import logging
import sys

from src.core.controller import ControladorCentral
from src.core.exceptions import CriticalError
from src.core.health import verificar_salud
from src.core.lifecycle import LifecycleManager
from src.core.logger import configurar_logging
from src.interfaces.cli import InterfazCLI

# Logger del punto de entrada; configurar_logging instala handlers para la app.
logger = logging.getLogger(__name__)


def main() -> int:
    """Prepara dependencias, valida el sistema, inicia la CLI y limpia al salir."""
    try:
        # Debe ir primero para que health/lifecycle puedan escribir logs.
        configurar_logging()
    except OSError as exc:
        # Si ni siquiera se puede abrir el log, no intentamos arrancar el servicio.
        logger.error("No se pudo configurar el sistema de logs: %s", exc)
        return 1

    # None permite distinguir que la construcción falló antes de tener lifecycle.
    lifecycle: LifecycleManager | None = None
    exit_code = 0
    try:
        lifecycle = LifecycleManager()

        # Composition root: main conecta implementación concreta con interfaz.
        controlador = ControladorCentral()
        cli = InterfazCLI(controlador)

        # Primero activa señales/lock, luego comprueba almacenamiento y logs.
        lifecycle.iniciar()
        verificar_salud(strict=True)

        # La CLI vuelve al prompt hasta que el usuario o una señal la detiene.
        cli.ejecutar()
    except KeyboardInterrupt:
        # Ctrl+C/SIGINT y SIGTERM son cierres normales si cleanup termina bien.
        logger.info("Interrupción recibida; cierre ordenado")
    except CriticalError as exc:
        # Salud crítica u otro fallo crítico impide continuar.
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
                # Garantizado para salida, fallo de salud y excepciones.
                lifecycle.detener()
            except Exception:
                # No ocultamos el error de cleanup: además lo reflejamos en exit code.
                logger.exception("Error durante el apagado de A.E.T.H.E.L.")
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    # sys.exit convierte el entero de main en estado de salida del proceso.
    sys.exit(main())
