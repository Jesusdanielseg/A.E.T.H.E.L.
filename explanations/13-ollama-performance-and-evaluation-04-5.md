# 04.5. Ollama, rendimiento y evaluación inicial

Implementación: [`src/core/config.py`](../src/core/config.py),
[`src/llm/ollama_provider.py`](../src/llm/ollama_provider.py),
[`src/llm/router.py`](../src/llm/router.py),
[`src/context/manager.py`](../src/context/manager.py) y
[`src/context/prompt_builder.py`](../src/context/prompt_builder.py).

Resultados: [`docs/evaluation-04-results.md`](../docs/evaluation-04-results.md).

Este bloque cierra la parte local de la Fase 04. No inicia la Fase 05, no cambia
la arquitectura y no convierte los módulos de fases futuras en funcionalidad
real.

## 1. Ollama como proveedor principal

La estrategia por defecto pasa a ser:

```text
ollama,gemini,offline
```

Ollama es el primer intento; Gemini queda como respaldo si está configurado y
el proveedor offline es el último recurso. El modelo por defecto es
`gemma3:4b`.

La configuración nueva en [`src/core/config.py`](../src/core/config.py) es:

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_THINK=false
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=512
OLLAMA_KEEP_ALIVE=30m
OLLAMA_TIMEOUT_SECONDS=120
LLM_BUDGET_USD=0.50
```

Se añadieron dos ayudantes internos:

- `_env_int()`: convierte enteros y devuelve `0` ante un valor inválido para que
  `validar()` lo rechace con un mensaje claro.
- `_env_bool()`: acepta `1/true/yes/on/si/sí` y `0/false/no/off`; cualquier
  otro valor conserva el valor por defecto.

También se eliminó `AI_PROVIDER`, que duplicaba la responsabilidad de
`LLM_PROVIDER_ORDER`, y se añadió `LLM_BUDGET_USD` para no dejar el presupuesto
fijo en el código.

`validar()` ahora comprueba que el modelo, el contexto, la salida máxima,
`keep_alive` y el presupuesto sean válidos. `main.py` llama a `config.validar()`
antes de crear la CLI.

## 2. Proveedor Ollama

[`src/llm/ollama_provider.py`](../src/llm/ollama_provider.py) envía:

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

Cambios relevantes:

- `think` desactiva el razonamiento interno de modelos que lo soportan.
- `num_ctx` acota el contexto enviado a Ollama.
- `num_predict` acota la salida y evita respuestas interminables.
- `keep_alive` mantiene el modelo cargado entre mensajes.
- El constructor valida tipos y valores para no enviar opciones inválidas.

El router guarda `last_model` además de `last_provider` y `last_latency_ms`. La
CLI muestra el modelo en `/modelo` y añadió `/estado` con proveedor, modelo,
latencia, tokens y coste acumulado.

## 3. Arranque y errores de base de datos

[`src/main.py`](../src/main.py) usa `config.LLM_BUDGET_USD` en lugar de `0.50`
fijo. También captura `sqlite3.Error` al iniciar para cerrar con código 1 y un
log claro si la base está bloqueada, corrupta o sin permisos.

## 4. Persistencia, retención y compactación

[`src/context/store.py`](../src/context/store.py):

- Las bases nuevas declaran
  `REFERENCES conversation_sessions(id) ON DELETE CASCADE`.
- La purga elimina primero los mensajes de las sesiones archivadas y después
  las sesiones. Esto mantiene compatibilidad con bases creadas antes de la
  cascada.
- Se añadió un índice por `archived` y `last_activity_at`.
- Si falla la creación del esquema, la conexión se cierra antes de propagar el
  error.

[`src/context/manager.py`](../src/context/manager.py) corrige una pérdida de
información en compactaciones sucesivas: el prompt del resumidor ahora incluye
el resumen anterior. Sin esto, un hecho como «el proyecto se llama Orion» podía
desaparecer al segundo resumen. La conversación real de 6 turnos lo verifica.

## 5. Personalidad y prompt

[`src/context/prompt_builder.py`](../src/context/prompt_builder.py) tenía un
fallo visible: los booleanos del YAML se renderizaban como texto literal.

Antes:

```text
- Primera línea directa: True.
- Brevedad por defecto: True.
```

El modelo copiaba ese «True.» al inicio de sus respuestas. Ahora se renderiza
como instrucciones naturales:

```text
- Primera línea: Empieza con una respuesta directa en la primera línea.
- Brevedad: Sé breve por defecto; amplía solo si el usuario lo pide.
```

Además, `PersonaBuilder` valida que `primera_linea_directa` y
`brevedad_por_defecto` sean booleanos reales.

[`prompts/persona.yaml`](../prompts/persona.yaml) se reforzó para reducir
alucinaciones y mejorar la conversación:

- No inventar listados de archivos ni resultados de comandos.
- No inventar precios, URLs ni estados de servicios.
- Reconocer y conservar los datos y preferencias del usuario.
- Ejemplo específico para «¿Qué archivos hay en mi escritorio?».
- Se retiró el ejemplo de saludo que provocaba respuestas empezando por
  «Operativa.».

## 6. Dependencias y documentación

- [`requirements.txt`](../requirements.txt) queda solo con dependencias de
  ejecución.
- [`requirements-dev.txt`](../requirements-dev.txt) añade `pytest`, `ruff`,
  `mypy`, `types-PyYAML` y referencia al archivo de ejecución.
- Se actualizaron `readme.md`, `docs/architecture.md`, `docs/data-flow.md`,
  `docs/testing-guide.md`, `docs/vision.md`, `docs/safety-policy.md`,
  `docs/requirements.md`, `docs/personality.md` y `docs/evaluation-04.md`.
- Los módulos de fases futuras que siguen vacíos recibieron docstrings para
  dejar claro que son marcadores de posición.
- Los permisos locales de `.env`, la base de datos y el log se ajustaron a
  `600`. Esto no se versiona en Git, pero forma parte del endurecimiento local.

## 7. Selección del modelo

Se probaron tres opciones:

| Modelo | Resultado | Decisión |
|---|---|---|
| `qwen3:8b` | ~7-10 s en caliente con `think=false`; ~44 s con pensamiento; 6.6 GB y reparto CPU/GPU. | Retirado. |
| `qwen3:4b` | Exponía razonamiento interno aunque `think=false`; respuestas lentas y contaminadas. | Retirado. |
| `gemma3:4b` | ~0.6-2.2 s en simples; ~6-10 s en complejas; 2.9 GB y 100 % GPU. | **Elegido.** |

La primera carga de `gemma3:4b` tarda ~9-14 s. Después se mantiene cargado 30
minutos. Solo queda instalado `gemma3:4b`.

## 8. Evaluación

La evaluación funcional cubrió preguntas fáciles, complejas, contradicciones,
incertidumbre y una conversación real con compactación. Los detalles, latencias
y limitaciones están en
[`docs/evaluation-04-results.md`](../docs/evaluation-04-results.md).

Resumen:

- Simples: ~0.6-2.2 s; correctas.
- Complejas: ~6-10 s; coherentes, a veces genéricas o verbosas.
- Contradicciones: la respuesta final usa el dato corregido.
- Incertidumbre: ya no inventa archivos, precios ni URLs en los casos probados.
- Conversación con compactación: conserva «Orion» y «Kubuntu» tras el resumen.

La conversación manual de 20 turnos no se completó por tiempo. Queda como
limitación documentada; la compactación y persistencia están cubiertas por
tests deterministas y por la conversación real de 6 turnos.

## 9. Pruebas y verificación

Comandos:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src tests
```

Resultado final:

```text
125 passed
All checks passed!
Success: no issues found in 55 source files
```

Si el entorno del shell define `OLLAMA_MODEL`, ese valor tiene prioridad sobre
`.env`. Para verificar el modelo elegido:

```bash
env -u OLLAMA_MODEL .venv/bin/python -m src.main
```

o:

```bash
OLLAMA_MODEL=gemma3:4b .venv/bin/python -m src.main
```

## 10. Alcance

No se inició la Fase 05. No se hizo commit ni push. Los cambios quedan en el
árbol de trabajo de la rama
`Fase-04/Cerebro-de-ia-y-personalidad` para revisión.
