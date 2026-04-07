# Melissa Human Patient Dialogue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que Melissa responda a pacientes desde el modelo, con identidad y criterio conversacional, sin saludos ni fallbacks prefabricados.

**Architecture:** El arreglo ataca tres capas: decisión de primer turno, prompt de paciente y estado persistido de control/reglas. La conversación debe pasar por el LLM en primer turno; las reglas duras quedan limitadas a restricciones de seguridad/tono, no a plantillas completas.

**Tech Stack:** Python, FastAPI, SQLite, pytest

---

### Task 1: Cubrir la regresión del primer turno y del saneamiento de estado

**Files:**
- Create: `tests/test_patient_conversation_humanity.py`
- Test: `tests/test_patient_conversation_humanity.py`

- [ ] **Step 1: Write the failing test**

```python
def test_first_turn_short_messages_do_not_use_seeded_templates():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)

    assert generator._should_use_seeded_first_turn("Hola buenas tardes", []) is False
    assert generator._should_use_seeded_first_turn("Botox precio", []) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /home/ubuntu/melissa-instances/clinica-de-las-americas/tests/test_patient_conversation_humanity.py -q`
Expected: FAIL because `_should_use_seeded_first_turn` does not exist yet and the sanitation helpers are missing.

- [ ] **Step 3: Add regression tests for persistent control state**

```python
def test_patient_control_state_strips_fixed_templates():
    module = load_melissa_module()
    raw_state = {
        "enabled": True,
        "patient": {
            "greeting_template": "Hola, soy Melissa, del equipo de {clinic_name}.",
            "second_bubble_template": "Te ayudo con información, valoración y disponibilidad.",
            "fallback_template": "Perdón, no te entendí bien.",
            "max_bubbles": 2,
            "register": "tu",
            "no_emojis": True,
        },
    }

    cleaned = module.sanitize_owner_style_control_state(raw_state)

    assert cleaned["patient"]["greeting_template"] == ""
    assert cleaned["patient"]["second_bubble_template"] == ""
    assert cleaned["patient"]["fallback_template"] == ""
    assert cleaned["patient"]["max_bubbles"] == 2
```

- [ ] **Step 4: Add regression test for trust-rule contamination**

```python
def test_patient_prompt_filters_admin_only_trust_rules():
    module = load_melissa_module()
    rules = [
        {"rule": "No hables así, soy tu admin"},
        {"rule": "Si preguntan precio, responde eso primero"},
    ]

    filtered = module.filter_trust_rules_for_audience(rules, is_admin=False)

    assert [item["rule"] for item in filtered] == [
        "Si preguntan precio, responde eso primero"
    ]
```

### Task 2: Quitar el bypass del primer turno

**Files:**
- Modify: `melissa.py`
- Test: `tests/test_patient_conversation_humanity.py`

- [ ] **Step 1: Implement helper for first-turn routing**

```python
def _should_use_seeded_first_turn(self, text: str, history: List[Dict]) -> bool:
    return False
```

- [ ] **Step 2: Replace the hardcoded branch in `process_message`**

```python
if is_first_patient_turn and self.generator._should_use_seeded_first_turn(text, history):
    ...
else:
    reasoning = await self.reasoning.reason(...)
    response = await self.generator.generate(...)
```

- [ ] **Step 3: Make first-turn normalization non-authoring**

```python
if not response.strip():
    return response
```

### Task 3: Reescribir el prompt de paciente alrededor de identidad

**Files:**
- Modify: `melissa.py`
- Test: `tests/test_patient_conversation_humanity.py`

- [ ] **Step 1: Replace first-turn prompt rules with identity-driven guidance**

```python
first_turn_rules = (
    "PRIMER TURNO:\n"
    "- si ya dijeron lo que buscan, responde desde ahí\n"
    "- si solo saludaron, saluda corto y sigue natural\n"
    "- no uses aperturas fijas ni speech de presentación\n"
    "- responde como alguien real del equipo, no como formulario"
) if user_turns <= 1 or is_first_turn else ""
```

- [ ] **Step 2: Tighten patient prompt constraints around directness and naturalness**

```python
prompt_sections.append(
    "REGLAS DE CONVERSACIÓN:\n"
    "- responde primero la duda real del paciente\n"
    "- una sola pregunta útil cuando haga falta\n"
    "- no uses frases prefabricadas repetidas\n"
    "- no actúes como bot ni como recepcionista de guion"
)
```

### Task 4: Sanear el estado persistido y acotar reglas por audiencia

**Files:**
- Modify: `melissa.py`
- Test: `tests/test_patient_conversation_humanity.py`

- [ ] **Step 1: Add sanitation helpers**

```python
def sanitize_owner_style_control_state(state: Dict[str, Any]) -> Dict[str, Any]:
    ...

def filter_trust_rules_for_audience(rules: List[Dict[str, Any]], *, is_admin: bool) -> List[Dict[str, Any]]:
    ...
```

- [ ] **Step 2: Use filtered rules in patient prompt builders**

```python
for rule in filter_trust_rules_for_audience(db.get_trust_rules(limit=4), is_admin=False):
    ...
```

- [ ] **Step 3: Apply sanitation to the live DB-backed control state**

```python
owner_style_controller.sanitize_persisted_state()
```

### Task 5: Verify end-to-end

**Files:**
- Modify: `melissa.py`
- Test: `tests/test_patient_conversation_humanity.py`

- [ ] **Step 1: Run targeted tests**

Run: `pytest /home/ubuntu/melissa-instances/clinica-de-las-americas/tests/test_patient_conversation_humanity.py -q`
Expected: PASS

- [ ] **Step 2: Run syntax verification**

Run: `python3 -m py_compile /home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.py`
Expected: exit 0

- [ ] **Step 3: Inspect live persisted state**

Run: `sqlite3 /home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.db "SELECT key, value FROM core_memory WHERE key IN ('v8_owner_style_control','v8_prompt_evolutions');"`
Expected: patient templates vaciadas y reglas de admin conservadas sin contaminar pacientes
