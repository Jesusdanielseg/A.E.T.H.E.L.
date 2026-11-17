import logging

import pytest

from src import main
from src.core.exceptions import CriticalError
from src.core.llm import GestorPresupuesto


def test_main_checks_health_then_starts_cli_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    controller = object()
    captured: dict[str, object] = {}

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
    def create_client(**kwargs: object) -> object:
        captured["client_kwargs"] = kwargs
        events.append("construct client")
        return object()

    def create_controller(**kwargs: object) -> object:
        captured["controller_kwargs"] = kwargs
        events.append("construct controller")
        return controller

    monkeypatch.setattr(main, "GeminiClient", create_client)
    monkeypatch.setattr(main, "ControladorCentral", create_controller)
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
        "health strict=True",
        "construct client",
        "construct controller",
        "construct cli",
        "start lifecycle",
        "execute cli",
        "stop lifecycle",
    ]
    client_kwargs = captured["client_kwargs"]
    assert isinstance(client_kwargs, dict)
    assert client_kwargs["modelo"] == main.config.AI_MODEL
    assert client_kwargs["modelos_fallback"] == main.config.AI_FALLBACK_MODELS

    controller_kwargs = captured["controller_kwargs"]
    assert isinstance(controller_kwargs, dict)
    assert controller_kwargs["proveedor_llm"] is not None
    presupuesto = controller_kwargs["presupuesto"]
    assert isinstance(presupuesto, GestorPresupuesto)
    assert presupuesto.limite_usd == 0.50


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
    monkeypatch.setattr(main, "GeminiClient", lambda **_kwargs: object())
    monkeypatch.setattr(
        main, "ControladorCentral", lambda **_kwargs: object()
    )
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


@pytest.mark.parametrize("failure_stage", ["client", "controller"])
def test_main_cleans_up_when_composition_root_fails(
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    events: list[str] = []

    class FakeLifecycle:
        def __init__(self) -> None:
            events.append("construct")

        def iniciar(self) -> None:
            pytest.fail("El lifecycle no debe iniciar si falla la composición")

        def detener(self) -> None:
            events.append("stop")

    def create_client(**_kwargs: object) -> object:
        events.append("client")
        if failure_stage == "client":
            raise CriticalError("client unavailable")
        return object()

    def create_controller(**_kwargs: object) -> object:
        events.append("controller")
        if failure_stage == "controller":
            raise ValueError("invalid controller")
        return object()

    monkeypatch.setattr(main, "configurar_logging", lambda: None)
    monkeypatch.setattr(main, "LifecycleManager", FakeLifecycle)
    monkeypatch.setattr(main, "GeminiClient", create_client)
    monkeypatch.setattr(main, "ControladorCentral", create_controller)
    monkeypatch.setattr(main, "verificar_salud", lambda **_kwargs: None)

    assert main.main() == 1
    assert events == (
        ["construct", "client", "stop"]
        if failure_stage == "client"
        else ["construct", "client", "controller", "stop"]
    )


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
    monkeypatch.setattr(main, "GeminiClient", lambda **_kwargs: object())
    monkeypatch.setattr(
        main, "ControladorCentral", lambda **_kwargs: object()
    )
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
    monkeypatch.setattr(main, "GeminiClient", lambda **_kwargs: object())
    monkeypatch.setattr(
        main, "ControladorCentral", lambda **_kwargs: object()
    )
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
    monkeypatch.setattr(main, "GeminiClient", lambda **_kwargs: object())
    monkeypatch.setattr(
        main, "ControladorCentral", lambda **_kwargs: object()
    )
    monkeypatch.setattr(main, "InterfazCLI", FakeCLI)
    monkeypatch.setattr(main, "verificar_salud", lambda **_kwargs: None)

    with pytest.raises(LookupError, match="unexpected cli failure"):
        main.main()

    assert "cleanup failure" in caplog.text
