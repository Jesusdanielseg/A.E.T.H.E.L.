import logging
from dataclasses import dataclass

from src.core.exceptions import RecoverableError
from src.core.logger import establecer_request_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MensajeEntrada:
    """Representa una petición cruda enviada desde una interfaz."""

    contenido: str
    origen: str = "interfaz_interna"


@dataclass(frozen=True)
class RespuestaSalida:
    """Representa la respuesta procesada que se devolverá al usuario."""

    request_id: str
    contenido: str
    simulada: bool = True


class ControladorCentral:
    """Orquesta la validación, procesamiento y registro de cada interacción."""

    MAX_CARACTERES: int = 2000

    def procesar_mensaje(self, mensaje: MensajeEntrada) -> RespuestaSalida:
        """Ejecuta el flujo completo de atención para un mensaje entrante."""
        request_id = establecer_request_id()
        logger.info("Mensaje recibido desde '%s'", mensaje.origen)

        texto_limpio = self._validar_mensaje(mensaje)
        respuesta_texto = self._generar_respuesta_simulada(texto_limpio)

        logger.info(
            "Respuesta generada correctamente (%d caracteres)",
            len(respuesta_texto),
        )
        return RespuestaSalida(request_id=request_id, contenido=respuesta_texto)

    def _validar_mensaje(self, mensaje: MensajeEntrada) -> str:
        """Limpia y valida el contenido antes de procesarlo."""
        texto = mensaje.contenido.strip()
        if not texto:
            raise RecoverableError("El mensaje no puede estar vacío.")
        if len(texto) > self.MAX_CARACTERES:
            raise RecoverableError(
                f"El mensaje excede el límite de {self.MAX_CARACTERES} caracteres."
            )
        return texto

    def _generar_respuesta_simulada(self, texto: str) -> str:
        """Devuelve una respuesta de prueba sin consultar un modelo externo."""
        if texto.lower() == "ping":
            return "pong (núcleo operativo)"
        return f"[A.E.T.H.E.L. - Simulación] Procesado: '{texto}'"
