"""Mapa didáctico de módulos reservados para fases posteriores."""

# src/ai/engine.py:
# reservado para política de inferencia, personalidad y selección de proveedor.
#
# src/ai/prompts.py:
# reservado para prompts versionados y composición de instrucciones.
#
# src/memory/models.py:
# reservado para DTOs de conversación, mensajes y metadatos persistentes.
#
# src/memory/manager.py:
# reservado para guardar y recuperar memoria. Actualmente no escribe en DB.
#
# src/tools/registry.py:
# reservado para registrar herramientas permitidas y sus metadatos.
#
# src/tools/executor.py:
# reservado para ejecutar herramientas después de validar permisos, argumentos,
# límites y auditoría. No ejecuta comandos del sistema actualmente.
#
# src/core/dispatcher.py:
# reservado para enrutar eventos/casos de uso cuando crezca la aplicación.
#
# Los __init__.py solo marcan paquetes Python y no contienen lógica.
