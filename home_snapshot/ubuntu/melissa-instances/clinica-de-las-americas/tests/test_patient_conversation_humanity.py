from __future__ import annotations

import asyncio
import importlib.util
import sqlite3
import sys
import types
import uuid
from pathlib import Path


MODULE_PATH = Path("/home/ubuntu/melissa-instances/clinica-de-las-americas/melissa.py")


def load_melissa_module():
    module_name = f"melissa_instance_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_first_turn_short_messages_do_not_use_seeded_templates():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)

    assert generator._should_use_seeded_first_turn("Hola buenas tardes", []) is False
    assert generator._should_use_seeded_first_turn("Botox precio", []) is False


def test_patient_control_state_strips_fixed_templates():
    module = load_melissa_module()
    raw_state = {
        "enabled": True,
        "global": {
            "forbidden_phrases": [],
            "forbidden_starts": ["claro"],
            "replacement_map": {"ay": "entiendo"},
            "style_notes": [],
            "greeting_template": "",
            "second_bubble_template": "",
            "third_bubble_template": "",
            "closing_template": "",
            "fallback_template": "",
            "max_bubbles": 2,
            "register": "auto",
            "respectful": True,
            "no_emojis": True,
        },
        "patient": {
            "forbidden_phrases": [],
            "forbidden_starts": ["oye", "claro", "listo"],
            "replacement_map": {},
            "style_notes": [
                "Suena humana, clara y profesional.",
                "No suenes robótica ni demasiado explicativa.",
            ],
            "greeting_template": "Hola, soy Melissa, del equipo de {clinic_name}.",
            "second_bubble_template": "Te ayudo con información, valoración y disponibilidad.",
            "third_bubble_template": "",
            "closing_template": "",
            "fallback_template": "Perdón, no te entendí bien.",
            "max_bubbles": 2,
            "register": "tu",
            "respectful": True,
            "no_emojis": True,
        },
    }

    cleaned = module.sanitize_owner_style_control_state(raw_state)

    assert cleaned["patient"]["greeting_template"] == ""
    assert cleaned["patient"]["second_bubble_template"] == ""
    assert cleaned["patient"]["fallback_template"] == ""
    assert cleaned["patient"]["max_bubbles"] == 2
    assert cleaned["patient"]["register"] == "tu"


def test_admin_control_state_strips_stock_templates_and_noisy_notes():
    module = load_melissa_module()
    raw_state = {
        "enabled": True,
        "global": module.OwnerStyleController()._blank_bucket(),
        "admin": {
            "forbidden_phrases": [],
            "forbidden_starts": ["oye", "a ver", "mira"],
            "replacement_map": {},
            "style_notes": [
                "Con el admin habla con respeto, claridad y criterio.",
                'Conmigo no empieces con "oye',
                "No hables asi, soy tu admin",
            ],
            "greeting_template": "Hola, {admin_name}.",
            "second_bubble_template": "Estoy lista para ayudarle con la instancia, el tono, los servicios o las pruebas.",
            "third_bubble_template": "Si quieres, te ayudo a dejarlo encaminado ahora mismo",
            "closing_template": "",
            "fallback_template": "No me quedó claro todavía. Dígame exactamente qué ajuste quiere y lo hago.",
            "max_bubbles": 2,
            "register": "usted",
            "respectful": True,
            "no_emojis": True,
        },
        "patient": module.OwnerStyleController()._blank_bucket(register="tu"),
    }

    cleaned = module.sanitize_owner_style_control_state(raw_state)

    assert cleaned["admin"]["greeting_template"] == ""
    assert cleaned["admin"]["second_bubble_template"] == ""
    assert cleaned["admin"]["third_bubble_template"] == ""
    assert cleaned["admin"]["fallback_template"] == ""
    assert cleaned["admin"]["style_notes"] == [
        "Con el admin habla con respeto, claridad y criterio.",
    ]


def test_patient_prompt_filters_admin_only_trust_rules():
    module = load_melissa_module()
    rules = [
        {"rule": "No hables así, soy tu admin"},
        {"rule": "a los administradores háblales con respeto y más ejecutivo"},
        {"rule": "Si preguntan precio, responde eso primero"},
        {"rule": 'Cuando te digan hola, responde parecido a esto: "hola ||| dime"'},
    ]

    filtered = module.filter_trust_rules_for_audience(rules, is_admin=False)

    assert [item["rule"] for item in filtered] == [
        "Si preguntan precio, responde eso primero",
    ]


def test_core_memory_block_keeps_only_business_identity_signals():
    module = load_melissa_module()
    db = module.DatabaseManager(
        str(MODULE_PATH.parent / "melissa.db"),
        str(MODULE_PATH.parent / "vectors.db"),
    )

    block = db.get_core_memory_block()

    assert "clinic_name" in block
    assert "pricing_policy" in block
    assert "v8_prompt_evolutions" not in block
    assert "google_snapshot_text" not in block
    assert "v8_owner_style_control" not in block


def test_minimum_business_knowledge_does_not_force_ustedeo_with_patients():
    module = load_melissa_module()

    block = module._build_minimum_business_knowledge(
        {"name": "Clinica de las americas", "services": ["Botox"]}
    )

    lowered = block.lower()
    assert "trato de usted con pacientes" not in lowered
    assert "adapta el trato al tono del paciente" in lowered


def test_ensure_minimum_business_state_migrates_legacy_ustedeo_defaults():
    module = load_melissa_module()

    class FakeDB:
        def __init__(self):
            self.clinic = {
                "name": "Clinica de las americas",
                "services": ["Botox"],
                "schedule": {},
                "pricing": {},
                "platform": "telegram",
                "persona_config": {
                    "name": "Melissa",
                    "rol": "bot conversacional del equipo",
                    "registro": "usted",
                    "tone_instruction": (
                        "Hablas como Melissa, bot conversacional del equipo de la clínica en Colombia."
                    ),
                },
            }
            self.updated = {}

        def get_clinic(self):
            return self.clinic

        def update_clinic(self, **kwargs):
            self.updated.update(kwargs)
            self.clinic.update(kwargs)

        def recall(self, key):
            return ""

        def remember(self, *args, **kwargs):
            return None

    fake_db = FakeDB()
    module.db = fake_db
    module.kb = None
    module._KB_AVAILABLE = False
    module._BRAND_ASSETS_AVAILABLE = False

    result = module.ensure_minimum_business_state(force=False)

    assert result["ok"] is True
    persona = fake_db.updated["persona_config"]
    assert persona["registro"] == "auto"
    assert persona["rol"] == "asesora del equipo"
    assert "bot conversacional del equipo" not in persona.get("tone_instruction", "").lower()
    assert "tuteas de forma natural" in persona.get("tone_instruction", "").lower()


def test_patient_message_scope_routes_pure_meta_and_off_topic_outside_business_path():
    module = load_melissa_module()
    clinic = {"services": ["Botox", "Rellenos", "Láser"]}

    assert module._patient_message_scope("Eres un bot?", clinic) == (
        "meta",
        "Eres un bot?",
    )
    assert module._patient_message_scope("háblame de bitcoin", clinic) == (
        "off_topic",
        "háblame de bitcoin",
    )


def test_price_inquiry_does_not_force_external_search():
    module = load_melissa_module()
    analyzer = module.MessageAnalyzer()

    analysis = analyzer.analyze("hola, vi que tienen botox, cuánto sale eso", [])

    assert module._is_price_like_message("hola, vi que tienen botox, cuánto sale eso") is True
    assert analysis.requires_search is False


def test_llm_engine_loads_fourth_gemini_key_before_external_providers(monkeypatch):
    module = load_melissa_module()

    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "k2")
    monkeypatch.setenv("GEMINI_API_KEY_3", "k3")
    monkeypatch.setenv("GEMINI_API_KEY_4", "k4")
    module.Config.OPENROUTER_API_KEY = "or"
    module.Config.OPENAI_API_KEY = "oa"
    module.Config.GROQ_API_KEY = "groq"

    engine = module.LLMEngine()

    assert [provider.name for provider in engine.providers[:4]] == [
        "gemini_k1",
        "gemini_k2",
        "gemini_k3",
        "gemini_k4",
    ]


def test_reasoning_uses_fast_tier_for_price_like_messages():
    module = load_melissa_module()
    engine = module.ReasoningEngine(llm=None)
    analysis = types.SimpleNamespace(
        intent=module.IntentType.GENERAL_QUESTION,
        requires_search=False,
    )

    tier = engine._select_model_tier(
        "o sea que no me pueden dar el precio",
        analysis,
        history=[{"role": "assistant", "content": "stub"}],
    )

    assert tier == "fast"


def test_google_requests_prefer_openrouter_and_openai_before_groq():
    module = load_melissa_module()
    engine = module.LLMEngine.__new__(module.LLMEngine)
    engine.providers = [
        types.SimpleNamespace(name="groq"),
        types.SimpleNamespace(name="gemini_k1"),
        types.SimpleNamespace(name="gemini_k2"),
        types.SimpleNamespace(name="openrouter"),
        types.SimpleNamespace(name="openai"),
    ]

    ordered = [p.name for p in module.LLMEngine._ordered_providers(engine, "google/gemini-2.5-pro")]

    assert ordered == ["gemini_k1", "gemini_k2", "openrouter", "openai", "groq"]


def test_llm_complete_reports_attempted_provider_chain_in_metadata():
    module = load_melissa_module()

    class FakeProvider:
        def __init__(self, name, response=None, error=None):
            self.name = name
            self._response = response
            self._error = error

        async def complete(self, *args, **kwargs):
            if self._error is not None:
                raise self._error
            return self._response, {"provider": self.name, "model": f"{self.name}-model", "latency_ms": 12}

    engine = module.LLMEngine.__new__(module.LLMEngine)
    engine.providers = [
        FakeProvider("gemini_k1", error=RuntimeError("boom")),
        FakeProvider("openrouter", response="ok desde openrouter"),
        FakeProvider("groq", response="ok desde groq"),
    ]
    engine._failures = {}
    engine._blocked_until = {}
    engine._blacklist_ttl = 60.0
    engine._cache = {}
    engine._cache_ttl = 300

    original_db = module.db
    module.db = None
    try:
        _, metadata = asyncio.run(
            module.LLMEngine.complete(
                engine,
                messages=[{"role": "user", "content": "hola"}],
                model_tier="fast",
                use_cache=False,
            )
        )
    finally:
        module.db = original_db

    assert metadata["provider"] == "openrouter"
    assert metadata["attempted_providers"] == ["gemini_k1", "openrouter"]


def test_gemini_pro_requests_retry_flash_before_external_fallbacks():
    module = load_melissa_module()

    class GeminiProbeProvider:
        def __init__(self):
            self.name = "gemini_k1"
            self.models = []

        async def complete(self, *args, **kwargs):
            model = kwargs.get("model")
            self.models.append(model)
            if model == "google/gemini-2.5-pro":
                raise RuntimeError("pro unavailable")
            return "respuesta desde flash", {"provider": self.name, "model": model, "latency_ms": 9}

    class FallbackProvider:
        def __init__(self, name):
            self.name = name
            self.calls = 0

        async def complete(self, *args, **kwargs):
            self.calls += 1
            return f"respuesta desde {self.name}", {"provider": self.name, "model": kwargs.get("model"), "latency_ms": 9}

    gemini = GeminiProbeProvider()
    openrouter = FallbackProvider("openrouter")
    groq = FallbackProvider("groq")

    engine = module.LLMEngine.__new__(module.LLMEngine)
    engine.providers = [gemini, openrouter, groq]
    engine._failures = {}
    engine._blocked_until = {}
    engine._blacklist_ttl = 60.0
    engine._cache = {}
    engine._cache_ttl = 300

    original_db = module.db
    module.db = None
    try:
        response, metadata = asyncio.run(
            module.LLMEngine.complete(
                engine,
                messages=[{"role": "user", "content": "necesito ayuda urgente con mi cita"}],
                model_tier="reasoning",
                use_cache=False,
            )
        )
    finally:
        module.db = original_db

    assert response == "respuesta desde flash"
    assert gemini.models == ["google/gemini-2.5-pro", "google/gemini-2.5-flash"]
    assert openrouter.calls == 0
    assert groq.calls == 0
    assert metadata["model"] == "google/gemini-2.5-flash"


def test_generate_keeps_fast_tier_for_price_like_turns_even_with_low_confidence():
    module = load_melissa_module()

    class FakeLLM:
        def __init__(self):
            self.tiers = []

        async def complete(self, *args, **kwargs):
            self.tiers.append(kwargs.get("model_tier"))
            return "No tengo ese dato exacto ahorita", {"model": "fake"}

    fake_llm = FakeLLM()
    generator = module.ResponseGenerator(llm=fake_llm)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    asyncio.run(
        generator.generate(
            message="o sea que no me pueden dar el precio",
            analysis=types.SimpleNamespace(intent=module.IntentType.GENERAL_QUESTION),
            reasoning={"confidence": 0.2, "response_strategy": "responder precio primero"},
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            patient={"is_new": False, "visits": 2},
            history=[{"role": "assistant", "content": "El valor depende de la valoración"}],
            search_context="",
            personality=personality,
            kb_context="",
            chat_id="price_generate_tier_probe",
        )
    )

    assert fake_llm.tiers[0] == "fast"


def test_admin_inbox_query_detects_cliente_te_ha_escrito_variants():
    module = load_melissa_module()

    assert module._is_admin_inbox_query("Holaaa melissa algun cliente te ha escrito?") is True
    assert module._is_admin_inbox_query("Melissa quién te ha escrito") is True
    assert module._is_admin_inbox_query("quien te escribió hoy") is True
    assert module._is_admin_inbox_query("Una disculap, te hago una pregunta quien ha escrito") is True
    assert module._is_admin_inbox_query("qué chats tienes") is True
    assert module._is_admin_inbox_query("hay conversaciones?") is True
    assert module._is_admin_inbox_query("han escrito hoy o estás sola") is True
    assert module._is_admin_inbox_query("quiero ajustar el tono") is False


def test_admin_recent_chat_followup_query_detects_natural_variants():
    module = load_melissa_module()

    assert module._is_admin_recent_chat_followup_query("Y que han hablado") is True
    assert module._is_admin_recent_chat_followup_query("y de qué hablaron") is True
    assert module._is_admin_recent_chat_followup_query("q hablaron") is True
    assert module._is_admin_recent_chat_followup_query("q te han dicho") is True
    assert module._is_admin_recent_chat_followup_query("quiero ajustar el tono") is False


def test_admin_recent_chat_context_followup_detects_anaphoric_variants():
    module = load_melissa_module()

    assert module._is_admin_recent_chat_context_followup("y luego") is True
    assert module._is_admin_recent_chat_context_followup("q t han dicho") is True
    assert module._is_admin_recent_chat_context_followup("cómo quedó eso") is True
    assert module._is_admin_recent_chat_context_followup("quiero ajustar el tono") is False


def test_owner_style_control_ignores_recent_chat_transcript_requests():
    module = load_melissa_module()
    controller = module.OwnerStyleController()

    assert controller.detect_control_intent("muestrame los ultimos 3 mensajes de cada uno") is False
    assert controller.detect_control_intent("muéstrame los últimos 3 mensajes de cada chat") is False
    assert controller.detect_control_intent("responde en 3 mensajes") is True


def test_admin_natural_command_handles_recent_chat_followup_without_llm():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {
        "6908159885": {
            "action": "recent_chats_snapshot",
            "latest_chat_id": "6437195704",
            "ts": module.time.time(),
        }
    }
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def should_not_run(*args, **kwargs):
        raise AssertionError("admin LLM no debería usarse en este seguimiento")

    melissa._admin_llm_brain = should_not_run
    module.owner_style_controller = None
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    saved_messages = []
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [
            {
                "role": "assistant",
                "content": "Me ha escrito 1 chat real en esta instancia. ||| El último que veo es un chat sin nombre guardado.",
            }
        ],
        get_patient_conversation=lambda chat_id, limit=8: [
            {
                "role": "user",
                "content": "Hola buenas noches, se que son las 3 am pero a qué precio tienen el botox",
            },
            {
                "role": "assistant",
                "content": "No tengo un precio exacto para el bótox en este momento ||| El valor final depende de una valoración inicial y de las zonas específicas a tratar",
            },
            {
                "role": "user",
                "content": "Pero un aproximado cuánto podría ser?",
            },
        ],
        get_patient=lambda chat_id: {},
        save_message=lambda chat_id, role, content: saved_messages.append((chat_id, role, content)),
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "Y que han hablado",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "botox" in merged or "bótox" in merged
    assert "precio" in merged
    assert "cuénteme qué quiere ajustar" not in merged
    assert saved_messages


def test_admin_natural_command_uses_recent_chat_context_followup_without_llm():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {
        "6908159885": {
            "action": "recent_chats_snapshot",
            "latest_chat_id": "6437195704",
            "ts": module.time.time(),
        }
    }
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def should_not_run(*args, **kwargs):
        raise AssertionError("admin LLM no debería usarse en follow-up anafórico")

    melissa._admin_llm_brain = should_not_run
    module.owner_style_controller = module.OwnerStyleController()
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    saved_messages = []
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        get_patient_conversation=lambda chat_id, limit=8: [
            {"role": "user", "content": "hola, vi botox y quiero saber el precio"},
            {"role": "assistant", "content": "Te cuento cómo se maneja y qué zona te interesa"},
            {"role": "user", "content": "la frente y patas de gallo"},
        ],
        get_patient=lambda chat_id: {"name": "Laura"},
        save_message=lambda chat_id, role, content: saved_messages.append((chat_id, role, content)),
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "y luego",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "laura" in merged or "ese chat" in merged
    assert "botox" in merged
    assert saved_messages


def test_admin_natural_command_handles_shorthand_recent_chat_followup_without_llm():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def should_not_run(*args, **kwargs):
        raise AssertionError("admin LLM no debería usarse en follow-up shorthand")

    melissa._admin_llm_brain = should_not_run
    module.owner_style_controller = module.OwnerStyleController()
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    saved_messages = []
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        get_recent_patient_chats=lambda limit=10: [
            {"chat_id": "6437195704", "name": "Laura"},
            {"chat_id": "3015559999", "name": "Camilo"},
        ],
        get_patient_conversation=lambda chat_id, limit=8: [
            {"role": "user", "content": "hola, vi botox y quiero saber el precio"},
            {"role": "assistant", "content": "Te cuento cómo se maneja y qué zona te interesa"},
            {"role": "user", "content": "la frente y patas de gallo"},
        ],
        get_patient=lambda chat_id: {"name": "Laura"},
        save_message=lambda chat_id, role, content: saved_messages.append((chat_id, role, content)),
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "q te han dicho",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "laura" in merged or "ese chat" in merged
    assert "botox" in merged
    assert "quedó aplicado" not in merged
    assert saved_messages


def test_admin_natural_command_handles_recent_chat_transcript_request_without_control_hijack():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {
        "6908159885": {
            "action": "recent_chats_snapshot",
            "latest_chat_id": "6437195704",
            "ts": module.time.time(),
        }
    }
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def should_not_run(*args, **kwargs):
        raise AssertionError("admin LLM no debería usarse en este transcript")

    melissa._admin_llm_brain = should_not_run
    module.owner_style_controller = module.OwnerStyleController()
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    saved_messages = []

    conversations = {
        "6437195704": [
            {"role": "user", "content": "hola, vi botox y quiero saber el precio"},
            {"role": "assistant", "content": "Te cuento cómo se maneja y qué zona te interesa"},
            {"role": "user", "content": "la frente y patas de gallo"},
        ],
        "3015559999": [
            {"role": "user", "content": "quiero cita el jueves"},
            {"role": "assistant", "content": "Te confirmo horario en la tarde"},
            {"role": "user", "content": "me sirve después de las 3"},
        ],
    }

    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [
            {
                "role": "assistant",
                "content": "Sí, hay 6 conversaciones. Las más recientes aún no tienen nombre guardado.",
            }
        ],
        get_recent_patient_chats=lambda limit=10: [
            {"chat_id": "6437195704", "name": "Laura"},
            {"chat_id": "3015559999", "name": "Camilo"},
        ],
        get_patient_conversation=lambda chat_id, limit=30: conversations.get(chat_id, []),
        get_patient=lambda chat_id: {"name": "Laura" if chat_id == "6437195704" else "Camilo"},
        save_message=lambda chat_id, role, content: saved_messages.append((chat_id, role, content)),
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "muestrame los ultimos 3 mensajes de cada uno",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "laura" in merged
    assert "camilo" in merged
    assert "botox" in merged
    assert "jueves" in merged
    assert "quedó aplicado" not in merged
    assert saved_messages


def test_admin_natural_command_handles_recent_chat_transcript_without_snapshot_context():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def should_not_run(*args, **kwargs):
        raise AssertionError("admin LLM no debería usarse en este transcript sin contexto previo")

    melissa._admin_llm_brain = should_not_run
    module.owner_style_controller = module.OwnerStyleController()
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    saved_messages = []

    conversations = {
        "6437195704": [
            {"role": "user", "content": "hola, vi botox y quiero saber el precio"},
            {"role": "assistant", "content": "Te cuento cómo se maneja y qué zona te interesa"},
            {"role": "user", "content": "la frente y patas de gallo"},
        ],
        "3015559999": [
            {"role": "user", "content": "quiero cita el jueves"},
            {"role": "assistant", "content": "Te confirmo horario en la tarde"},
            {"role": "user", "content": "me sirve después de las 3"},
        ],
    }

    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        get_recent_patient_chats=lambda limit=10: [
            {"chat_id": "6437195704", "name": "Laura"},
            {"chat_id": "3015559999", "name": "Camilo"},
        ],
        get_patient_conversation=lambda chat_id, limit=30: conversations.get(chat_id, []),
        get_patient=lambda chat_id: {"name": "Laura" if chat_id == "6437195704" else "Camilo"},
        save_message=lambda chat_id, role, content: saved_messages.append((chat_id, role, content)),
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "ue has hablado? muestrame los ultimos 3 mensajes de cada uno",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "laura" in merged
    assert "camilo" in merged
    assert "quedó aplicado" not in merged
    assert saved_messages


def test_admin_greeting_prefers_llm_before_local_fallback():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def fake_brain(*args, **kwargs):
        return {
            "reply": "Todo bien. Qué quieres revisar hoy?",
            "action": "none",
            "data": {},
        }

    async def fake_apply_action(*args, **kwargs):
        return True

    melissa._admin_llm_brain = fake_brain
    melissa._admin_apply_action = fake_apply_action
    module.owner_style_controller = None
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        save_message=lambda *args, **kwargs: None,
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "como estas",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "todo bien" in merged
    assert "bien, gracias" not in merged


def test_admin_brain_prompt_asks_model_to_pivot_after_out_of_scope_turn():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    captured = {}

    class FakeLLM:
        async def complete(self, messages, **kwargs):
            captured["system"] = messages[0]["content"]
            return '{"reply":"Todo bien.","action":"none","data":{}}', {"model": "fake"}

    old_llm = module.llm_engine
    module.llm_engine = FakeLLM()
    module.owner_style_controller = None
    module.skill_engine = None
    module.bus = None
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
    )

    try:
        asyncio.run(
            melissa._admin_llm_brain(
                "6908159885",
                "quien ha escrito",
                [{"role": "user", "content": "ponme one day de dua lipa en yt de la tv"}],
                {"name": "Clinica de las americas", "sector": "estetica"},
                "Melissa",
            )
        )
    finally:
        module.llm_engine = old_llm

    system_prompt = captured["system"].lower()
    assert "no uses frases como" in system_prompt
    assert "mi función es" in system_prompt or "mi funcion es" in system_prompt
    assert "si el dueño cambia de tema" in system_prompt


def test_admin_brain_prompt_avoids_scripted_dialogue_examples():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    captured = {}

    class FakeLLM:
        async def complete(self, messages, **kwargs):
            captured["system"] = messages[0]["content"]
            return '{"reply":"Entendido.","action":"none","data":{}}', {"model": "fake"}

    old_llm = module.llm_engine
    module.llm_engine = FakeLLM()
    module.owner_style_controller = None
    module.skill_engine = None
    module.bus = None
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
    )

    try:
        asyncio.run(
            melissa._admin_llm_brain(
                "6908159885",
                "hola",
                [],
                {"name": "Clinica de las americas", "sector": "estetica"},
                "Melissa",
            )
        )
    finally:
        module.llm_engine = old_llm

    system_prompt = captured["system"].lower()
    assert "así hablas con el dueño" not in system_prompt
    assert "ponme one day de dua lipa" not in system_prompt
    assert "hola, santiago. estoy lista." not in system_prompt


def test_admin_natural_command_uses_minimal_outage_fallback_for_generic_chat():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def broken_brain(*args, **kwargs):
        return None

    melissa._admin_llm_brain = broken_brain
    module.owner_style_controller = None
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        save_message=lambda *args, **kwargs: None,
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "hola",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "se me cayó" in merged or "caida" in merged or "caída" in merged
    assert "estoy lista para ayudarte" not in merged
    assert "cuénteme qué quiere ajustar" not in merged


def test_admin_local_fallback_keeps_deterministic_chat_snapshot_route():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        _conn=lambda: None,
    )
    melissa._admin_recent_chat_snapshot = lambda chat_id, clinic: [
        "Veo 2 chats reales en esta instancia.",
        "Los más recientes son Laura y Camilo.",
    ]
    melissa._admin_has_recent_chat_snapshot_context = lambda chat_id: False

    reply = melissa._admin_local_fallback(
        "hay conversaciones?",
        "hay conversaciones?",
        {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        "Melissa",
        "6908159885",
    )

    merged = " ".join(reply).lower()
    assert "2 chats reales" in merged
    assert "laura" in merged


def test_admin_natural_command_keeps_reply_when_history_save_fails():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def fake_brain(*args, **kwargs):
        return {
            "reply": "Todo bien. Qué quieres revisar hoy?",
            "action": "none",
            "data": {},
        }

    async def fake_apply_action(*args, **kwargs):
        return True

    def failing_save(*args, **kwargs):
        raise sqlite3.OperationalError("database or disk is full")

    melissa._admin_llm_brain = fake_brain
    melissa._admin_apply_action = fake_apply_action
    module.owner_style_controller = None
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        save_message=failing_save,
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "hola buenos dias",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "todo bien" in merged
    assert "algo salió mal" not in merged


def test_admin_output_pipeline_strips_dangling_trailing_quote():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    module.owner_style_controller = None
    module.db = types.SimpleNamespace(get_history=lambda chat_id, limit=8: [])

    cleaned = melissa._apply_admin_output_pipeline(
        'Comprendo. Estoy atenta para cualquier configuración o prueba de los servicios que requiera."',
        "6908159885",
        {"name": "Clinica de las americas"},
        user_msg="estoy probando a ver si te sales de contexto",
    )

    assert not cleaned.endswith('"')
    assert "requiera" in cleaned


def test_patient_message_scope_routes_identity_question_to_meta():
    module = load_melissa_module()

    scope, effective = module._patient_message_scope(
        "eres bot o qué",
        {"name": "Clinica de las americas", "services": ["Botox"]},
    )

    assert scope == "meta"
    assert effective == "eres bot o qué"


def test_calendar_admin_notification_uses_direct_human_copy():
    module = load_melissa_module()
    bridge = module.CalendarBridge()
    sent = []

    async def fake_send(chat_id, message, *args, **kwargs):
        sent.append((chat_id, message))

    asyncio.run(
        bridge.notify_admin_availability_request(
            ["admin_1"],
            "Laura",
            "Hola buenas tardes",
            fake_send,
        )
    )

    assert sent
    _, message = sent[0]
    lowered = message.lower()
    assert "te paso una consulta de disponibilidad" in lowered
    assert "no tengo la agenda conectada" in lowered
    assert "hola!" not in lowered


def test_calendar_admin_notification_skips_probe_ids_when_real_admin_exists():
    module = load_melissa_module()
    bridge = module.CalendarBridge()
    sent = []

    async def fake_send(chat_id, message, *args, **kwargs):
        sent.append((chat_id, message))

    asyncio.run(
        bridge.notify_admin_availability_request(
            ["6908159885", "admin_probe_20260328_real", "admin_control_20260328"],
            "Laura",
            "Tienen algo para el jueves?",
            fake_send,
        )
    )

    assert [chat_id for chat_id, _ in sent] == ["6908159885"]


def test_patient_acknowledgement_closes_without_repeating_previous_price_handoff():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._pending_buffers = {}
    melissa._admin_pending = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    class FakeAnalyzer:
        def analyze(self, text, history):
            return types.SimpleNamespace(
                language="es",
                urgency=module.UrgencyLevel.LOW,
                intent=module.IntentType.GENERAL_QUESTION,
                requires_search=False,
                closing_score=0.0,
                lead_temperature="warm",
            )

    class FakeReasoning:
        async def reason(self, *args, **kwargs):
            return {}

    class FakeGenerator:
        def _get_default_personality(self, clinic):
            return types.SimpleNamespace(archetype="amigable")

        def _apply_output_pipeline(self, response, **kwargs):
            return response

        def _repair_fragmented_response(self, response, **kwargs):
            return response

        def get_last_response_metadata(self):
            return {}

        async def generate(self, *args, **kwargs):
            raise AssertionError("no debería llamar al generator para un agradecimiento simple")

    melissa.analyzer = FakeAnalyzer()
    melissa.reasoning = FakeReasoning()
    melissa.generator = FakeGenerator()
    module.db = types.SimpleNamespace(
        get_clinic=lambda: {
            "name": "Clinica de las americas",
            "sector": "estetica",
            "setup_done": 1,
            "admin_chat_ids": ["admin_1"],
            "pricing": {},
            "services": ["Botox"],
            "schedule": {"General": "Lunes a sábado de 9 a.m. a 7 p.m."},
        },
        get_admin=lambda chat_id: None,
        get_or_create_patient=lambda chat_id: {"is_new": False, "name": "Laura"},
        get_history=lambda chat_id, limit=None: [
            {"role": "assistant", "content": "No tengo un aproximado confiable aquí en este momento. ||| Si quieres, lo consulto con el equipo y te confirmo apenas me respondan."}
        ],
        get_conversation_state=lambda chat_id: types.SimpleNamespace(turn_count=1, last_intent=module.IntentType.PRICE_INQUIRY),
        save_message=lambda *args, **kwargs: None,
        save_conversation_state=lambda *args, **kwargs: None,
        record_metric=lambda *args, **kwargs: None,
    )

    bubbles = asyncio.run(melissa.process_message("7000001002", "ah vale gracias"))

    merged = " ".join(bubbles).lower()
    assert "consulto con el equipo" not in merged
    assert "aproximado confiable" not in merged
    assert "aquí estoy" in merged or "aqui estoy" in merged or "cuando quieras" in merged


def test_patient_hours_followup_answers_schedule_without_dragging_price():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._pending_buffers = {}
    melissa._admin_pending = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    class FakeAnalyzer:
        def analyze(self, text, history):
            return types.SimpleNamespace(
                language="es",
                urgency=module.UrgencyLevel.LOW,
                intent=module.IntentType.HOURS_INQUIRY,
                requires_search=False,
                closing_score=0.0,
                lead_temperature="warm",
            )

    class FakeReasoning:
        async def reason(self, *args, **kwargs):
            return {}

    class FakeGenerator:
        def _get_default_personality(self, clinic):
            return types.SimpleNamespace(archetype="amigable")

        def _apply_output_pipeline(self, response, **kwargs):
            return response

        def _repair_fragmented_response(self, response, **kwargs):
            return response

        def get_last_response_metadata(self):
            return {}

        async def generate(self, *args, **kwargs):
            raise AssertionError("no debería llamar al generator para un follow-up puro de horario")

    melissa.analyzer = FakeAnalyzer()
    melissa.reasoning = FakeReasoning()
    melissa.generator = FakeGenerator()
    module.db = types.SimpleNamespace(
        get_clinic=lambda: {
            "name": "Clinica de las americas",
            "sector": "estetica",
            "setup_done": 1,
            "admin_chat_ids": ["admin_1"],
            "pricing": {},
            "services": ["Botox"],
            "schedule": {"General": "Lunes a sábado de 9 a.m. a 7 p.m."},
        },
        get_admin=lambda chat_id: None,
        get_or_create_patient=lambda chat_id: {"is_new": False, "name": "Laura"},
        get_history=lambda chat_id, limit=None: [
            {"role": "user", "content": "precio rápido porfavor"},
            {"role": "assistant", "content": "No tengo un aproximado confiable aquí en este momento. ||| Si quieres, lo consulto con el equipo y te confirmo apenas me respondan."},
        ],
        get_conversation_state=lambda chat_id: types.SimpleNamespace(turn_count=1, last_intent=module.IntentType.PRICE_INQUIRY),
        save_message=lambda *args, **kwargs: None,
        save_conversation_state=lambda *args, **kwargs: None,
        record_metric=lambda *args, **kwargs: None,
    )

    bubbles = asyncio.run(melissa.process_message("7000001003", "y horarios"))

    merged = " ".join(bubbles).lower()
    assert "lunes a sábado" in merged or "lunes a sabado" in merged
    assert "precio" not in merged
    assert "consulto con el equipo" not in merged


def test_calendar_bridge_ignores_casual_a_esta_hora_phrase():
    module = load_melissa_module()
    bridge = module.CalendarBridge()

    assert bridge.needs_calendar("hola, vi botox pero me da pena preguntar a esta hora jaja") is False
    assert bridge.needs_calendar("quiero una cita esta semana en la tarde, tienen espacio?") is True


def test_admin_availability_feedback_is_rewritten_before_sending_to_patient():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._availability_pending_patient = "patient_1"
    melissa._last_reviewed_chat = None
    melissa._pending_buffers = {}
    melissa._admin_pending = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    sent = []

    async def fake_send(chat_id, message, *args, **kwargs):
        sent.append((chat_id, message))

    async def fake_compose(patient_chat_id, admin_text, clinic):
        return "Ya me confirmaron que el jueves de 3 a 5 pm hay disponibilidad. Si te sirve, te lo dejo agendado."

    melissa._send_message = fake_send
    melissa._compose_patient_availability_reply = fake_compose
    module.db = types.SimpleNamespace()

    reply = asyncio.run(
        melissa._process_admin_feedback(
            "6908159885",
            "dile que entre el jueves de 3 a 5 pm hay disponibilidad que si le gustaria agendar a esa hora",
            {"name": "Clinica de las americas"},
        )
    )

    assert sent == [
        (
            "patient_1",
            "Ya me confirmaron que el jueves de 3 a 5 pm hay disponibilidad. Si te sirve, te lo dejo agendado.",
        )
    ]
    assert melissa._availability_pending_patient is None
    assert reply and "listo" in " ".join(reply).lower()


def test_pending_availability_context_uses_human_internal_instruction():
    module = load_melissa_module()

    context = module.build_pending_availability_context()
    lowered = context.lower()

    assert "agenda del dueño" not in lowered
    assert "déjame" in lowered or "dejame" in lowered
    assert "dueño" not in lowered
    assert "respuesta corta" in lowered


def test_live_admin_chat_ids_skip_probe_and_control_variants_when_real_admin_exists():
    module = load_melissa_module()

    ids = module.live_admin_chat_ids(
        ["6908159885", "admin_probe_20260328_real", "admin_control_20260328"]
    )
    assert ids == ["6908159885"]

    ids_without_real = module.live_admin_chat_ids(["admin_1"])
    assert ids_without_real == ["admin_1"]


def test_admin_natural_command_recovers_truncated_llm_json_instead_of_generic_fallback():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._admin_pending = {}
    melissa._pending_buffers = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}

    async def fake_complete(*args, **kwargs):
        return (
            '{"reply":"No, para nada. Si algo te suena raro me lo pegas y lo rehago",'
            '"action":"none","data":{',
            {},
        )

    module.llm_engine = types.SimpleNamespace(complete=fake_complete)
    module.owner_style_controller = None
    module.trainer_gateway = None
    module.prompt_evolver = None
    module.anti_robot_filter = None
    module.db = types.SimpleNamespace(
        get_admin=lambda chat_id: {"name": "Santiago"},
        get_history=lambda chat_id, limit=8: [],
        save_message=lambda *args, **kwargs: None,
    )

    reply = asyncio.run(
        melissa._admin_natural_command(
            "6908159885",
            "si te digo algo raro te ofendes o no?",
            {"name": "Clinica de las americas", "admin_chat_ids": ["6908159885"]},
        )
    )

    merged = " ".join(reply).lower()
    assert "no, para nada" in merged
    assert "cuénteme qué quiere ajustar" not in merged


def test_synthetic_chat_id_filters_probe_and_test_variants():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)

    assert melissa._is_synthetic_chat_id("provider_probe_fast_20260329") is True
    assert melissa._is_synthetic_chat_id("pipeline_probe_bot") is True
    assert melissa._is_synthetic_chat_id("stage2_probe_direct_01") is True
    assert melissa._is_synthetic_chat_id("p1_skeptica_v5") is True
    assert melissa._is_synthetic_chat_id("6908159885") is False


def test_repair_fragmented_response_does_not_replace_price_answers_with_template():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }
    personality = generator._get_default_personality(clinic)

    repaired = generator._repair_fragmented_response(
        response="No tengo el precio exacto cargado ahora, porque cambia según la zona que te valoren",
        clinic=clinic,
        user_msg="Me interesa el botox, que vale",
        personality=personality,
        history=[],
    )

    assert "El valor depende de la valoración y de las zonas a trabajar" not in repaired
    assert "No tengo el precio exacto cargado ahora" in repaired


def test_repair_fragmented_response_preserves_follow_up_instead_of_service_menu():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }

    repaired = generator._repair_fragmented_response(
        response="En esas zonas primero toca revisar si sí te conviene o si hay otra opción",
        clinic=clinic,
        user_msg="Es la cara y la barriga",
        personality=None,
        history=[{"role": "assistant", "content": "Cuéntame un poco más"}],
    )

    assert "Si quiere, le ubico información o disponibilidad" not in repaired
    assert "En esas zonas primero toca revisar" in repaired


def test_repair_fragmented_response_keeps_short_tail_visible_for_retry():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)

    repaired = generator._repair_fragmented_response(
        response="No, para nada. Soy Melissa del equipo de la clínica\n\nCu",
        clinic={"name": "Clinica de las americas"},
        user_msg="Eres un bot?",
        personality=None,
        history=[{"role": "assistant", "content": "Hola"}],
    )

    assert repaired.endswith("Cu")
    assert not repaired.endswith("Cu.")


def test_retry_until_human_keeps_model_output_when_only_soft_conflicts_exist():
    module = load_melissa_module()

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def complete(self, *args, **kwargs):
            self.calls += 1
            return "hola. Soy Melissa, del equipo de Clinica", {"model": "fake"}

    fake_llm = FakeLLM()
    generator = module.ResponseGenerator(llm=fake_llm)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})
    original = "hola, buenas tardes. Cuéntame qué te gustaría mejorar o qué te trae por acá."

    result = asyncio.run(
        generator._retry_until_human(
            messages=[{"role": "system", "content": "stub"}],
            response=original,
            model_tier="fast",
            personality=personality,
            chat_id="soft_conflict_probe",
            clinic={"name": "Clinica de las americas"},
            user_msg="Hola buenas tardes",
            history=[],
        )
    )

    assert result == original
    assert fake_llm.calls == 0


def test_v8_process_response_preserves_multi_paragraph_patient_reply():
    module = load_melissa_module()
    module.init_v8_systems()

    response = (
        "¡Hola! Para nada, soy Melissa del equipo de la Clínica de las Américas.\n\n"
        "Cuéntame, ¿qué tenías en mente hoy? ¿Hay algún tratamiento que te llame la atención "
        "o alguna zona que quieras revisar?"
    )

    processed = module.v8_process_response(response, chat_id="v8_guard_probe", archetype="amigable")

    assert "Melissa del equipo de la Clínica de las Américas" in processed
    assert "alguna zona que quieras revisar" in processed


def test_postprocess_preserves_later_paragraphs_in_long_patient_reply():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    response = (
        "Ay no, para nada! Soy Melissa, una persona de verdad aquí en la clínica.\n\n"
        "Mira, el bótox es excelente para las líneas de expresión en la cara, "
        "pero para la barriga no es el tratamiento indicado. ¿Qué te gustaría mejorar en esa zona? "
        "Tal vez tenemos otra cosa que te sirva súper bien.\n\n"
        "Y sobre el precio del bótox para la cara, la cosa es que depende mucho de cuántas zonas necesites tratar, "
        "porque no es lo mismo solo la frente que frente, entrecejo y patitas de gallo. "
        "Lo mejor es que la doctora te vea en una valoración gratuita para que te diga exactamente qué necesitas y cuánto costaría."
    )

    processed = generator._postprocess(response, personality)

    assert "la barriga no es el tratamiento indicado" in processed
    assert "valoración gratuita" in processed


def test_postprocess_does_not_break_mid_sentence_help_question():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    processed = generator._postprocess(
        "No, soy Melissa del equipo de la clínica. ||| Cuéntame, ¿qué te gustaría revisar o en qué te puedo ayudar?",
        personality,
    )

    assert "qué te gustaría revisar o en qué te puedo ayudar" in processed
    assert "o?" not in processed


def test_compact_prompt_does_not_claim_human_identity_or_inject_fewshots():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }
    personality = generator._get_default_personality(clinic)

    prompt = generator._build_compact_system_prompt(
        clinic=clinic,
        patient={"is_new": True, "visits": 0},
        personality=personality,
        search_context="",
        reasoning={"response_strategy": "responder precio primero"},
        kb_context="",
        context_summary="",
        pre_prompt_injection="",
        chat_id="identity_probe",
        history=[],
    ).lower()

    assert "como parte del equipo" in prompt
    assert "no ocultes que eres bot si te lo preguntan" in prompt
    assert "bot conversacional del equipo" not in prompt
    assert "asesora humana" not in prompt
    assert "así suenas" not in prompt


def test_compact_prompt_keeps_bot_disclosure_abstract_not_literal():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }
    personality = generator._get_default_personality(clinic)

    prompt = generator._build_compact_system_prompt(
        clinic=clinic,
        patient={"is_new": True, "visits": 0},
        personality=personality,
        search_context="",
        reasoning={"response_strategy": "responder identidad"},
        kb_context="",
        context_summary="",
        pre_prompt_injection="",
        chat_id="identity_instruction_probe",
        history=[],
    ).lower()

    assert "si te preguntan si eres bot, responde eso con honestidad en una sola línea" in prompt
    assert "di 'sí, soy melissa'" not in prompt
    assert 'di "sí, soy melissa"' not in prompt


def test_compact_prompt_does_not_force_first_turn_self_intro():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }
    personality = generator._get_default_personality(clinic)

    prompt = generator._build_compact_system_prompt(
        clinic=clinic,
        patient={"is_new": True, "visits": 0},
        personality=personality,
        search_context="",
        reasoning={"response_strategy": "responder precio primero"},
        kb_context="",
        context_summary="",
        pre_prompt_injection="",
        chat_id="first_turn_prompt_probe",
        history=[],
    ).lower()

    assert "no te presentes salvo que haga falta" in prompt
    assert "responde como melissa del equipo" not in prompt


def test_compact_prompt_forces_last_user_message_priority():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }
    personality = generator._get_default_personality(clinic)

    prompt = generator._build_compact_system_prompt(
        clinic=clinic,
        patient={"is_new": True, "visits": 0},
        personality=personality,
        search_context="",
        reasoning={"response_strategy": "responder precio primero"},
        kb_context="",
        context_summary="",
        pre_prompt_injection="",
        chat_id="prompt_probe",
        history=[
            {"role": "user", "content": "Eres un bot?"},
            {"role": "assistant", "content": "No, soy Melissa del equipo de la clínica"},
        ],
    ).lower()

    assert "prioriza el último mensaje" in prompt
    assert "no sigas respondiendo la pregunta anterior" in prompt


def test_compact_prompt_skips_behavior_playbooks_for_patient():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    clinic = {
        "name": "Clinica de las americas",
        "sector": "estetica",
        "services": ["Botox", "Rellenos", "Láser"],
    }
    personality = generator._get_default_personality(clinic)

    module.db = types.SimpleNamespace(
        get_core_memory_block=lambda: "",
        get_trust_rules=lambda limit=12: [],
        get_behavior_playbooks=lambda limit=3: [
            {
                "trigger_text": "si te saludan",
                "response_example": "hola ||| dime",
            }
        ],
    )
    module.owner_style_controller = None

    prompt = generator._build_compact_system_prompt(
        clinic=clinic,
        patient={"is_new": True, "visits": 0},
        personality=personality,
        search_context="",
        reasoning={"response_strategy": "responder precio primero"},
        kb_context="",
        context_summary="",
        pre_prompt_injection="",
        chat_id="playbook_probe",
        history=[],
    ).lower()

    assert "playbooks del dueño" not in prompt
    assert "si te saludan" not in prompt


def test_unanswered_price_request_requires_real_price_signal_not_only_valoracion():
    module = load_melissa_module()

    assert module.detect_unanswered_price_request(
        "Tu sabes de casualidad el precio?",
        "En la clínica primero te hacen una valoración para diseñarte un plan a tu medida.",
    ) is True

    assert module.detect_unanswered_price_request(
        "Tu sabes de casualidad el precio?",
        "El valor depende de las zonas que quieran trabajar y eso se define en valoración.",
    ) is False

    assert module.detect_unanswered_price_request(
        "Tu sabes de casualidad el precio?",
        "Ay, mira, el bótox es muy bueno para la cara y sí lo trabajamos, pero el precio exacto",
    ) is True

    assert module.detect_unanswered_price_request(
        "Pero un aproximado cuánto podría ser?",
        "No tengo un aproximado confiable aquí ahora mismo, pero si quieres lo consulto con el equipo y te confirmo.",
    ) is False


def test_generate_without_pricing_offers_to_consult_team_instead_of_repeating_valoracion():
    module = load_melissa_module()

    class FakeLLM:
        async def complete(self, *args, **kwargs):
            return (
                "No tengo un precio exacto para el bótox en este momento ||| "
                "El valor final depende de una valoración inicial y de las zonas específicas a tratar",
                {"model": "fake"},
            )

    generator = module.ResponseGenerator(llm=FakeLLM())
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    response = asyncio.run(
        generator.generate(
            message="Pero un aproximado cuánto podría ser?",
            analysis=types.SimpleNamespace(intent=module.IntentType.GENERAL_QUESTION),
            reasoning={"confidence": 1.0, "response_strategy": "responder precio con honestidad"},
            clinic={"name": "Clinica de las americas", "sector": "estetica", "pricing": {}},
            patient={"is_new": False, "visits": 1},
            history=[
                {"role": "user", "content": "Hola buenas noches, se que son las 3 am pero a qué precio tienen el botox"},
                {"role": "assistant", "content": "No tengo un precio exacto para el bótox en este momento"},
            ],
            search_context="",
            personality=personality,
            kb_context="",
            chat_id="price_team_consult_probe",
        )
    )

    lowered = response.lower()
    assert "no tengo un aproximado" in lowered
    assert "consult" in lowered and "equipo" in lowered
    assert "depende de la valoración" not in lowered


def test_missing_price_handoff_detection_catches_varia_without_consult_offer():
    module = load_melissa_module()

    assert module.detect_missing_price_handoff_needed(
        "Hola buenas noches, se que son las 3 am pero a qué precio tienen el botox",
        "El precio del Botox varía según el tratamiento que necesites.",
        {"name": "Clinica de las americas", "pricing": {}},
    ) is True


def test_hallucination_guard_safe_price_reply_offers_team_consult_when_no_pricing():
    module = load_melissa_module()
    guard = module.HallucinationGuard()

    has_hallucination, kind, safe = guard.check(
        "El bótox te puede salir en $350.000",
        {"name": "Clinica de las americas", "pricing": {}},
        "",
    )

    lowered = safe.lower()
    assert has_hallucination is True
    assert kind == "PRICE_INVENTED"
    assert "consult" in lowered and "equipo" in lowered
    assert not any(ch.isdigit() for ch in safe)


def test_process_message_notifies_admin_when_team_consult_is_promised():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._pending_buffers = {}
    melissa._admin_pending = {}
    melissa._last_reviewed_chat = None
    melissa._availability_pending_patient = None
    melissa._demo_sessions = {}
    melissa._emoji_chats = set()
    melissa._chat_routes = {}
    melissa._orchestrator = None
    melissa.search = types.SimpleNamespace(detect_procedure=lambda text: None)
    module.auth_engine = None
    module.trainer_gateway = None
    module.nova_rule_sync = None
    module.kb = None
    module.calendar_bridge = None
    module.task_manager = None
    module.owner_style_controller = None
    module.anti_robot_filter = None
    module.response_variation = None
    module.hallucination_guard = None
    module.notify_omni = lambda *args, **kwargs: None

    class FakeAnalyzer:
        def analyze(self, text, history):
            return types.SimpleNamespace(
                intent=module.IntentType.GENERAL_QUESTION,
                urgency=module.UrgencyLevel.NONE,
                language="es",
                requires_search=False,
                closing_score=0.0,
                lead_temperature="cold",
            )

    class FakeReasoning:
        async def reason(self, *args, **kwargs):
            return {"confidence": 1.0, "response_strategy": "responder con handoff al equipo"}

    class FakeGenerator:
        def _get_default_personality(self, clinic):
            return types.SimpleNamespace(archetype="amigable")

        def _should_use_seeded_first_turn(self, text, history):
            return False

        async def generate(self, *args, **kwargs):
            return (
                "No tengo un aproximado confiable aquí en este momento. ||| "
                "Si quieres, lo consulto con el equipo y te confirmo apenas me respondan."
            )

        def get_last_response_metadata(self):
            return {}

        def _repair_fragmented_response(self, response, **kwargs):
            return response

        def _normalize_first_patient_turn(self, response, **kwargs):
            return response

    sent = []

    async def fake_send_message(chat_id, message, *args, **kwargs):
        sent.append((chat_id, message))

    melissa.analyzer = FakeAnalyzer()
    melissa.reasoning = FakeReasoning()
    melissa.generator = FakeGenerator()
    melissa._send_message = fake_send_message
    module.db = types.SimpleNamespace(
        get_clinic=lambda: {
            "name": "Clinica de las americas",
            "sector": "estetica",
            "setup_done": 1,
            "admin_chat_ids": ["admin_1"],
            "pricing": {},
            "services": ["Botox"],
        },
        get_admin=lambda chat_id: None,
        get_or_create_patient=lambda chat_id: {"is_new": True, "name": "Laura"},
        get_history=lambda chat_id, limit=None: [],
        get_conversation_state=lambda chat_id: types.SimpleNamespace(turn_count=0, last_intent=None),
        save_message=lambda *args, **kwargs: None,
        save_conversation_state=lambda *args, **kwargs: None,
        record_metric=lambda *args, **kwargs: None,
    )

    bubbles = asyncio.run(
        melissa.process_message(
            "7000001001",
            "Hola buenas noches, se que son las 3 am pero a qué precio tienen el botox",
        )
    )

    assert any("consulto con el equipo" in bubble.lower() for bubble in bubbles)
    assert sent
    admin_chat_id, admin_message = sent[0]
    assert admin_chat_id == "admin_1"
    assert "laura" in admin_message.lower()
    assert "botox" in admin_message.lower()


def test_send_message_retries_plain_text_when_telegram_markdown_fails():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)
    melissa._emoji_chats = set()
    melissa._strip_emojis = lambda text: text
    melissa._resolve_route = lambda chat_id, route: {"platform": "telegram"}

    calls = []

    class FakeResponse:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            calls.append(json)
            if len(calls) == 1:
                return FakeResponse(400, "Bad Request: can't parse entities")
            return FakeResponse(200, "ok")

    original_client = module.httpx.AsyncClient
    module.httpx.AsyncClient = lambda timeout=15.0: FakeClient()
    try:
        asyncio.run(
            melissa._send_message(
                "6908159885",
                "Melissa quedó pendiente por chat e_v2",
            )
        )
    finally:
        module.httpx.AsyncClient = original_client

    assert len(calls) == 2
    assert calls[0]["parse_mode"] == "Markdown"
    assert "parse_mode" not in calls[1]


def test_retry_until_human_rewrites_incomplete_appointment_reply():
    module = load_melissa_module()

    class FakeLLM:
        async def complete(self, *args, **kwargs):
            return (
                "Te la puedo dejar encaminada. Te sirve cualquier hora de la tarde o prefieres una hora puntual?",
                {"model": "fake"},
            )

    generator = module.ResponseGenerator(llm=FakeLLM())
    personality = generator._get_default_personality(
        {"name": "Clinica de las americas", "sector": "estetica"}
    )

    rewritten = asyncio.run(
        generator._retry_until_human(
            messages=[{"role": "user", "content": "quiero cita el miércoles en la tarde"}],
            response="Para agendar tu cita el miércoles en la tarde.",
            model_tier="fast",
            personality=personality,
            chat_id="appointment_retry_probe",
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            user_msg="quiero cita el miércoles en la tarde",
            history=[],
        )
    )

    lowered = rewritten.lower()
    assert "prefieres una hora puntual" in lowered or "te sirve cualquier hora de la tarde" in lowered


def test_fragment_detector_catches_dangling_price_follow_ups():
    module = load_melissa_module()

    assert module.looks_fragmented_reply(
        "El valor cambia según las zonas que quieras tratar ||| Si me dices qué parte"
    ) is True

    assert module.looks_fragmented_reply(
        "Para la barriga no se maneja botox, pero para la."
    ) is True

    assert module.looks_fragmented_reply(
        "Ay, mira, el bótox es muy bueno para la cara y sí lo trabajamos, pero el precio exacto"
    ) is True

    assert module.looks_fragmented_reply(
        "El valor del bótox cambia según."
    ) is True


def test_simple_botox_interest_does_not_trigger_medical_search():
    module = load_melissa_module()
    melissa = module.MelissaUltra.__new__(module.MelissaUltra)

    low_signal = types.SimpleNamespace(
        intent=module.IntentType.SERVICE_INFO,
        requires_search=True,
    )
    high_signal = types.SimpleNamespace(
        intent=module.IntentType.SERVICE_INFO,
        requires_search=True,
    )

    assert (
        melissa._should_run_medical_search(
            "hola, vi botox pero me da pena preguntar a esta hora jaja",
            low_signal,
        )
        is False
    )
    assert (
        melissa._should_run_medical_search(
            "quiero saber cuánto dura el botox, qué efectos tiene y si deja la cara tiesa",
            high_signal,
        )
        is True
    )


def test_detect_invented_objection_when_patient_never_mentioned_fear():
    module = load_melissa_module()

    assert module.detect_invented_objection(
        "Es la cara y la barriga",
        "Te preocupa quedar con un aspecto exagerado. Eso es muy común antes del bótox.",
        history=[
            {"role": "user", "content": "Me interesa el botox, que vale"},
            {"role": "assistant", "content": "El valor cambia según las zonas"},
        ],
    ) == "objecion_estetica_no_mencionada"

    assert module.detect_invented_objection(
        "Me da miedo quedar exagerada",
        "Te preocupa quedar con un aspecto exagerado. Eso es muy común antes del bótox.",
        history=[],
    ) == ""


def test_detect_topic_regression_when_bot_topic_is_reopened_after_price_question():
    module = load_melissa_module()

    assert module.detect_topic_regression(
        "Me interesa el botox, que vale",
        "Soy Melissa, del equipo de la clínica, para nada soy un bot. El valor cambia según la zona.",
        history=[
            {"role": "user", "content": "Eres un bot?"},
            {"role": "assistant", "content": "No, soy Melissa del equipo de la clínica"},
        ],
    ) == "tema_bot_reabierto"

    assert module.detect_topic_regression(
        "Me interesa el botox, que vale",
        "El valor cambia según las zonas que quieran trabajar.",
        history=[
            {"role": "user", "content": "Eres un bot?"},
            {"role": "assistant", "content": "No, soy Melissa del equipo de la clínica"},
        ],
    ) == ""


def test_drop_out_of_context_bubbles_keeps_useful_reply_content():
    module = load_melissa_module()

    assert module._drop_out_of_context_bubbles(
        'Soy Melissa, del equipo de la clínica. ||| El valor del bótox varía según las zonas que quieras tratar.',
        drop_topic_regression=True,
    ) == 'El valor del bótox varía según las zonas que quieras tratar.'

    assert module._drop_out_of_context_bubbles(
        'Te preocupa quedar exagerada. ||| Para la barriga no se trabaja con bótox.',
        drop_invented_objection=True,
    ) == 'Para la barriga no se trabaja con bótox.'


def test_detect_ignored_user_zones_when_response_does_not_answer_them():
    module = load_melissa_module()

    assert module.detect_ignored_user_zones(
        "Es la cara y la barriga",
        "Buscamos resultados muy naturales para que no se vea exagerado.",
    ) == ["cara", "barriga"]

    assert module.detect_ignored_user_zones(
        "Es la cara y la barriga",
        "Para la cara sí se maneja bótox, pero para la barriga no se usa.",
    ) == []


def test_apply_output_pipeline_drops_out_of_context_patient_bubbles():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    rewritten = generator._apply_output_pipeline(
        response='Soy Melissa del equipo de la clínica. ||| El valor del bótox depende de las zonas que quieras tratar.',
        personality=personality,
        chat_id='pipeline_probe_bot',
        clinic={"name": "Clinica de las americas", "sector": "estetica"},
        user_msg='Me interesa el botox, que vale',
        history=[
            {"role": "user", "content": "Eres un bot?"},
            {"role": "assistant", "content": "No, soy Melissa del equipo de la clínica"},
        ],
        is_admin=False,
    )

    assert "soy melissa" not in rewritten.lower()
    assert "depende de las zonas" in rewritten.lower()

    rewritten = generator._apply_output_pipeline(
        response='Te preocupa quedar exagerada. ||| Para la barriga no se trabaja con bótox.',
        personality=personality,
        chat_id='pipeline_probe_obj',
        clinic={"name": "Clinica de las americas", "sector": "estetica"},
        user_msg='Es la cara y la barriga',
        history=[
            {"role": "user", "content": "Me interesa el botox, que vale"},
            {"role": "assistant", "content": "El valor cambia según las zonas"},
        ],
        is_admin=False,
    )

    assert "quedar exagerada" not in rewritten.lower()
    assert "barriga no se trabaja" in rewritten.lower()


def test_identity_question_helpers_detect_robotic_help_pitch():
    module = load_melissa_module()

    assert module._is_identity_question("Eres un bot?") is True
    assert module._has_generic_help_pitch("Sí, soy Melissa. Cómo le puedo ayudar hoy?") is True
    assert module._has_generic_help_pitch("Sí, soy Melissa del equipo.") is False


def test_generate_applies_price_guardrail_when_model_still_does_not_answer_price():
    module = load_melissa_module()

    class FakeLLM:
        async def complete(self, *args, **kwargs):
            return "Soy Melissa, del equipo de la clínica", {"model": "fake"}

    generator = module.ResponseGenerator(llm=FakeLLM())
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    response = asyncio.run(
        generator.generate(
            message="Me interesa el botox, que vale",
            analysis=types.SimpleNamespace(intent=module.IntentType.PRICE_INQUIRY),
            reasoning={"confidence": 1.0, "response_strategy": "responder precio primero"},
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            patient={"is_new": True, "visits": 0},
            history=[
                {"role": "user", "content": "Eres un bot?"},
                {"role": "assistant", "content": "No, soy Melissa del equipo de la clínica"},
            ],
            search_context="",
            personality=personality,
            kb_context="",
            chat_id="price_guardrail_probe",
        )
    )

    assert "depende de las zonas" in response.lower()
    assert "si me dices qué parte te interesa" in response.lower()


def test_retry_until_human_reworks_identity_answer_with_help_pitch():
    module = load_melissa_module()

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def complete(self, *args, **kwargs):
            self.calls += 1
            return "Sí, soy Melissa, la asistente virtual de la clínica. ||| Dime qué tratamiento estás mirando.", {"model": "fake"}

    fake_llm = FakeLLM()
    generator = module.ResponseGenerator(llm=fake_llm)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    rewritten = asyncio.run(
        generator._retry_until_human(
            messages=[{"role": "system", "content": "stub"}],
            response="Sí, soy Melissa, la asistente virtual de la clínica ||| Cómo le puedo ayudar hoy?",
            model_tier="fast",
            personality=personality,
            chat_id="identity_pitch_probe",
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            user_msg="Eres un bot?",
            history=[{"role": "user", "content": "Hola buenas tardes"}],
        )
    )

    assert fake_llm.calls == 1
    assert "cómo le puedo ayudar hoy" not in rewritten.lower()
    assert "dime qué tratamiento estás mirando" in rewritten.lower()


def test_retry_until_human_keeps_fast_tier_on_price_like_rewrites():
    module = load_melissa_module()

    class FakeLLM:
        def __init__(self):
            self.tiers = []

        async def complete(self, *args, **kwargs):
            self.tiers.append(kwargs.get("model_tier"))
            return "hola, en qué te ayudo", {"model": "fake"}

    fake_llm = FakeLLM()
    generator = module.ResponseGenerator(llm=fake_llm)
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    asyncio.run(
        generator._retry_until_human(
            messages=[{"role": "system", "content": "stub"}],
            response="hola, en qué te ayudo",
            model_tier="fast",
            personality=personality,
            chat_id="price_retry_probe",
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            user_msg="o sea que no me pueden dar el precio",
            history=[{"role": "assistant", "content": "No tengo ese dato exacto"}],
        )
    )

    assert fake_llm.tiers == ["fast", "fast"]


def test_generate_applies_zone_guardrail_when_zone_reply_stays_fragmented():
    module = load_melissa_module()

    class FakeLLM:
        async def complete(self, *args, **kwargs):
            return "Para la cara sí manejamos el Botox. Para", {"model": "fake"}

    generator = module.ResponseGenerator(llm=FakeLLM())
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    response = asyncio.run(
        generator.generate(
            message="Es la cara y la barriga",
            analysis=types.SimpleNamespace(intent=module.IntentType.GENERAL_QUESTION),
            reasoning={"confidence": 1.0, "response_strategy": "responder por zonas"},
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            patient={"is_new": True, "visits": 0},
            history=[
                {"role": "user", "content": "Me interesa el botox, que vale"},
                {"role": "assistant", "content": "El valor depende de las zonas"},
            ],
            search_context="",
            personality=personality,
            kb_context="",
            chat_id="zone_guardrail_probe",
        )
    )

    assert "para la cara sí se maneja bótox" in response.lower()
    assert "para la barriga no se usa bótox" in response.lower()


def test_generate_applies_identity_guardrail_when_identity_reply_is_cut_or_corporate():
    module = load_melissa_module()

    class FakeLLM:
        async def complete(self, *args, **kwargs):
            return "Sí, soy Melissa, la asistente virtual de la ||| Cómo le puedo ayudar hoy?", {"model": "fake"}

    generator = module.ResponseGenerator(llm=FakeLLM())
    personality = generator._get_default_personality({"name": "Clinica de las americas"})

    response = asyncio.run(
        generator.generate(
            message="Eres un bot?",
            analysis=types.SimpleNamespace(intent=module.IntentType.GENERAL_QUESTION),
            reasoning={"confidence": 1.0, "response_strategy": "responder identidad con honestidad"},
            clinic={"name": "Clinica de las americas", "sector": "estetica"},
            patient={"is_new": True, "visits": 0},
            history=[{"role": "user", "content": "Hola buenas tardes"}],
            search_context="",
            personality=personality,
            kb_context="",
            chat_id="identity_guardrail_probe",
        )
    )

    assert response.lower() == "sí, soy melissa, el bot de la clínica."


def test_retry_owner_injection_ignores_admin_rules_for_patient_chat():
    module = load_melissa_module()
    generator = module.ResponseGenerator(llm=None)

    module.db = types.SimpleNamespace(
        get_trust_rules=lambda limit=8: [
            {"rule": "a los administradores háblales con respeto y más ejecutivo"},
            {"rule": "Si preguntan precio, responde eso primero"},
        ]
    )
    module.owner_style_controller = types.SimpleNamespace(
        _merged_bucket=lambda scope: {
            "forbidden_phrases": ["claro que sí"] if scope == "patient" else ["no hables así"],
            "forbidden_starts": [],
        }
    )

    conflicts, retry_block = generator._build_owner_rule_retry_injection(
        "claro que sí, depende de la zona",
        is_admin=False,
    )

    assert "claro que sí" in " ".join(conflicts).lower()
    assert "administradores" not in retry_block.lower()
    assert "ejecutivo" not in retry_block.lower()
    assert "no hables así" not in retry_block.lower()


def test_owner_style_patient_addon_stays_soft_and_bot_honest():
    module = load_melissa_module()
    controller = module.OwnerStyleController()
    controller._state = {
        "enabled": True,
        "global": controller._blank_bucket(),
        "admin": controller._seed_admin_defaults(controller._blank_bucket(register="usted")),
        "patient": controller._seed_patient_defaults(controller._blank_bucket(register="tu")),
    }
    controller._loaded = True

    addon = controller.build_prompt_addon(is_admin=False).lower()

    assert "preferencias vivas del negocio" in addon
    assert "control duro del admin" not in addon
