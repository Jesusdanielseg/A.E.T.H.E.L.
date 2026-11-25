# Contrato LLM y control de presupuesto

> **Estado 04.5:** el contrato del núcleo sigue vigente. La integración con el
> router, `LLM_BUDGET_USD` y las opciones de Ollama se explica en
> [`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md).
> Ver también [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

Implementación: [`src/core/llm.py`](../src/core/llm.py).
Pruebas: [`tests/test_llm.py`](../tests/test_llm.py).

## Objetivo arquitectónico

El núcleo no debe importar un SDK de Gemini, OpenAI ni un cliente HTTP
concreto. `ProveedorLLM` usa `typing.Protocol` para describir la operación que
necesita el núcleo:

```python
def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
    ...
```

Cualquier cliente que implemente esa firma puede utilizarse aunque no herede de
una clase base. El cliente real vivirá en infraestructura y devolverá el DTO
`RespuestaLLM`.

## `RespuestaLLM`

La respuesta es un `@dataclass(frozen=True)`, por lo que sus métricas no se
pueden modificar después de crearla. Contiene:

- `contenido`: texto no vacío devuelto por el modelo.
- `modelo`: identificador no vacío del modelo utilizado.
- `tokens_entrada` y `tokens_salida`: contadores enteros no negativos.
- `coste_usd`: coste finito y no negativo de la petición.

`__post_init__()` valida estas invariantes inmediatamente. Se rechazan
respuestas vacías, modelos vacíos, tokens negativos, tipos de token incorrectos
y valores `NaN` o infinitos. Esto evita contaminar los cálculos posteriores con
métricas imposibles.

## `GestorPresupuesto`

El gestor recibe un límite finito y no negativo en dólares. Inicializa:

```python
gasto_acumulado = 0.0
tokens_totales = 0
```

`verificar_disponibilidad()` lanza `RecoverableError` cuando el gasto es igual
o superior al límite. Es recuperable porque la aplicación puede rechazar esa
consulta y continuar atendiendo otras funciones sin apagar el proceso.

`registrar_uso()` suma el coste y los dos tipos de tokens, y registra el modelo,
los tokens de la petición, el coste individual y el acumulado. Si una respuesta
lleva el gasto por encima del límite, se registra una advertencia; la
verificación de la siguiente petición será la que la rechace.

## Concurrencia

El acumulador utiliza `threading.Lock` para proteger las lecturas y escrituras
de `gasto_acumulado` y `tokens_totales`. El método privado
`_verificar_disponibilidad_sin_bloqueo()` solo se llama con el lock adquirido,
evitando un bloqueo doble accidental.

El lock protege el estado en memoria dentro del proceso. No sustituye una
política de presupuesto distribuida entre varios procesos o instancias.

## Flujo previsto del cliente

El futuro controlador o servicio de aplicación seguirá este orden:

1. Validar el mensaje de usuario.
2. Ejecutar `verificar_disponibilidad()`.
3. Invocar `ProveedorLLM.generar_respuesta()`.
4. Ejecutar `registrar_uso(respuesta)`.
5. Devolver `respuesta.contenido`.

El cliente de infraestructura será responsable de timeouts, reintentos y
traducción de errores externos a excepciones del dominio. `llm.py` no conoce
red, credenciales ni SDKs.

## Pruebas

`tests/test_llm.py` verifica:

- Inmutabilidad de `RespuestaLLM`.
- Inicio del presupuesto en cero.
- Acumulación correcta de coste y tokens.
- Registro del modelo y del acumulado.
- Rechazo al alcanzar el límite.
- Aceptación mientras el gasto permanece por debajo del límite.
- Rechazo de límites inválidos.
- Rechazo de métricas negativas, no enteras, `NaN` o infinitas.
- Rechazo de contenido o nombres de modelo vacíos.

Comandos:

```bash
.venv/bin/python -m pytest -q tests/test_llm.py
.venv/bin/ruff check src/core/llm.py tests/test_llm.py
.venv/bin/mypy src/core/llm.py tests/test_llm.py
```

La carpeta `explanations/` es local e ignorada por Git; este documento sirve
como material de estudio y no es una segunda fuente de ejecución.
