import logging
import sys
from threading import Event

from src.core.lifecycle import LifecycleManager

logger = logging.getLogger(__name__)


def main() -> int:
    """Punto de entrada principal de A.E.T.H.E.L."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    lifecycle = LifecycleManager()
    shutdown_event = Event()

    def limpiar_prueba() -> None:
        logger.info("Limpiando recursos temporales...")

    lifecycle.registrar_tarea_cierre(shutdown_event.set)
    lifecycle.registrar_tarea_cierre(limpiar_prueba)

    try:
        lifecycle.iniciar()
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
