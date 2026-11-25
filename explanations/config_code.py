"""Guía anotada de src/core/config.py.

Este archivo es material didáctico y no se importa desde la aplicación.
La implementación ejecutable está en ../src/core/config.py.

Estado 04.5: guía desactualizada. No incluye _env_int(), _env_bool(),
OLLAMA_THINK, OLLAMA_NUM_CTX, OLLAMA_NUM_PREDICT, OLLAMA_KEEP_ALIVE,
LLM_BUDGET_USD ni el modelo gemma3:4b. Ver
explanations/14-auditoria-explanations-04-5.md.
"""

# 1. Se importan os y pathlib para leer variables y resolver rutas.
# 2. dotenv.load_dotenv carga .env desde la raíz del proyecto.
# 3. Si python-dotenv no está instalado, se usa un fallback que no rompe la
#    lectura de variables del sistema.
# 4. Settings normaliza ENVIRONMENT, DB_PATH, AI_PROVIDER, AI_API_KEY,
#    AI_MODEL y AI_FALLBACK_MODELS.
# 5. DB_PATH se convierte en una ruta absoluta para que el directorio actual
#    desde el que se ejecuta Python no cambie el destino.
# 6. requires_api_key indica si el entorno exige credenciales.
# 7. validar() acumula todos los errores y lanza un único ValueError.
# 8. as_dict() oculta la API key antes de exponer configuración en diagnósticos.
# 9. config = Settings() crea la configuración usada por los demás módulos.

# Regla importante:
# nunca se debe imprimir config.AI_API_KEY ni copiarla a logs, excepciones,
# documentación o capturas de pantalla.
