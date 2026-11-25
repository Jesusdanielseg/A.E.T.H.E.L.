# Guía de pruebas de A.E.T.H.E.L.

Esta guía valida la aplicación desde la terminal sin exponer la API key.
Ejecuta los comandos desde la raíz del repositorio.

## 1. Preparar el entorno

Linux/macOS:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Windows PowerShell:

```powershell
py --version
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## 2. Configurar la clave

1. Copia `.env.example` como `.env`.
2. Edita `.env` y configura el proveedor que quieras usar.
3. No uses comillas adicionales y no compartas el archivo.

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configuración mínima:

```dotenv
ENVIRONMENT=development
LLM_PROVIDER_ORDER=ollama,gemini,offline
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_THINK=false
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=512
OLLAMA_KEEP_ALIVE=30m
AI_API_KEY=tu_clave_sin_comillas
AI_MODEL=gemini-3.8-flash
AI_FALLBACK_MODELS=gemini-3.5-flash-lite,gemini-3.1-flash-lite
LLM_BUDGET_USD=0.50
```

La clave solo es necesaria si `gemini` aparece en `LLM_PROVIDER_ORDER`.
Para una prueba completamente local, usa `LLM_PROVIDER_ORDER=ollama,offline`
y comprueba con `ollama list` que el modelo indicado ya está instalado. No es
necesario descargar otro modelo para ejecutar los tests.

Si el shell exporta `OLLAMA_MODEL`, ese valor tiene prioridad sobre `.env`.
Para probar el modelo del archivo, ejecuta `env -u OLLAMA_MODEL python -m
src.main` o `OLLAMA_MODEL=gemma3:4b python -m src.main`.

## 3. Ejecutar pruebas automáticas

Estas pruebas no llaman a Google y no consumen cuota:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src tests
.venv/bin/python -m pytest -q tests/test_main.py
```

En Windows PowerShell, sustituye `.venv/bin/python` por
`.venv\Scripts\python.exe`.

Resultado esperado actual:

```text
125 passed
```

## 4. Probar la aplicación sin consumir API

Ejecuta:

```bash
.venv/bin/python -m src.main
```

Escribe:

```text
ping
```

Resultado esperado:

```text
pong (núcleo operativo)
```

`ping` no consulta ningún proveedor ni registra consumo. Después escribe
`salir` para cerrar la CLI.

## 5. Probar una consulta real

Vuelve a iniciar la aplicación y escribe una petición breve, por ejemplo:

```text
Explícame en dos líneas qué es una cláusula de guarda en Python
```

Comprueba que:

- recibes una respuesta del modelo;
- aparece un `request_id`;
- los logs muestran el modelo, tokens y coste estimado;
- si el modelo principal falla de forma recuperable, se intenta un fallback.

Con `ollama,gemini,offline`, la primera respuesta normalmente será local y no
consumirá cuota de Gemini. `/modelo` muestra el proveedor, el modelo y la
latencia; `/estado` añade tokens y coste acumulado.

El modelo por defecto es `gemma3:4b`. En el hardware de referencia usa unos
2.9 GB de VRAM y responde en ~0.6-2.2 s en caliente para preguntas simples; un
diagnóstico de 5 pasos tarda ~6-10 s. La primera carga tarda ~9-14 s.
`OLLAMA_NUM_CTX` y `OLLAMA_NUM_PREDICT` acotan contexto y salida;
`OLLAMA_NUM_PREDICT=512` mantiene la latencia controlada. Si usas un modelo
Qwen3, mantén `OLLAMA_THINK=false`. Los modelos Qwen3 de 4B probados en esta
versión de Ollama pueden seguir mostrando razonamiento interno; verifica la
salida antes de adoptarlos.

Para comprobar la personalidad configurable, cambia temporalmente el modo en
`.env` y reinicia:

```dotenv
PERSONALITY_MODE=codigo
```

El perfil se carga desde `prompts/persona.yaml`. Un YAML inválido o incompleto
produce un error explícito de arranque; no se usa un perfil silencioso de
respaldo.

El presupuesto se configura con `LLM_BUDGET_USD` (por defecto `$0.50`). Es un
límite local acumulado para la ejecución y no una garantía de facturación
gratuita del proveedor.

## 6. Revisar logs

Los registros se escriben en:

```text
logs/aethel.log
```

Linux/macOS:

```bash
tail -f logs/aethel.log
```

Windows PowerShell:

```powershell
Get-Content logs\aethel.log -Wait
```

Nunca pegues en un reporte el contenido de `.env` ni una API key.

## Memoria persistente y cifrado opcional

Para cifrar mensajes y resúmenes en SQLite, genera una clave una sola vez:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guárdala como `CONTEXT_ENCRYPTION_KEY` en `.env`, sin publicarla ni perderla.
Al abrir una base existente por primera vez con una clave, la aplicación migra
sus textos en claro a formato cifrado. Si se usa otra clave, o se quita la
clave después de cifrar, el arranque se detiene para evitar corromper o
interpretar incorrectamente el historial.
También puedes ajustar:

```dotenv
CONTEXT_RETENTION_DAYS=30
```

Durante la sesión:

```text
/modelo
/estado
/memoria
/limpiar
```

`/limpiar` elimina la memoria de la sesión activa de SQLite.

## 7. Diagnóstico de errores

### Falta la clave

Verifica que `.env` exista en la raíz, que `AI_API_KEY` no esté vacío y que
no hayas escrito el nombre como `API_KEY`.

### Error 401 o 403

La credencial no es válida o no tiene permisos. Revócala si fue expuesta,
crea una nueva y actualiza `.env`.

### Error 404, 503 o 504

El modelo puede no estar habilitado o estar saturado. Mantén configurados los
modelos fallback y vuelve a intentar más tarde.

### El presupuesto está agotado

La aplicación bloquea nuevos mensajes cuando el gasto acumulado alcanza el
límite local. Reiniciar la aplicación reinicia el acumulador actual. Para
cambiar el límite, ajusta `LLM_BUDGET_USD` en `.env`.

## 8. Cierre seguro

Escribe `salir`, `exit` o `quit`. También puedes usar Ctrl+C o Ctrl+D. La
aplicación libera el candado de instancia y restaura los manejadores de
señales antes de terminar.

## 9. Evaluación inicial 04.5

El protocolo completo está en [`evaluation-04.md`](./evaluation-04.md). Para
medir latencia y coste usa `/estado` después de cada respuesta. Los casos
deterministas viven en `tests/test_evaluation_04.py`; las pruebas con modelos
reales se registran en la tabla de resultados del documento de evaluación.

Antes de cerrar la fase, ejecuta:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src tests
```

Y comprueba que el número de tests coincide con el documentado.
