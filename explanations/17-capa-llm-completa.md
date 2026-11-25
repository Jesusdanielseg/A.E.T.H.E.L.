# 17. Capa LLM completa

**Estado:** vigente para la Fase 04.5.
**Implementación:** [`src/llm/`](../src/llm/)
**Integración:** [`src/main.py`](../src/main.py)
**Pruebas principales:** [`tests/test_llm_abstraction.py`](../tests/test_llm_abstraction.py),
[`tests/test_gemini_client.py`](../tests/test_gemini_client.py) y
[`tests/test_llm.py`](../tests/test_llm.py).

Este documento explica la capa de proveedores LLM completa: el contrato común,
los adaptadores de Gemini, Ollama y offline, y el router que decide cuál usar.
Complementa los documentos 08, 10, 11 y 13.

## 1. Arquitectura

```text
ControladorCentral
  -> LLMRouter (BaseLLMProvider)
       -> OllamaProvider
       -> GeminiProvider -> GeminiClient
       -> OfflineProvider
```

El núcleo sigue usando `RespuestaLLM` y `GestorPresupuesto`. La capa `src/llm/`
traduce esos contratos a un contrato propio, `ModelResponse`, y devuelve el DTO
del núcleo con `to_core_response()`.

La separación permite:

- probar el controlador con un fake;
- cambiar el orden de proveedores sin tocar el núcleo;
- agregar un proveedor nuevo implementando `BaseLLMProvider`;
- mantener Gemini y Ollama fuera de `src/core/`.

## 2. `src/llm/base.py`

### 2.1 `ProviderError`

```python
class ProviderError(ExternalServiceError):
    ...
```

Es el error normalizado de la capa LLM. El router solo hace fallback cuando
recibe `ProviderError`; los errores inesperados no se ocultan.

### 2.2 `ModelResponse`

Es un `@dataclass(frozen=True)` con:

- `text`: texto de la respuesta;
- `provider`: nombre del proveedor;
- `model`: identificador del modelo;
- `tokens_input` y `tokens_output`;
- `cost_usd`.

`to_core_response()` convierte el resultado en `RespuestaLLM`, el DTO que ya
espera `ControladorCentral`.

### 2.3 `BaseLLMProvider`

Es una clase abstracta con:

```python
generate_response(prompt, context=None) -> ModelResponse
```

`generar_respuesta(mensaje)` existe por compatibilidad con el contrato actual
del núcleo y delega en `generate_response()` + `to_core_response()`.

## 3. `src/llm/gemini_provider.py`

`GeminiProvider` envuelve un `GeminiClient` ya construido.

- Ignora el parámetro `context`; el prompt ya llega compuesto.
- Llama a `client.generar_respuesta(prompt)`.
- Cualquier excepción del cliente se traduce a `ProviderError`.
- Devuelve un `ModelResponse` con `provider="gemini"` y las métricas del DTO de
  Gemini.

La captura amplia de excepciones es intencional: el router necesita un error
uniforme para continuar con el siguiente proveedor. El detalle original queda
encadenado con `raise ... from exc`.

## 4. `src/llm/offline_provider.py`

`OfflineProvider` no usa red ni dependencias externas. Es el último recurso para
que la CLI siga operativa.

Reglas actuales:

- saludos como `hola`, `hola aethel` o `hello` reciben una respuesta fija;
- preguntas que terminan en `?` o empiezan por `qué`, `cómo`, `por qué`, etc.
  reciben un aviso de que no hay modelo disponible;
- cualquier otro texto recibe un mensaje genérico de indisponibilidad.

Devuelve `provider="offline"`, `model="offline-rules"` y coste/tokens cero. No
es un modelo de lenguaje: es un respaldo determinista.

## 5. `src/llm/ollama_provider.py`

`OllamaProvider` habla con la API HTTP local de Ollama mediante
`urllib.request`, sin añadir una dependencia Python.

### 5.1 Validación del constructor

| Parámetro | Validación |
|---|---|
| `model` | Texto no vacío. |
| `timeout_seconds` | Entero mayor que cero; rechaza `bool`. |
| `think` | Booleano real. |
| `num_ctx` | Entero mayor que cero; rechaza `bool`. |
| `num_predict` | Entero mayor que cero; rechaza `bool`. |
| `keep_alive` | Texto no vacío. |

`base_url` se normaliza quitando la barra final.

### 5.2 Petición

El payload enviado a `POST /api/generate` es:

```json
{
  "model": "gemma3:4b",
  "prompt": "...",
  "stream": false,
  "think": false,
  "keep_alive": "30m",
  "options": {
    "num_ctx": 8192,
    "num_predict": 512
  }
}
```

- `stream=false`: espera la respuesta completa.
- `think=false`: desactiva el razonamiento interno cuando el modelo lo soporta.
- `keep_alive`: mantiene el modelo cargado entre mensajes.
- `num_ctx`: acota el contexto.
- `num_predict`: acota la salida.

### 5.3 Errores y respuesta

- `OSError` y `json.JSONDecodeError` se traducen a `ProviderError`.
- Si `response` no es texto no vacío, lanza `ProviderError`.
- `prompt_eval_count` y `eval_count` se normalizan con `_metric()`.
- `_metric()` devuelve `0` si el valor es booleano, no entero o negativo.
- El coste es `0.0` porque el modelo es local.

No hay streaming, reintentos automáticos ni descarga de modelos desde este
adaptador.

## 6. `src/llm/router.py`

`LLMRouter` también implementa `BaseLLMProvider`.

### 6.1 Construcción

- Recibe una secuencia de proveedores.
- La convierte en tupla.
- Rechaza una lista vacía con `ValueError`.
- Inicializa `last_provider`, `last_model` y `last_latency_ms`.

### 6.2 Selección

Para cada proveedor, en orden:

1. Mide el tiempo con `time.perf_counter()`.
2. Llama a `generate_response(prompt, context)`.
3. Si lanza `ProviderError`, registra un warning y prueba el siguiente.
4. Si responde, actualiza `last_provider`, `last_model` y `last_latency_ms`.
5. Devuelve el `ModelResponse`.

Si todos fallan, lanza:

```text
ProviderError("Todos los proveedores de modelos fallaron.")
```

El error del último proveedor queda encadenado con `from last_error`.

`generar_respuesta()` delega en la implementación base para conservar la
compatibilidad con el núcleo.

## 7. Integración en `main.py`

`_crear_router_llm()` recorre `config.LLM_PROVIDER_ORDER` y construye:

- `OllamaProvider` con modelo, URL, timeout, `think`, `num_ctx`, `num_predict` y
  `keep_alive`;
- `GeminiProvider` solo si `GeminiClient` se puede construir; si falta la clave
  o falla, se omite con un warning;
- `OfflineProvider` siempre que esté en el orden.

Configuración por defecto:

```env
LLM_PROVIDER_ORDER=ollama,gemini,offline
OLLAMA_MODEL=gemma3:4b
OLLAMA_THINK=false
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=512
OLLAMA_KEEP_ALIVE=30m
OLLAMA_TIMEOUT_SECONDS=120
LLM_BUDGET_USD=0.50
```

`main.py` construye un único `GestorPresupuesto` y lo inyecta en el
controlador. El router no registra consumo por sí mismo; el controlador y la
compactación del contexto lo hacen.

Si el shell define `OLLAMA_MODEL`, ese valor tiene prioridad sobre `.env`. Para
verificar el modelo elegido:

```bash
env -u OLLAMA_MODEL .venv/bin/python -m src.main
```

## 8. Pruebas

`tests/test_llm_abstraction.py` cubre:

- obligatoriedad de la ABC;
- normalización a `RespuestaLLM`;
- fallback del router;
- rechazo de router vacío;
- petición HTTP de Ollama con mock.

`tests/test_gemini_client.py` cubre el cliente Gemini: respuesta estructurada,
modelo por defecto, reintentos, credenciales inválidas, errores de red,
validación, fallback y backoff con jitter.

`tests/test_llm.py` cubre inmutabilidad, métricas inválidas y presupuesto.

`tests/test_config.py` cubre los valores por defecto de Ollama, las opciones de
rendimiento y el rechazo de presupuesto o límites inválidos.

## 9. Límites y notas operativas

- Ollama debe estar ejecutándose y el modelo debe estar descargado.
- El coste local se registra como `0.0`; no representa consumo eléctrico ni
  hardware.
- Si Ollama no devuelve métricas, se usan `0`.
- El router solo conserva la latencia del último proveedor exitoso.
- No hay reintentos automáticos en `OllamaProvider`; el fallback es el router.
- `OfflineProvider` no responde preguntas reales: mantiene la CLI operativa.
- `GeminiProvider` captura cualquier excepción del cliente para normalizarla;
  el detalle se conserva en la cadena de excepción.
- En `development`, la ausencia de clave de Gemini no impide arrancar: el health
  queda `degraded` y el router omite Gemini. En `production` y `test`,
  `config.validar()` exige la clave si Gemini está en `LLM_PROVIDER_ORDER`.

## 10. Verificación

```text
125 passed
All checks passed!
Success: no issues found in 55 source files
```

No se modificó código de `src/` al crear este documento.
