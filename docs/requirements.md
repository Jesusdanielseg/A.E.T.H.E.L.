# REQUIREMENTS - A.E.T.H.E.L.

> **Estado (Fase 04):** implementado el núcleo conversacional, la personalidad
> configurable, la memoria de sesión en SQLite y el router Ollama/Gemini/offline.
> La evaluación inicial 04.5 está completada con limitaciones documentadas en
> [`evaluation-04-results.md`](./evaluation-04-results.md). El diario, las
> herramientas, la voz, las integraciones, la automatización y la interfaz web
> siguen siendo requisitos planificados.

## 1. Requisitos Funcionales (El "Qué")

### Prioridad Alta (Fases 02-06: MVP y Núcleo)

* **Gestión de Conversación:**
  * Procesar entrada por texto y mantener el contexto de la conversación actual.
  * Separar las instrucciones de sistema (personalidad/reglas) de los mensajes del usuario.
  * Mantener una personalidad configurable con voz, modos, ejemplos y reglas de situaciones serias.
* **Memoria y Diario:**
  * Guardar mensajes de forma persistente.
  * Crear, consultar, editar y eliminar entradas del diario personal.
  * Generar resúmenes periódicos de las conversaciones o días.
* **Sistema de Herramientas (Acciones Aisladas):**
  * Interfaz estándar para registrar herramientas (nombre, propósito, argumentos y permisos).
  * Herramientas iniciales: Consultar fecha/hora, leer archivos en directorios permitidos, crear recordatorios.

### Prioridad Media (Fases 07-11: Expansión)

* **Voz y Audio:**
  * Captura de audio por micrófono (activación por botón inicialmente) y conversión STT.
  * Síntesis de voz (TTS) con voz femenina estilo japonés, controlando velocidad, pausas y capacidad de interrupción.
* **Integraciones Personales:**
  * Conexión con calendario y tareas para consultar o crear eventos, detectando conflictos.
  * Conexión con correo electrónico (lectura de carpetas autorizadas y preparación de borradores).
* **Automatización y Autonomía:**
  * Cola persistente para programar tareas únicas o recurrentes.
  * Ejecución en segundo plano con notificaciones de éxito o fallo.
* **Agente Programador:**
  * Leer repositorios autorizados y proponer cambios en ramas de trabajo aisladas.
  * Ejecutar pruebas de código, analizar errores y mostrar un *diff* comprensible antes de solicitar aprobación.
* **Interfaces Cliente:**
  * API privada con autenticación.
  * Interfaz web responsiva (chat, historial, panel de estado) accesible desde PC y móvil.

### Prioridad Baja (Fases 14-18: Largo Plazo)

* **Servidor 24/7:** Despliegue permanente en un mini PC con Linux, monitorizado y con acceso remoto mediante VPN privada (ej. Tailscale).
* **IA Local:** Enrutamiento inteligente de tareas hacia modelos locales cuantizados (ej. Ollama) para reducir costes y maximizar privacidad.
* **Realidad Aumentada:** Interfaz espacial con paneles flotantes compatibles con hardware AR.

---

## 2. Requisitos No Funcionales (El "Cómo")

### Seguridad y Privacidad (Crítico)

* **Mínimo Privilegio:** Cada módulo y herramienta debe recibir únicamente los permisos estrictamente necesarios.
* **Separación Decisión/Ejecución:** El modelo puede sugerir una acción, pero el sistema debe validar los permisos antes de ejecutarla.
* **Aprobación Humana:** Exigir confirmación explícita para acciones sensibles, destructivas, financieras o que envíen datos al exterior.
* **Protección de Datos:** Ningún token, contraseña o API key se almacenará en el código ni en la memoria conversacional. Todo dato sensible guardado debe estar cifrado.
* **Auditoría:** Se debe registrar qué usuario solicitó la acción, qué herramienta se usó y el resultado obtenido.

### Rendimiento y Recursos

* **Eficiencia Inicial:** El desarrollo debe operar de forma fluida en un portátil Asus TUF con aproximadamente 100 GB de almacenamiento libre.
* **Límites de Ejecución:** Las tareas automatizadas y las herramientas deben tener un tiempo máximo de ejecución (*timeout*) y límites de reintentos.

### Resiliencia y Tolerancia a Fallos

* **Manejo de Errores Externos:** Si la API del modelo de lenguaje o el internet falla, el sistema no debe romperse; debe registrar el error y notificar al usuario.
* **Recuperación de Tareas:** Si el sistema se apaga abruptamente, las tareas automatizadas pendientes deben recuperarse de la base de datos al reiniciar.
* **Parada de Emergencia:** Existirá un mecanismo rápido (*kill switch*) para detener procesos en ejecución o revocar permisos si el agente se comporta de manera indeseada.

---

## 3. Criterios de Éxito de la Arquitectura

* **Testabilidad:** Cada componente central debe poder probarse de forma automatizada y reproducible.
* **Trazabilidad:** Cualquier error o decisión del sistema debe poder diagnosticarse leyendo los *logs* (registros).
* **Mantenibilidad:** El código debe ser lo suficientemente claro y documentado como para que el desarrollador principal pueda modificarlo sin ayuda.
