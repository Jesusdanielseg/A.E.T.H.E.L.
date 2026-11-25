# Jerarquía de excepciones

Archivo de implementación: [`src/core/exceptions.py`](../src/core/exceptions.py).

## Objetivo

Las clases propias distinguen fallos esperados del dominio de errores
inesperados del intérprete y separan fallos que permiten continuar de los que
requieren detener el asistente.

```text
Exception
└── AethelError
    ├── RecoverableError
    │   ├── ExternalServiceError
    │   └── ToolExecutionError
    └── CriticalError
        ├── ConfigurationError
        └── InstanceLockError
```

## Excepción base

`AethelError(mensaje, detalle=None)` conserva por separado `mensaje` y
`detalle`. Su representación de texto queda como `mensaje (detalle)` cuando se
proporciona detalle; sin detalle, muestra solamente el mensaje.

```python
from src.core.exceptions import AethelError

error = AethelError("No se pudo completar la operación", "timeout")
print(error.mensaje)  # No se pudo completar la operación
print(error.detalle)  # timeout
print(str(error))     # No se pudo completar la operación (timeout)
```

## Recuperables y críticos

- `RecoverableError`: una parte puntual puede fallar sin invalidar el proceso.
  Ejemplos: `ExternalServiceError` para fallos temporales de API/red y
  `ToolExecutionError` para una herramienta fallida.
- `CriticalError`: continuar es inseguro o inútil. Ejemplos:
  `ConfigurationError` para configuración inválida y `InstanceLockError` para
  el bloqueo de instancia.

Capturar por categoría facilita reaccionar sin depender de textos:

```python
from src.core.exceptions import CriticalError, RecoverableError

try:
    ejecutar_operacion()
except CriticalError:
    solicitar_apagado_ordenado()
except RecoverableError:
    registrar_y_continuar()
```

El orden importa: las clases concretas heredan de esas categorías, así que el
`except` más específico debe ir antes de cualquier captura general de
`AethelError` o `Exception`.

## Estado actual de integración

La jerarquía proporciona los tipos del dominio, pero algunos productores aún
usan excepciones estándar: `config.validar()` lanza `ValueError` y la
contención del candado de `LifecycleManager` lanza `RuntimeError`. `main.py`
todavía captura esos tipos por separado. `verificar_salud(strict=True)` sí
lanza `CriticalError`. Al migrar los productores a `ConfigurationError` e
`InstanceLockError`, hay que actualizar conjuntamente sus pruebas y las
capturas de `main.py`.

## Excepciones con causa

Al traducir una excepción externa a una excepción de A.E.T.H.E.L., conserva su
causa con `raise ... from exc`. Esto mantiene el traceback para depuración:

```python
try:
    llamar_servicio()
except TimeoutError as exc:
    raise ExternalServiceError("Falló el servicio", "timeout") from exc
```

No incluyas tokens ni contenido privado en `mensaje` o `detalle`: pueden
terminar registrados por el llamador.
