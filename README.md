# A.E.T.H.E.L.

**Automated Execution & Technical Handling Environment Logic**

A.E.T.H.E.L. es un proyecto modular en Python que está construyendo la base de
un asistente de consola. En su estado actual incluye una CLI funcional para
probar el flujo de mensajes, validación de entradas, registro de eventos y
apagado ordenado.

> **Estado actual:** la respuesta del asistente es simulada. La CLI todavía no
> consulta Gemini ni otro proveedor de IA, no ejecuta herramientas del sistema
> y no persiste conversaciones en una base de datos.

## Funcionalidades implementadas

- Interfaz de consola con `ping`, mensajes de prueba y comandos para salir.
- Validación de mensajes vacíos y límite de 2000 caracteres.
- IDs de petición para correlacionar respuestas y registros.
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

La CLI de demostración puede iniciarse en desarrollo sin una API key. La
configuración se lee de las variables de entorno y, si está instalado
`python-dotenv`, de un archivo `.env` en la raíz.

Opcionalmente, crea `.env` para personalizar el entorno:

```dotenv
ENVIRONMENT=development
DB_PATH=database/aethel.db
AI_PROVIDER=gemini
AI_API_KEY=
AI_MODEL=gemini-1.5-flash
```

`AI_API_KEY` no se usa para generar las respuestas simuladas. Sin clave, el
chequeo de salud informará estado `degraded`, pero la CLI de demostración puede
seguir funcionando. No publiques claves ni agregues `.env` al repositorio.

## Ejecutar la interfaz

Con el entorno virtual activado:

```bash
python -m src.main
```

Prueba estos mensajes:

| Entrada | Resultado esperado |
|---|---|
| `ping` | `pong (núcleo operativo)` |
| `Hola` | Respuesta de demostración que indica que el texto fue procesado |
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
│   ├── controller.py   # Validación y procesamiento simulado
│   ├── exceptions.py   # Excepciones del dominio
│   ├── health.py       # Comprobaciones de salud
│   ├── lifecycle.py    # Candado, señales y apagado
│   └── logger.py       # Logging e IDs de petición
├── interfaces/
│   └── cli.py          # Interfaz de consola
└── main.py             # Punto de entrada
tests/                  # Pruebas automatizadas
docs/                   # Notas de arquitectura y flujo previsto
```

Hay directorios preparados para componentes futuros, como IA, memoria y
herramientas; aún no forman parte del flujo funcional de la CLI.

## Próximos pasos

1. Integrar un proveedor de IA detrás de una interfaz desacoplada.
2. Definir permisos y límites antes de habilitar herramientas que ejecuten
   acciones.
3. Implementar persistencia de conversaciones y pruebas de integración.
4. Actualizar los diagramas de arquitectura al conectar esos componentes.

## Documentación adicional

Los documentos de arquitectura disponibles están en [`docs/`](./docs/).
Las explicaciones locales y copias didácticas están en `explicaciones/`, una
carpeta excluida de Git según la configuración del proyecto.
