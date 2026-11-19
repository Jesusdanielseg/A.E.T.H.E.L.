# A.E.T.H.E.L.

**Automated Execution & Technical Handling Environment Logic**

A.E.T.H.E.L. es un proyecto modular en Python que está construyendo la base de
un asistente de consola. Incluye una CLI funcional, validación de entradas,
control de presupuesto, integración con Gemini, registro de eventos y apagado
ordenado.

> **Estado actual:** `ping` se resuelve localmente sin consumir API. Los demás
> mensajes usan el orden de proveedores configurado (Ollama, Gemini u offline)
> y registran tokens, latencia y coste estimado. El contexto se mantiene en RAM
> y se persiste en SQLite; las herramientas del sistema todavía no están
> integradas.

## Funcionalidades implementadas

- Interfaz de consola con `ping`, mensajes de prueba y comandos para salir.
- Validación de mensajes vacíos y límite de 2000 caracteres.
- IDs de petición para correlacionar respuestas y registros.
- Contrato `ProveedorLLM` desacoplado de Google mediante Clean Architecture.
- Cliente Gemini con reintentos, timeout y modelos fallback configurables.
- Router configurable con Gemini, Ollama local y proveedor offline.
- Memoria conversacional híbrida RAM + SQLite con sesiones, compactación,
  retención y cifrado Fernet opcional.
- Comandos CLI `/modelo`, `/memoria` y `/limpiar`.
- Presupuesto acumulado configurable; el valor actual de arranque es `$0.50`.
- Logs en consola y en `logs/aethel.log`, con rotación y censura básica de
  claves reconocidas.
- Comprobación de salud de los directorios de almacenamiento y logs, y aviso
  cuando falta la clave de IA.
- Candado de instancia y cierre ordenado ante Ctrl+C, Ctrl+D o SIGTERM.
- Pruebas automatizadas con `pytest`.

## Requisitos

- Python 3.10 o posterior.
- `pip`.

## Instalación

Desde la raíz del repositorio:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Windows, activa el entorno con:

```powershell
.venv\Scripts\Activate.ps1
```

La configuración se lee de las variables de entorno y, si está instalado
`python-dotenv`, de un archivo `.env` en la raíz. Para usar mensajes reales
necesitas una API key válida del proveedor configurado.

Opcionalmente, crea `.env` para personalizar el entorno:

```dotenv
ENVIRONMENT=development
DB_PATH=database/aethel.db
AI_PROVIDER=gemini
AI_API_KEY=tu_clave_sin_comillas
AI_MODEL=gemini-3.8-flash
AI_FALLBACK_MODELS=gemini-3.5-flash-lite,gemini-3.1-flash-lite
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SECONDS=120
LLM_PROVIDER_ORDER=ollama,gemini,offline
CONTEXT_RETENTION_DAYS=30
# Opcional: clave Fernet generada fuera del código
CONTEXT_ENCRYPTION_KEY=
```

`AI_FALLBACK_MODELS` es una lista separada por comas. Si el modelo principal
responde con saturación, indisponibilidad o un error recuperable, el cliente
intentará los modelos alternativos. No publiques claves ni agregues `.env` al
repositorio. Si una clave se expone, revócala y genera otra.

`LLM_PROVIDER_ORDER` controla el orden global de estrategias. Ollama no
requiere una API key. `CONTEXT_ENCRYPTION_KEY` cifra el historial local; si se
pierde, el historial no puede recuperarse.

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

Prueba rápida:

| Entrada | Resultado esperado |
|---|---|
| `ping` | `pong (núcleo operativo)` |
| `Hola` | Respuesta generada por Gemini |
| `/modelo` | Proveedor usado y latencia de la última consulta |
| `/memoria` | Estado de la sesión y ventana activa |
| `/limpiar` | Borra la memoria de la sesión actual |
| Solo Enter | Aviso de que el mensaje no puede estar vacío; la CLI sigue activa |
| `salir`, `exit` o `quit` | Cierre ordenado de la interfaz |

Cada respuesta muestra un ID de petición. Ctrl+D también termina la entrada;
Ctrl+C y SIGTERM inician el apagado ordenado. Los logs se guardan en
`logs/aethel.log`.

## Ejecutar las pruebas

```bash
python -m pytest -q
```

También se puede ejecutar solo la suite de la interfaz:

```bash
python -m pytest -q tests/test_cli.py
```

Si Ruff y mypy están instalados, ejecuta las comprobaciones estáticas:

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
├── context/              # Memoria, sanitización, personalidad y SQLite
│   ├── manager.py
│   ├── prompt_builder.py
│   ├── sanitizer.py
│   └── store.py
├── llm/                  # ABC, adaptadores y router
│   ├── base.py
│   ├── gemini_provider.py
│   ├── ollama_provider.py
│   ├── offline_provider.py
│   └── router.py
├── infrastructure/
│   └── gemini_client.py # Adaptador del proveedor Gemini
├── interfaces/
│   └── cli.py          # Interfaz de consola
└── main.py             # Punto de entrada
tests/                  # Pruebas automatizadas
docs/                   # Notas de arquitectura y flujo previsto
```

Hay directorios preparados para componentes futuros, como personalidad
avanzada, herramientas y automatizaciones. La memoria y la abstracción LLM sí
forman parte del flujo funcional actual.

## Próximos pasos

1. Definir permisos y límites antes de habilitar herramientas que ejecuten
   acciones.
2. Añadir migraciones de esquema posteriores cuando evolucionen las tablas.
3. Implementar herramientas con auditoría y confirmación explícita.

## Documentación adicional

Los documentos de arquitectura disponibles están en [`docs/`](./docs/).
Las explicaciones locales y copias didácticas están en `explanations/`, una
carpeta excluida de Git según la configuración del proyecto.
