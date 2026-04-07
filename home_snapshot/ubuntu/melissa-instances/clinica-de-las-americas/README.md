# Melissa · Clinica de las Americas

## Qué es hoy

Melissa dejó de ser un flujo rígido de respuestas cableadas y hoy funciona como una recepcionista conversacional model-first.
El modelo lleva la conversación, y el código solo interviene para:

- enrutar bien el contexto
- proteger contra respuestas rotas o demasiado robóticas
- conectar a Melissa con agenda, admin, KB, brand vault y métricas
- evitar caídas tontas a fallback local

En esta instancia, Melissa ya opera como una capa conversacional real para una clínica estética:

- atiende pacientes por lenguaje natural
- conversa con admins también en lenguaje natural
- usa Gemini 2.5 Flash/Pro como ruta principal
- escapa a fallback local solo cuando de verdad falla el camino inteligente

## En lo que se convirtió Melissa

Melissa ahora es un sistema híbrido:

1. Núcleo conversacional model-driven.
   El LLM decide casi toda la redacción. El objetivo no es decirle qué frase usar, sino darle contexto, identidad y límites reales.

2. Orquestador clínico.
   El runtime mete contexto de clínica, servicios, pricing, agenda, historial, KB y reglas aprendidas para que la respuesta salga situada.

3. Copiloto del admin.
   El admin ya no depende solo de comandos rígidos. Puede preguntar cosas naturales sobre chats, tono, clientes o disponibilidad.

4. Capa de humanidad.
   Hay guardrails para detectar frases cortadas, saludos redundantes, respuestas demasiado genéricas, identity pitches, handoffs de precio incompletos y regresiones de tema.

5. Memoria operativa por instancia.
   La instancia guarda historial conversacional, reglas aprendidas, brand assets y conocimiento activo en su propio entorno.

## Capacidades actuales verificadas

- Preguntas meta del paciente como `eres bot o qué` ya se responden por la ruta correcta y no se mezclan con la lógica de negocio.
- Pedidos de cita como `quiero cita el miércoles en la tarde` ya no quedan en media frase.
- Si Melissa no tiene precio confiable, lo dice claro y avisa al admin.
- Si no hay agenda conectada, Melissa pregunta al admin y luego puede devolverle al paciente una respuesta propia con ese contexto.
- El admin puede preguntar variantes naturales como `han escrito hoy o estás sola` y recibe snapshot real de chats.
- Los uploads de marca/conocimiento sí aceptan `PDF`, `DOCX`, `TXT`, `MD` y `JSON`; si extraen texto, ese texto se anexa al conocimiento activo.

## Estado técnico

- Archivo principal: [melissa.py](/home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.py)
- Base local: [melissa.db](/home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.db)
- Tests de comportamiento: [test_patient_conversation_humanity.py](/home/ubuntu/melissa-instances/clinica-de-las-americas/tests/test_patient_conversation_humanity.py)
- Puerto activo: `8003`
- Modelo principal verificado en runtime:
  `reasoning=google/gemini-2.5-pro`
  `fast=google/gemini-2.5-flash`

## Qué falta

Lo siguiente sigue pendiente y vale la pena atacarlo en el próximo tramo:

- Partir [melissa.py](/home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.py) en módulos serios.
  Ya es demasiado grande y hay riesgo real de duplicados silenciosos, como el que rompía `_compose_patient_availability_reply`.

- Memoria explícita por admin y por clínica.
  Falta una estructura de carpetas y/o storage más clara para aprendizaje persistente separado por dueño, instancia y negocio.

- Humanizar más el flujo de disponibilidad pendiente.
  Mejoró, pero el primer mensaje de “te confirmo” todavía puede sonar operativo en algunos turnos.

- Limpiar `admin_chat_ids` sintéticos o probes viejos.
  La instancia sigue intentando notificar IDs de prueba que hoy devuelven `400`.

- Más pruebas multi-turno reales.
  Ya hay buena cobertura unitaria, pero faltan simulaciones largas de admin→Melissa→paciente y conversaciones completas por perfiles.

- Separar mejor documentación viva de operación.
  Falta una doc corta para sync/rollforward y otra para assets/KB/aprendizaje.

## Operación rápida

- Health:
  `curl http://127.0.0.1:8003/health`

- Tests:
  `pytest -q /home/ubuntu/melissa-instances/clinica-de-las-americas/tests/test_patient_conversation_humanity.py`

- Reinicio local:
  `pkill -f '/home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.py'`
  `nohup python3 /home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.py >/tmp/clinica-americas.out 2>&1 &`

## Última validación de esta etapa

- Suite verde: `54 passed`
- Flujo admin natural: OK
- Handoff de precio al admin: OK
- Reenvío de disponibilidad admin→paciente con texto propio: OK
