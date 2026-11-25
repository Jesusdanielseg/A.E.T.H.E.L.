# Mapa completo del código

> **Estado 04.5:** documento histórico. No incluye `src/context/`, el router,
> la CLI ampliada ni los cambios de configuración. No usarlo como mapa actual;
> ver [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

Este documento describe todos los archivos Python actuales del repositorio.
Los módulos vacíos son espacios reservados para fases posteriores; se
documentan para que quede claro qué responsabilidad tendrán y qué no hacen
todavía.

## Flujo ejecutable actual

```text
src.main.main
  -> configurar_logging()
  -> LifecycleManager()
  -> verificar_salud(strict=True)
  -> GeminiClient()
  -> GestorPresupuesto()
  -> ControladorCentral()
  -> InterfazCLI.ejecutar()
       -> MensajeEntrada
       -> ControladorCentral.procesar_mensaje()
            -> validar
            -> ping local, o
            -> presupuesto.verificar_disponibilidad()
            -> GeminiClient.generar_respuesta()
            -> presupuesto.registrar_uso()
       -> RespuestaSalida
  -> LifecycleManager.detener()
```

## Paquete `src`

### `src/main.py`

Es el **composition root**: el único lugar que conoce las implementaciones
concretas. Configura logs, crea el ciclo de vida, valida el entorno, crea el
cliente Gemini, crea el presupuesto y conecta las dependencias del controlador.

`main()` devuelve códigos de salida en vez de lanzar errores operativos al
shell:

- `0`: ejecución normal, Ctrl+C o cierre limpio.
- `1`: configuración, credenciales, sistema o limpieza fallida.

Los errores inesperados no se convierten silenciosamente en éxito. El bloque
`finally` siempre intenta detener el ciclo de vida si llegó a construirse.

### `src/core/config.py`

Define `Settings` y la instancia global `config`.

- Carga `.env` desde la raíz mediante `python-dotenv`.
- Normaliza `ENVIRONMENT`, `DB_PATH`, proveedor, modelo y fallbacks.
- Convierte rutas relativas de base de datos en rutas absolutas.
- `validar()` comprueba entorno, proveedor, modelo y la clave cuando el
  entorno la exige.
- `as_dict()` redacta `AI_API_KEY` y es seguro para diagnósticos.

La ausencia de `python-dotenv` tiene un fallback que permite usar variables de
entorno, pero la instalación normal se realiza desde `requirements.txt`.

### `src/core/exceptions.py`

Define la jerarquía del dominio:

- `AethelError`: raíz común.
- `RecoverableError`: el usuario puede corregir la entrada o reintentar.
- `CriticalError`: el arranque o una dependencia esencial no es segura.
- `ExternalServiceError`: fallo de un servicio externo.

La CLI muestra errores recuperables sin tumbar el proceso. `main.py` trata los
errores críticos y de infraestructura durante el arranque.

### `src/core/logger.py`

Configura dos destinos de observabilidad:

- consola para interacción inmediata;
- `logs/aethel.log` con rotación.

También genera IDs de petición y aplica redacción a valores que parecen
secretos antes de escribirlos. Nunca debe recibir una API key en un mensaje de
log. La configuración es idempotente para no duplicar handlers al llamar
varias veces.

### `src/core/health.py`

Comprueba condiciones del entorno:

- existencia y accesibilidad de directorios;
- escritura en almacenamiento;
- espacio disponible;
- presencia de la clave según el modo.

Devuelve un estado degradado en comprobaciones no críticas cuando corresponde
y lanza un error en modo estricto si el arranque no es seguro.

### `src/core/lifecycle.py`

`LifecycleManager` protege el proceso y sus recursos:

- candado de instancia con `fcntl` en POSIX y `msvcrt` en Windows;
- instalación y restauración de `SIGINT` y `SIGTERM`;
- tareas de cierre en orden LIFO;
- rollback si falla el arranque;
- apagado idempotente;
- soporte como context manager.

El candado se mantiene mediante el descriptor abierto. No es un mecanismo
distribuido entre máquinas.

### `src/core/controller.py`

Contiene los DTO inmutables `MensajeEntrada` y `RespuestaSalida`, además de
`ControladorCentral`.

El controlador no importa Google. Solo conoce los contratos del núcleo:

1. limpia y valida el mensaje;
2. responde `ping` localmente;
3. verifica presupuesto;
4. llama al proveedor;
5. registra consumo;
6. devuelve la respuesta.

La marca `simulada` solo es `True` para `ping`, porque esa respuesta es un
diagnóstico local y no una generación del modelo.

### `src/core/llm.py`

Define:

- `RespuestaLLM`: contenido y métricas inmutables;
- `ProveedorLLM`: `Protocol` que desacopla el núcleo del SDK;
- `GestorPresupuesto`: acumulador protegido por `Lock`.

Se rechazan tokens negativos, tipos incorrectos, costes no finitos,
respuestas vacías y límites inválidos. El gestor bloquea nuevas solicitudes al
alcanzar el límite, pero registra el uso que produjo el exceso para no perder
la métrica real.

### `src/core/dispatcher.py`

Actualmente está vacío. Es una reserva arquitectónica para un futuro
enrutador de eventos o casos de uso. No participa en `main.py` ni debe
presentarse como una dependencia activa.

### `src/core/__init__.py`

Marcador del paquete `core`; no contiene lógica ejecutable.

## Adaptadores e interfaces

### `src/infrastructure/gemini_client.py`

`GeminiClient` adapta `google-genai` al protocolo `ProveedorLLM`.

- valida clave, modelo, timeout, reintentos, esperas y jitter;
- elimina modelos fallback duplicados;
- configura timeout HTTP;
- extrae texto y metadatos de tokens;
- calcula un coste estimado;
- reintenta 429, 500, 502, 503 y 504 con backoff y jitter;
- cambia a fallbacks ante errores recuperables de disponibilidad;
- traduce 401/403 a `CriticalError`;
- traduce fallos externos a `ExternalServiceError`.

La tarifa incorporada es una estimación local y puede quedar desactualizada.
No representa una factura del proveedor.

### `src/infrastructure/__init__.py`

Marcador del paquete de infraestructura.

### `src/interfaces/cli.py`

`InterfazCLI` recibe el controlador por inyección. Lee `input()`, reconoce
`salir`, `exit` y `quit`, transforma el texto en `MensajeEntrada` y muestra
`RespuestaSalida`.

Captura errores recuperables para mantener la sesión viva y trata EOF/Ctrl+C
como cierre normal.

### `src/interfaces/__init__.py`

Marcador del paquete de interfaces.

## Espacios reservados

### `src/ai/engine.py` y `src/ai/prompts.py`

Están vacíos. Podrán contener una capa de personalidad, selección de prompts
o una política de inferencia, pero la conexión Gemini actual vive en
`infrastructure/gemini_client.py`.

### `src/ai/__init__.py`

Marcador del paquete de IA futuro.

### `src/memory/models.py` y `src/memory/manager.py`

Están vacíos. Todavía no se persisten conversaciones ni se recupera memoria.
`DB_PATH` solo prepara la configuración de almacenamiento.

### `src/memory/__init__.py`

Marcador del paquete de memoria futuro.

### `src/tools/registry.py` y `src/tools/executor.py`

Están vacíos. A.E.T.H.E.L. todavía no ejecuta comandos del sistema ni
herramientas externas. Antes de activarlos habrá que definir permisos,
validación, auditoría y límites.

### `src/tools/__init__.py`

Marcador del paquete de herramientas futuro.

### `src/__init__.py`

Marcador del paquete raíz.

## Pruebas automatizadas

Cada archivo prueba una responsabilidad concreta y evita llamadas reales a
Google:

| Archivo | Responsabilidad |
|---|---|
| `tests/conftest.py` | Fixtures y configuración común de pytest. |
| `tests/test_core.py` | Contratos base y comportamiento general del núcleo. |
| `tests/test_exceptions.py` | Jerarquía y herencia de excepciones. |
| `tests/test_logger.py` | IDs, redacción, handlers y rotación. |
| `tests/test_health.py` | Estados de salud, almacenamiento y clave. |
| `tests/test_lifecycle.py` | Candado, señales, rollback, tareas y apagado. |
| `tests/test_controller.py` | Validación, `ping`, proveedor y presupuesto. |
| `tests/test_cli.py` | Entrada, comandos y errores de consola. |
| `tests/test_llm.py` | DTO, métricas, presupuesto y concurrencia lógica. |
| `tests/test_gemini_client.py` | Reintentos, fallbacks y traducción de errores usando mocks. |
| `tests/test_main.py` | Composition root, orden de arranque y limpieza. |
| `tests/test_memory.py` | Reserva para memoria; refleja el estado actual del módulo. |

Para comprobar que esta explicación sigue sincronizada:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src tests
```

Esta carpeta es material local de estudio y está ignorada por Git. El código
ejecutable siempre es el que está bajo `src/`.
