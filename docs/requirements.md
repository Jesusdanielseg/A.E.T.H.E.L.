# REQUIREMENTS - A.E.T.H.E.L.

## 1. Requisitos Funcionales (El "Qué")

### Prioridad Alta (Fases 02-06: MVP y Núcleo)

* **Gestión de Conversación:**
  * Procesar entrada por texto y mantener el contexto de la conversación actual[cite: 3].
  * Separar las instrucciones de sistema (personalidad/reglas) de los mensajes del usuario[cite: 3].
  * Mantener una personalidad configurable con voz, modos, ejemplos y reglas de situaciones serias.
* **Memoria y Diario:**
  * Guardar mensajes de forma persistente[cite: 3].
  * Crear, consultar, editar y eliminar entradas del diario personal[cite: 3].
  * Generar resúmenes periódicos de las conversaciones o días[cite: 2].
* **Sistema de Herramientas (Acciones Aisladas):**
  * Interfaz estándar para registrar herramientas (nombre, propósito, argumentos y permisos)[cite: 3].
  * Herramientas iniciales: Consultar fecha/hora, leer archivos en directorios permitidos, crear recordatorios[cite: 3].

### Prioridad Media (Fases 07-11: Expansión)

* **Voz y Audio:**
  * Captura de audio por micrófono (activación por botón inicialmente) y conversión STT[cite: 3].
  * Síntesis de voz (TTS) con voz femenina estilo japonés[cite: 2], controlando velocidad, pausas y capacidad de interrupción[cite: 3].
* **Integraciones Personales:**
  * Conexión con calendario y tareas para consultar o crear eventos, detectando conflictos[cite: 3].
  * Conexión con correo electrónico (lectura de carpetas autorizadas y preparación de borradores)[cite: 3].
* **Automatización y Autonomía:**
  * Cola persistente para programar tareas únicas o recurrentes[cite: 3].
  * Ejecución en segundo plano con notificaciones de éxito o fallo[cite: 3].
* **Agente Programador:**
  * Leer repositorios autorizados y proponer cambios en ramas de trabajo aisladas[cite: 3].
  * Ejecutar pruebas de código, analizar errores y mostrar un *diff* comprensible antes de solicitar aprobación[cite: 3].
* **Interfaces Cliente:**
  * API privada con autenticación[cite: 2].
  * Interfaz web responsiva (chat, historial, panel de estado) accesible desde PC y móvil[cite: 3].

### Prioridad Baja (Fases 14-18: Largo Plazo)

* **Servidor 24/7:** Despliegue permanente en un mini PC con Linux, monitorizado y con acceso remoto mediante VPN privada (ej. Tailscale)[cite: 3].
* **IA Local:** Enrutamiento inteligente de tareas hacia modelos locales cuantizados (ej. Ollama) para reducir costes y maximizar privacidad[cite: 3].
* **Realidad Aumentada:** Interfaz espacial con paneles flotantes compatibles con hardware AR[cite: 3].

---

## 2. Requisitos No Funcionales (El "Cómo")

### Seguridad y Privacidad (Crítico)

* **Mínimo Privilegio:** Cada módulo y herramienta debe recibir únicamente los permisos estrictamente necesarios[cite: 2].
* **Separación Decisión/Ejecución:** El modelo puede sugerir una acción, pero el sistema debe validar los permisos antes de ejecutarla[cite: 2].
* **Aprobación Humana:** Exigir confirmación explícita para acciones sensibles, destructivas, financieras o que envíen datos al exterior[cite: 2, 3].
* **Protección de Datos:** Ningún token, contraseña o API key se almacenará en el código ni en la memoria conversacional[cite: 2]. Todo dato sensible guardado debe estar cifrado[cite: 3].
* **Auditoría:** Se debe registrar qué usuario solicitó la acción, qué herramienta se usó y el resultado obtenido[cite: 3].

### Rendimiento y Recursos

* **Eficiencia Inicial:** El desarrollo debe operar de forma fluida en un portátil Asus TUF con aproximadamente 100 GB de almacenamiento libre[cite: 3].
* **Límites de Ejecución:** Las tareas automatizadas y las herramientas deben tener un tiempo máximo de ejecución (*timeout*) y límites de reintentos[cite: 3].

### Resiliencia y Tolerancia a Fallos

* **Manejo de Errores Externos:** Si la API del modelo de lenguaje o el internet falla, el sistema no debe romperse; debe registrar el error y notificar al usuario[cite: 3].
* **Recuperación de Tareas:** Si el sistema se apaga abruptamente, las tareas automatizadas pendientes deben recuperarse de la base de datos al reiniciar[cite: 3].
* **Parada de Emergencia:** Existirá un mecanismo rápido (*kill switch*) para detener procesos en ejecución o revocar permisos si el agente se comporta de manera indeseada[cite: 3].

---

## 3. Criterios de Éxito de la Arquitectura

* **Testabilidad:** Cada componente central debe poder probarse de forma automatizada y reproducible[cite: 2].
* **Trazabilidad:** Cualquier error o decisión del sistema debe poder diagnosticarse leyendo los *logs* (registros)[cite: 2].
* **Mantenibilidad:** El código debe ser lo suficientemente claro y documentado como para que el desarrollador principal pueda modificarlo sin ayuda[cite: 1, 3].
