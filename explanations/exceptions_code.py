"""Copia didáctica de src/core/exceptions.py; no es el módulo importado."""


class AethelError(Exception):
    """Raíz de los errores controlados propios de la aplicación."""

    def __init__(self, mensaje: str, detalle: str | None = None) -> None:
        # Guardamos las dos partes como atributos para que el llamador pueda
        # mostrarlas o procesarlas por separado.
        self.mensaje = mensaje
        self.detalle = detalle

        # Exception conserva ambos argumentos; __str__ define la presentación.
        super().__init__(mensaje, detalle)

    def __str__(self) -> str:
        # Añadimos el detalle solo si el usuario proporcionó uno.
        return f"{self.mensaje} ({self.detalle})" if self.detalle else self.mensaje


class RecoverableError(AethelError):
    """Base para fallos puntuales después de los cuales el asistente puede seguir."""


class CriticalError(AethelError):
    """Base para fallos que requieren abortar el arranque o apagar el sistema."""


class ConfigurationError(CriticalError):
    """Configuración ausente o inválida: el sistema no debe arrancar."""


class InstanceLockError(CriticalError):
    """Candado de instancia ocupado o imposible de crear."""


class ExternalServiceError(RecoverableError):
    """Fallo temporal de red o de un servicio externo."""


class ToolExecutionError(RecoverableError):
    """Falló una herramienta individual, no necesariamente el asistente completo."""
