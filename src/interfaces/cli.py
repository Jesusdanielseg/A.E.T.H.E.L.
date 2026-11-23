import logging

from src.core.controller import ControladorCentral, MensajeEntrada
from src.core.exceptions import RecoverableError

logger = logging.getLogger(__name__)


class InterfazCLI:
    """Interfaz interna por consola para interactuar con A.E.T.H.E.L."""

    COMANDOS_SALIDA: frozenset[str] = frozenset(
        {"salir", "exit", "quit", "/salir", "/exit", "/quit"}
    )

    def __init__(self, controlador: ControladorCentral) -> None:
        self.controlador = controlador
        self.contexto = controlador.contexto

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
            comando = entrada.strip().lower() if entrada is not None else ""
            if entrada is None or comando in self.COMANDOS_SALIDA:
                logger.info("Cerrando interfaz CLI por solicitud del usuario")
                print("A.E.T.H.E.L. cerrado.", flush=True)
                break
            if comando == "/memoria":
                self._mostrar_memoria()
                continue
            if comando == "/limpiar":
                self._limpiar_memoria()
                continue
            if comando == "/modelo":
                self._mostrar_modelo()
                continue

            try:
                mensaje = MensajeEntrada(contenido=entrada, origen="cli")
                respuesta = self.controlador.procesar_mensaje(mensaje)
                print(f"A.E.T.H.E.L. [{respuesta.request_id}] > {respuesta.contenido}")
            except RecoverableError as exc:
                logger.warning("Entrada rechazada: %s", exc.mensaje)
                print(f"[Aviso] {exc.mensaje}")

    def _mostrar_memoria(self) -> None:
        if self.contexto is None:
            print("[Memoria] Desactivada.")
            return
        print(
            f"[Memoria] sesión={self.contexto.session_id} "
            f"mensajes={len(self.contexto.messages)} "
            f"resumen={'sí' if self.contexto.summary else 'no'}"
        )

    def _limpiar_memoria(self) -> None:
        if self.contexto is None:
            print("[Memoria] Desactivada.")
            return
        self.contexto.clear()
        print("[Memoria] Sesión limpiada.")

    def _mostrar_modelo(self) -> None:
        provider = self.controlador.proveedor_llm
        name = getattr(provider, "last_provider", "") or provider.__class__.__name__
        latency = getattr(provider, "last_latency_ms", 0.0)
        print(f"[Modelo] {name} | latencia={latency:.1f} ms")
