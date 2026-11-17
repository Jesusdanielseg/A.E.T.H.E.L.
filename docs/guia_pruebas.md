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
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py --version
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Configurar la clave

1. Copia `.env.example` como `.env`.
2. Edita `.env` y sustituye únicamente el valor de `AI_API_KEY`.
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
AI_PROVIDER=gemini
AI_API_KEY=tu_clave_sin_comillas
AI_MODEL=gemini-3.8-flash
AI_FALLBACK_MODELS=gemini-3.5-flash-lite,gemini-3.1-flash-lite
```

La clave debe tener permisos para generar contenido con al menos uno de los
modelos configurados. La disponibilidad de modelos puede variar por cuenta,
región y cuota.

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
87 passed
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

`ping` no consulta Gemini ni registra consumo. Después escribe `salir` para
cerrar la CLI.

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

El presupuesto configurado en `src/main.py` es `$0.50`. Es un límite local
acumulado para la ejecución y no una garantía de facturación gratuita del
proveedor.

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
límite local. Reiniciar la aplicación reinicia el acumulador actual; para
cambiar el límite modifica `GestorPresupuesto(limite_usd=0.50)` de forma
consciente.

## 8. Cierre seguro

Escribe `salir`, `exit` o `quit`. También puedes usar Ctrl+C o Ctrl+D. La
aplicación libera el candado de instancia y restaura los manejadores de
señales antes de terminar.
