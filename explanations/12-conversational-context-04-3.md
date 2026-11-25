# 04.3. Contexto conversacional

> **Estado 04.5:** el diseño sigue vigente, pero faltan el resumen previo
> acumulado, la retención con cascada y el comando `/estado`. Ver
> [`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md)
> y [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

Implementación: [`src/context/`](../src/context/).
Pruebas: [`tests/test_context.py`](../tests/test_context.py).

## Diseño híbrido

A.E.T.H.E.L. usa dos niveles:

- **RAM:** `ContextManager.messages` contiene la ventana activa que se envía
  al modelo.
- **SQLite:** `ConversationStore` persiste cada turno inmediatamente, no solo
  al cerrar el proceso.

Esto permite retomar una sesión reciente después de reiniciar sin cargar todo
el historial antiguo. Una sesión se reanuda si su última actividad tiene menos
de dos horas; después se marca como archivada y se crea otra.

## Privacidad

`sanitize_text()` se ejecuta antes de guardar o construir una petición. Oculta:

- claves con prefijos conocidos;
- tokens `AQ.`;
- contraseñas y API keys en asignaciones;
- correos electrónicos;
- rutas bajo `/home/...`.

La base de datos contiene texto saneado, no una copia secreta del mensaje
original. Esto no sustituye cifrado de disco ni controles de acceso del sistema
operativo.

## Ventana y presupuesto

Las instrucciones permanentes viven en
[`src/context/system_prompt.py`](../src/context/system_prompt.py), separadas
del historial dinámico. La configuración equilibrada usa 14 mensajes y
aproximadamente 4000 tokens
estimados mediante `len(texto) // 4`. El system prompt no forma parte de la
lista que se recorta: `build_prompt()` lo antepone siempre.

Al superar la ventana, `compact()` toma los mensajes antiguos y llama al
router para generar un resumen. El resumen también se sanea, se guarda en la
sesión y su consumo se registra en `GestorPresupuesto`. Si el router o el
presupuesto no permiten resumir, se conserva la sesión sin propagar un fallo
secundario al usuario.

## Flujo de un mensaje

1. El controlador valida el texto.
2. `ContextManager.build_prompt()` incorpora system prompt, resumen y ventana.
3. El mensaje de usuario saneado se persiste.
4. El router genera la respuesta.
5. El controlador registra el consumo.
6. La respuesta saneada se persiste.
7. Si hace falta, la memoria se compacta.

`ping` continúa siendo local y no se añade como turno LLM.

## Base de datos

`DB_PATH` apunta por defecto a `database/aethel.db`. Las tablas son:

- `conversation_sessions`: sesión, actividad, resumen y estado archivado.
- `conversation_messages`: roles, contenido saneado y fecha de cada turno.

SQLite usa WAL y claves foráneas. El cierre de la conexión se realiza en
`main.py` mediante `ContextManager.close()`. La persistencia ocurre antes,
turno por turno, para reducir la pérdida ante cierres abruptos.

## Seguridad, retención y migraciones

Si `CONTEXT_ENCRYPTION_KEY` contiene una clave Fernet válida, mensajes y
resúmenes se cifran antes de entrar en SQLite. La clave no se guarda en la
base: debe vivir en el entorno o en un gestor externo. Perderla impide
descifrar el historial.

`CONTEXT_RETENTION_DAYS` elimina sesiones archivadas antiguas. La tabla
`schema_versions` registra la versión aplicada para que futuras migraciones
sean explícitas en vez de modificar tablas silenciosamente.

El cifrado de contenido no sustituye permisos del archivo, cifrado de disco ni
copias de seguridad protegidas.

## Operación

La CLI incluye:

- `/modelo`: último proveedor y latencia;
- `/memoria`: sesión activa, mensajes y estado del resumen;
- `/limpiar`: elimina los mensajes y resumen de la sesión actual.

## Pruebas

Las pruebas usan bases temporales y comprueban sanitización, reanudación,
ventana, compactación, roles inválidos y persistencia. No requieren red ni
proveedores externos.
