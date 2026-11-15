import pickle

import pytest

from src.core.exceptions import (
    AethelError,
    ConfigurationError,
    CriticalError,
    ExternalServiceError,
    InstanceLockError,
    RecoverableError,
    ToolExecutionError,
)


@pytest.mark.parametrize(
    ("error_type", "parent_type"),
    [
        (ConfigurationError, CriticalError),
        (InstanceLockError, CriticalError),
        (ExternalServiceError, RecoverableError),
        (ToolExecutionError, RecoverableError),
    ],
)
def test_domain_errors_have_the_expected_severity(
    error_type: type[AethelError], parent_type: type[AethelError]
) -> None:
    error = error_type("operation failed", "connection refused")

    assert isinstance(error, parent_type)
    assert isinstance(error, AethelError)
    assert error.mensaje == "operation failed"
    assert error.detalle == "connection refused"
    assert str(error) == "operation failed (connection refused)"


def test_aethel_error_without_detail_formats_as_message_only() -> None:
    error = AethelError("operation failed")

    assert error.args == ("operation failed", None)
    assert str(error) == "operation failed"


def test_aethel_error_preserves_message_and_detail_when_pickled() -> None:
    original = CriticalError("critical failure", "disk full")

    restored = pickle.loads(pickle.dumps(original))

    assert type(restored) is CriticalError
    assert restored.mensaje == original.mensaje
    assert restored.detalle == original.detalle
    assert str(restored) == str(original)
