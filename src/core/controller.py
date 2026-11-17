import logging
from dataclasses import dataclass

from src.core.exceptions import RecoverableError
from src.core.llm import GestorPresupuesto, ProveedorLLM
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
    simulada: bool = False


class ControladorCentral:
    """Orquesta validación, presupuesto y consulta al modelo."""

    MAX_CARACTERES: int = 2000

    def __init__(
        self,
        proveedor_llm: ProveedorLLM,
        presupuesto: GestorPresupuesto,
    ) -> None:
        self.proveedor_llm = proveedor_llm
        self.presupuesto = presupuesto

    def procesar_mensaje(self, mensaje: MensajeEntrada) -> RespuestaSalida:
        """Ejecuta el flujo completo de atención para un mensaje entrante."""
        request_id = establecer_request_id()
        logger.info("Mensaje recibido desde '%s'", mensaje.origen)

        texto_limpio = self._validar_mensaje(mensaje)
        if texto_limpio.lower() == "ping":
            return RespuestaSalida(
                request_id=request_id,
                contenido="pong (núcleo operativo)",
                simulada=True,
            )

        self.presupuesto.verificar_disponibilidad()
        respuesta_llm = self.proveedor_llm.generar_respuesta(texto_limpio)
        self.presupuesto.registrar_uso(respuesta_llm)

        logger.info(
            "Respuesta generada correctamente (%d caracteres)",
            len(respuesta_llm.contenido),
        )
        return RespuestaSalida(
            request_id=request_id,
            contenido=respuesta_llm.contenido,
            simulada=False,
        )

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
