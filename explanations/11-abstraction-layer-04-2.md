# 04.2. Capa de abstracción

> **Estado 04.5:** la estructura de adaptadores y router sigue vigente. El
> ejemplo de modelo `qwen3:8b` y las opciones de Ollama quedaron actualizados en
> [`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md).
> Ver también [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

La implementación está en [`src/llm/`](../src/llm/). El objetivo es que el
núcleo trabaje con un contrato propio y no conozca Gemini, Ollama ni HTTP.

## Patrones usados

- **Adapter:** `GeminiProvider` y `OllamaProvider` traducen APIs externas a
  `ModelResponse`.
- **Strategy:** cada proveedor es una estrategia intercambiable.
- **Router:** `LLMRouter` intenta las estrategias en el orden configurado.
- **ABC:** `BaseLLMProvider` obliga a implementar `generate_response()`.

## Contrato común

`BaseLLMProvider` define:

```python
generate_response(prompt, context=None) -> ModelResponse
```

`ModelResponse` normaliza texto, proveedor, modelo, tokens y coste. Su método
`to_core_response()` convierte el resultado al DTO existente
`RespuestaLLM`, por lo que `ControladorCentral` conserva su contrato actual.
`ProviderError` unifica los errores de red, SDK y proveedores locales como un
error recuperable.

## Proveedores

### Gemini

`GeminiProvider` envuelve el `GeminiClient` ya probado. El SDK de Google sigue
aislado en `src/infrastructure/gemini_client.py`; ningún módulo de `src/core`
ni el router lo importa.

### Ollama

`OllamaProvider` usa la API HTTP local `POST /api/generate`. No añade una
dependencia Python nueva. Requiere Ollama ejecutándose y un modelo descargado,
por ejemplo `qwen3:8b`. También normaliza `prompt_eval_count` y `eval_count`
cuando Ollama los devuelve, para que el presupuesto y los logs conserven
métricas reales.

### Offline

`OfflineProvider` no usa red. Devuelve respuestas deterministas por reglas
básicas y funciona como último recurso para que la CLI siga operativa.
Sus respuestas tienen coste y tokens cero.

## Orden y configuración

El orden se controla desde `.env`:

```dotenv
LLM_PROVIDER_ORDER=ollama,gemini,offline
```

Ejemplos:

```dotenv
# Solo Gemini
LLM_PROVIDER_ORDER=gemini

# Ollama antes que Gemini
LLM_PROVIDER_ORDER=ollama,gemini,offline

# Siempre disponible, sin red
LLM_PROVIDER_ORDER=offline
```

Si Gemini no tiene clave o falla al inicializarse, se omite y el router
continúa con Ollama y offline. Si un proveedor falla durante una petición,
`LLMRouter` registra una advertencia y pasa al siguiente.

## Integración con el núcleo

`main.py` crea el router en el composition root y lo inyecta como
`proveedor_llm` en `ControladorCentral`. El controlador solo llama a
`generar_respuesta()` y registra el consumo; no conoce la estrategia elegida.

## Pruebas

[`tests/test_llm_abstraction.py`](../tests/test_llm_abstraction.py) cubre:

- obligatoriedad de la ABC;
- normalización al DTO del núcleo;
- fallback del router;
- rechazo de router vacío;
- petición HTTP de Ollama mediante mock.

Ninguna de estas pruebas necesita Gemini, Ollama, internet o una API key.
