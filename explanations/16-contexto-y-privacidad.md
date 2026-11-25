# 16. Contexto, privacidad y persistencia

**Estado:** vigente para la Fase 04.5.
**Implementación:** [`src/context/`](../src/context/)
**Pruebas principales:** [`tests/test_context.py`](../tests/test_context.py),
[`tests/test_evaluation_04.py`](../tests/test_evaluation_04.py) y
[`tests/test_personality.py`](../tests/test_personality.py).

Este documento explica el subsistema de contexto completo: qué se sanea, cómo
se construye el prompt, cómo se guarda la conversación en SQLite y cómo se
compacta la memoria. Complementa el documento 12, que describe el diseño
original de 04.3.

## 1. Flujo general

```text
Entrada del usuario
  -> ControladorCentral valida el texto
  -> ContextManager.build_prompt()
       -> [SYSTEM] + [RESUMEN_PREVIO] + mensajes + [USER]
  -> LLMRouter genera la respuesta
  -> ControladorCentral registra el consumo
  -> ContextManager.add_message("assistant", respuesta)
  -> ConversationStore persiste el turno saneado
  -> Si la ventana crece, ContextManager.compact()
```

Hay dos niveles de memoria:

- **RAM:** `ContextManager.messages` es la ventana activa que se envía al
  modelo.
- **SQLite:** `ConversationStore` conserva los turnos y el resumen para
  reanudar una sesión reciente.

La persistencia ocurre turno a turno, no solo al cerrar el programa. Así se
reduce la pérdida de información si el proceso termina de forma abrupta.

## 2. `src/context/sanitizer.py`

Este módulo aplica una redacción básica antes de guardar o enviar texto.

### 2.1 Patrones

| Patrón | Reemplazo | Qué detecta |
|---|---|---|
| `\b(?:sk|AIza)[A-Za-z0-9_-]+` | `[CREDENCIAL_OCULTA]` | Claves con prefijos tipo OpenAI/Google. |
| `\bAQ\.[A-Za-z0-9_-]+` | `[CREDENCIAL_OCULTA]` | Tokens con prefijo `AQ.`. |
| `password`, `passwd`, `contraseña`, `token`, `api key`, `api_key`, `api-key` seguidos de `:` o `=` | `[DATO_SENSIBLE_OCULTO]` | Asignaciones de credenciales. |
| Correo electrónico | `[CORREO_OCULTO]` | Direcciones de email. |
| `/home/<usuario>/...` | `~/proyecto/[RUTA_OCULTA]` | Rutas personales absolutas. |

`sanitize_text()` recorre primero los secretos, después los correos y finalmente
las rutas. El orden evita que un correo o una ruta se procesen antes que una
credencial.

### 2.2 Límites

- Es una defensa **heurística**, no un detector universal de secretos.
- No sustituye el cifrado de disco, los permisos del sistema operativo ni un
  gestor de secretos.
- No se debe usar para justificar el envío de datos privados a un proveedor
  externo.
- El texto saneado es el que se persiste y el que se envía al modelo.

## 3. `src/context/system_prompt.py`

Contiene una constante corta:

```python
SYSTEM_PROMPT = (
    "Eres A.E.T.H.E.L., un asistente claro, prudente y conciso. "
    "No inventes datos y reconoce cuando no tengas información."
)
```

La intención es separar las instrucciones permanentes del historial dinámico.

**Importante para el estado actual:** `src/main.py` construye el system prompt
activo con `PersonaBuilder(...).build_system_prompt()` a partir de
`prompts/persona.yaml`. La constante `SYSTEM_PROMPT` no se importa desde
`main.py` en este bloque; se conserva como instrucción base/legado. No hay que
confundirla con el prompt de personalidad que se usa realmente.

## 4. `src/context/prompt_builder.py`

`PersonaBuilder` carga un perfil YAML y lo convierte en instrucciones estables
para cualquier proveedor.

### 4.1 Contrato del perfil

El YAML debe incluir estas secciones:

- `identidad`: nombre, rol, propósito y directrices.
- `estilo`: formalidad, idioma, tratamiento, humor, modos y situaciones serias.
- `respuesta`: primera línea, brevedad, límite de líneas, estructura, formato de
  código/error y prohibiciones.
- `seguridad`: reglas de seguridad.
- `ejemplos`: lista de ejemplos con `tipo`, `usuario`, `no_deseado` y `deseado`.

`PersonaConfigError` hereda de `ValueError` y se lanza cuando el archivo no
existe, no es YAML válido o no cumple el contrato.

### 4.2 Modos y validación

Los modos válidos son:

```text
enfoque, codigo, casual
```

Los niveles de humor válidos son:

```text
ninguno, sutil, activo
```

El constructor acepta un modo explícito; si no se pasa, usa
`estilo.modo` del YAML. `build_system_prompt(mode)` permite cambiarlo sin editar
el archivo.

La validación comprueba tipos, textos no vacíos, listas, los tres modos, las
situaciones serias, los límites de respuesta y que
`primera_linea_directa` y `brevedad_por_defecto` sean booleanos reales.

### 4.3 Renderizado de booleanos

Los booleanos se transforman en instrucciones naturales, no en `True`/`False`:

```text
- Primera línea: Empieza con una respuesta directa en la primera línea.
- Brevedad: Sé breve por defecto; amplía solo si el usuario lo pide.
```

Esto evita que el modelo copie literalmente `True.` al inicio de sus respuestas.

### 4.4 Composición

El prompt resultante contiene, en orden:

1. Identidad, rol, propósito y directrices.
2. Estilo, idioma, tratamiento, modo activo, humor y situaciones serias.
3. Formato de respuesta y prohibiciones.
4. Reglas de seguridad.
5. Ejemplos de comportamiento.
6. Prioridad del tono serio sobre el humor.

Las reglas de personalidad no pueden anular las políticas de seguridad ni los
permisos del sistema.

## 5. `src/context/store.py`

`ConversationStore` es la persistencia SQLite de sesiones y mensajes ya
saneados.

### 5.1 Esquema

Tablas principales:

- `conversation_sessions`: `id`, `started_at`, `last_activity_at`, `summary`,
  `archived`.
- `conversation_messages`: `id`, `session_id`, `role`, `content`,
  `created_at`.
- `schema_versions`: versión del esquema aplicada.
- `storage_metadata`: formato del contenido (`plain` o `encrypted`).

La tabla de mensajes declara:

```sql
REFERENCES conversation_sessions(id) ON DELETE CASCADE
```

También hay índices por sesión/fecha y por `archived`/`last_activity_at`. La
conexión usa WAL, claves foráneas y `RLock` para proteger accesos.

### 5.2 Cifrado y migración

Si se pasa `encryption_key`, se construye un `Fernet`. El contenido se cifra
antes de insertarse y se descifra al leerse.

`_ensure_storage_format()` distingue:

- base nueva sin clave: `plain`;
- base nueva con clave: `encrypted`;
- base `plain` que pasa a `encrypted`: migra resúmenes y mensajes;
- base `encrypted` sin la clave correcta: error explícito.

Perder la clave impide descifrar el historial. El cifrado de contenido no
sustituye permisos del archivo ni cifrado de disco.

### 5.3 Sesiones

`get_or_create_session()` busca la sesión no archivada más reciente. Si su
última actividad está dentro del timeout (2 horas por defecto), la reutiliza.
Si no, la marca como archivada y crea una nueva con UUID.

### 5.4 Mensajes, resumen y retención

- `load_recent_messages()` devuelve los últimos mensajes en orden cronológico.
- `append_message()` inserta el mensaje y actualiza `last_activity_at`.
- `update_summary()` guarda el resumen cifrado si corresponde.
- `clear_session()` borra los mensajes y limpia el resumen.
- `_purge_archived()` elimina primero los mensajes de sesiones archivadas y
  después las sesiones. El orden mantiene compatibilidad con bases creadas antes
  de la cascada.
- `close()` hace un checkpoint WAL pasivo y cierra la conexión.

`ConversationStore` **no sanea** el texto: asume que `ContextManager` ya lo hizo.

## 6. `src/context/manager.py`

`ContextManager` combina la ventana RAM con la persistencia.

### 6.1 Construcción

Valida:

- `max_messages` entero y al menos 2;
- `max_estimated_tokens` entero y al menos 1;
- `system_prompt` de tipo texto y no vacío.

Sanea el system prompt, crea el store, recupera o crea la sesión, carga los
últimos mensajes y recorta la ventana.

### 6.2 Añadir mensajes

`add_message(role, content)`:

1. Acepta solo `user`, `assistant` o `system`.
2. Sanea el contenido y rechaza vacíos.
3. Añade el mensaje a RAM.
4. Lo persiste inmediatamente.
5. Si supera `max_messages` y hay summarizer, compacta.
6. Recorta la ventana por mensajes y tokens.

### 6.3 Construir el prompt

`build_prompt(user_message)` compone:

```text
[SYSTEM]
<system prompt>

[RESUMEN_PREVIO]
<resumen, si existe>

[USER]
<mensaje anterior>

[ASSISTANT]
<respuesta anterior>

[USER]
<mensaje actual>
```

El mensaje actual también se sanea antes de entrar al prompt.

### 6.4 Compactación

`compact(summarizer)` solo actúa si `len(messages) > max_messages`.

- Toma como máximo 6 mensajes antiguos, dejando al menos 2.
- Incluye el **resumen anterior** en el prompt del resumidor. Esto evita perder
  hechos en compactaciones sucesivas.
- Consulta y registra el consumo en `GestorPresupuesto` si está disponible.
- Si el proveedor falla con `ProviderError` o `RecoverableError`, conserva la
  sesión sin propagar el fallo.
- Sanea el resumen, lo guarda y elimina de RAM los mensajes resumidos.

### 6.5 Recorte y estimación

`_trim_window()` elimina los mensajes más antiguos mientras se supere el límite
de mensajes o de tokens estimados. Siempre conserva al menos uno.

La estimación es deliberadamente simple:

```python
max(1, len(content) // 4)
```

No es un tokenizador real; es una aproximación para acotar el contexto.

### 6.6 Limpieza y cierre

- `clear()` borra los mensajes y el resumen de la sesión actual.
- `close()` cierra el store.

`main.py` llama a `ContextManager.close()` en el bloque de limpieza.

## 7. Fronteras de privacidad

1. **Antes de persistir:** `ContextManager` sanea el texto.
2. **Antes de enviar:** `build_prompt()` sanea el mensaje del usuario.
3. **En reposo:** si hay clave Fernet, el contenido se cifra en SQLite.
4. **En memoria:** los mensajes activos están en RAM sin cifrar; el cifrado de
   SQLite no protege la memoria del proceso.
5. **En logs:** el logger tiene su propio filtro de secretos; no se debe asumir
   que el contexto sustituye ese filtro.

## 8. Pruebas

`tests/test_context.py` cubre:

- saneamiento de secretos, correos y rutas;
- persistencia y recarga de turnos saneados;
- system prompt y límite de ventana;
- compactación con router;
- conservación del resumen previo;
- rechazo de roles inválidos;
- retención de sesiones archivadas;
- nueva sesión tras timeout;
- cifrado y migración de bases plaintext.

`tests/test_evaluation_04.py` añade:

- conversación larga con compactación y resumen persistido;
- conservación de afirmaciones contradictorias en el contexto;
- guía de incertidumbre en el prompt de personalidad.

`tests/test_personality.py` verifica la composición del prompt, los modos y la
validación del perfil.

## 9. Limitaciones

- El resumen puede perder matices; conserva hechos y preferencias, no una
  transcripción completa.
- La estimación de tokens es aproximada.
- El saneamiento es heurístico y no detecta cualquier secreto imaginable.
- La retención solo purga sesiones archivadas antiguas.
- El cifrado depende de una clave externa; si se pierde, el historial no se
  puede recuperar.
- `SYSTEM_PROMPT` no es el prompt activo actual; la integración usa
  `PersonaBuilder`.

## 10. Verificación

```text
125 passed
All checks passed!
Success: no issues found in 55 source files
```

No se modificó código de `src/` al crear este documento.
