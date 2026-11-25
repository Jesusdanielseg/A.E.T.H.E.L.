# A.E.T.H.E.L.

**Automated Execution & Technical Handling Environment Logic**

A.E.T.H.E.L. es un proyecto modular en Python que construye la base de un
asistente de consola. La Fase 04 ya incluye CLI, validación, presupuesto,
personalidad configurable, memoria conversacional en SQLite y un router de
proveedores con Ollama como opción principal, Gemini como respaldo y un modo
offline determinista.

> **Estado actual:** Ollama es el proveedor principal. `ping` se resuelve
> localmente sin consumir API. El resto de mensajes usa el orden configurado,
> registra tokens, latencia y coste estimado, y conserva el contexto en RAM y
> SQLite. Las herramientas del sistema, la voz y la memoria a largo plazo
> todavía no están implementadas.

## Funcionalidades implementadas

- Interfaz de consola con `ping`, mensajes y comandos de estado.
- Validación de mensajes vacíos y límite de 2000 caracteres.
- IDs de petición para correlacionar respuestas y registros.
- Contrato `ProveedorLLM` desacoplado de Google mediante Clean Architecture.
- Router configurable con Ollama, Gemini y proveedor offline.
- Ollama local con pensamiento desactivado por defecto (`OLLAMA_THINK=false`),
  contexto y límite de salida configurables.
- Cliente Gemini con reintentos, timeout y modelos fallback configurables.
- Memoria conversacional híbrida RAM + SQLite con sesiones, compactación,
  retención y cifrado Fernet opcional.
- Comandos CLI `/modelo`, `/estado`, `/memoria` y `/limpiar`.
- Presupuesto acumulado configurable con `LLM_BUDGET_USD`.
- Logs en consola y en `logs/aethel.log`, con rotación y censura básica.
- Comprobación de salud de almacenamiento, logs y clave de IA.
- Candado de instancia y cierre ordenado ante Ctrl+C, Ctrl+D o SIGTERM.
- Pruebas automatizadas con `pytest`, `ruff` y `mypy`.

## Requisitos

- Python 3.11 o posterior.
- `pip`.
- Ollama instalado y su servicio activo para usar el proveedor local.

## Instalación

Desde la raíz del repositorio:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Para ejecutar pruebas y análisis estático:

```bash
python -m pip install -r requirements-dev.txt
```

En Windows, activa el entorno con:

```powershell
.venv\Scripts\Activate.ps1
```

La configuración se lee de variables de entorno y, si está instalado
`python-dotenv`, de un archivo `.env` en la raíz. Para usar Gemini necesitas
una API key válida; Ollama no requiere clave.

Copia `.env.example` como `.env` y ajusta lo necesario:

```dotenv
ENVIRONMENT=development
DB_PATH=database/aethel.db

LLM_PROVIDER_ORDER=ollama,gemini,offline

OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_THINK=false
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=512
OLLAMA_KEEP_ALIVE=30m
OLLAMA_TIMEOUT_SECONDS=120

AI_API_KEY=tu_clave_sin_comillas
AI_MODEL=gemini-3.8-flash
AI_FALLBACK_MODELS=gemini-3.5-flash-lite,gemini-3.1-flash-lite

LLM_BUDGET_USD=0.50
CONTEXT_RETENTION_DAYS=30
CONTEXT_ENCRYPTION_KEY=
```

`LLM_PROVIDER_ORDER` controla el orden global de estrategias. Ollama no
requiere una API key. `OLLAMA_THINK=false` es importante con modelos Qwen3:
sin esa opción el modelo puede gastar decenas de segundos en razonamiento
interno antes de responder. `OLLAMA_NUM_CTX` y `OLLAMA_NUM_PREDICT` acotan el
contexto y la salida para mantener la latencia y el uso de memoria bajo
control. `OLLAMA_KEEP_ALIVE` evita recargar el modelo entre mensajes.

`CONTEXT_ENCRYPTION_KEY` cifra el historial local; si se pierde, el historial
no puede recuperarse. `LLM_BUDGET_USD` es un límite local acumulado por
ejecución, no una garantía de facturación del proveedor.

La personalidad se configura externamente en
[`prompts/persona.yaml`](./prompts/persona.yaml). Puedes cambiar el modo sin
modificar Python:

```dotenv
PERSONALITY_MODE=enfoque
```

Consulta [`docs/personality.md`](./docs/personality.md) para conocer los
modos, reglas de situaciones serias y pruebas del perfil.

## Ejecutar la interfaz

Con el entorno virtual activado:

```bash
python -m src.main
```

Para una guía paso a paso, consulta [`docs/testing-guide.md`](./docs/testing-guide.md).
La evaluación de cierre de Fase 04 está en
[`docs/evaluation-04.md`](./docs/evaluation-04.md); los resultados y las
limitaciones están en
[`docs/evaluation-04-results.md`](./docs/evaluation-04-results.md).

Prueba rápida:

| Entrada | Resultado esperado |
|---|---|
| `ping` | `pong (núcleo operativo)` |
| `Hola` | Respuesta generada por Ollama (o el proveedor disponible) |
| `/modelo` | Proveedor, modelo y latencia de la última consulta |
| `/estado` | Proveedor, latencia, tokens y coste acumulado |
| `/memoria` | Estado de la sesión y ventana activa |
| `/limpiar` | Borra la memoria de la sesión actual |
| Solo Enter | Aviso de que el mensaje no puede estar vacío; la CLI sigue activa |
| `salir`, `exit` o `quit` | Cierre ordenado de la interfaz |

Cada respuesta muestra un ID de petición. Ctrl+D también termina la entrada;
Ctrl+C y SIGTERM inician el apagado ordenado. Los logs se guardan en
`logs/aethel.log`.

## Rendimiento local

El hardware de referencia de este repositorio es una CPU de 12 hilos, 15 GB
de RAM y una GPU de 6 GB de VRAM. El modelo por defecto es `gemma3:4b`
(Q4_K_M, 3.4 GB en disco): ocupa unos 2.9 GB de VRAM y se ejecuta al 100 % en
GPU, dejando margen para el contexto. En caliente, una respuesta simple tarda
~0.6-2.2 s y un diagnóstico de 5 pasos ~6-10 s; la primera carga ronda los
9-14 s.

`qwen3:8b` se probó como alternativa. Aunque `OLLAMA_THINK=false` eliminaba el
razonamiento largo (de ~44 s a ~7-10 s en respuestas simples con el perfil
completo), seguía usando ~6.6 GB y repartía carga entre CPU y GPU. Se retiró
para liberar VRAM. `qwen3:4b` también se probó y se descartó porque, con esta
versión de Ollama, seguía exponiendo razonamiento interno aunque
`OLLAMA_THINK=false`.

Si la latencia sigue siendo alta, reduce `OLLAMA_NUM_CTX` o
`OLLAMA_NUM_PREDICT`, o usa un modelo aún más pequeño. `OLLAMA_NUM_PREDICT=512`
acota la salida; súbelo solo si necesitas respuestas largas.

## Ejecutar las pruebas

```bash
python -m pytest -q
```

También se puede ejecutar solo la suite de la interfaz:

```bash
python -m pytest -q tests/test_cli.py
```

Comprobaciones estáticas:

```bash
ruff check src tests
mypy src tests
```

## Estructura actual

```text
src/
├── core/
│   ├── config.py       # Configuración del entorno
│   ├── controller.py   # Validación y orquestación del flujo
│   ├── exceptions.py   # Excepciones del dominio
│   ├── health.py       # Comprobaciones de salud
│   ├── lifecycle.py    # Candado, señales y apagado
│   └── logger.py       # Logging e IDs de petición
├── context/            # Memoria, sanitización, personalidad y SQLite
│   ├── manager.py
│   ├── prompt_builder.py
│   ├── sanitizer.py
│   └── store.py
├── llm/                # Contrato, adaptadores y router
│   ├── base.py
│   ├── gemini_provider.py
│   ├── ollama_provider.py
│   ├── offline_provider.py
│   └── router.py
├── infrastructure/
│   └── gemini_client.py
├── interfaces/
│   └── cli.py
└── main.py
```

Los módulos `src/ai/`, `src/memory/`, `src/tools/` y
`src/core/dispatcher.py` están reservados para fases posteriores y contienen
solo marcadores de posición. No forman parte del flujo actual.

## Documentación adicional

- [`docs/architecture.md`](./docs/architecture.md): arquitectura real de Fase 04
  y componentes planificados.
- [`docs/data-flow.md`](./docs/data-flow.md): flujo actual de una petición.
- [`docs/testing-guide.md`](./docs/testing-guide.md): pruebas manuales y
  diagnóstico.
- [`docs/evaluation-04.md`](./docs/evaluation-04.md): protocolo de evaluación
  inicial 04.5.
- [`docs/evaluation-04-results.md`](./docs/evaluation-04-results.md):
  resultados, fallos corregidos y limitaciones de la evaluación 04.5.
- [`docs/personality.md`](./docs/personality.md): personalidad configurable.
- [`docs/safety-policy.md`](./docs/safety-policy.md): política objetivo de
  seguridad, con el estado actual separado de lo planificado.
- [`docs/requirements.md`](./docs/requirements.md): requisitos y estado.

## Próximos pasos

1. Cerrar la evaluación 04.5 y registrar sus resultados.
2. Convertir los fallos reproducibles en tests de regresión.
3. Diseñar la migración de Fase 05 antes de implementar usuarios y memoria a
   largo plazo.
4. No habilitar herramientas que ejecuten acciones hasta definir permisos,
   confirmaciones y auditoría.
