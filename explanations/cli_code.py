"""Copia didáctica de src/interfaces/cli.py; no es el módulo importado.

Estado 04.5: copia desactualizada. Faltan /memoria, /limpiar, /modelo,
/estado y sus métodos. Ver explanations/14-auditoria-explanations-04-5.md.
"""

import logging

from src.core.controller import ControladorCentral, MensajeEntrada
from src.core.exceptions import RecoverableError

# El logger de la interfaz distingue sus eventos de los del núcleo.
logger = logging.getLogger(__name__)


class InterfazCLI:
    """Traduce líneas de consola a contratos del controlador y muestra respuestas."""

    # El frozenset es inmutable y las búsquedas de comandos son rápidas.
    COMANDOS_SALIDA: frozenset[str] = frozenset({"salir", "exit", "quit"})

    def __init__(self, controlador: ControladorCentral) -> None:
        # Inyección: la interfaz usa un controlador recibido, no crea uno propio.
        self.controlador = controlador

    def _leer_entrada(self) -> str | None:
        """Lee consola; convierte EOF/Ctrl+C/señal en una salida limpia."""
        try:
            return input("\nTú > ")
        except (KeyboardInterrupt, EOFError):
            # KeyboardInterrupt también lo lanza LifecycleManager tras SIGTERM.
            print()
            return None

    def ejecutar(self) -> None:
        """Atiende entradas hasta recibir un comando de salida o fin de entrada."""
        print("A.E.T.H.E.L. está listo. Escribe 'salir' para terminar.")
        while True:
            entrada = self._leer_entrada()
            if entrada is None or entrada.strip().lower() in self.COMANDOS_SALIDA:
                logger.info("Cerrando interfaz CLI por solicitud del usuario")
                break

            try:
                # La interfaz identifica su origen y delega la lógica al núcleo.
                mensaje = MensajeEntrada(contenido=entrada, origen="cli")
                respuesta = self.controlador.procesar_mensaje(mensaje)
                print(
                    f"A.E.T.H.E.L. [{respuesta.request_id}] > "
                    f"{respuesta.contenido}"
                )
            except RecoverableError as exc:
                # Un mensaje malo no termina la sesión; se pide el siguiente.
                logger.warning("Entrada rechazada: %s", exc.mensaje)
                print(f"[Aviso] {exc.mensaje}")
