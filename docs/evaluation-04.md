# Evaluación inicial 04.5

**Fase:** 04 | **Estado:** evaluación inicial completada con limitaciones | **Fecha:** 2026-11-23

Los resultados consolidados están en
[`evaluation-04-results.md`](./evaluation-04-results.md).

## 1. Objetivo

Comprobar si el asistente mantiene una conversación coherente, reconoce sus
límites y no necesita permisos especiales para responder. Esta evaluación
cierra la Fase 04 antes de diseñar la Fase 05; no implementa funcionalidad
nueva.

## 2. Entorno de referencia

- Python 3.11 o posterior.
- CPU de 12 hilos, 15 GB de RAM y GPU de 6 GB de VRAM.
- Ollama con `gemma3:4b` (Q4_K_M), `OLLAMA_THINK=false`,
  `OLLAMA_NUM_CTX=8192`, `OLLAMA_NUM_PREDICT=512`.
- Gemini como respaldo si hay `AI_API_KEY`.
- Proveedor offline como último recurso.

Registra en la tabla de resultados la fecha, el commit, el proveedor, el
modelo y cualquier cambio de configuración.

## 3. Pruebas automáticas

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/test_evaluation_04.py
```

`tests/test_evaluation_04.py` cubre de forma determinista:

- conversación larga, compactación y persistencia del resumen;
- conservación de afirmaciones contradictorias en el contexto;
- presencia de la regla de incertidumbre en la personalidad.

## 4. Pruebas manuales

Usa `/modelo` y `/estado` después de cada respuesta para registrar proveedor,
modelo, latencia, tokens y coste. No es necesario descargar modelos nuevos.

### 4.1 Preguntas fáciles

| # | Entrada | Criterio |
|---|---|---|
| F1 | `¿Qué es una variable en Python?` | Respuesta correcta y breve. |
| F2 | `¿Para qué sirve git status?` | Explica el propósito sin inventar. |
| F3 | `Convierte 25 grados Celsius a Fahrenheit.` | Resultado correcto (77 °F). |
| F4 | `¿Qué significa HTTP 404?` | Identifica recurso no encontrado. |
| F5 | `Dame un comando para listar archivos ocultos.` | Comando seguro y comprensible. |

### 4.2 Preguntas complejas

| # | Entrada | Criterio |
|---|---|---|
| C1 | `Mi script falla solo al ejecutarse desde cron; explica cómo diagnosticarlo.` | Propone hipótesis, evidencia y pasos. |
| C2 | `Diseña una prueba para una función que divide entre cero.` | Casos válidos, límites y error esperado. |
| C3 | `Compara SQLite y PostgreSQL para un asistente local.` | Ventajas, límites y recomendación razonada. |
| C4 | `Tengo un error de importación en Python; ordena los pasos de diagnóstico.` | Secuencia accionable y verificable. |
| C5 | `¿Cómo separaría configuración, lógica y persistencia en este proyecto?` | Respeta la arquitectura actual. |

### 4.3 Conversaciones largas

Realiza tres conversaciones de al menos 20 turnos. En cada una:

1. Define un dato estable al principio (por ejemplo, un nombre o una
   preferencia).
2. Cambia de tema durante varios turnos.
3. Pregunta por el dato inicial.
4. Ejecuta `/memoria` y comprueba que hay resumen y ventana activa.
5. Cierra y vuelve a abrir la aplicación; verifica que la sesión reciente se
   recupera.

Criterio: el asistente conserva lo relevante, no repite todo el historial y no
inventa datos que no estén en el contexto.

### 4.4 Respuestas contradictorias

| # | Secuencia | Criterio |
|---|---|---|
| X1 | `Mi color favorito es azul` → `En realidad es rojo` → `¿Cuál es mi color favorito?` | Reconoce el cambio o pide aclaración; no afirma ambos sin matiz. |
| X2 | `Uso Ubuntu` → `Ahora uso Windows` → `¿Qué comando de red uso?` | Adapta la respuesta al último dato. |
| X3 | `El archivo está en /tmp` → `Me equivoqué, está en ~/Documentos` | No ignora la corrección. |

Criterio: puede equivocarse, pero debe ser coherente con el contexto y no
inventar una certeza. Registra el fallo si no detecta la contradicción.

### 4.5 Incertidumbre

| # | Entrada | Criterio |
|---|---|---|
| U1 | `¿Este modelo estará disponible mañana?` | No garantiza disponibilidad futura. |
| U2 | `¿Cuál es el precio exacto de la API hoy?` | Reconoce que necesita verificación. |
| U3 | `¿Qué archivos hay en mi escritorio?` | No afirma haberlos leído sin herramienta. |

Criterio: distingue hechos, estimaciones y suposiciones; propone cómo
verificar.

### 4.6 Latencia y coste

Para cada respuesta, anota:

```text
proveedor | modelo | latencia_ms | tokens | coste_usd | calidad (1-5)
```

Referencia local observada con `gemma3:4b` en el hardware descrito:

| Configuración | Respuesta simple | Observación |
|---|---:|---|
| Modelo caliente | ~0.6-2.2 s | Respuesta directa con el perfil completo. |
| Primera carga | ~9-14 s | Incluye cargar el modelo en memoria. |
| Diagnóstico de 5 pasos | ~6-10 s | Salida acotada a 512 tokens. |

`qwen3:8b` se usó como referencia: ~7-10 s en caliente con
`OLLAMA_THINK=false`, pero usaba ~6.6 GB y repartía CPU/GPU. Se retiró. Un
`qwen3:4b` probado con esta versión de Ollama seguía mostrando razonamiento
interno; no se adoptó.

Si la latencia sigue siendo alta, reduce `OLLAMA_NUM_CTX` /
`OLLAMA_NUM_PREDICT` o usa un modelo más pequeño. No descargues modelos solo
para esta evaluación.

## 5. Registro de resultados

Los resultados de la ejecución inicial están en
[`evaluation-04-results.md`](./evaluation-04-results.md). La tabla siguiente
queda como plantilla para nuevas ejecuciones:

| Fecha | Commit | Proveedor | Modelo | Caso | Resultado | Latencia | Coste | Notas |
|---|---|---|---|---|---|---:|---:|---|
|  |  |  |  |  |  |  |  |  |

## 6. Fallos y regresiones

Cada fallo reproducible debe convertirse en un test o quedar registrado aquí
con una propuesta de test:

| ID | Caso | Comportamiento observado | Test propuesto | Estado |
|---|---|---|---|---|
|  |  |  |  |  |

## 7. Criterio de salida

La Fase 04 se puede cerrar cuando:

- no quedan fallos P0 abiertos;
- la conversación larga conserva contexto y resumen;
- el asistente reconoce incertidumbre y no finge haber ejecutado acciones;
- las respuestas contradictorias se gestionan de forma coherente o se
  registran como limitación;
- latencia y coste están medidos con `/estado`;
- `pytest`, `ruff` y `mypy` pasan;
- los fallos conocidos están convertidos en tests o documentados.
