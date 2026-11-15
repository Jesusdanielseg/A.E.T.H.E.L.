import logging
from threading import Event

import pytest

from src import main


def test_main_waits_for_shutdown_and_runs_cleanup(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    events: list[str] = []

    class FakeLifecycle:
        en_ejecucion = False

        def registrar_tarea_cierre(self, task) -> None:
            if not hasattr(self, "tasks"):
                self.tasks = []
            self.tasks.append(task)

        def iniciar(self) -> None:
            events.append("start")
            self.en_ejecucion = True

        def detener(self) -> None:
            if not self.en_ejecucion:
                return
            events.append("stop")
            self.en_ejecucion = False
            for task in reversed(self.tasks):
                task()

    class FakeEvent:
        def __init__(self) -> None:
            self.event = Event()

        def set(self) -> None:
            events.append("wake")
            self.event.set()

        def wait(self) -> None:
            events.append("wait")
            lifecycle.detener()
            self.event.wait()

    lifecycle = FakeLifecycle()
    monkeypatch.setattr(main, "Event", FakeEvent)
    monkeypatch.setattr(main, "LifecycleManager", lambda: lifecycle)
    caplog.set_level(logging.INFO)

    assert main.main() == 0
    assert events == ["start", "wait", "stop", "wake"]
    assert "Limpiando recursos temporales..." in caplog.text


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (RuntimeError("already running"), "already running"),
        (ValueError("invalid configuration"), "invalid configuration"),
        (OSError("lock file unavailable"), "lock file unavailable"),
    ],
)
def test_main_reports_startup_errors_and_stops(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    message: str,
) -> None:
    events: list[str] = []

    class FakeLifecycle:
        en_ejecucion = False

        def registrar_tarea_cierre(self, _task) -> None:
            pass

        def iniciar(self) -> None:
            events.append("start")
            raise error

        def detener(self) -> None:
            events.append("stop")

    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    caplog.set_level(logging.ERROR)

    assert main.main() == 1
    assert events == ["start", "stop"]
    assert message in caplog.text


def test_main_does_not_miss_shutdown_before_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeLifecycle:
        en_ejecucion = False

        def registrar_tarea_cierre(self, task) -> None:
            self.task = task

        def iniciar(self) -> None:
            self.en_ejecucion = True
            self.task()
            self.en_ejecucion = False

        def detener(self) -> None:
            events.append("stop")

    lifecycle = FakeLifecycle()
    monkeypatch.setattr(main, "LifecycleManager", lambda: lifecycle)
    real_event = Event

    class AlreadySetEvent:
        def __init__(self) -> None:
            self.event = real_event()

        def set(self) -> None:
            self.event.set()

        def wait(self) -> None:
            events.append("wait")
            assert self.event.is_set()

    monkeypatch.setattr(main, "Event", AlreadySetEvent)

    assert main.main() == 0
    assert "wait" not in events
    assert events == ["stop"]
