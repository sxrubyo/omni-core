from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .architecture import WorkflowArchitecture, discover_architecture
from .backends import (
    BackendError,
    BackendResult,
    generate_response,
    generate_vision_response,
    transcribe_audio,
)
from .config import AgentConfig, RuntimeState, append_session_message
from .layout import ensure_runtime_layout, resolve_state_paths
from .router import RouteResult, route_message


BOGOTA = ZoneInfo("America/Bogota")


@dataclass
class AgentReply:
    text: str
    route: RouteResult
    backend: str


def load_persona_fragments(persona_root: str, workspace_dir: Path | None = None) -> dict[str, str]:
    root = Path(persona_root)
    fragments = {}
    for name in ("SOUL.md", "CLAUDE.md", "ECO_NOVA_SPEC.md"):
        path = root / name
        if path.exists():
            fragments[name] = path.read_text(encoding="utf-8")
    if workspace_dir:
        for name in ("SOUL.md", "IDENTITY.md", "USER.md", "TOOLS.md", "AGENTS.md"):
            path = workspace_dir / name
            if path.exists():
                fragments[f"workspace:{name}"] = path.read_text(encoding="utf-8")
    return fragments


def _compact_lines(raw: str, limit: int) -> str:
    cleaned = " ".join(raw.split())
    return cleaned[:limit]


def _build_system_prompt(
    architecture: WorkflowArchitecture,
    route: RouteResult,
    persona_fragments: dict[str, str],
) -> str:
    cluster = architecture.clusters.get(route.cluster_id)
    laws = _compact_lines(
        persona_fragments.get(
            "SOUL.md",
            "Eco Nova. Responde en espanol. No anuncies pasos intermedios. No menciones herramientas internas. Actua con sobriedad.",
        ),
        1200,
    )
    cluster_excerpt = cluster.prompt_excerpt if cluster else ""
    subagents = ", ".join(route.selected_subagents) if route.selected_subagents else "Sin subagentes detectados"
    workspace_identity = _compact_lines(persona_fragments.get("workspace:IDENTITY.md", ""), 400)
    workspace_user = _compact_lines(persona_fragments.get("workspace:USER.md", ""), 400)
    workspace_tools = _compact_lines(persona_fragments.get("workspace:TOOLS.md", ""), 500)
    return (
        "Eres Eco Nova, un mega agente autonomo personal inspirado en el patron de gateway local de OpenClaw.\n"
        "Debes responder siempre en espanol y absorber cualquier complejidad interna en una voz unica.\n"
        "No menciones Workflows-n8n, OpenClaw, Claude Flow, backends, nombres de herramientas ni rutas internas.\n"
        "No entregues JSON ni listas tecnicas salvo que el usuario lo pida.\n"
        "Si una accion real no esta conectada todavia, dilo en una frase sobria y ofrece el siguiente paso concreto.\n"
        "Tu arquitectura heredada es: Entrada -> Orquestador -> Cluster -> Output Engine.\n"
        f"Orquestador principal heredado: {architecture.main_orchestrator or 'No detectado'}.\n"
        f"Output engine heredado: {architecture.output_engine or 'No detectado'}.\n"
        f"Cluster operativo actual: {route.cluster_id.upper()}.\n"
        f"Subagentes sugeridos por la arquitectura real: {subagents}.\n"
        f"Identidad operativa: {workspace_identity}\n"
        f"Contexto del usuario: {workspace_user}\n"
        f"Herramientas y notas locales: {workspace_tools}\n"
        f"Doctrina Eco Nova resumida: {laws}\n"
        f"Doctrina del cluster heredado: {_compact_lines(cluster_excerpt, 1600)}"
    )


def _build_user_prompt(
    architecture: WorkflowArchitecture,
    state: RuntimeState,
    session_id: str,
    route: RouteResult,
    channel: str,
    user_text: str,
) -> str:
    now = datetime.now(BOGOTA).strftime("%Y-%m-%d %H:%M:%S %Z")
    history = state.sessions.get(session_id, [])
    rendered_history = []
    for message in history[-8:]:
        rendered_history.append(f"{message['role'].upper()}: {message['content']}")
    history_block = "\n".join(rendered_history) if rendered_history else "Sin historial previo."
    ext_workflows = ", ".join(architecture.ext_workflows[:5]) if architecture.ext_workflows else "Sin extras"
    return (
        f"Fecha actual: {now}\n"
        f"Canal: {channel}\n"
        f"Sesion: {session_id}\n"
        f"Ruta elegida: {route.cluster_id.upper()} (confianza {route.confidence:.2f})\n"
        f"Keywords detectadas: {', '.join(route.matched_keywords) if route.matched_keywords else 'ninguna'}\n"
        f"Workflows E.X.T disponibles: {ext_workflows}\n\n"
        "Historial reciente:\n"
        f"{history_block}\n\n"
        "Mensaje actual del usuario:\n"
        f"{user_text}"
    )


class EcoNovaAgent:
    def __init__(self, config: AgentConfig, state: RuntimeState) -> None:
        self.config = config
        self.state = state
        self.paths = ensure_runtime_layout(config)
        self.persona_fragments = load_persona_fragments(config.persona_root, self.paths.workspace_dir)
        self.architecture = discover_architecture(config.workflows_dir)

    def reload_architecture(self) -> WorkflowArchitecture:
        self.architecture = discover_architecture(self.config.workflows_dir)
        return self.architecture

    def handle_text(self, text: str, session_id: str, channel: str) -> AgentReply:
        route = route_message(text, self.architecture)
        append_session_message(self.state, session_id, "user", text, self.config.history_limit)
        system_prompt = _build_system_prompt(self.architecture, route, self.persona_fragments)
        user_prompt = _build_user_prompt(
            self.architecture,
            self.state,
            session_id,
            route,
            channel,
            text,
        )
        try:
            result = generate_response(self.config, system_prompt, user_prompt)
            reply_text = result.text.strip()
            backend = result.provider
        except BackendError as error:
            reply_text = (
                "No pude responder con el backend configurado. "
                f"Diagnostico: {error}. "
                "Ejecuta `eco-nova doctor` o `eco-nova onboard` para corregirlo."
            )
            backend = "error"

        append_session_message(
            self.state,
            session_id,
            "assistant",
            reply_text,
            self.config.history_limit,
        )
        return AgentReply(text=reply_text, route=route, backend=backend)

    def handle_vision(
        self,
        image_paths: list[str],
        prompt: str,
        session_id: str,
        channel: str = "vision",
    ) -> AgentReply:
        text = prompt.strip() or "Analiza esta imagen y dime lo importante."
        route = route_message(text, self.architecture)
        append_session_message(self.state, session_id, "user", text, self.config.history_limit)
        system_prompt = _build_system_prompt(self.architecture, route, self.persona_fragments)
        user_prompt = _build_user_prompt(
            self.architecture,
            self.state,
            session_id,
            route,
            channel,
            text + f"\nImagenes adjuntas: {', '.join(Path(path).name for path in image_paths)}",
        )
        try:
            result = generate_vision_response(self.config, system_prompt, user_prompt, image_paths)
            reply_text = result.text.strip()
            backend = result.provider
        except BackendError as error:
            reply_text = (
                "No pude analizar la imagen. "
                f"Diagnostico: {error}. "
                "Revisa `eco doctor` y el backend configurado."
            )
            backend = "error"
        append_session_message(self.state, session_id, "assistant", reply_text, self.config.history_limit)
        return AgentReply(text=reply_text, route=route, backend=backend)

    def handle_audio(
        self,
        audio_path: str,
        prompt: str,
        session_id: str,
        channel: str = "audio",
    ) -> tuple[str, AgentReply]:
        transcript = transcribe_audio(self.config, audio_path, prompt).text
        reply = self.handle_text(transcript, session_id=session_id, channel=channel)
        return transcript, reply
