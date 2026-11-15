import logging
import sys
from threading import Event

from src.core.exceptions import CriticalError, RecoverableError
from src.core.health import verificar_salud
from src.core.lifecycle import LifecycleManager
from src.core.logger import configurar_logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Punto de entrada principal de A.E.T.H.E.L."""
    lifecycle = LifecycleManager()
    shutdown_event = Event()

    def limpiar_prueba() -> None:
        logger.info("Limpiando recursos temporales...")

    lifecycle.registrar_tarea_cierre(shutdown_event.set)
    lifecycle.registrar_tarea_cierre(limpiar_prueba)

    try:
        configurar_logging()
        try:
            verificar_salud(strict=True)
        except RecoverableError as exc:
            logger.warning("Comprobación de salud con error recuperable: %s", exc)
        lifecycle.iniciar()
        while lifecycle.en_ejecucion:
            shutdown_event.wait()
    except CriticalError as exc:
        logger.critical("Fallo crítico; A.E.T.H.E.L. no puede continuar: %s", exc)
        return 1
    except RecoverableError as exc:
        logger.warning("Error recuperable durante el arranque: %s", exc)
        while lifecycle.en_ejecucion:
            shutdown_event.wait()
    except RuntimeError as exc:
        logger.error("No se pudo iniciar A.E.T.H.E.L.: %s", exc)
        return 1
    except ValueError as exc:
        logger.error("Configuración inválida: %s", exc)
        return 1
    except OSError as exc:
        logger.error("Error del sistema al iniciar A.E.T.H.E.L.: %s", exc)
        return 1
    finally:
        lifecycle.detener()

    return 0


if __name__ == "__main__":
    sys.exit(main())
