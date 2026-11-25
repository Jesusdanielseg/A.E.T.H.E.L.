# Arranque y ciclo de vida

> **Estado 04.5:** parcialmente desactualizado. No incluye el router, el
> contexto, `config.validar()` ni el manejo de `sqlite3.Error`. Ver
> [`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md)
> y [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

Archivos: [`src/main.py`](../src/main.py),
[`src/interfaces/cli.py`](../src/interfaces/cli.py) y
[`src/core/lifecycle.py`](../src/core/lifecycle.py).

## Secuencia de arranque

`main()` conecta los servicios en este orden:

1. Configura logging. Si no puede crear o abrir el log, devuelve código 1.
2. Construye el gestor de ciclo de vida.
3. Ejecuta `verificar_salud(strict=True)`.
4. Construye `GeminiClient`, `GestorPresupuesto`, `ControladorCentral` y la CLI.
5. `lifecycle.iniciar()` valida configuración, adquiere el candado e instala
   los handlers de `SIGINT` y `SIGTERM`.
6. `cli.ejecutar()` procesa entradas hasta que el usuario salga o llegue una
   señal.
7. El bloque `finally` llama a `lifecycle.detener()` aunque ocurra un error.

La CLI espera dentro de `input()`; no existe un bucle activo consumiendo CPU.
Al llegar `SIGINT` o `SIGTERM`, el gestor ejecuta las tareas, restaura los
handlers anteriores, libera el candado y lanza `KeyboardInterrupt`. La CLI
captura esa interrupción en `_leer_entrada()` y termina sin traceback. El
`finally` de `main()` vuelve a llamar `detener()`, que no repite tareas si el
gestor ya quedó detenido.

El `KeyboardInterrupt` también representa Ctrl+C durante la ejecución normal.
En ambos casos se registra el cierre como normal y el proceso devuelve código
0 si la limpieza termina correctamente.

## Tareas de cierre

`registrar_tarea_cierre()` acepta una función sin argumentos. El gestor ejecuta
las funciones en orden inverso al registro, igual que una pila de recursos:
primero cierra lo adquirido al final.

```python
lifecycle.registrar_tarea_cierre(cerrar_base_datos)
lifecycle.registrar_tarea_cierre(cerrar_cliente_http)
```

En este ejemplo el cliente HTTP se cierra primero y la base de datos después.
Si una función lanza una excepción, se intentan ejecutar las tareas restantes,
se liberan señales/candado y finalmente se informa el error.

## Candado de instancia y plataformas

El archivo de bloqueo predeterminado es `aethel.lock` junto a la base de datos.
Se abre sin truncarlo y queda bloqueado mientras el file handle permanezca
abierto:

- POSIX (Linux/macOS): `fcntl.flock` con bloqueo exclusivo no bloqueante.
- Windows: `msvcrt.locking` sobre el primer byte del archivo.

El candado evita dos instancias que usan la misma ruta de bloqueo. Es un
bloqueo local del sistema de archivos, no un mecanismo distribuido para
coordinar máquinas distintas o volúmenes de red con semántica desconocida.

## Señales y restauración

Al iniciar, se guardan los handlers previos y se registran handlers para
`SIGINT` y `SIGTERM`. Una señal causa esta secuencia: registro informativo,
`detener()`, ejecución de tareas LIFO, restauración de handlers, liberación del
candado y una interrupción controlada para abandonar una lectura bloqueada.
Si el registro de señales durante el inicio falla, la inicialización revierte
los recursos ya adquiridos.

Los handlers de Python solo pueden instalarse desde el hilo principal. Si se
intenta iniciar el gestor desde otro hilo, `signal.signal()` puede lanzar
`ValueError`; el gestor hace rollback del inicio.

## Context manager

El gestor soporta `with`; al salir del bloque, llama a `detener()`:

```python
with LifecycleManager() as lifecycle:
    ...
```

El punto de entrada usa explícitamente `try/finally`, porque allí también se
manejan códigos de salida y señales.

## Tratamiento de errores en `main`

- `CriticalError`: registra `critical` y devuelve código 1.
- `RuntimeError`, `ValueError` u `OSError`: registra el fallo y devuelve 1.
- `KeyboardInterrupt`: registra cierre ordenado; devuelve 0 si no falla la
  limpieza.
- Errores inesperados no se silencian: se propagan, pero el `finally` aún
  intenta apagar el ciclo de vida.
- El `finally` siempre intenta `lifecycle.detener()`.

La limpieza fallida se registra con traceback y cambia el código de salida a 1.
Si ya había una excepción inesperada, se conserva su propagación.
