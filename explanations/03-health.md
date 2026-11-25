# Comprobaciones de salud

Archivo de implementación: [`src/core/health.py`](../src/core/health.py).

## Qué comprueba

`verificar_salud(strict=False)` comprueba tres componentes:

1. **`almacenamiento`**: el directorio que contiene `config.DB_PATH` debe
   aceptar escritura real y tener al menos 100 MiB libres.
2. **`logs`**: el directorio `logs/` del proyecto debe aceptar escritura.
3. **`api_key`**: `config.AI_API_KEY` no debe estar vacía ni contener solo
   espacios.

No realiza una llamada de red a Gemini: la comprobación de API solo detecta si
hay una clave configurada. No confirma que sea válida o que el proveedor esté
disponible.

## Funciones auxiliares

`_es_escribible(directorio)` crea el directorio si falta, consulta
`os.access(..., os.W_OK)` y después intenta crear un archivo temporal real.
La prueba real evita confiar únicamente en bits de permisos, que no siempre
reflejan la capacidad efectiva de escribir (por ejemplo, con ACL o sistemas de
archivos especiales). El archivo temporal se elimina al salir del `with`.

`_tiene_espacio_disco(directorio, minimo_mb=100)` usa
`shutil.disk_usage()` y compara los bytes libres con `minimo_mb * 1024 * 1024`.
Un umbral negativo es un error de entrada (`ValueError`), no un estado de
salud válido.

Los errores `OSError` al comprobar rutas o disco se expresan como `False`;
luego el reporte explica cuál comprobación no se pudo completar.

## Reporte inmutable

`HealthReport` es una dataclass congelada. `estado` está tipado como uno de:

- `healthy`: almacenamiento, logs y API key disponibles.
- `degraded`: almacenamiento y logs operativos, API key ausente.
- `unhealthy`: almacenamiento o logs no disponibles.

`componentes` y `detalles` se copian y envuelven en `MappingProxyType`, de modo
que el consumidor no pueda mutar accidentalmente el contenido del reporte.

## Uso y modo estricto

```python
from src.core.health import verificar_salud

reporte = verificar_salud()
print(reporte.estado)
print(reporte.componentes["almacenamiento"])
```

Con `strict=True`, el estado `unhealthy` registra el error y lanza
`CriticalError`. El estado `degraded` se devuelve normalmente: la ausencia de
API key no impide que arranque el núcleo.

```python
from src.core.exceptions import CriticalError
from src.core.health import verificar_salud

try:
    reporte = verificar_salud(strict=True)
except CriticalError as exc:
    # El llamador puede dejar de arrancar y hacer limpieza.
    ...
```

La función escribe en el logger `src.core.health`; configura primero el
logging central si quieres que el reporte vaya a consola y archivo.
