import logging

import pytest

from src import main
from src.core.exceptions import CriticalError


def test_main_checks_health_then_starts_cli_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    controller = object()

    class FakeLifecycle:
        def __init__(self) -> None:
            events.append("construct lifecycle")

        def iniciar(self) -> None:
            events.append("start lifecycle")

        def detener(self) -> None:
            events.append("stop lifecycle")

    class FakeCLI:
        def __init__(self, received_controller: object) -> None:
            assert received_controller is controller
            events.append("construct cli")

        def ejecutar(self) -> None:
            events.append("execute cli")

    monkeypatch.setattr(main, "configurar_logging", lambda: events.append("logging"))
    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    monkeypatch.setattr(main, "ControladorCentral", lambda: controller)
    monkeypatch.setattr(
        main,
        "InterfazCLI",
        FakeCLI,
    )
    monkeypatch.setattr(
        main,
        "verificar_salud",
        lambda *, strict: events.append(f"health strict={strict}"),
    )

    assert main.main() == 0
    assert events == [
        "logging",
        "construct lifecycle",
        "construct cli",
        "start lifecycle",
        "health strict=True",
        "execute cli",
        "stop lifecycle",
    ]


@pytest.mark.parametrize(
    ("failure_stage", "error", "expected_return"),
    [
        ("health", CriticalError("health failed"), 1),
        ("start", CriticalError("start failed"), 1),
        ("start", RuntimeError("instance already active"), 1),
        ("start", ValueError("invalid configuration"), 1),
        ("start", OSError("lock file unavailable"), 1),
    ],
)
def test_main_reports_startup_failure_and_always_stops(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure_stage: str,
    error: Exception,
    expected_return: int,
) -> None:
    events: list[str] = []

    class FakeLifecycle:
        def iniciar(self) -> None:
            events.append("start")
            if failure_stage == "start":
                raise error

        def detener(self) -> None:
            events.append("stop")

    class FakeCLI:
        def __init__(self, _controller: object) -> None:
            pass

        def ejecutar(self) -> None:
            events.append("execute cli")

    def check_health(*, strict: bool) -> None:
        assert strict
        if failure_stage == "health":
            raise error

    monkeypatch.setattr(main, "configurar_logging", lambda: None)
    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    monkeypatch.setattr(main, "ControladorCentral", object)
    monkeypatch.setattr(main, "InterfazCLI", FakeCLI)
    monkeypatch.setattr(main, "verificar_salud", check_health)
    caplog.set_level(logging.ERROR)

    assert main.main() == expected_return
    assert events[-1] == "stop"
    assert str(error) in caplog.text


def test_main_returns_error_if_logging_setup_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    lifecycle_created = False

    def fail_logging() -> None:
        raise OSError("log directory unavailable")

    def create_lifecycle():
        nonlocal lifecycle_created
        lifecycle_created = True
        raise AssertionError("Lifecycle must not start when logging setup fails")

    monkeypatch.setattr(main, "configurar_logging", fail_logging)
    monkeypatch.setattr(main, "LifecycleManager", create_lifecycle)
    caplog.set_level(logging.ERROR)

    assert main.main() == 1
    assert not lifecycle_created
    assert "log directory unavailable" in caplog.text


def test_main_returns_error_if_shutdown_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeLifecycle:
        def iniciar(self) -> None:
            pass

        def detener(self) -> None:
            raise OSError("lock release failed")

    class FakeCLI:
        def __init__(self, _controller: object) -> None:
            pass

        def ejecutar(self) -> None:
            pass

    monkeypatch.setattr(main, "configurar_logging", lambda: None)
    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    monkeypatch.setattr(main, "ControladorCentral", object)
    monkeypatch.setattr(main, "InterfazCLI", FakeCLI)
    monkeypatch.setattr(main, "verificar_salud", lambda **_kwargs: None)
    caplog.set_level(logging.ERROR)

    assert main.main() == 1
    assert "lock release failed" in caplog.text


def test_main_handles_signal_interrupt_as_clean_shutdown(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    events: list[str] = []

    class FakeLifecycle:
        def iniciar(self) -> None:
            events.append("start")
            raise KeyboardInterrupt

        def detener(self) -> None:
            events.append("stop")

    class FakeCLI:
        def __init__(self, _controller: object) -> None:
            pass

        def ejecutar(self) -> None:
            pytest.fail("CLI should not run after an interrupted start")

    monkeypatch.setattr(main, "configurar_logging", lambda: None)
    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    monkeypatch.setattr(main, "ControladorCentral", object)
    monkeypatch.setattr(main, "InterfazCLI", FakeCLI)
    monkeypatch.setattr(main, "verificar_salud", lambda **_kwargs: None)
    caplog.set_level(logging.INFO)

    assert main.main() == 0
    assert events == ["start", "stop"]
    assert "cierre ordenado" in caplog.text


def test_main_preserves_unexpected_error_if_shutdown_also_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FakeLifecycle:
        def iniciar(self) -> None:
            pass

        def detener(self) -> None:
            raise OSError("cleanup failure")

    class FakeCLI:
        def __init__(self, _controller: object) -> None:
            pass

        def ejecutar(self) -> None:
            raise LookupError("unexpected cli failure")

    monkeypatch.setattr(main, "configurar_logging", lambda: None)
    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    monkeypatch.setattr(main, "ControladorCentral", object)
    monkeypatch.setattr(main, "InterfazCLI", FakeCLI)
    monkeypatch.setattr(main, "verificar_salud", lambda **_kwargs: None)

    with pytest.raises(LookupError, match="unexpected cli failure"):
        main.main()

    assert "cleanup failure" in caplog.text
