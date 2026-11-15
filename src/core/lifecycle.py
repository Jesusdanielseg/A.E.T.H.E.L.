import errno
import logging
import os
import signal
from collections.abc import Callable
from pathlib import Path
from types import FrameType, TracebackType
from typing import IO, Literal, Self

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from src.core.config import config

logger = logging.getLogger(__name__)
_SignalHandler = Callable[[int, FrameType | None], object] | int | None


class LifecycleManager:
    """Controla el arranque, las señales del SO y el apagado ordenado de A.E.T.H.E.L."""

    def __init__(self, lock_path: str | Path | None = None) -> None:
        default_lock = Path(config.DB_PATH).parent / "aethel.lock"
        self.lock_path = Path(lock_path) if lock_path is not None else default_lock
        self._lock_file: IO[str] | None = None
        self._manejadores_senales: dict[int, _SignalHandler] = {}
        self._deteniendo = False
        self.en_ejecucion = False
        self.tareas_cierre: list[Callable[[], None]] = []

    def __enter__(self) -> Self:
        self.iniciar()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        try:
            self.detener()
        except Exception as cleanup_error:
            if exc_value is None:
                raise
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
        if not callable(tarea):
            raise TypeError("La tarea de cierre debe ser una función ejecutable")
        self.tareas_cierre.append(tarea)

    def _adquirir_candado(self) -> None:
        """Impide que se ejecuten dos instancias simultáneamente en el mismo host."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.lock_path.open("a+", encoding="utf-8")
        try:
            if os.name == "nt":
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
                    if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise RuntimeError(
                            "A.E.T.H.E.L. ya se encuentra en ejecución"
                        ) from exc
                    raise
            else:
                try:
                    fcntl.flock(
                        lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                except BlockingIOError as exc:
                    raise RuntimeError(
                        "A.E.T.H.E.L. ya se encuentra en ejecución"
                    ) from exc
        except BaseException:
            lock_file.close()
            raise
        self._lock_file = lock_file

    def _registrar_senales(self) -> None:
        """Captura Ctrl+C y SIGTERM, conservando los manejadores anteriores."""
        for signum in (signal.SIGINT, signal.SIGTERM):
            self._manejadores_senales[signum] = signal.getsignal(signum)
            try:
                signal.signal(signum, self._manejar_senal)
            except ValueError:
                del self._manejadores_senales[signum]
                raise

    def _restaurar_senales(self) -> list[Exception]:
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
        lock_file = self._lock_file
        self._lock_file = None
        if lock_file is not None:
            lock_file.close()

    def _manejar_senal(self, signum: int, _frame: FrameType | None) -> None:
        """Callback ejecutado por el SO al recibir una señal de terminación."""
        del _frame
        if self._deteniendo:
            return
        try:
            logger.info("Señal %s recibida; iniciando apagado ordenado", signum)
        finally:
            self.detener()
        raise KeyboardInterrupt

    def iniciar(self) -> None:
        if self.en_ejecucion:
            return

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
                for tarea in reversed(tuple(self.tareas_cierre)):
                    try:
                        tarea()
                    except Exception as exc:  # noqa: BLE001 - run every shutdown task
                        errores.append(exc)
        finally:
            errores.extend(self._restaurar_senales())
            try:
                self._liberar_candado()
            except OSError as exc:
                errores.append(exc)
            self._deteniendo = False

        for error in errores[1:]:
            logger.error(
                "Error adicional durante el apagado",
                exc_info=(type(error), error, error.__traceback__),
            )
        if errores:
            raise errores[0]
