# Logger y observabilidad

Archivo de implementación: [`src/core/logger.py`](../src/core/logger.py).

## Para qué sirve

Centraliza el registro de eventos en consola y en `logs/aethel.log`. Añade un ID
de petición a cada registro, limita el crecimiento del archivo mediante
rotación y trata de ocultar claves conocidas antes de emitir mensajes,
tracebacks o información de pila.

La configuración se activa llamando una vez a `configurar_logging()`, como
hace el punto de entrada. La función es idempotente respecto a sus propios
handlers: si se vuelve a llamar, reemplaza los handlers que creó antes en
lugar de añadir duplicados. Conserva los handlers instalados por otros
componentes.

## Imports y herramientas

- `logging`: API estándar de Python para niveles, records, formatters, filtros
  y handlers.
- `re`: expresiones regulares para buscar formatos conocidos de claves.
- `uuid`: genera IDs aleatorios; se usan ocho caracteres hexadecimales para un
  ID breve por defecto.
- `ContextVar`: mantiene el ID en el contexto de la tarea/hilo actual y evita
  una variable global compartida entre tareas asíncronas.
- `contextmanager` e `Iterator`: permiten exponer un bloque `with` que restaura
  el ID anterior al salir.
- `RotatingFileHandler`: rota el log al superar 5 MiB y conserva tres copias
  anteriores.
- `Path`: crea la ubicación del directorio de logs de forma independiente del
  directorio desde donde se ejecuta Python.
- `config`: aporta `AI_API_KEY` y el indicador del entorno de desarrollo.

## ID de petición

`_request_id_ctx` comienza con el valor `"system"`. `establecer_request_id()`
usa un ID proporcionado o genera uno nuevo y lo guarda en el contexto actual.
Los IDs se validan para aceptar solamente 1–128 caracteres alfanuméricos o los
separadores `.`, `_`, `:`, `-`; esto evita saltos de línea que falsifiquen
entradas del log.

```python
from src.core.logger import establecer_request_id

request_id = establecer_request_id()  # por ejemplo: "a1b2c3d4"
```

Cuando el ID solo debe vivir durante una operación, usa
`contexto_request_id()`. El contexto previo se restaura incluso cuando el
bloque termina con una excepción:

```python
from src.core.logger import contexto_request_id

with contexto_request_id("chat-42"):
    # Los logs de esta operación llevan [chat-42].
    ...
```

## Filtros

`RequestIdFilter` añade `record.request_id` para que el formato no falle si un
record viene de cualquier módulo. También aplica la censura al ID.

`SecretMaskingFilter` primero resuelve el mensaje con `record.getMessage()`,
censura `config.AI_API_KEY` y patrones conocidos (`sk-...` y `AIza...`), y
reemplaza `record.msg`/vacía `record.args`. Así evita que el formatter
reformatee los argumentos originales.

También limpia los tracebacks (`exc_info`), el texto de excepción ya calculado
(`exc_text`) y `stack_info`. Esto ayuda si una librería externa incluye una
clave en el error.

**Límite importante:** un filtro por patrones no garantiza que toda credencial
posible se oculte. No registres explícitamente secretos ni dependas del filtro
como sustituto de una política de no incluirlos en mensajes.

## Configuración y rotación

`configurar_logging()` deriva la raíz del proyecto desde la ubicación de este
módulo, crea `logs/` y prepara:

- `StreamHandler`: consola.
- `RotatingFileHandler`: `logs/aethel.log`, UTF-8, máximo de 5 MiB, tres
  respaldos.
- Un `Formatter` con fecha, nivel, ID y nombre del logger.
- Los dos filtros anteriores en ambos handlers.

El logger raíz acepta `DEBUG` en desarrollo y `INFO` en los demás entornos.
`logs/` está excluida por `.gitignore`.

## Niveles

- `debug`: detalles de diagnóstico; principalmente desarrollo.
- `info`: eventos normales como inicio, comprobaciones correctas y cierre.
- `warning`: degradación o situación recuperable.
- `error`: operación fallida.
- `critical`: fallo que impide seguir operando con seguridad.

Ejemplo:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Solicitud aceptada")
logger.warning("Servicio temporalmente no disponible")
```
