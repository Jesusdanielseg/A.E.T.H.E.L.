import logging
from collections import namedtuple
from pathlib import Path
from types import MappingProxyType

import pytest

from src.core import health
from src.core.exceptions import CriticalError

DiskUsage = namedtuple("DiskUsage", "total used free")


def test_health_report_is_healthy_when_all_checks_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db_path = tmp_path / "database" / "aethel.db"
    monkeypatch.setattr(health.config, "DB_PATH", str(db_path))
    monkeypatch.setattr(health.config, "AI_API_KEY", "available-key")
    monkeypatch.setattr(health, "__file__", str(tmp_path / "src/core/health.py"))
    monkeypatch.setattr(health.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(
        health.shutil,
        "disk_usage",
        lambda _path: DiskUsage(1024**3, 512 * 1024**2, 512 * 1024**2),
    )
    caplog.set_level(logging.INFO)

    report = health.verificar_salud()

    assert report.estado == "healthy"
    assert report.componentes == {
        "almacenamiento": True,
        "logs": True,
        "api_key": True,
    }
    assert set(report.detalles) == set(report.componentes)
    assert all(detail == "OK" for detail in report.detalles.values())
    assert "healthy" in caplog.text
    assert isinstance(report.componentes, MappingProxyType)
    assert isinstance(report.detalles, MappingProxyType)


def test_missing_api_key_degrades_without_raising(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(health.config, "DB_PATH", str(tmp_path / "db" / "aethel.db"))
    monkeypatch.setattr(health.config, "AI_API_KEY", " ")
    monkeypatch.setattr(health, "__file__", str(tmp_path / "src/core/health.py"))
    monkeypatch.setattr(health.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(
        health.shutil,
        "disk_usage",
        lambda _path: DiskUsage(1024**3, 512 * 1024**2, 512 * 1024**2),
    )
    caplog.set_level(logging.WARNING)

    report = health.verificar_salud(strict=True)

    assert report.estado == "degraded"
    assert report.componentes["api_key"] is False
    assert report.detalles["api_key"] == "AI_API_KEY no está configurada"
    assert "degraded" in caplog.text


@pytest.mark.parametrize("failed_component", ["storage", "logs"])
def test_unhealthy_state_raises_critical_error_in_strict_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_component: str,
) -> None:
    monkeypatch.setattr(health.config, "DB_PATH", str(tmp_path / "db" / "aethel.db"))
    monkeypatch.setattr(health.config, "AI_API_KEY", "available-key")
    monkeypatch.setattr(health, "__file__", str(tmp_path / "src/core/health.py"))
    monkeypatch.setattr(
        health.os,
        "access",
        lambda path, _mode: not (
            failed_component == "logs" and Path(path).name == "logs"
        ),
    )
    monkeypatch.setattr(
        health.shutil,
        "disk_usage",
        lambda _path: DiskUsage(1024**3, 1024**3, 0)
        if failed_component == "storage"
        else DiskUsage(1024**3, 512 * 1024**2, 512 * 1024**2),
    )

    with pytest.raises(CriticalError, match="Fallo crítico"):
        health.verificar_salud(strict=True)


def test_unhealthy_state_is_reported_without_raising_in_non_strict_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health.config, "DB_PATH", str(tmp_path / "db" / "aethel.db"))
    monkeypatch.setattr(health.config, "AI_API_KEY", "available-key")
    monkeypatch.setattr(health, "__file__", str(tmp_path / "src/core/health.py"))
    monkeypatch.setattr(health.os, "access", lambda _path, _mode: False)

    report = health.verificar_salud()

    assert report.estado == "unhealthy"
    assert report.componentes["almacenamiento"] is False
    assert report.componentes["logs"] is False


def test_writable_check_probes_real_file_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "readonly"
    directory.mkdir()
    monkeypatch.setattr(health.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(
        health.tempfile,
        "NamedTemporaryFile",
        lambda **_kwargs: (_ for _ in ()).throw(PermissionError("write denied")),
    )

    assert not health._es_escribible(directory)


def test_disk_space_check_rejects_negative_threshold(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        health._tiene_espacio_disco(tmp_path, minimo_mb=-1)
