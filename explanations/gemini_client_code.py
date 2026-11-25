"""Guía anotada de src/infrastructure/gemini_client.py.

Este archivo explica el adaptador; no es una segunda implementación ejecutable.
"""

# GeminiClient es un adaptador: traduce el SDK google-genai al contrato
# ProveedorLLM definido en src/core/llm.py.
#
# Constructor:
# - exige config.AI_API_KEY;
# - valida timeout, reintentos, backoff, jitter y modelos;
# - conserva el modelo principal primero;
# - elimina fallbacks repetidos;
# - crea genai.Client con timeout HTTP en milisegundos.
#
# _calcular_coste():
# convierte tokens a millones, aplica las tarifas locales de entrada/salida y
# redondea el resultado. Es una estimación, no una factura.
#
# _ejecutar_peticion():
# realiza una sola llamada, comprueba que response.text sea texto no vacío,
# extrae usage_metadata y construye RespuestaLLM.
#
# generar_respuesta():
# 1. valida el mensaje;
# 2. comprueba presupuesto si se inyectó uno;
# 3. recorre modelo principal y fallbacks;
# 4. reintenta errores transitorios con backoff y jitter;
# 5. cambia de modelo ante indisponibilidad recuperable;
# 6. convierte 401/403 en CriticalError;
# 7. convierte fallos agotados en ExternalServiceError;
# 8. registra el uso solo después de una respuesta válida.
#
# El controlador actual registra el presupuesto en su propio flujo, por lo que
# main.py crea GeminiClient sin pasarle GestorPresupuesto. El parámetro opcional
# existe para poder reutilizar el adaptador en otro servicio.
