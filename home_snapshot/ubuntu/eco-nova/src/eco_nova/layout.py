from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import AgentConfig


@dataclass
class StatePaths:
    state_dir: Path
    config_path: Path
    runtime_state_path: Path
    credentials_dir: Path
    logs_dir: Path
    memory_dir: Path
    workspace_dir: Path
    channels_dir: Path
    telegram_dir: Path
    devices_dir: Path
    canvas_dir: Path
    command_log_path: Path
    event_log_path: Path
    workspace_state_path: Path
    heartbeat_state_path: Path


WORKSPACE_TEMPLATES = {
    "AGENTS.md": """# AGENTS.md - Eco Nova Workspace

Este workspace es la memoria viva de Eco Nova.

## Arranque

Antes de operar:

1. Lee `SOUL.md`
2. Lee `IDENTITY.md`
3. Lee `USER.md`
4. Lee `TOOLS.md`
5. Revisa `memory/` para contexto reciente

## Regla central

Eco Nova habla con una sola voz hacia afuera y absorbe la complejidad hacia adentro.

## Seguridad

- No expongas datos privados
- No ejecutes acciones destructivas sin criterio
- Documenta decisiones importantes en `memory/`
""",
    "SOUL.md": """# SOUL.md

Eco Nova no narra pasos intermedios. Decide, ejecuta y reporta.

## Rasgos

- Español siempre
- Sobriedad
- Resultado antes que teatro
- Una sola voz
- Arquitectura interna invisible para el usuario
""",
    "IDENTITY.md": """# IDENTITY.md

- Nombre: Eco Nova
- Naturaleza: Mega agente local
- Vibe: Sobrio, directo, operativo
- Firma: ejecutar, decidir, reportar
""",
    "USER.md": """# USER.md

- Nombre: Santiago Rubio
- Zona horaria: America/Bogota
- Contexto: Arquitecto de sistemas y operador principal
""",
    "TOOLS.md": """# TOOLS.md

Notas locales del entorno:

- Telegram
- Workflows-n8n
- Drive
- Multimedia
- Hosts y dispositivos
""",
    "HEARTBEAT.md": """# HEARTBEAT.md

Si nada necesita atencion, responde HEARTBEAT_OK.
Si hay algo importante, prioriza:

1. Mensajes entrantes
2. Eventos proximos
3. Estado de gateways
4. Contexto operativo pendiente
""",
    "BOOTSTRAP.md": """# BOOTSTRAP.md

Usa `eco onboard` para completar la configuracion inicial.
""",
}


def resolve_state_paths(config: AgentConfig) -> StatePaths:
    state_dir = Path(config.state_dir).expanduser()
    return StatePaths(
        state_dir=state_dir,
        config_path=Path(config.config_path).expanduser(),
        runtime_state_path=Path(config.runtime_state_path).expanduser(),
        credentials_dir=state_dir / "credentials",
        logs_dir=state_dir / "logs",
        memory_dir=state_dir / "memory",
        workspace_dir=state_dir / "workspace",
        channels_dir=state_dir / "channels",
        telegram_dir=state_dir / "channels" / "telegram",
        devices_dir=state_dir / "devices",
        canvas_dir=state_dir / "canvas",
        command_log_path=state_dir / "logs" / "commands.log",
        event_log_path=state_dir / "logs" / "events.jsonl",
        workspace_state_path=state_dir / "workspace" / "workspace-state.json",
        heartbeat_state_path=state_dir / "memory" / "heartbeat-state.json",
    )


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content.strip() + "\n", encoding="utf-8")


def ensure_runtime_layout(config: AgentConfig) -> StatePaths:
    paths = resolve_state_paths(config)
    directories = [
        paths.state_dir,
        paths.credentials_dir,
        paths.logs_dir,
        paths.memory_dir,
        paths.workspace_dir,
        paths.channels_dir,
        paths.telegram_dir,
        paths.devices_dir,
        paths.canvas_dir,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    for name, content in WORKSPACE_TEMPLATES.items():
        _write_if_missing(paths.workspace_dir / name, content)

    if not paths.workspace_state_path.exists():
        paths.workspace_state_path.write_text(
            json.dumps(
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "assistant_name": config.assistant_name,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    if not paths.heartbeat_state_path.exists():
        paths.heartbeat_state_path.write_text(
            json.dumps({"last_checks": {}}, indent=2) + "\n",
            encoding="utf-8",
        )
    return paths


def append_event(paths: StatePaths, event: str, detail: dict | None = None) -> None:
    payload = {
        "at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "detail": detail or {},
    }
    with paths.event_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_command_log(paths: StatePaths, command_line: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with paths.command_log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {command_line}\n")
