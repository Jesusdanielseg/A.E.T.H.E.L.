# Cobertura de módulos Python en `explanations/`

**Fecha:** 2026-11-24
**Pregunta:** ¿hay archivos `.py` que no estén documentados o explicados
didácticamente en `explanations/`?

> **Actualización posterior:** los huecos de contexto y de la capa LLM se
> cubrieron con [`16-contexto-y-privacidad.md`](./16-contexto-y-privacidad.md)
> y [`17-capa-llm-completa.md`](./17-capa-llm-completa.md). Además,
> [`05-libraries-and-tests.md`](./05-libraries-and-tests.md) se amplió con la
> tabla completa de pruebas. Las tablas siguientes conservan el estado de la
> auditoría previa.

## Resumen

No hay módulos funcionales de `src/` completamente invisibles: todos tienen al
menos una referencia conceptual. Sin embargo, **sí hay archivos sin una
explicación dedicada** y varios cuya documentación existe pero está desfasada.

El inventario real es:

- **36 archivos `.py` en `src/`**, de los cuales 27 no son `__init__.py`.
- **19 archivos `.py` en `tests/`**, de los cuales 17 son `test_*.py`.
- **0 enlaces rotos** en los Markdown de `explanations/` después de la
  corrección del índice.

La cobertura más débil está en:

1. `src/context/sanitizer.py`
2. `src/context/prompt_builder.py`
3. `src/context/system_prompt.py`
4. `src/llm/base.py`, `src/llm/gemini_provider.py` y
   `src/llm/offline_provider.py`
5. Los tests nuevos de configuración, evaluación, personalidad y comandos CLI.

## Criterios usados

| Estado | Significado |
|---|---|
| **Completa** | Tiene explicación dedicada y el documento o snapshot está alineado con el código actual. |
| **Parcial** | Se explica conceptualmente o solo se documenta un cambio, pero no hay recorrido completo del archivo. |
| **Histórica** | Solo aparece en `09-complete-code-map.md`, que ya está marcado como histórico. |
| **Placeholder** | Es un módulo vacío reservado para fases futuras; se documenta como tal. |
| **Sin cobertura** | No aparece en ningún documento de `explanations/`. |

## Cobertura de `src/`

| Archivo | Estado | Dónde se explica | Observación |
|---|---|---|---|
| `src/main.py` | Parcial | `04`, `13`, `main_code.py` | El flujo actual está en `13`; `04` y el snapshot son antiguos. |
| `src/core/config.py` | Parcial | `13`, `config_code.py` | `13` explica los cambios; `config_code.py` es una guía antigua. |
| `src/core/controller.py` | Parcial | `06`, `controller_code.py` | El flujo está explicado; el snapshot no es exacto. |
| `src/core/exceptions.py` | Completa | `02`, `exceptions_code.py` | Snapshot equivalente a nivel AST. |
| `src/core/health.py` | Parcial | `03`, `health_code.py` | El snapshot no refleja que la API key solo se exige con Gemini. |
| `src/core/lifecycle.py` | Parcial | `04`, `lifecycle_code.py` | El snapshot no incluye la guarda `_deteniendo` ni el relanzamiento de `KeyboardInterrupt`. |
| `src/core/llm.py` | Completa | `08`, `llm_code.py` | Snapshot equivalente a nivel AST. |
| `src/core/logger.py` | Parcial | `01`, `logger_code.py` | El snapshot no incluye el patrón `AQ.` en la redacción de secretos. |
| `src/core/dispatcher.py` | Placeholder | `future_modules_code.py`, `09` | Módulo vacío reservado. |
| `src/interfaces/cli.py` | Parcial | `07`, `13`, `cli_code.py` | `07` y el snapshot no incluyen `/memoria`, `/limpiar`, `/modelo` ni `/estado`. |
| `src/infrastructure/gemini_client.py` | Completa | `10`, `gemini_client_code.py` | La guía conceptual sigue vigente. |
| `src/llm/base.py` | Parcial | `11` | Explica `BaseLLMProvider`, `ModelResponse` y `ProviderError`, pero no hay snapshot ni recorrido línea a línea. |
| `src/llm/gemini_provider.py` | Parcial | `11` | Se explica como adaptador, sin sección dedicada al archivo. |
| `src/llm/offline_provider.py` | Parcial | `11` | Se explica como último recurso, sin recorrido completo. |
| `src/llm/ollama_provider.py` | Parcial | `11`, `13` | `13` explica el payload y las opciones nuevas; no hay snapshot completo. |
| `src/llm/router.py` | Parcial | `11`, `13` | `13` explica `last_model` y el orden; no hay snapshot completo. |
| `src/context/manager.py` | Parcial | `12`, `13` | El diseño y la compactación están explicados; no hay snapshot. |
| `src/context/prompt_builder.py` | Parcial | `13` | Solo se documenta el fallo de booleanos y su corrección; falta explicar el constructor completo. |
| `src/context/sanitizer.py` | Parcial | `12` | Se explica `sanitize_text()` y sus patrones, pero no se nombra el archivo ni hay snapshot. |
| `src/context/store.py` | Parcial | `12`, `13` | Persistencia, retención y cascada explicadas; no hay snapshot. |
| `src/context/system_prompt.py` | Parcial | `12` | Se menciona como instrucciones permanentes; no hay explicación detallada. |
| `src/ai/engine.py` | Placeholder | `future_modules_code.py`, `09` | Reservado para fases futuras. |
| `src/ai/prompts.py` | Placeholder | `future_modules_code.py`, `09` | Reservado; el prompt activo real es `prompts/persona.yaml`. |
| `src/memory/manager.py` | Placeholder | `future_modules_code.py`, `09` | Reservado; no implementa memoria todavía. |
| `src/memory/models.py` | Placeholder | `future_modules_code.py`, `09` | Reservado. |
| `src/tools/executor.py` | Placeholder | `future_modules_code.py`, `09` | Reservado; no ejecuta herramientas. |
| `src/tools/registry.py` | Placeholder | `future_modules_code.py`, `09` | Reservado. |
| `src/**/__init__.py` | No aplica | — | Marcadores de paquete sin lógica; no necesitan explicación individual. |

## Cobertura de `tests/`

`05-libraries-and-tests.md` explica la estrategia general y describe ocho
archivos. Otros se explican en documentos específicos:

- `tests/test_gemini_client.py` en `10`.
- `tests/test_llm_abstraction.py` en `11`.
- `tests/test_context.py` en `12`.

| Archivo | Estado | Dónde se explica |
|---|---|---|
| `tests/conftest.py` | Histórica | Solo `09`. |
| `tests/test_cli.py` | Completa | `05`, `07`, `09`. |
| `tests/test_cli_commands.py` | **Sin cobertura** | No aparece en ningún documento. |
| `tests/test_config.py` | **Sin cobertura** | No aparece en ningún documento. |
| `tests/test_context.py` | Completa | `12`. |
| `tests/test_controller.py` | Completa | `05`, `06`, `09`. |
| `tests/test_core.py` | Histórica | Solo `09`. |
| `tests/test_evaluation_04.py` | **Sin cobertura** | No aparece en ningún documento. |
| `tests/test_exceptions.py` | Completa | `05`, `09`. |
| `tests/test_gemini_client.py` | Completa | `10`, `09`. |
| `tests/test_health.py` | Completa | `05`, `09`. |
| `tests/test_lifecycle.py` | Completa | `05`, `09`. |
| `tests/test_llm_abstraction.py` | Completa | `11`. |
| `tests/test_llm.py` | Completa | `05`, `08`, `09`. |
| `tests/test_logger.py` | Completa | `05`, `09`. |
| `tests/test_main.py` | Completa | `05`, `09`. |
| `tests/test_memory.py` | Placeholder | `09`; actualmente no contiene pruebas. |
| `tests/test_personality.py` | **Sin cobertura** | No aparece en ningún documento. |
| `tests/__init__.py` | No aplica | Marcador de paquete. |

## Huecos reales y prioridad

### Prioridad alta

1. **`src/context/sanitizer.py`**
   Es una pieza de privacidad y seguridad. `12` explica qué hace
   `sanitize_text()`, pero no hay una sección dedicada al archivo, a sus
   patrones ni a sus límites.

2. **`src/context/prompt_builder.py`**
   `13` solo documenta el fallo de los booleanos. Falta explicar la carga del
   YAML, la validación de modos, la composición de identidad/estilo/respuesta y
   las prohibiciones.

3. **`src/context/system_prompt.py`**
   Solo se menciona de pasada. Es corto, pero conviene explicar por qué está
   separado del historial y cómo se combina con `PersonaBuilder`.

### Prioridad media

4. **`src/llm/base.py`, `gemini_provider.py` y `offline_provider.py`**
   `11` los explica por concepto y por clase, pero no por archivo. No hay
   snapshots anotados como los del núcleo.

5. **`src/llm/ollama_provider.py` y `router.py`**
   `13` cubre los cambios 04.5, pero no son una explicación completa del
   adaptador ni del router.

6. **Tests sin cobertura**
   `test_cli_commands.py`, `test_config.py`, `test_evaluation_04.py` y
   `test_personality.py` no aparecen en ningún documento. `test_core.py`,
   `test_memory.py` y `conftest.py` solo están en el mapa histórico `09`.

### Prioridad baja

7. **Snapshots desactualizados**
   `config_code.py`, `main_code.py`, `cli_code.py`, `health_code.py`,
   `lifecycle_code.py`, `logger_code.py` y `controller_code.py` ya están
   marcados con avisos, pero siguen sin coincidir exactamente con `src/`.

8. **Placeholders**
   Los módulos de `src/ai/`, `src/memory/`, `src/tools/` y
   `src/core/dispatcher.py` están documentados como reservados. No necesitan
   explicación funcional mientras sigan vacíos.

## Qué no es un hueco

- Los `__init__.py` vacíos no requieren explicación individual.
- Los módulos placeholder están correctamente identificados como tales.
- `09-complete-code-map.md` no es una fuente actual; su valor es histórico.
- La ausencia de un snapshot no significa ausencia de explicación: varios
  módulos de `src/llm/` y `src/context/` se explican en `11`, `12` y `13`.

## Recomendación

Si se quiere completar la documentación didáctica, el orden más útil sería:

1. Crear un documento específico de contexto que cubra `sanitizer.py`,
   `prompt_builder.py`, `system_prompt.py`, `store.py` y `manager.py`.
2. Crear un documento específico de la capa LLM que cubra `base.py`,
   `gemini_provider.py`, `offline_provider.py`, `ollama_provider.py` y
   `router.py`.
3. Ampliar `05-libraries-and-tests.md` con una tabla de todos los tests
   actuales, incluyendo `test_config.py`, `test_cli_commands.py`,
   `test_evaluation_04.py` y `test_personality.py`.
4. Refrescar los snapshots antiguos o mantenerlos explícitamente como
   históricos.

## Verificación

- Inventario obtenido con `find src tests -type f -name '*.py'`.
- Búsqueda de rutas, nombres de archivo y clases en todos los documentos y
  snapshots de `explanations/`.
- Comparación AST de los snapshots con sus fuentes.
- Comprobación de enlaces relativos: 0 rotos.
- Suite actual: `125 passed`.

Este documento no modifica código de `src/` ni inicia la Fase 05.
