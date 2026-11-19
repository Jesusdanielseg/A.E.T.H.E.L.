
# SAFETY_POLICY - A.E.T.H.E.L.

*Política Integral de Seguridad, Privacidad, Permisos, Control de Autonomía y Recuperación*

## 1. Principios Arquitectónicos de Seguridad

* **Principio de Mínimo Privilegio (PoLP):** Ningún módulo, componente, interfaz o herramienta del sistema poseerá más privilegios de los estrictamente necesarios para cumplir su función en un momento dado. Las credenciales, el acceso a directorios y los alcances de red estarán compartimentados.
* **Separación Estricta entre Decisión y Ejecución:** El modelo de lenguaje (IA) actúa exclusivamente como un motor de procesamiento y razonamiento, pudiendo *proponer* planes o llamadas a herramientas. Jamás tendrá la capacidad de autoejecutar acciones en el sistema. Una capa intermedia de políticas independientes validará obligatoriamente los parámetros, los permisos y el contexto antes de autorizar cualquier ejecución.
* **Seguridad por Diseño (Security by Design):** Ninguna herramienta, integración o módulo nuevo podrá incorporarse al proyecto si carece de controles de acceso, registro de auditoría y pruebas de fallo previas.

## 2. Gestión, Almacenamiento y Ciclo de Vida de Secretos

* **Prohibición Absoluta de Credenciales en el Repositorio:** Queda terminantemente prohibido almacenar claves de API (API keys), tokens de sesión, contraseñas, claves privadas SSH o certificados en el código fuente, historiales de chat o bases de datos de memoria conversacional.
* **Aislamiento mediante Variables de Entorno:** Toda credencial o parámetro sensible externo se gestionará única y exclusivamente mediante variables de entorno en archivos de configuración local protegidos (`.env`) o gestores de secretos dedicados.
* **Protocolo de Rotación y Revocación:** Si se sospecha o se detecta una brecha de seguridad o la exposición accidental de un secreto, el sistema o el desarrollador principal deberán revocar inmediatamente la credencial afectada ante el proveedor y generar una nueva.

## 3. Matriz de Permisos y Clasificación de Riesgo Operativo

Para gobernar la autonomía del sistema, las operaciones se clasifican en tres categorías estrictas de riesgo:

### Nivel 1: Operaciones Seguras de Solo Lectura

* **Definición:** Tareas que consultan información estática o interna sin alterar el estado del sistema ni exponer datos privados al exterior.
* **Ejemplos:** Consultar la fecha y hora, leer archivos dentro de directorios explícitamente permitidos, buscar en la base de datos de memoria local o analizar la estructura de un repositorio en modo de solo lectura.
* **Requisito de Autorización:** Ejecución autónoma sin intervención humana.

### Nivel 2: Operaciones de Escritura Local y Controlada

* **Definición:** Tareas que modifican el entorno local de forma acotada y reversible.
* **Ejemplos:** Registrar notas en el diario personal, crear recordatorios de agenda, redactar borradores de documentos o inicializar ramas de trabajo locales en Git.
* **Requisito de Autorización:** Validación previa de esquemas de datos, tipos de argumentos y restricciones de rutas (*sandboxing* de directorios).

### Nivel 3: Operaciones Sensibles, Irreversibles o de Alto Impacto

* **Definición:** Acciones que alteran sistemas externos, comprometen recursos de pago, destruyen información o ejecutan código en entornos operativos.
* **Ejemplos:** Modificación o borrado masivo de archivos/bases de datos, envío de correos electrónicos externos, publicación de código en repositorios públicos, despliegue de servicios en producción, ejecución de comandos con privilegios elevados o interacción con servicios financieros (a largo plazo).
* **Requisito de Autorización:** **Aprobación humana obligatoria.** El sistema interrumpirá el flujo de ejecución, presentará una solicitud clara de confirmación al usuario y esperará una respuesta afirmativa explícita (`[S/N]`) antes de proceder.

## 4. Privacidad de los Datos y Gestión de la Memoria

* **Políticas de Retención Selectiva:** Ninguna conversación ni dato de entrada se convertirá automáticamente en recuerdo a largo plazo o entrada de diario a menos que posea un valor explícito validado por el usuario o una regla programada.
* **Derecho de Auditoría, Supresión y Corrección:** El usuario mantendrá el control absoluto para consultar, editar, exportar o eliminar de forma permanente cualquier registro de la base de datos de memoria, garantizando que no queden rastros ocultos.
* **Minimización de Datos ante Proveedores Externos:** Al enviar peticiones a modelos de IA basados en la nube, el sistema filtrará el contexto para eliminar datos personales innecesarios, información financiera o secretos, minimizando la exposición de datos privados.

## 5. Mitigación de Vulnerabilidades de Agentes y Entornos de Ejecución

* **Tratamiento de Contenidos Externos como Datos No Confiables:** Todo contenido proveniente de fuentes externas (páginas web leídas, correos electrónicos, documentos subidos, issues de GitHub o archivos de texto de terceros) será tratado estrictamente como *datos pasivos*, jamás como instrucciones o comandos de control (*system prompts*). El sistema ignorará cualquier intento de anulación de reglas incrustado en dichos contenidos.
* **Aislamiento Estricto (Sandbox) del Agente Programador:** El agente encargado de analizar y modificar repositorios operará en un entorno aislado con restricciones estrictas de recursos (memoria, CPU, tiempo de ejecución máximo) y acotado únicamente a los directorios permitidos del proyecto.
* **Pruebas Previas obligatorias:** Ningún código generado por el agente podrá integrarse o proponerse formalmente sin haber superado un ciclo básico de pruebas y una revisión de los cambios (*diff*) por parte del desarrollador.

## 6. Auditoría, Registro de Incidencias y Mecanismo de Parada de Emergencia

* **Registro de Auditoría Persistente (Logs de Seguridad):** El sistema mantendrá un registro detallado e imborrable en disco de todas las operaciones de Nivel 2 y Nivel 3 ejecutadas, especificando la marca temporal, la herramienta invocada, los parámetros desensibilizados y el resultado devuelto.
* **Botón de Pánico / Parada de Emergencia (Kill Switch):** Existirá un mecanismo rápido y accesible (a nivel de proceso y de interfaz) para detener de forma fulminante cualquier hilo de ejecución en segundo plano, tarea automatizada o bucle de razonamiento descontrolado, revocando temporalmente los permisos activos del sistema.
* **Procedimientos de Recuperación y Respalduros:** Se programarán copias de seguridad cifradas periódicas de la base de datos de memoria y configuraciones críticas, acompañadas de un procedimiento documentado de restauración ante fallos catastróficos del sistema operativo o el hardware.
