import logging
import math
import random
import time
from collections.abc import Sequence

from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.core.config import config
from src.core.exceptions import CriticalError, ExternalServiceError
from src.core.llm import GestorPresupuesto, RespuestaLLM

logger = logging.getLogger(__name__)


class GeminiClient:
    """Adaptador de infraestructura para comunicarse con la API de Gemini."""

    PRECIO_ENTRADA_MILLON: float = 0.15
    PRECIO_SALIDA_MILLON: float = 0.60
    CODIGOS_REINTENTABLES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        modelo: str | None = None,
        modelos_fallback: Sequence[str] | None = None,
        timeout_segundos: int = 30,
        max_reintentos: int = 3,
        espera_base: float = 1.5,
        espera_maxima: float = 30.0,
        jitter: float = 0.1,
        presupuesto: GestorPresupuesto | None = None,
    ) -> None:
        if not config.AI_API_KEY.strip():
            raise CriticalError(
                "No se encontró AI_API_KEY para inicializar GeminiClient."
            )
        modelo_final = modelo if modelo is not None else config.AI_MODEL
        if not isinstance(modelo_final, str) or not modelo_final.strip():
            raise ValueError("El modelo de Gemini no puede estar vacío.")
        if not isinstance(timeout_segundos, int) or isinstance(
            timeout_segundos, bool
        ):
            raise TypeError("El timeout debe ser un entero.")
        if timeout_segundos <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")
        if not isinstance(max_reintentos, int) or isinstance(max_reintentos, bool):
            raise TypeError("max_reintentos debe ser un entero.")
        if max_reintentos < 1:
            raise ValueError("max_reintentos debe ser al menos 1.")
        if not isinstance(espera_base, (int, float)) or isinstance(
            espera_base, bool
        ):
            raise TypeError("La espera base debe ser numérica.")
        if not math.isfinite(espera_base) or espera_base < 0:
            raise ValueError(
                "La espera base debe ser un número finito no negativo."
            )
        if not isinstance(espera_maxima, (int, float)) or isinstance(
            espera_maxima, bool
        ):
            raise TypeError("La espera máxima debe ser numérica.")
        if not math.isfinite(espera_maxima) or espera_maxima < 0:
            raise ValueError(
                "La espera máxima debe ser un número finito no negativo."
            )
        if not isinstance(jitter, (int, float)) or isinstance(jitter, bool):
            raise TypeError("El jitter debe ser numérico.")
        if not math.isfinite(jitter) or jitter < 0:
            raise ValueError("El jitter debe ser un número finito no negativo.")

        fallbacks_configurados = (
            config.AI_FALLBACK_MODELS
            if modelos_fallback is None
            else modelos_fallback
        )
        fallbacks = tuple(modelo.strip() for modelo in fallbacks_configurados)
        if any(not modelo for modelo in fallbacks):
            raise ValueError("Los modelos fallback no pueden estar vacíos.")

        self.modelo = modelo_final.strip()
        self.modelos = tuple(dict.fromkeys((self.modelo, *fallbacks)))
        self.max_reintentos = max_reintentos
        self.espera_base = espera_base
        self.espera_maxima = float(espera_maxima)
        self.jitter = float(jitter)
        self.presupuesto = presupuesto
        self._client = genai.Client(
            api_key=config.AI_API_KEY,
            http_options=types.HttpOptions(timeout=timeout_segundos * 1000),
        )

    def _calcular_coste(self, tokens_entrada: int, tokens_salida: int) -> float:
        """Calcula el coste estimado en USD según los tokens consumidos."""
        coste_in = (tokens_entrada / 1_000_000) * self.PRECIO_ENTRADA_MILLON
        coste_out = (tokens_salida / 1_000_000) * self.PRECIO_SALIDA_MILLON
        return round(coste_in + coste_out, 6)

    def _ejecutar_peticion(self, modelo: str, mensaje: str) -> RespuestaLLM:
        """Realiza un único intento contra la API y empaqueta la respuesta."""
        respuesta = self._client.models.generate_content(
            model=modelo,
            contents=mensaje,
        )
        texto = respuesta.text
        if not isinstance(texto, str):
            raise ExternalServiceError(
                "Gemini devolvió una respuesta sin texto utilizable."
            )
        texto = texto.strip()
        if not texto:
            raise ExternalServiceError("El modelo devolvió una respuesta vacía.")

        usage = respuesta.usage_metadata
        tokens_in, tokens_out = self._extraer_tokens(usage)
        return RespuestaLLM(
            contenido=texto,
            modelo=modelo,
            tokens_entrada=tokens_in,
            tokens_salida=tokens_out,
            coste_usd=self._calcular_coste(tokens_in, tokens_out),
        )

    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        """Genera una respuesta con reintentos para fallos transitorios."""
        if not isinstance(mensaje, str):
            raise TypeError("El mensaje para Gemini debe ser texto.")
        if not mensaje.strip():
            raise ValueError("El mensaje para Gemini no puede estar vacío.")

        if self.presupuesto is not None:
            self.presupuesto.verificar_disponibilidad()

        ultimo_error: BaseException | None = None
        for modelo in self.modelos:
            for intento in range(self.max_reintentos):
                try:
                    respuesta = self._ejecutar_peticion(modelo, mensaje)
                    if self.presupuesto is not None:
                        self.presupuesto.registrar_uso(respuesta)
                    return respuesta
                except APIError as exc:
                    ultimo_error = exc
                    if exc.code in {401, 403}:
                        detalle = exc.message or str(exc)
                        raise CriticalError(
                            "Credenciales de Gemini inválidas o sin permisos.",
                            detalle,
                        ) from exc
                    es_fallback = exc.code in {404, 503, 504}
                    ultimo_intento = intento >= self.max_reintentos - 1
                    if exc.code not in self.CODIGOS_REINTENTABLES:
                        if es_fallback and modelo != self.modelos[-1]:
                            logger.warning(
                                "El modelo %s no está disponible; probando fallback",
                                modelo,
                            )
                            break
                        detalle = exc.message or str(exc)
                        raise ExternalServiceError(
                            "Fallo al comunicarse con Gemini.", detalle
                        ) from exc
                    if ultimo_intento:
                        if es_fallback and modelo != self.modelos[-1]:
                            logger.warning(
                                "El modelo %s sigue no disponible; probando fallback",
                                modelo,
                            )
                            break
                        detalle = exc.message or str(exc)
                        raise ExternalServiceError(
                            "Fallo al comunicarse con Gemini.", detalle
                        ) from exc
                    self._esperar_reintento(intento, exc.code)
                except (TimeoutError, ConnectionError, OSError) as exc:
                    ultimo_error = exc
                    if intento >= self.max_reintentos - 1:
                        if modelo != self.modelos[-1]:
                            logger.warning(
                                "Red no disponible para %s; probando fallback",
                                modelo,
                            )
                            break
                        raise ExternalServiceError(
                            "Tiempo de espera agotado o error de red con Gemini."
                        ) from exc
                    self._esperar_reintento(intento, None)

        raise ExternalServiceError(
            "No se pudo obtener respuesta de Gemini.",
            str(ultimo_error) if ultimo_error else None,
        ) from ultimo_error

    @staticmethod
    def _extraer_tokens(usage: object) -> tuple[int, int]:
        """Extrae y valida contadores de uso proporcionados por el SDK."""
        if usage is None:
            return 0, 0

        tokens_in = getattr(usage, "prompt_token_count", 0) or 0
        tokens_out = getattr(usage, "candidates_token_count", 0) or 0
        if any(
            not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0
            for tokens in (tokens_in, tokens_out)
        ):
            raise ExternalServiceError(
                "Gemini devolvió métricas de tokens inválidas."
            )
        return tokens_in, tokens_out

    def _esperar_reintento(self, intento: int, codigo: int | None) -> None:
        """Espera con backoff exponencial antes del siguiente intento."""
        espera = min(self.espera_base * (2**intento), self.espera_maxima)
        espera += random.uniform(0, self.jitter)
        logger.warning(
            "Reintentando Gemini tras error %s (intento %d/%d); "
            "espera %.2f segundos",
            codigo if codigo is not None else "red",
            intento + 1,
            self.max_reintentos,
            espera,
        )
        time.sleep(espera)
