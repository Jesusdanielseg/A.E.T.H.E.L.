
# Flujo de Datos y Ciclo de Vida: A.E.T.H.E.L.

**Versión:** 0.2.0 | **Fase:** 02

## 1. Ciclo de Vida de una Petición (Secuencia)

El siguiente diagrama detalla cómo viaja la información desde la entrada del usuario hasta la respuesta final, incluyendo la validación de seguridad y la ejecución de herramientas locales (Tool Calling).

```mermaid
sequenceDiagram
    participant U as Usuario
    participant I as interface (CLI)
    participant C as core (Dispatcher)
    participant M as memory (Manager)
    participant A as ai (Engine)
    participant S as security (Permisos)
    participant T as tools (Executor)

    U->>I: Ingresa instrucción
    I->>C: Inicia transacción
  
    C->>M: Recupera contexto de sesión
    M-->>C: Historial inyectado
  
    C->>A: Prompt + Contexto
    Note over A: Inferencia LLM
    A-->>C: Solicitud de Herramienta (JSON)
  
    C->>S: Valida riesgo (Ej. Comando SO)
    S-->>C: Aprobado (Automático o Manual)
  
    C->>T: Ejecuta acción/script
    T-->>C: Retorna Resultado (Output/Error)
  
    C->>A: Re-inyecta resultado al modelo
    Note over A: Genera respuesta en lenguaje natural
    A-->>C: Transmisión (Streaming de tokens)
  
    C->>M: Guarda la transacción completa
    C-->>I: Retorna respuesta formateada
    I->>U: Muestra al usuario
```
