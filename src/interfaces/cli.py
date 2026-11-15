import logging

from src.core.controller import ControladorCentral, MensajeEntrada
from src.core.exceptions import RecoverableError

logger = logging.getLogger(__name__)


class InterfazCLI:
    """Interfaz interna por consola para interactuar con A.E.T.H.E.L."""

    COMANDOS_SALIDA: frozenset[str] = frozenset({"salir", "exit", "quit"})

    def __init__(self, controlador: ControladorCentral) -> None:
        self.controlador = controlador

    def _leer_entrada(self) -> str | None:
        """Lee texto desde consola y captura interrupciones de teclado."""
        try:
            return input("\nTú > ")
        except (KeyboardInterrupt, EOFError):
            print()
            return None

    def ejecutar(self) -> None:
        """Lee y procesa mensajes hasta que el usuario solicite salir."""
        print("A.E.T.H.E.L. está listo. Escribe 'salir' para terminar.")
        while True:
            entrada = self._leer_entrada()
            if entrada is None or entrada.strip().lower() in self.COMANDOS_SALIDA:
                logger.info("Cerrando interfaz CLI por solicitud del usuario")
                break

            try:
                mensaje = MensajeEntrada(contenido=entrada, origen="cli")
                respuesta = self.controlador.procesar_mensaje(mensaje)
                print(
                    f"A.E.T.H.E.L. [{respuesta.request_id}] > "
                    f"{respuesta.contenido}"
                )
            except RecoverableError as exc:
                logger.warning("Entrada rechazada: %s", exc.mensaje)
                print(f"[Aviso] {exc.mensaje}")
