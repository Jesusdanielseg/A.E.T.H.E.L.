import errno
import os
import signal
from types import FrameType, SimpleNamespace

import pytest

from src.core import lifecycle

SignalHandler = lifecycle._SignalHandler


@pytest.fixture
def fake_signals(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[int, SignalHandler]:
    handlers: dict[int, SignalHandler] = {}

    def getsignal(signum: int) -> SignalHandler:
        return handlers.get(signum, signal.SIG_DFL)

    def set_signal(signum: int, handler: SignalHandler) -> SignalHandler:
        previous = getsignal(signum)
        handlers[signum] = handler
        return previous

    monkeypatch.setattr(signal, "getsignal", getsignal)
    monkeypatch.setattr(signal, "signal", set_signal)
    return handlers


def test_start_and_stop_manage_lock_signals_and_tasks(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    other_manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    completed: list[str] = []
    manager.registrar_tarea_cierre(lambda: completed.append("first"))
    manager.registrar_tarea_cierre(lambda: completed.append("second"))

    manager.iniciar()
    assert manager.en_ejecucion
    assert fake_signals[signal.SIGINT] == manager._manejar_senal
    assert fake_signals[signal.SIGTERM] == manager._manejar_senal
    with pytest.raises(RuntimeError, match="ya se encuentra en ejecución"):
        other_manager.iniciar()

    manager.detener()
    manager.detener()

    assert completed == ["second", "first"]
    assert not manager.en_ejecucion
    assert manager._lock_file is None
    assert fake_signals[signal.SIGINT] == signal.SIG_DFL
    assert fake_signals[signal.SIGTERM] == signal.SIG_DFL
    other_manager.iniciar()
    other_manager.detener()


def test_stop_runs_remaining_tasks_and_releases_lock_after_task_error(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    other_manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    completed: list[str] = []

    def fail() -> None:
        raise ValueError("cleanup failed")

    manager.registrar_tarea_cierre(lambda: completed.append("first"))
    manager.registrar_tarea_cierre(fail)
    manager.registrar_tarea_cierre(lambda: completed.append("last"))
    manager.iniciar()

    with pytest.raises(ValueError, match="cleanup failed"):
        manager.detener()

    assert completed == ["last", "first"]
    assert not manager.en_ejecucion
    assert fake_signals[signal.SIGINT] == signal.SIG_DFL
    assert fake_signals[signal.SIGTERM] == signal.SIG_DFL
    other_manager.iniciar()
    other_manager.detener()


def test_start_rolls_back_lock_and_signals_when_registration_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    other_manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    original_set_signal = signal.signal

    def fail_sigterm_registration(
        signum: int, handler: SignalHandler
    ) -> SignalHandler:
        if signum == signal.SIGTERM and handler == manager._manejar_senal:
            raise ValueError("signal registration failed")
        return original_set_signal(signum, handler)

    monkeypatch.setattr(signal, "signal", fail_sigterm_registration)

    with pytest.raises(ValueError, match="signal registration failed"):
        manager.iniciar()

    assert not manager.en_ejecucion
    assert manager._lock_file is None
    assert fake_signals[signal.SIGINT] == signal.SIG_DFL
    other_manager.iniciar()
    other_manager.detener()


def test_windows_lock_path_creates_and_locks_a_byte(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    locked: list[tuple[int, int, int]] = []
    windows_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        locking=lambda fd, mode, count: locked.append((fd, mode, count)),
    )
    monkeypatch.setattr(
        lifecycle, "os", SimpleNamespace(name="nt", SEEK_END=os.SEEK_END)
    )
    monkeypatch.setattr(lifecycle, "msvcrt", windows_msvcrt, raising=False)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")

    manager._adquirir_candado()

    assert manager._lock_file is not None
    assert manager._lock_file.read() == "\0"
    assert len(locked) == 1
    manager._liberar_candado()


def test_windows_lock_contention_is_reported_as_already_running(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_to_lock(_fd: int, _mode: int, _count: int) -> None:
        raise OSError(errno.EACCES, "lock held")

    monkeypatch.setattr(
        lifecycle, "os", SimpleNamespace(name="nt", SEEK_END=os.SEEK_END)
    )
    monkeypatch.setattr(
        lifecycle,
        "msvcrt",
        SimpleNamespace(LK_NBLCK=1, locking=fail_to_lock),
        raising=False,
    )
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")

    with pytest.raises(RuntimeError, match="ya se encuentra en ejecución"):
        manager._adquirir_candado()

    assert manager._lock_file is None


def test_original_signal_handlers_are_restored(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)

    def previous_handler(_signum: int, _frame: FrameType | None) -> None:
        return None

    fake_signals[signal.SIGINT] = previous_handler
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")

    manager.iniciar()
    manager.detener()

    assert fake_signals[signal.SIGINT] is previous_handler
    assert fake_signals[signal.SIGTERM] == signal.SIG_DFL


def test_signal_restore_failure_keeps_handler_for_retry_and_releases_lock(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    other_manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    original_set_signal = signal.signal
    fail_once = True

    def fail_first_sigterm_restore(
        signum: int, handler: SignalHandler
    ) -> SignalHandler:
        nonlocal fail_once
        if signum == signal.SIGTERM and handler == signal.SIG_DFL and fail_once:
            fail_once = False
            raise ValueError("signal restore failed")
        return original_set_signal(signum, handler)

    monkeypatch.setattr(signal, "signal", fail_first_sigterm_restore)
    manager.iniciar()

    with pytest.raises(ValueError, match="signal restore failed"):
        manager.detener()

    assert manager._lock_file is None
    assert signal.SIGTERM in manager._manejadores_senales
    manager.detener()
    assert not manager._manejadores_senales
    other_manager.iniciar()
    other_manager.detener()


def test_signal_logging_failure_does_not_skip_shutdown(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    other_manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    manager.iniciar()
    original_info = lifecycle.logger.info

    def fail_logging(*_args: object) -> None:
        raise RuntimeError("logging failed")

    monkeypatch.setattr(lifecycle.logger, "info", fail_logging)
    with pytest.raises(RuntimeError, match="logging failed"):
        manager._manejar_senal(signal.SIGTERM, None)

    assert not manager.en_ejecucion
    assert manager._lock_file is None
    assert fake_signals[signal.SIGINT] == signal.SIG_DFL
    assert fake_signals[signal.SIGTERM] == signal.SIG_DFL
    monkeypatch.setattr(lifecycle.logger, "info", original_info)
    other_manager.iniciar()
    other_manager.detener()


def test_context_manager_stops_on_exit_and_preserves_body_exception(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    fake_signals: dict[int, SignalHandler],
) -> None:
    monkeypatch.setattr(lifecycle.config, "validar", lambda: True)
    manager = lifecycle.LifecycleManager(tmp_path / "aethel.lock")
    completed: list[str] = []

    def fail_cleanup() -> None:
        raise RuntimeError("cleanup failed")

    manager.registrar_tarea_cierre(lambda: completed.append("closed"))
    manager.registrar_tarea_cierre(fail_cleanup)

    with pytest.raises(ValueError, match="body failed"), manager:
        assert manager.en_ejecucion
        raise ValueError("body failed")

    assert completed == ["closed"]
    assert not manager.en_ejecucion
