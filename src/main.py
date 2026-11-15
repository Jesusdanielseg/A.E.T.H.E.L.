import logging
import sys

from src.core.controller import ControladorCentral
from src.core.exceptions import CriticalError
from src.core.health import verificar_salud
from src.core.lifecycle import LifecycleManager
from src.core.logger import configurar_logging
from src.interfaces.cli import InterfazCLI

logger = logging.getLogger(__name__)


def main() -> int:
    """Punto de entrada principal de A.E.T.H.E.L."""
    try:
        configurar_logging()
    except OSError as exc:
        logger.error("No se pudo configurar el sistema de logs: %s", exc)
        return 1

    lifecycle: LifecycleManager | None = None
    exit_code = 0
    try:
        lifecycle = LifecycleManager()
        controlador = ControladorCentral()
        cli = InterfazCLI(controlador)
        lifecycle.iniciar()
        verificar_salud(strict=True)
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

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
