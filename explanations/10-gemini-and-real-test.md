# Gemini: explicación del flujo real

Implementación: [`src/infrastructure/gemini_client.py`](../src/infrastructure/gemini_client.py).
Pruebas aisladas: [`tests/test_gemini_client.py`](../tests/test_gemini_client.py).

## Por qué está fuera de `core`

El SDK de Google, la red, las credenciales y los códigos HTTP son detalles de
infraestructura. El controlador solo recibe `ProveedorLLM`, por lo que puede
probarse con un fake sin red.

## Construcción

`GeminiClient` exige `AI_API_KEY` y valida todos los parámetros que afectan a
la confiabilidad: timeout, reintentos, esperas, jitter y modelos. El cliente
principal se coloca primero y los fallbacks se deduplican conservando el orden.

## Una solicitud

`generar_respuesta()` valida el texto, comprueba el presupuesto opcional y
recorre los modelos. Cada intento llama a `generate_content`, valida que exista
texto, extrae `usage_metadata` y devuelve `RespuestaLLM`.

Cuando existe un `GestorPresupuesto`, el cliente registra el uso después de una
respuesta válida. En la integración actual el controlador también registra el
uso, por lo que el cliente se construye sin pasarle presupuesto desde
`main.py`; así se mantiene una sola responsabilidad de registro.

## Reintentos y fallbacks

- 429, 500, 502, 503 y 504 pueden reintentarse.
- El backoff crece de forma exponencial y respeta un máximo.
- El jitter evita que varios procesos reintenten exactamente al mismo tiempo.
- 404, 503 y 504 pueden cambiar al siguiente modelo.
- 401 y 403 son críticos: no se reintentan porque indican credenciales o
  permisos.
- Los errores de red se convierten en `ExternalServiceError` tras agotar
  intentos.

Por eso el primer mensaje puede tardar: el cliente puede esperar reintentos
antes de probar el siguiente modelo. Los logs indican cuándo se selecciona un
fallback.

## Coste

El coste se estima con tokens de entrada y salida. Es una métrica local
redondeada, no una confirmación de facturación. Las tarifas deben revisarse si
el proveedor cambia precios o si se cambia de modelo.

## Prueba segura

`ping` no llega a este cliente. Las pruebas de `tests/test_gemini_client.py`
simulan respuestas y errores, por lo que no consumen cuota. La prueba real se
hace únicamente con:

```bash
.venv/bin/python -m src.main
```

Después de escribir una consulta, revisa `logs/aethel.log` para identificar el
modelo que respondió y los tokens registrados. Nunca incluyas `AI_API_KEY` en
capturas, issues o logs compartidos.
