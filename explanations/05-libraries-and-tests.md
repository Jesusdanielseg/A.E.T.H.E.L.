# Bibliotecas y pruebas usadas

Los módulos del bloque usan principalmente la biblioteca estándar de Python.
No se añade una dependencia de terceros para logging, señales, salud ni
excepciones.

## Referencia rápida de bibliotecas

| Biblioteca / símbolo | Uso en el proyecto |
|---|---|
| `logging` | Crea loggers, niveles, records, filtros, formatos y salida. |
| `logging.handlers.RotatingFileHandler` | Rota el archivo de log por tamaño y retiene respaldos. |
| `re` | Reconoce patrones de claves externas y valida IDs de petición. |
| `uuid` | Genera un identificador breve cuando no se proporciona uno. |
| `contextvars.ContextVar` | Mantiene IDs aislados por contexto de ejecución. |
| `contextlib.contextmanager` | Implementa `contexto_request_id()` como bloque `with`. |
| `pathlib.Path` | Une rutas y crea directorios sin depender del directorio actual. |
| `os` | Consulta permisos, detecta la plataforma y usa `SEEK_END`. |
| `fcntl` | Bloquea el archivo de instancia en sistemas POSIX. |
| `msvcrt` | Bloquea un byte del archivo en Windows. |
| `errno` | Identifica errores de contención del candado en Windows. |
| `signal` | Registra y restaura handlers para `SIGINT` y `SIGTERM`. |
| `input` | Lee una línea de la consola; `EOFError` y `KeyboardInterrupt` se convierten en salida. |
| `shutil.disk_usage` | Consulta el espacio libre de la partición. |
| `tempfile.NamedTemporaryFile` | Prueba que se puede crear un archivo real en el directorio. |
| `dataclasses.dataclass` | Define un objeto de reporte conciso. |
| `types.MappingProxyType` | Expone mapas de solo lectura dentro del reporte de salud. |
| `typing.Literal`, `Self`, `IO` | Documenta restricciones y tipos para análisis estático. |
| `sys.exit` | Convierte el resultado entero de `main()` en el código de salida. |
| `pickle` | En pruebas, verifica que una excepción conserva sus datos al serializarse. |
| `math` | Rechaza costes y límites `NaN`, infinitos o negativos. |
| `threading.Lock` | Protege el acumulador de presupuesto frente a accesos concurrentes. |
| `typing.Protocol` | Define un contrato estructural para proveedores LLM sin acoplar el núcleo a un SDK. |

`pytest` es una dependencia de desarrollo usada para pruebas. `monkeypatch`
reemplaza temporalmente funciones/atributos, `tmp_path` proporciona un
directorio aislado y `caplog` captura registros. Ruff y mypy son herramientas
de desarrollo para lint y tipos.

## Pruebas y su propósito

La suite actual tiene 17 archivos `test_*.py` y 125 casos. La tabla siguiente
resume qué cubre cada uno y en qué documento se explica su contexto.

| Archivo | Qué cubre | Documento |
|---|---|---|
| `tests/conftest.py` | Fixtures y configuración común de pytest. | Este documento |
| `tests/test_cli.py` | Inyección de dependencias, entrada/salida, errores recuperables, comandos de salida y señales durante `input()`. | `07`, este documento |
| `tests/test_cli_commands.py` | Comandos `/memoria`, `/modelo`, `/estado` y `/limpiar`; salida de sesión, modelo, tokens y coste. | `07`, `13` |
| `tests/test_config.py` | Valores por defecto de Ollama, `gemma3:4b`, `think=false`, presupuesto y rechazo de límites inválidos. | `13` |
| `tests/test_context.py` | Saneamiento, persistencia, recarga, ventana, compactación, resumen previo, retención, timeout, cifrado y migración. | `12`, `16` |
| `tests/test_controller.py` | Validación, límites, `ping`, inmutabilidad, proveedor inyectado y presupuesto. | `06` |
| `tests/test_core.py` | Valores seguros por defecto de `MensajeEntrada` y `RespuestaSalida`. | `06` |
| `tests/test_evaluation_04.py` | Conversación larga con compactación persistida, afirmaciones contradictorias y guía de incertidumbre. | `13`, `16` |
| `tests/test_exceptions.py` | Herencia de severidad, formato y serialización con `pickle`. | `02` |
| `tests/test_gemini_client.py` | Respuesta estructurada, modelo, reintentos, credenciales inválidas, red, validación, fallback y backoff. | `10`, `17` |
| `tests/test_health.py` | Estados, clave ausente, proveedor local sin clave, modo estricto, escritura real y umbral de disco. | `03` |
| `tests/test_lifecycle.py` | Lock, señales, tareas, rollback, ruta Windows, restauración de handlers y apagado. | `04` |
| `tests/test_llm.py` | Inmutabilidad de respuestas, métricas inválidas, presupuesto y límites. | `08`, `17` |
| `tests/test_llm_abstraction.py` | ABC, DTO, fallback del router, router vacío y petición HTTP de Ollama con mock. | `11`, `17` |
| `tests/test_logger.py` | Filtros de secretos, excepciones, request IDs, contexto y configuración idempotente. | `01` |
| `tests/test_main.py` | Orden de arranque, health check, CLI, fallos de configuración, cierre y señales. | `04`, `13` |
| `tests/test_memory.py` | Marcador de posición; actualmente no contiene pruebas. | `09`, `15` |
| `tests/test_personality.py` | Identidad, estilo, modo serio, cambio de modo, booleanos naturales y perfiles inválidos. | `13`, `16` |

Los documentos `10`, `11`, `12`, `16` y `17` amplían la explicación de los tests
de Gemini, abstracción LLM, contexto y personalidad. El mapa histórico `09`
conserva la lista antigua y no debe usarse como inventario actual.

Las señales durante `input()` se verificaron con procesos reales en Linux:
SIGINT y SIGTERM terminan con código 0 y sin dejar ocupado el candado. Esto no
sustituye pruebas nativas del candado Windows.

Ejecutar validaciones desde la raíz del proyecto:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/mypy src tests
```

Los tests sustituyen señales, espacio disponible, filesystem y lifecycle para
ser deterministas y no depender de servicios externos. La ruta Windows del
candado probada en Linux es una simulación; una validación nativa requiere
ejecutar la suite en Windows.

## Buenas prácticas

- No uses `print()` para eventos operativos: usa un logger por módulo con
  `logging.getLogger(__name__)`.
- No registres claves, tokens, contraseñas ni datos privados en mensajes.
- Lanza errores de dominio en vez de comunicar errores mediante strings.
- Captura excepciones específicas; conserva la causa con `raise ... from exc`.
- Mantén cada prueba aislada y usa archivos temporales, no recursos reales.
