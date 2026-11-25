# Explicaciones del núcleo de A.E.T.H.E.L.

Esta carpeta contiene una guía de estudio del núcleo, la interfaz interna y los
bloques de IA, contexto y evaluación local. También incluye copias Python
anotadas: las explicaciones están junto al código con comentarios `#` y
docstrings.

> **Estado (04.5):** el índice se corrigió para que apunte a los nombres reales
> de los archivos. Varios documentos y copias anotadas son material histórico:
> explican el estado de su bloque, no necesariamente el código actual. La
> auditoría completa está en
> [`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).
> La fuente de verdad ejecutable siempre es `src/`; los resultados de la
> evaluación 04.5 están en
> [`docs/evaluation-04-results.md`](../docs/evaluation-04-results.md).

## Documentos

- [Logger y observabilidad](./01-logger.md): niveles de log, IDs de petición,
  redacción de claves y rotación de archivos.
- [Jerarquía de excepciones](./02-exceptions.md): errores recuperables,
  críticos y específicos del dominio.
- [Comprobaciones de salud](./03-health.md): almacenamiento, permisos,
  espacio, API key y evaluación del estado.
- [Arranque y ciclo de vida](./04-startup-and-lifecycle.md): cómo `main.py`
  configura el sistema, hace health check, inicia CLI y cierra por señal.
  **Parcialmente desactualizado:** no incluye el router, el contexto ni la
  validación de configuración actual.
- [Bibliotecas y pruebas](./05-libraries-and-tests.md): referencia de
  bibliotecas estándar y técnicas de pruebas usadas.
- [Controlador central](./06-controller.md): contratos de mensajes,
  validación, ID de petición, proveedor LLM y presupuesto.
- [Interfaz CLI](./07-cli.md): inyección del controlador, lectura de consola,
  comandos de salida y errores recuperables. **Desactualizado:** faltan
  `/memoria`, `/limpiar`, `/modelo` y `/estado`.
- [Contrato LLM y presupuesto](./08-llm-and-budget.md): protocolo del
  proveedor, métricas, validación de consumo y límite económico. **Parcial:**
  el contrato del núcleo sigue vigente; la integración actual se explica en
  [`13-ollama-performance-and-evaluation-04-5.md`](./13-ollama-performance-and-evaluation-04-5.md).
- [Mapa completo del código](./09-complete-code-map.md): inventario de
  módulos y pruebas. **Histórico:** no incluye `src/context/`, el router ni los
  cambios 04.5. No usarlo como mapa actual; ver el documento 14.
- [Gemini y prueba real](./10-gemini-and-real-test.md): cliente, reintentos,
  fallbacks, coste estimado y diagnóstico de latencia.
- [Capa de abstracción 04.2](./11-abstraction-layer-04-2.md): adaptadores,
  router y proveedores. **Parcial:** la estructura sigue vigente; el ejemplo
  `qwen3:8b` y las opciones de Ollama quedaron actualizados en el documento 13.
- [Contexto conversacional 04.3](./12-conversational-context-04-3.md): memoria
  RAM, persistencia SQLite, sanitización, sesiones y compactación. **Parcial:**
  falta el resumen previo acumulado, la retención con cascada y `/estado`.
- [Ollama, rendimiento y evaluación 04.5](./13-ollama-performance-and-evaluation-04-5.md):
  configuración local, selección de modelo, cambios de personalidad,
  compactación, resultados y limitaciones.
- [Auditoría de explanations 04.5](./14-auditoria-explanations-04-5.md):
  inventario real, comparación de documentos y snapshots con el código,
  enlaces corregidos y estado de cada archivo.
- [Cobertura de módulos Python](./15-cobertura-de-modulos-python.md): auditoría
  previa sobre qué archivos de `src/` y `tests/` tenían explicación dedicada y
  qué huecos quedaban.
- [Contexto, privacidad y persistencia](./16-contexto-y-privacidad.md):
  `sanitizer.py`, `system_prompt.py`, `prompt_builder.py`, `store.py` y
  `manager.py`, con el flujo de saneamiento, SQLite, cifrado y compactación.
- [Capa LLM completa](./17-capa-llm-completa.md): contrato `BaseLLMProvider`,
  `ModelResponse`, `ProviderError`, adaptadores Gemini/Ollama/offline y router.

## Copias Python anotadas

Estos archivos son para lectura y estudio; no sustituyen a los módulos de
`src/` ni deben importarse en la aplicación. No se actualizan automáticamente
cuando cambia el código real.

- [`logger_code.py`](./logger_code.py)
- [`exceptions_code.py`](./exceptions_code.py)
- [`health_code.py`](./health_code.py)
- [`lifecycle_code.py`](./lifecycle_code.py)
- [`controller_code.py`](./controller_code.py)
- [`cli_code.py`](./cli_code.py)
- [`llm_code.py`](./llm_code.py)
- [`main_code.py`](./main_code.py)
- [`config_code.py`](./config_code.py)
- [`gemini_client_code.py`](./gemini_client_code.py)
- [`future_modules_code.py`](./future_modules_code.py)

Los módulos añadidos en el bloque LLM se explican directamente en
[`10-gemini-and-real-test.md`](./10-gemini-and-real-test.md) y el inventario
histórico está en
[`09-complete-code-map.md`](./09-complete-code-map.md). El estado actual de los
snapshots, con las diferencias concretas, está en
[`14-auditoria-explanations-04-5.md`](./14-auditoria-explanations-04-5.md).

## Cómo usar estos apuntes

Empieza por `main.py` para entender el orden general. Después sigue el flujo:
`InterfazCLI` crea `MensajeEntrada`, `ControladorCentral` valida y devuelve
`RespuestaSalida`, y el ciclo de vida gestiona señales y recursos. `logger.py`,
`health.py` y `exceptions.py` son servicios compartidos por esas capas.
Para la integración de IA, `llm.py` define el contrato que implementan los
proveedores; el router elige entre Ollama, Gemini y offline.

Los ejemplos son ilustrativos y algunos requieren configurar `config` o
proporcionar un directorio temporal. No pegues claves reales en ejemplos,
pruebas, mensajes de error ni logs.

## Nota sobre Git

`explanations/` sigue en `.gitignore`, pero estos archivos se añadieron
explícitamente con `git add -f` y ya están versionados. Las modificaciones a
archivos ya rastreados aparecen normalmente en `git status`; los archivos
nuevos que se creen en esta carpeta seguirán ignorados hasta que se añadan con
`git add -f` o se quite la regla del `.gitignore`.
