"""Copia didáctica del controlador actual.

El módulo ejecutable es ``src/core/controller.py``. Esta copia se conserva
para explicar el flujo sin convertirse en una segunda implementación.

Estado 04.5: el flujo general coincide, pero faltan los logs de entrada y
salida y los argumentos nombrados de RespuestaSalida. Ver
explanations/14-auditoria-explanations-04-5.md.
"""

from dataclasses import dataclass

from src.context.manager import ContextManager
from src.core.exceptions import RecoverableError
from src.core.llm import GestorPresupuesto, ProveedorLLM
from src.core.logger import establecer_request_id


@dataclass(frozen=True)
class MensajeEntrada:
    """Texto recibido y origen de la petición."""

    contenido: str
    origen: str = "interfaz_interna"


@dataclass(frozen=True)
class RespuestaSalida:
    """Resultado público que la interfaz muestra al usuario."""

    request_id: str
    contenido: str
    simulada: bool = False


class ControladorCentral:
    """Coordina validación, memoria, presupuesto y proveedor LLM."""

    MAX_CARACTERES = 2000

    def __init__(
        self,
        proveedor_llm: ProveedorLLM,
        presupuesto: GestorPresupuesto,
        contexto: ContextManager | None = None,
    ) -> None:
        self.proveedor_llm = proveedor_llm
        self.presupuesto = presupuesto
        self.contexto = contexto

    def procesar_mensaje(self, mensaje: MensajeEntrada) -> RespuestaSalida:
        """Procesa una entrada y devuelve una respuesta normalizada."""
        request_id = establecer_request_id()
        texto = self._validar_mensaje(mensaje)
        if texto.lower() == "ping":
            return RespuestaSalida(request_id, "pong (núcleo operativo)", True)

        self.presupuesto.verificar_disponibilidad()
        if self.contexto is not None:
            prompt = self.contexto.build_prompt(texto)
            self.contexto.add_message("user", texto)
        else:
            prompt = texto

        respuesta = self.proveedor_llm.generar_respuesta(prompt)
        self.presupuesto.registrar_uso(respuesta)
        if self.contexto is not None:
            self.contexto.add_message("assistant", respuesta.contenido)
            self.contexto.compact(self.proveedor_llm)
        return RespuestaSalida(request_id, respuesta.contenido)

    def _validar_mensaje(self, mensaje: MensajeEntrada) -> str:
        """Recorta espacios y rechaza mensajes vacíos o demasiado largos."""
        texto = mensaje.contenido.strip()
        if not texto:
            raise RecoverableError("El mensaje no puede estar vacío.")
        if len(texto) > self.MAX_CARACTERES:
            raise RecoverableError(
                f"El mensaje excede el límite de {self.MAX_CARACTERES} caracteres."
            )
        return texto
