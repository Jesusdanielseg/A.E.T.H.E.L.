
# Documentación de Arquitectura: A.E.T.H.E.L.

**Versión:** 0.2.0 | **Estado:** En Desarrollo (Fase 02)

## 1. Visión General

A.E.T.H.E.L. es un asistente virtual modular y backend-driven diseñado bajo los principios de la **Arquitectura Limpia (Clean Architecture)** y el patrón **Event-Driven (Basado en Eventos)**. El objetivo principal es mantener un acoplamiento nulo entre la lógica de inferencia (IA), las herramientas de ejecución local y la interfaz de usuario.

---

## 2. Diagrama de Componentes Principales

El sistema opera a través de un orquestador central (`dispatcher.py`) que enruta las peticiones entre los módulos aislados.

```mermaid
graph TD
    %% Definición de Interfaz y Core
    U([Usuario]) -->|Input Texto/Voz| INT[interface/cli.py]
    INT -->|Evento Petición| CORE{core/dispatcher.py}
  
    %% Módulos del Sistema
    CORE -->|Consulta de Permisos| SEC[security/permissions.py]
    CORE <-->|Recuperación/Guardado| MEM[memory/manager.py]
    CORE -->|Inferencia Híbrida| AI[ai/engine.py]
    CORE <-->|Ejecución de Acciones| TOOLS[tools/executor.py]
    CORE -->|Automatizaciones| AUTO[automation/task_runner.py]

    %% Conexiones Externas
    MEM <-->|Persistencia| DB[(database/aethel.db)]
    AI <-->|API Streaming| LLM_CLOUD((Gemini / OpenAI))
    AI <-->|Inferencia Local| LLM_LOCAL((Ollama Local))
    TOOLS -->|Llamadas a SO| OS[Sistema Operativo Linux]
  
    classDef core fill:#2b2b2b,stroke:#00ff00,stroke-width:2px,color:#fff;
    classDef external fill:#1e1e1e,stroke:#00aaff,stroke-width:2px,color:#fff;
    class CORE core;
    class LLM_CLOUD,LLM_LOCAL,DB,OS external;
```
