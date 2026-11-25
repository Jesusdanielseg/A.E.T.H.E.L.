"""Copia didáctica de src/core/lifecycle.py; no es el módulo importado.

Estado 04.5: _manejar_senal() está desactualizado; falta la guarda
_deteniendo y el relanzamiento de KeyboardInterrupt. Ver
explanations/14-auditoria-explanations-04-5.md.
"""

import errno
import logging
import os
import signal
from collections.abc import Callable
from pathlib import Path
from types import FrameType, TracebackType
from typing import IO, Literal, Self

# Solo se importa el mecanismo de bloqueo correspondiente al sistema actual.
if os.name == "nt":
    import msvcrt
else:
    import fcntl

from src.core.config import config

logger = logging.getLogger(__name__)

# Un handler Python, un entero SIG_DFL/SIG_IGN o None.
_SignalHandler = Callable[[int, FrameType | None], object] | int | None


class LifecycleManager:
    """Controla adquisición de candado, señales y limpieza ordenada."""

    def __init__(self, lock_path: str | Path | None = None) -> None:
        # El valor predeterminado queda junto a la base de datos.
        default_lock = Path(config.DB_PATH).parent / "aethel.lock"
        self.lock_path = Path(lock_path) if lock_path is not None else default_lock

        # El file handle debe permanecer abierto mientras el proceso posee el lock.
        self._lock_file: IO[str] | None = None

        # Guardamos handlers originales para restaurarlos en detener().
        self._manejadores_senales: dict[int, _SignalHandler] = {}
        self._deteniendo = False
        self.en_ejecucion = False
        self.tareas_cierre: list[Callable[[], None]] = []

    def __enter__(self) -> Self:
        """Permite usar `with LifecycleManager() as lifecycle`."""
        self.iniciar()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        """Detiene al salir y no suprime la excepción del bloque."""
        try:
            self.detener()
        except Exception as cleanup_error:
            if exc_value is None:
                # Sin excepción previa, el fallo de cleanup se propaga.
                raise
            # Si ya había excepción, la registramos y preservamos la original.
            logger.error(
                "Error durante el apagado al manejar otra excepción",
                exc_info=(
                    type(cleanup_error),
                    cleanup_error,
                    cleanup_error.__traceback__,
                ),
            )
        return False

    def registrar_tarea_cierre(self, tarea: Callable[[], None]) -> None:
        """Añade una función sin argumentos a la pila de tareas de limpieza."""
        if not callable(tarea):
            raise TypeError("La tarea de cierre debe ser una función ejecutable")
        self.tareas_cierre.append(tarea)

    def _adquirir_candado(self) -> None:
        """Impide que dos procesos locales compartan la misma instancia."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        # a+ crea si falta y no trunca un archivo que podría estar bloqueado.
        lock_file = self.lock_path.open("a+", encoding="utf-8")
        try:
            if os.name == "nt":
                # Windows bloquea un byte; garantizamos que el archivo lo contenga.
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write("\0")
                    lock_file.flush()
                lock_file.seek(0)
                try:
                    msvcrt.locking(  # type: ignore[attr-defined]
                        lock_file.fileno(), msvcrt.LK_NBLCK, 1  # type: ignore[attr-defined]
                    )
                except OSError as exc:
                    # Estos códigos indican que otra instancia tiene el byte.
                    if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise RuntimeError(
                            "A.E.T.H.E.L. ya se encuentra en ejecución"
                        ) from exc
                    raise
            else:
                try:
                    # LOCK_NB falla inmediatamente si ya existe dueño del lock.
                    fcntl.flock(
                        lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                except BlockingIOError as exc:
                    raise RuntimeError(
                        "A.E.T.H.E.L. ya se encuentra en ejecución"
                    ) from exc
        except BaseException:
            # No dejamos abierto el archivo si adquirir el lock falla.
            lock_file.close()
            raise

        self._lock_file = lock_file

    def _registrar_senales(self) -> None:
        """Instala manejadores para Ctrl+C y SIGTERM sin perder los previos."""
        for signum in (signal.SIGINT, signal.SIGTERM):
            self._manejadores_senales[signum] = signal.getsignal(signum)
            try:
                signal.signal(signum, self._manejar_senal)
            except ValueError:
                # Quitamos la entrada no instalada; el rollback restaura las demás.
                del self._manejadores_senales[signum]
                raise

    def _restaurar_senales(self) -> list[Exception]:
        """Restaura todos los handlers posibles y devuelve errores de restauración."""
        errores: list[Exception] = []
        for signum, manejador in reversed(tuple(self._manejadores_senales.items())):
            try:
                signal.signal(signum, manejador)
            except (OSError, ValueError) as exc:
                errores.append(exc)
            else:
                del self._manejadores_senales[signum]
        return errores

    def _liberar_candado(self) -> None:
        """Cierra el descriptor; el sistema operativo libera el bloqueo."""
        lock_file = self._lock_file
        self._lock_file = None
        if lock_file is not None:
            lock_file.close()

    def _manejar_senal(self, signum: int, _frame: FrameType | None) -> None:
        """Se ejecuta al recibir una señal de terminación."""
        del _frame
        try:
            logger.info("Señal %s recibida; iniciando apagado ordenado", signum)
        finally:
            # Aunque el logging falle, siempre se intenta la limpieza.
            self.detener()

    def iniciar(self) -> None:
        """Valida configuración, adquiere lock e instala handlers de señal."""
        if self.en_ejecucion:
            return

        # La configuración inválida falla antes de tocar el lock.
        config.validar()
        self._adquirir_candado()
        self.en_ejecucion = True
        try:
            self._registrar_senales()
            logger.info(
                "Programa iniciado: %s, versión %s, entorno %s",
                config.PROJECT_NAME,
                config.VERSION,
                config.ENVIRONMENT,
            )
        except BaseException:
            # El inicio es transaccional: revertimos cualquier recurso adquirido.
            self.en_ejecucion = False
            errores = self._restaurar_senales()
            try:
                self._liberar_candado()
            except OSError as exc:
                errores.append(exc)
            for error in errores:
                logger.error(
                    "No se pudo completar la limpieza tras un fallo de inicio",
                    exc_info=(type(error), error, error.__traceback__),
                )
            raise

    def detener(self) -> None:
        """Ejecuta limpiezas LIFO, restaura señales y libera el candado."""
        if self._deteniendo:
            return
        if (
            not self.en_ejecucion
            and self._lock_file is None
            and not self._manejadores_senales
        ):
            return

        estaba_en_ejecucion = self.en_ejecucion
        self._deteniendo = True
        self.en_ejecucion = False
        errores: list[Exception] = []
        try:
            if estaba_en_ejecucion:
                # Cerrar al revés del registro respeta dependencias entre recursos.
                for tarea in reversed(tuple(self.tareas_cierre)):
                    try:
                        tarea()
                    except Exception as exc:  # noqa: BLE001 - seguir con las demás
                        errores.append(exc)
        finally:
            # El finally asegura la liberación aun cuando una tarea falle.
            errores.extend(self._restaurar_senales())
            try:
                self._liberar_candado()
            except OSError as exc:
                errores.append(exc)
            self._deteniendo = False

        # Se propaga el primer fallo; los demás no se pierden silenciosamente.
        for error in errores[1:]:
            logger.error(
                "Error adicional durante el apagado",
                exc_info=(type(error), error, error.__traceback__),
            )
        if errores:
            raise errores[0]
