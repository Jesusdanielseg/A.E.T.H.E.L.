# Resultados de la evaluación inicial 04.5

**Fase:** 04 | **Estado:** evaluación inicial completada con limitaciones
**Fecha:** 2026-11-23 | **Rama:** `Fase-04/Cerebro-de-ia-y-personalidad`
**Commit base:** `95c03c1` (los cambios de esta evaluación están sin commit)

## 1. Entorno

- Python 3.14 en el equipo de referencia.
- CPU de 12 hilos, 15 GB de RAM y GPU de 6 GB de VRAM.
- Ollama con `gemma3:4b` (Q4_K_M, 3.4 GB en disco).
- `OLLAMA_THINK=false`, `OLLAMA_NUM_CTX=8192`, `OLLAMA_NUM_PREDICT=512`,
  `OLLAMA_KEEP_ALIVE=30m`.
- Orden de proveedores: `ollama,gemini,offline`.
- Gemini no se usó en esta evaluación local; el proveedor offline solo
  apareció como último recurso si Ollama fallaba.

## 2. Pruebas automáticas

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src tests
```

Resultado final:

```text
125 passed
All checks passed!
Success: no issues found in 55 source files
```

`tests/test_evaluation_04.py` cubre de forma determinista la compactación, la
persistencia del resumen y la conservación de afirmaciones contradictorias.
`tests/test_context.py` comprueba además que una compactación nueva conserva el
resumen anterior en el prompt del resumidor.

## 3. Selección de modelo

| Modelo | Tamaño / VRAM | Reparto | Respuesta simple en caliente | Observación | Decisión |
|---|---|---:|---:|---|---|
| `qwen3:8b` | 5.2 GB / ~6.6 GB | 30 % CPU, 70 % GPU | ~7-10 s | Con pensamiento activado llegaba a ~44 s. | Retirado. |
| `qwen3:4b` | 2.5 GB | GPU | ~10-28 s | Exponía razonamiento interno aunque `think=false`. | Retirado. |
| `gemma3:4b` | 3.4 GB / ~2.9 GB | 100 % GPU | ~0.6-2.2 s | Sin razonamiento visible; buen español. | **Elegido.** |

La primera carga de `gemma3:4b` tarda aproximadamente 9-14 s. Después, el
modelo permanece cargado durante 30 minutos gracias a `OLLAMA_KEEP_ALIVE`.

## 4. Resultados funcionales

Las latencias siguientes se midieron con el modelo caliente, el perfil de
personalidad completo y `OLLAMA_NUM_PREDICT=512`. No incluyen la primera carga.

### 4.1 Preguntas fáciles

| Caso | Latencia | Resultado |
|---|---:|---|
| Variable en Python | 1.25 s | Correcto y breve. |
| `git status` | 1.39 s | Correcto. |
| 25 °C a °F | 0.63 s | `77`, correcto. |
| HTTP 404 | 1.05 s | Correcto. |
| Archivos ocultos | 1.58 s | `ls -a`, correcto. |

### 4.2 Preguntas complejas

| Caso | Latencia | Resultado |
|---|---:|---|
| Diagnóstico de un script en cron | 7.31 s | Cinco pasos coherentes; respuesta acotada por el límite de tokens. |
| Prueba para división entre cero | 6.05 s | Propone casos y excepción esperada; diseño mejorable. |
| SQLite frente a PostgreSQL | 8.73 s | Comparación razonable en tres puntos. |
| Error de importación en Python | 6.57 s | Secuencia de diagnóstico accionable. |
| Separar configuración, lógica y persistencia | 7.28 s | Respeta la arquitectura general del proyecto. |

### 4.3 Contradicciones

Secuencia: «Mi color favorito es azul» → «Anotado: azul» → «En realidad es
rojo» → «¿Cuál es mi color favorito?».

| Turno | Latencia | Resultado |
|---|---:|---|
| 1 | 2.02 s | Reconoce la preferencia. |
| 2 | 1.52 s | Confirma que la tiene en cuenta. |
| 3 | 1.74 s | Reconoce el cambio a rojo. |
| 4 | 1.73 s | Responde «rojo». |

La respuesta final es correcta, aunque el modelo añade que no conserva
preferencias personales. Es una limitación de estilo, no una contradicción del
dato.

### 4.4 Incertidumbre

| Caso | Latencia | Resultado |
|---|---:|---|
| Disponibilidad futura del modelo | 2.57 s | No garantiza disponibilidad; propone verificar. |
| Precio exacto de la API | 2.28 s | No inventa una cifra ni una URL; remite a la fuente oficial. |
| Archivos del escritorio | 2.36 s | No inventa el listado; propone `ls ~/Escritorio`. |

### 4.5 Conversación con compactación real

Se ejecutó una conversación de 6 turnos con `max_messages=4` para forzar una
compactación real:

| Turno | Latencia | Observación |
|---|---:|---|
| 1 | 1.49 s | Registra «Orion» y «Kubuntu». |
| 2 | 7.51 s | Cambia a Python y funciones. |
| 3 | 4.97 s | Explica función pura. |
| 4 | 3.68 s | Cambia a bases de datos. |
| 5 | 9.98 s | Cambia a Git. |
| 6 | 4.89 s | Recupera «Orion» y «Kubuntu» desde el resumen. |

El turno 6 conserva los datos iniciales, pero añade una frase contradictoria:
después de decir «Kubuntu», afirma que no puede determinar el sistema operativo.
Se registra como limitación menor de coherencia.

La conversación manual de 20 turnos no se completó: dos intentos agotaron el
tiempo de 900 s. La compactación y la persistencia quedaron cubiertas por las
pruebas deterministas y por esta conversación real de 6 turnos.

## 5. Fallos encontrados y corregidos

| ID | Fallo | Corrección | Verificación |
|---|---|---|---|
| E1 | El prompt contenía `Primera línea directa: True.` y `Brevedad por defecto: True.`; el modelo empezaba con «True.». | Renderizar los booleanos como instrucciones naturales y validar su tipo. | Test de personalidad y respuesta real sin «True.». |
| E2 | El ejemplo de saludo hacía que el modelo empezara muchas respuestas con «Operativa.». | Se retiró el ejemplo de saludo; se añadió una regla para reconocer datos del usuario. | Respuestas de contradicciones sin «Operativa.». |
| E3 | El modelo ignoraba una preferencia compartida por el usuario. | Regla explícita para reconocer y conservar datos y preferencias. | Secuencia de contradicciones responde «rojo». |
| E4 | El modelo inventaba archivos del escritorio. | Regla y ejemplo para no inventar listados; proponer el comando de verificación. | Respuesta U3 corregida. |
| E5 | El modelo inventaba precios y URLs de una API. | Regla para no inventar precios, URLs ni estados; remitir a la fuente oficial. | Respuesta U2 sin cifras ni URLs inventadas. |
| E6 | Al compactar de nuevo, el resumen perdía hechos anteriores porque no se pasaba el resumen previo al resumidor. | Incluir `self.summary` en el prompt de compactación. | Test de contexto y conversación real de 6 turnos. |

## 6. Limitaciones conocidas

- `gemma3:4b` es un modelo pequeño: puede ser verboso, divagar o contradecirse
  en detalles menores.
- `OLLAMA_NUM_PREDICT=512` acota la latencia, pero puede truncar respuestas
  complejas. Súbelo solo si necesitas respuestas más largas.
- La conversación manual de 20 turnos sigue pendiente; no se debe interpretar
  esta evaluación como una certificación de conversaciones ilimitadas.
- El modelo puede alucinar. Las reglas de personalidad reducen el riesgo, no lo
  eliminan.
- No se probó Gemini en esta ejecución; el foco fue Ollama local.

## 7. Criterio de salida

- No quedan fallos P0 abiertos en la evaluación inicial.
- La compactación conserva el resumen anterior y un hecho estable en una
  conversación real de 6 turnos.
- Las respuestas contradictorias y de incertidumbre son aceptables con las
  limitaciones anteriores.
- La latencia está medida: ~0.6-2.2 s para preguntas simples y ~6-10 s para
  preguntas complejas en caliente.
- `pytest`, `ruff` y `mypy` pasan.
- Los fallos conocidos están documentados y los corregidos tienen pruebas.

La Fase 04 puede cerrarse como evaluación inicial con limitaciones
documentadas. No se inicia la Fase 05.
