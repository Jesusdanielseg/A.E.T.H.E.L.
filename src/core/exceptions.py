class AethelError(Exception):
    """Excepción base para todos los errores controlados de A.E.T.H.E.L."""

    def __init__(self, mensaje: str, detalle: str | None = None) -> None:
        self.mensaje = mensaje
        self.detalle = detalle
        super().__init__(mensaje, detalle)

    def __str__(self) -> str:
        return f"{self.mensaje} ({self.detalle})" if self.detalle else self.mensaje


class RecoverableError(AethelError):
    """Errores temporales o de operación que no requieren detener el asistente."""


class CriticalError(AethelError):
    """Errores graves que comprometen el sistema y exigen apagado ordenado."""


class ConfigurationError(CriticalError):
    """Variables de entorno faltantes o valores inválidos en la configuración."""


class InstanceLockError(CriticalError):
    """Otra instancia está activa o no se puede crear el archivo de bloqueo."""


class ExternalServiceError(RecoverableError):
    """Fallos temporales al consultar servicios externos."""


class ToolExecutionError(RecoverableError):
    """Fallo de una herramienta o tarea puntual sin afectar al núcleo."""
