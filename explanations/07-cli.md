# Interfaz de línea de comandos

> **Estado 04.5:** desactualizado en comandos. La CLI actual también admite
> `/memoria`, `/limpiar`, `/modelo` y `/estado`. Ver
> [`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md)
> y [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

Implementación: [`src/interfaces/cli.py`](../src/interfaces/cli.py).

## Inyección de dependencias

`InterfazCLI` recibe una instancia de `ControladorCentral` en `__init__`.
La CLI no construye su propio controlador ni conoce las reglas internas del
procesamiento; solo adapta texto de consola a `MensajeEntrada` y presenta
`RespuestaSalida`.

```python
controlador = ControladorCentral()
cli = InterfazCLI(controlador)
cli.ejecutar()
```

Esta separación permite probar la interfaz con un controlador falso sin usar
red, base de datos ni ciclo de vida real.

## Lectura y comandos de salida

`_leer_entrada()` encapsula `input("\nTú > ")`. Devuelve el texto leído o
`None` si el usuario presiona Ctrl+C (`KeyboardInterrupt`) o Ctrl+D (`EOFError`).
La CLI reconoce `salir`, `exit` y `quit`, ignorando mayúsculas y espacios
exteriores.

Al recibir `None` o un comando de salida, registra el motivo y termina el bucle
con normalidad.

## Procesamiento de mensajes

Para cada texto normal:

1. Construye `MensajeEntrada(contenido=entrada, origen="cli")`.
2. Llama al controlador inyectado.
3. Imprime `A.E.T.H.E.L. [request_id] > respuesta`.
4. Si el controlador lanza `RecoverableError`, registra un warning, muestra un
   aviso y vuelve a pedir entrada.

Solo se captura `RecoverableError`; errores inesperados no se disfrazan como un
problema de usuario y pueden ser gestionados por el proceso superior.

## SIGINT/SIGTERM durante `input()`

El `LifecycleManager` instala los handlers de señal antes de que arranque la
CLI. Cuando recibe SIGINT o SIGTERM, completa el apagado (tareas, restauración
de handlers y liberación del lock) y luego lanza `KeyboardInterrupt`. Ese tipo
es capturado por `_leer_entrada()`, que devuelve `None`; por ello, el bucle
termina limpiamente sin dejar `input()` bloqueado después de liberar el lock.

La misma ruta cubre Ctrl+C interactivo. Ctrl+D genera `EOFError` y produce una
salida normal sin requerir una señal del sistema.

## Pruebas

[`tests/test_cli.py`](../tests/test_cli.py) cubre los comandos de salida,
respuesta de ping y texto normal, error recuperable seguido de otra entrada,
EOF/Ctrl+C y señales de terminación recibidas mientras se espera entrada.
