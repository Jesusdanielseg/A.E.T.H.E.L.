# Auditoría de `explanations/` y comparación con el código actual

**Fecha:** 2026-11-24
**Rama:** `Fase-04/Cerebro-de-ia-y-personalidad`
**Alcance:** inventario real de `explanations/`, comparación de sus documentos y
copias anotadas con `src/`, y localización de los cambios de la Fase 04.5.

Este documento responde a una comprobación concreta: qué hay realmente en
`explanations/`, qué sigue vigente, qué quedó desactualizado y dónde están
documentados los cambios que se hicieron en el código.

## 1. Qué hay realmente en `explanations/`

### 1.1 Documentos Markdown

| Archivo | Contenido | Estado 04.5 |
|---|---|---|
| `01-logger.md` | Logging, IDs, redacción y rotación. | Vigente para su bloque. |
| `02-exceptions.md` | Jerarquía de excepciones. | Vigente. |
| `03-health.md` | Comprobaciones de salud. | Vigente en concepto; el snapshot asociado está desactualizado. |
| `04-startup-and-lifecycle.md` | Arranque y ciclo de vida. | **Parcialmente desactualizado.** |
| `05-libraries-and-tests.md` | Bibliotecas y pruebas. | Vigente como referencia general. |
| `06-controller.md` | Controlador central. | Vigente. |
| `07-cli.md` | Interfaz CLI. | **Desactualizado** en comandos. |
| `08-llm-and-budget.md` | Contrato LLM y presupuesto. | **Parcial:** contrato vigente, integración antigua. |
| `09-complete-code-map.md` | Mapa completo del código. | **Histórico:** no refleja la Fase 04 actual. |
| `10-gemini-and-real-test.md` | Cliente Gemini y prueba real. | Vigente para Gemini. |
| `11-abstraction-layer-04-2.md` | Adaptadores, router y proveedores. | **Parcial:** estructura vigente, ejemplo de modelo antiguo. |
| `12-conversational-context-04-3.md` | Contexto conversacional. | **Parcial:** falta el resumen acumulado y `/estado`. |
| `13-ollama-performance-and-evaluation-04-5.md` | Cambios y evaluación 04.5. | **Vigente y específico de 04.5.** |
| `14-auditoria-explanations-04-5.md` | Este informe. | **Nuevo.** |
| `readme.md` | Índice de la carpeta. | **Corregido en esta auditoría.** |

### 1.2 Copias Python anotadas

| Snapshot | Fuente real | Estado |
|---|---|---|
| `logger_code.py` | `src/core/logger.py` | Parcial: falta el patrón `AQ.` en `_SECRET_PATTERN`. |
| `exceptions_code.py` | `src/core/exceptions.py` | Equivalente a nivel AST. |
| `health_code.py` | `src/core/health.py` | Desactualizado en `verificar_salud()`. |
| `lifecycle_code.py` | `src/core/lifecycle.py` | Desactualizado en `_manejar_senal()`. |
| `controller_code.py` | `src/core/controller.py` | Parcial: mismo flujo, faltan logs y nombres explícitos. |
| `cli_code.py` | `src/interfaces/cli.py` | **Desactualizado:** faltan cuatro comandos y métodos. |
| `llm_code.py` | `src/core/llm.py` | Equivalente a nivel AST. |
| `main_code.py` | `src/main.py` | **Desactualizado:** falta el composition root actual. |
| `config_code.py` | `src/core/config.py` | **Guía antigua:** no contiene código y menciona `AI_PROVIDER`. |
| `gemini_client_code.py` | `src/infrastructure/gemini_client.py` | Guía conceptual; no es una copia ejecutable. |
| `future_modules_code.py` | Módulos reservados | Vigente como mapa de placeholders. |

## 2. Hallazgo principal: los snapshots no se actualizan solos

Los archivos `*_code.py` son material didáctico. No se importan desde la
aplicación y no se sincronizan automáticamente cuando cambia `src/`.

Las modificaciones reales de la Fase 04.5 se hicieron en:

- `src/core/config.py`
- `src/llm/ollama_provider.py`
- `src/llm/router.py`
- `src/interfaces/cli.py`
- `src/main.py`
- `src/context/store.py`
- `src/context/prompt_builder.py`
- `src/context/manager.py`
- `prompts/persona.yaml`
- pruebas y documentación

Por eso, quien lea solo `explanations/config_code.py`,
`explanations/main_code.py` o `explanations/cli_code.py` verá una versión
antigua. La explicación actualizada está en
[`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md).

## 3. Comparación de snapshots con el código real

La comparación se hizo con AST, ignorando comentarios y docstrings, para
distinguir diferencias estructurales de simples anotaciones didácticas.

### 3.1 `config_code.py`

No contiene una clase `Settings` ejecutable: es una guía de comentarios.

Diferencias:

- Menciona `AI_PROVIDER`, que ya se eliminó del código.
- No menciona `_env_int()` ni `_env_bool()`.
- No incluye `OLLAMA_THINK`, `OLLAMA_NUM_CTX`, `OLLAMA_NUM_PREDICT`,
  `OLLAMA_KEEP_ALIVE` ni `LLM_BUDGET_USD`.
- No refleja la validación nueva de límites de Ollama y presupuesto.
- No refleja el modelo por defecto `gemma3:4b`.

### 3.2 `main_code.py`

Es una versión anterior del punto de entrada.

Diferencias:

- No tiene `_crear_router_llm()`.
- No llama a `config.validar()`.
- No construye `PersonaBuilder` ni `ContextManager`.
- No pasa las opciones nuevas a `OllamaProvider`.
- No usa `config.LLM_BUDGET_USD`.
- No captura `sqlite3.Error`.
- No cierra el contexto en el bloque `finally`.

### 3.3 `cli_code.py`

Es una versión anterior de la interfaz.

Diferencias:

- No inicializa `self.contexto`.
- No reconoce `/memoria`, `/limpiar`, `/modelo` ni `/estado`.
- No tiene `_mostrar_memoria()`, `_limpiar_memoria()`, `_mostrar_modelo()` ni
  `_mostrar_estado()`.
- No muestra el modelo ni el presupuesto acumulado.

### 3.4 `health_code.py`

La función `verificar_salud()` cambió:

- El snapshot exige `AI_API_KEY` siempre.
- El código actual solo la exige si `gemini` está en `LLM_PROVIDER_ORDER`.
- Esto es importante porque la configuración por defecto es Ollama local y no
  necesita clave.

### 3.5 `lifecycle_code.py`

`_manejar_senal()` cambió:

- El snapshot no comprueba `self._deteniendo`.
- El snapshot no relanza `KeyboardInterrupt` después de `detener()`.
- El código actual evita apagados duplicados y desbloquea correctamente la
  lectura de `input()`.

### 3.6 `logger_code.py`

La estructura y las funciones coinciden, pero el snapshot no incluye el patrón
`AQ.` que el código actual añadió a `_SECRET_PATTERN` para redactar tokens con
ese prefijo.

### 3.7 `controller_code.py`

El flujo general coincide, pero el snapshot es anterior a los logs de entrada y
salida y a los argumentos nombrados de `RespuestaSalida`. No es una diferencia
funcional grave, pero no es una copia exacta.

### 3.8 Snapshots equivalentes

`exceptions_code.py` y `llm_code.py` coinciden a nivel AST con sus fuentes.
`future_modules_code.py` sigue siendo un mapa válido de los módulos reservados.

### 3.9 `gemini_client_code.py`

Es una guía conceptual, no una copia del cliente. La ruta real
`src/infrastructure/gemini_client.py` sigue siendo la correcta.

## 4. Comparación de documentos con el estado actual

### 4.1 `04-startup-and-lifecycle.md`

Describe un arranque que construye `GeminiClient` directamente. El código actual
crea un `LLMRouter` con Ollama, Gemini y offline, valida la configuración,
construye el contexto y captura errores de SQLite. Está marcado como parcial.

### 4.2 `07-cli.md`

Describe solo los comandos de salida. La CLI actual también tiene:

- `/memoria`
- `/limpiar`
- `/modelo`
- `/estado`

Está marcado como desactualizado.

### 4.3 `08-llm-and-budget.md`

El contrato `RespuestaLLM`, `ProveedorLLM` y `GestorPresupuesto` sigue vigente.
Lo que quedó antiguo es la integración: no menciona el router, ni
`LLM_BUDGET_USD`, ni las opciones de Ollama.

### 4.4 `09-complete-code-map.md`

Es el documento más desactualizado. Describe un flujo con `GeminiClient` directo
y dice que la memoria no persiste conversaciones. Tampoco incluye
`src/context/`, el router ni los tests nuevos. Se conserva como histórico, pero
no debe usarse como mapa actual.

### 4.5 `11-abstraction-layer-04-2.md`

La arquitectura de adaptadores y router sigue siendo correcta. El ejemplo de
modelo `qwen3:8b` quedó antiguo; el modelo elegido es `gemma3:4b` y las opciones
nuevas se explican en el documento 13.

### 4.6 `12-conversational-context-04-3.md`

El diseño de contexto sigue vigente, pero faltan tres cambios de 04.5:

- el resumen previo se incluye en la siguiente compactación;
- la retención elimina mensajes y sesiones con compatibilidad hacia atrás;
- la CLI añadió `/estado`.

### 4.7 Documentos vigentes para su alcance

`01-logger.md`, `02-exceptions.md`, `03-health.md`, `05-libraries-and-tests.md`,
`06-controller.md` y `10-gemini-and-real-test.md` siguen siendo útiles para sus
respectivos bloques. `13` es el documento de referencia para los cambios 04.5.

## 5. Dónde están documentados los cambios de 04.5

El documento
[`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md)
explica:

- configuración de Ollama y presupuesto;
- proveedor y router;
- CLI `/modelo` y `/estado`;
- errores de SQLite;
- retención y compactación;
- corrección de booleanos en el prompt;
- reglas de personalidad contra alucinaciones;
- selección de `gemma3:4b`;
- resultados y limitaciones de la evaluación.

Los resultados funcionales y las latencias están en
[`docs/evaluation-04-results.md`](../docs/evaluation-04-results.md).

## 6. Cambios realizados en esta auditoría

- Se corrigió `explanations/readme.md`: tenía enlaces rotos porque usaba nombres
  en español que no existen.
- Se añadieron estados y advertencias a los documentos parcialmente
  desactualizados.
- Se creó este documento `14`.
- No se modificó el código de `src/`.
- No se inició la Fase 05.
- No se hizo commit ni push.

## 7. Verificación

Comandos usados para comprobar el estado real:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src tests
```

Resultado:

```text
125 passed
All checks passed!
Success: no issues found in 55 source files
```

También se comprobó que los enlaces relativos de los Markdown de
`explanations/` apunten a archivos existentes. Antes de esta auditoría, el
índice tenía 18 enlaces rotos; después de la corrección, no quedan enlaces
rotos en `explanations/`.

## 8. Recomendaciones

1. Usar `src/` como fuente de verdad y `13`/`14` como documentación actual.
2. Si se quiere conservar el valor didáctico de los snapshots, actualizar
   `config_code.py`, `main_code.py`, `cli_code.py`, `health_code.py` y
   `lifecycle_code.py` en un bloque separado.
3. No presentar `09-complete-code-map.md` como mapa vigente; ya está marcado
   como histórico.
4. Mantener `explanations/` fuera de Git si se sigue prefiriendo material local,
   o sacarlo de `.gitignore` si se quiere versionar la documentación.

## 9. Limitaciones de esta auditoría

- La comparación de snapshots se hizo por estructura AST y por inspección de
  las diferencias relevantes; no es una comparación byte a byte.
- Los snapshots contienen comentarios didácticos y no están pensados para
  ejecutarse.
- `explanations/` está ignorado por Git, por lo que este informe existe
  localmente y no aparecerá en `git status`.
