# Controlador central

Implementación: [`src/core/controller.py`](../src/core/controller.py).
Interfaz que lo consume: [`src/interfaces/cli.py`](../src/interfaces/cli.py).

## Responsabilidad y arquitectura

`ControladorCentral` es parte del núcleo: no lee de `input()` ni imprime en
consola. Recibe un proveedor LLM, un gestor de presupuesto y, opcionalmente,
un `ContextManager` por inyección. Valida el contenido, construye el prompt
con memoria, produce una respuesta y registra el consumo. No conoce Gemini,
Ollama ni ningún SDK externo.

## Contratos de datos

`MensajeEntrada` contiene el texto y su origen (`"interfaz_interna"` por
defecto). `RespuestaSalida` contiene el ID para correlacionar logs y respuesta, el texto y una marca `simulada`.
La marca solo es `True` para `ping`, que se resuelve localmente.
Ambos son `@dataclass(frozen=True)`, por lo que sus campos no se reasignan tras
la construcción.

```python
entrada = MensajeEntrada(contenido="ping", origen="cli")
salida = RespuestaSalida(
    request_id="a1b2c3d4",
    contenido="pong (núcleo operativo)",
)
```

## Flujo de `procesar_mensaje`

1. `establecer_request_id()` genera un ID de ocho caracteres y lo fija en el
   contexto actual del logger.
2. Se registra el origen, nunca el contenido completo del mensaje.
3. `_validar_mensaje()` limpia el texto y aplica reglas.
4. Si el texto es `ping`, devuelve la respuesta local sin presupuesto ni red.
5. Verifica el presupuesto disponible.
6. Si existe contexto, persiste el turno de usuario y lo incluye en el prompt.
7. Invoca `ProveedorLLM.generar_respuesta()`. El router decide el proveedor.
8. Persiste la respuesta y compacta la ventana si supera sus límites.
9. Registra tokens y coste mediante `GestorPresupuesto`.
10. Se registra la longitud resultante y se devuelve `RespuestaSalida`.

El ID generado se propaga en el objeto retornado para que la CLI muestre el
mismo valor que aparece en cada log producido durante esa operación.

## Validación

- Se eliminan espacios exteriores con `strip()`.
- Un texto vacío o solo con espacios genera `RecoverableError`.
- El límite es 2000 caracteres; 2000 se acepta y 2001 se rechaza.

El error recuperable es adecuado porque se puede descartar esa entrada y seguir
leyendo la siguiente. La interfaz captura el tipo, muestra el aviso y mantiene
el bucle.

## Diagnóstico local y respuesta real

`ping` se compara sin distinguir mayúsculas (`texto.lower()`) y devuelve
`"pong (núcleo operativo)"`. Todo otro texto se envía al proveedor inyectado y
devuelve el contenido real del modelo. El controlador no necesita saber si el
proveedor es Gemini, un fake de pruebas o una futura implementación local.

## Pruebas

[`tests/test_controller.py`](../tests/test_controller.py) valida trimming,
request ID, respuesta de ping, límite, errores de texto vacío/excesivo,
inyección del proveedor, registro de presupuesto, bloqueo por límite y la
inmutabilidad de los contratos.
