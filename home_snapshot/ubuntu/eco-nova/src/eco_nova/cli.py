from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .architecture import discover_architecture
from .backends import BackendError
from .config import (
    load_config,
    load_runtime_state,
    resolve_nested_value,
    save_config,
    save_runtime_state,
    set_nested_value,
)
from .layout import append_command_log, append_event, ensure_runtime_layout, resolve_state_paths
from .router import route_message
from .runtime import EcoNovaAgent
from .telegram_gateway import TelegramGatewayError, run_telegram_gateway, telegram_get_me


console = Console()
NOVA_SYMBOL = "✦"


def _print_banner(subtitle: str = "Control plane local") -> None:
    title = Text(f" {NOVA_SYMBOL} ECO NOVA ", style="bold white on rgb(33,48,72)")
    console.print(Panel(title, subtitle=subtitle, subtitle_align="center", border_style="bright_blue"))


def _json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def _parse_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _coerce_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value).strip()
    return str(value).strip()


def _interactive_chat(agent: EcoNovaAgent) -> int:
    _print_banner("chat local")
    console.print(
        Panel(
            "Modo chat interactivo.\nEscribe `salir` para terminar.",
            title="Eco Nova",
            border_style="cyan",
        )
    )
    while True:
        message = Prompt.ask("Eco Nova")
        if message.strip().lower() in {"salir", "exit", "quit"}:
            break
        reply = agent.handle_text(message, session_id="cli:interactive", channel="cli")
        console.print(Panel(reply.text, border_style="blue", title=reply.route.cluster_id.upper()))
        save_runtime_state(agent.state, Path(agent.config.runtime_state_path))
    return 0


def command_onboard(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    _print_banner("onboarding")

    workflows_default = config.workflows_dir
    workflows_dir = Prompt.ask("Directorio de Workflows-n8n", default=workflows_default)
    config.workflows_dir = workflows_dir

    backend_type = Prompt.ask(
        "Backend principal",
        default=config.backend.type,
        choices=["auto", "openai", "codex"],
    )
    config.backend.type = backend_type

    if backend_type in {"auto", "openai"}:
        openai_key = config.backend.openai_api_key or ""
        if not openai_key:
            openai_key = Prompt.ask(
                "OpenAI API key (opcional, Enter para omitir)",
                default="",
                show_default=False,
            )
        config.backend.openai_api_key = openai_key.strip()

    if backend_type in {"auto", "codex"}:
        codex_workdir = Prompt.ask("Codex workdir", default=config.backend.codex_workdir)
        config.backend.codex_workdir = codex_workdir
        config.backend.codex_sandbox = Prompt.ask(
            "Codex sandbox",
            default=config.backend.codex_sandbox,
            choices=["read-only", "workspace-write", "danger-full-access"],
        )

    wants_telegram = Confirm.ask(
        "Configurar gateway de Telegram ahora?",
        default=bool(config.telegram.bot_token),
    )
    if wants_telegram:
        config.telegram.enabled = True
        config.telegram.bot_token = Prompt.ask(
            "Telegram bot token",
            default=config.telegram.bot_token,
            show_default=bool(config.telegram.bot_token),
        ).strip()
        config.telegram.dm_policy = Prompt.ask(
            "Politica DM",
            default=config.telegram.dm_policy,
            choices=["allowlist", "pairing", "open"],
        )
        if config.telegram.dm_policy == "allowlist":
            allow_raw = Prompt.ask(
                "User IDs permitidos (separados por coma)",
                default=",".join(config.telegram.allow_from),
                show_default=bool(config.telegram.allow_from),
            )
            config.telegram.allow_from = [item.strip() for item in allow_raw.split(",") if item.strip()]
    else:
        config.telegram.enabled = False

    path = save_config(config)
    ensure_runtime_layout(config)
    console.print(f"Configuracion guardada en {path}")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    config = load_config()
    paths = ensure_runtime_layout(config)
    table = Table(title="Eco Nova Doctor")
    table.add_column("Check")
    table.add_column("Estado")
    table.add_column("Detalle")

    workflows_exists = Path(config.workflows_dir).exists()
    table.add_row("Workflows-n8n", "OK" if workflows_exists else "FALLA", config.workflows_dir)

    backend = config.backend.type
    table.add_row("Backend", "OK", backend)

    has_openai = bool(
        config.backend.openai_api_key.strip()
        or os.environ.get(config.backend.openai_api_key_env, "").strip()
    )
    table.add_row(
        "OpenAI key",
        "OK" if has_openai else "INFO",
        "configurada" if has_openai else f"usa {config.backend.openai_api_key_env} o onboard",
    )

    has_codex = shutil.which("codex") is not None
    table.add_row("Codex", "OK" if has_codex else "INFO", shutil.which("codex") or "no encontrado")

    if config.telegram.bot_token.strip():
        try:
            me = telegram_get_me(config).get("result", {})
            detail = f"@{me.get('username', 'sin-username')}"
            state = "OK"
        except TelegramGatewayError as error:
            detail = str(error)
            state = "FALLA"
    else:
        detail = "sin token configurado"
        state = "INFO"
    table.add_row("Telegram", state, detail)
    table.add_row("Workspace", "OK", str(paths.workspace_dir))
    table.add_row("Vision", "OK", "OpenAI o Codex con imagen" if shutil.which("codex") else "requiere backend")
    table.add_row(
        "Listen",
        "OK" if has_openai else "INFO",
        "requiere OpenAI para transcribir audio",
    )

    console.print(table)
    return 0


def command_chat(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    state = load_runtime_state(Path(config.runtime_state_path))
    agent = EcoNovaAgent(config, state)
    message = _coerce_text(args.message)
    reply = agent.handle_text(message, session_id=args.session, channel="cli")
    console.print(Panel(reply.text, title=reply.route.cluster_id.upper(), border_style="blue"))
    save_runtime_state(state, Path(config.runtime_state_path))
    return 0


def command_architecture(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    architecture = discover_architecture(config.workflows_dir)
    console.print(
        Panel(
            f"Entrada: {', '.join(architecture.entry_workflows) or 'N/D'}\n"
            f"Orquestador: {architecture.main_orchestrator or 'N/D'}\n"
            f"Output: {architecture.output_engine or 'N/D'}",
            title="Pipeline",
            border_style="cyan",
        )
    )
    table = Table(title="Clusters")
    table.add_column("Cluster")
    table.add_column("Workflow")
    table.add_column("Subagentes")
    for cluster_id, cluster in architecture.clusters.items():
        table.add_row(cluster_id.upper(), cluster.workflow_name, "\n".join(cluster.subagents[:8]))
    console.print(table)
    return 0


def command_route(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    architecture = discover_architecture(config.workflows_dir)
    result = route_message(_coerce_text(args.message), architecture)
    table = Table(title="Routing")
    table.add_column("Campo")
    table.add_column("Valor")
    table.add_row("cluster", result.cluster_id)
    table.add_row("confidence", f"{result.confidence:.2f}")
    table.add_row("keywords", ", ".join(result.matched_keywords) or "ninguna")
    table.add_row("subagents", ", ".join(result.selected_subagents) or "ninguno")
    console.print(table)
    return 0


def command_gateway_telegram(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    state = load_runtime_state(Path(config.runtime_state_path))
    agent = EcoNovaAgent(config, state)
    me = telegram_get_me(config).get("result", {})
    console.print(
        Panel(
            f"Gateway Telegram activo para @{me.get('username', 'sin-username')}",
            title="Eco Nova",
            border_style="green",
        )
    )
    try:
        run_telegram_gateway(agent)
    finally:
        save_runtime_state(state, Path(config.runtime_state_path))
    return 0


def command_start(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    if args.chat:
        state = load_runtime_state(Path(config.runtime_state_path))
        agent = EcoNovaAgent(config, state)
        try:
            return _interactive_chat(agent)
        finally:
            save_runtime_state(state, Path(config.runtime_state_path))

    if config.telegram.enabled and config.telegram.bot_token.strip():
        return command_gateway_telegram(args)

    console.print("No hay canales activos. Entro a chat local.")
    state = load_runtime_state(Path(config.runtime_state_path))
    agent = EcoNovaAgent(config, state)
    try:
        return _interactive_chat(agent)
    finally:
        save_runtime_state(state, Path(config.runtime_state_path))


def command_status(args: argparse.Namespace) -> int:
    config = load_config()
    paths = ensure_runtime_layout(config)
    architecture = discover_architecture(config.workflows_dir)
    table = Table(title="Eco Nova Status")
    table.add_column("Area")
    table.add_column("Estado")
    table.add_column("Detalle")
    table.add_row("assistant", "OK", config.assistant_name)
    table.add_row("backend", "OK", config.backend.type)
    table.add_row("workflows", "OK" if Path(config.workflows_dir).exists() else "FALLA", config.workflows_dir)
    table.add_row("clusters", "OK", ", ".join(sorted(architecture.clusters.keys())))
    table.add_row("workspace", "OK", str(paths.workspace_dir))
    table.add_row("memory", "OK", str(paths.memory_dir))
    table.add_row(
        "telegram",
        "ON" if config.telegram.enabled and config.telegram.bot_token.strip() else "OFF",
        config.telegram.dm_policy,
    )
    console.print(table)
    console.print(
        Panel(
            "Comandos simples:\n"
            "eco start\n"
            "eco chat \"...\"\n"
            "eco tg connect --token <TOKEN>\n"
            "eco tg start\n"
            "eco see imagen.png \"que ves\"\n"
            "eco listen audio.m4a",
            title="Uso rapido",
            border_style="cyan",
        )
    )
    return 0


def command_connect_telegram(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    token = (args.token or "").strip()
    if not token:
        token = Prompt.ask(
            "Telegram bot token",
            default=config.telegram.bot_token,
            show_default=bool(config.telegram.bot_token),
        ).strip()
    config.telegram.bot_token = token
    config.telegram.enabled = True
    config.telegram.dm_policy = args.policy or config.telegram.dm_policy
    if args.allow_from:
        config.telegram.allow_from = [item.strip() for item in args.allow_from.split(",") if item.strip()]
    save_config(config)
    try:
        me = telegram_get_me(config).get("result", {})
        console.print(
            Panel(
                f"Telegram conectado para @{me.get('username', 'sin-username')}",
                title="Eco Nova",
                border_style="green",
            )
        )
    except TelegramGatewayError as error:
        console.print(
            Panel(
                f"Se guardo el token, pero la validacion fallo: {error}",
                title="Eco Nova",
                border_style="yellow",
            )
        )
    if args.start:
        return command_gateway_telegram(args)
    return 0


def command_gateway_status(args: argparse.Namespace) -> int:
    config = load_config()
    paths = ensure_runtime_layout(config)
    table = Table(title="Gateway")
    table.add_column("Canal")
    table.add_column("Enabled")
    table.add_column("Detalle")
    telegram_detail = "sin token"
    if config.telegram.bot_token.strip():
        telegram_detail = config.telegram.dm_policy
    table.add_row("telegram", "yes" if config.telegram.enabled else "no", telegram_detail)
    table.add_row("offset", "-", str(Path(config.runtime_state_path)))
    table.add_row("state", "-", str(paths.telegram_dir))
    console.print(table)
    return 0


def command_workspace_init(args: argparse.Namespace) -> int:
    config = load_config()
    paths = ensure_runtime_layout(config)
    console.print(
        Panel(
            "Workspace listo.\n"
            f"Ruta: {paths.workspace_dir}",
            title="Eco Nova",
            border_style="green",
        )
    )
    return 0


def command_workspace_show(args: argparse.Namespace) -> int:
    config = load_config()
    paths = ensure_runtime_layout(config)
    table = Table(title="Workspace")
    table.add_column("Archivo")
    table.add_column("Ruta")
    for name in ["AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md", "TOOLS.md", "HEARTBEAT.md"]:
        table.add_row(name, str(paths.workspace_dir / name))
    console.print(table)
    return 0


def command_see(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    state = load_runtime_state(Path(config.runtime_state_path))
    agent = EcoNovaAgent(config, state)
    prompt = _coerce_text(args.prompt or []) or "Analiza esta imagen y dime lo importante."
    reply = agent.handle_vision(args.images, prompt, session_id=args.session, channel="vision")
    console.print(Panel(reply.text, title=f"{reply.route.cluster_id.upper()} / VISION", border_style="magenta"))
    save_runtime_state(state, Path(config.runtime_state_path))
    return 0


def command_listen(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    state = load_runtime_state(Path(config.runtime_state_path))
    agent = EcoNovaAgent(config, state)
    prompt = _coerce_text(args.prompt or [])
    try:
        transcript, reply = agent.handle_audio(args.audio, prompt, session_id=args.session, channel="audio")
    except BackendError as error:
        console.print(Panel(f"No pude escuchar el audio. Diagnostico: {error}", title="AUDIO", border_style="red"))
        return 1
    console.print(Panel(transcript, title="TRANSCRIPCION", border_style="yellow"))
    console.print(Panel(reply.text, title=f"{reply.route.cluster_id.upper()} / AUDIO", border_style="blue"))
    save_runtime_state(state, Path(config.runtime_state_path))
    return 0


def command_config_show(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    if args.key:
        value = resolve_nested_value(config, args.key)
        console.print_json(data=json.loads(json.dumps(_json_ready(value), default=str)))
        return 0
    console.print_json(data=json.loads(json.dumps(asdict(config), default=str)))
    return 0


def command_config_set(args: argparse.Namespace) -> int:
    config = load_config()
    ensure_runtime_layout(config)
    value = _parse_value(args.value)
    set_nested_value(config, args.key, value)
    save_config(config)
    console.print(f"{args.key} actualizado.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eco", add_help=True, description="Eco Nova control plane CLI")
    subparsers = parser.add_subparsers(dest="command")

    start = subparsers.add_parser("start", help="Arranque inteligente")
    start.add_argument("--chat", action="store_true", help="Forzar chat local")
    start.set_defaults(func=command_start)

    status = subparsers.add_parser("status", help="Estado general")
    status.set_defaults(func=command_status)

    onboard = subparsers.add_parser("onboard", help="Wizard paso a paso")
    onboard.set_defaults(func=command_onboard)

    doctor = subparsers.add_parser("doctor", help="Diagnostico rapido")
    doctor.set_defaults(func=command_doctor)

    chat = subparsers.add_parser("chat", help="Enviar un mensaje local al agente")
    chat.add_argument("message", nargs="+")
    chat.add_argument("--session", default="cli:default")
    chat.set_defaults(func=command_chat)

    say = subparsers.add_parser("say", help="Alias corto de chat")
    say.add_argument("message", nargs="+")
    say.add_argument("--session", default="cli:default")
    say.set_defaults(func=command_chat)

    see = subparsers.add_parser("see", help="Analizar imagenes")
    see.add_argument("images", nargs="+")
    see.add_argument("prompt", nargs="*")
    see.add_argument("--session", default="cli:vision")
    see.set_defaults(func=command_see)

    listen = subparsers.add_parser("listen", help="Escuchar audio y responder")
    listen.add_argument("audio")
    listen.add_argument("prompt", nargs="*")
    listen.add_argument("--session", default="cli:audio")
    listen.set_defaults(func=command_listen)

    architecture = subparsers.add_parser("architecture", help="Ver arquitectura n8n detectada")
    architecture.set_defaults(func=command_architecture)

    route = subparsers.add_parser("route", help="Probar el router")
    route.add_argument("message", nargs="+")
    route.set_defaults(func=command_route)

    connect = subparsers.add_parser("connect", help="Conectar canales")
    connect_subparsers = connect.add_subparsers(dest="connect_command")
    connect_telegram = connect_subparsers.add_parser("telegram", help="Configurar Telegram")
    connect_telegram.add_argument("--token")
    connect_telegram.add_argument("--policy", choices=["allowlist", "pairing", "open"])
    connect_telegram.add_argument("--allow-from")
    connect_telegram.add_argument("--start", action="store_true")
    connect_telegram.set_defaults(func=command_connect_telegram)

    tg = subparsers.add_parser("tg", help="Atajos para Telegram")
    tg_sub = tg.add_subparsers(dest="tg_command")
    tg_connect = tg_sub.add_parser("connect", help="Configurar Telegram")
    tg_connect.add_argument("--token")
    tg_connect.add_argument("--policy", choices=["allowlist", "pairing", "open"])
    tg_connect.add_argument("--allow-from")
    tg_connect.add_argument("--start", action="store_true")
    tg_connect.set_defaults(func=command_connect_telegram)
    tg_start = tg_sub.add_parser("start", help="Iniciar Telegram")
    tg_start.set_defaults(func=command_gateway_telegram)
    tg_status = tg_sub.add_parser("status", help="Estado Telegram")
    tg_status.set_defaults(func=command_gateway_status)

    gateway = subparsers.add_parser("gateway", help="Gateways disponibles")
    gateway_subparsers = gateway.add_subparsers(dest="gateway_command")
    telegram = gateway_subparsers.add_parser("telegram", help="Iniciar Telegram")
    telegram.set_defaults(func=command_gateway_telegram)
    gateway_status = gateway_subparsers.add_parser("status", help="Estado de gateways")
    gateway_status.set_defaults(func=command_gateway_status)

    config = subparsers.add_parser("config", help="Mostrar o editar configuracion")
    config_subparsers = config.add_subparsers(dest="config_command")
    config_show = config_subparsers.add_parser("show", help="Ver configuracion")
    config_show.add_argument("key", nargs="?")
    config_show.set_defaults(func=command_config_show)
    config_set = config_subparsers.add_parser("set", help="Actualizar una clave")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_set.set_defaults(func=command_config_set)

    workspace = subparsers.add_parser("workspace", help="Workspace de Eco Nova")
    workspace_sub = workspace.add_subparsers(dest="workspace_command")
    workspace_init = workspace_sub.add_parser("init", help="Crear layout local")
    workspace_init.set_defaults(func=command_workspace_init)
    workspace_show = workspace_sub.add_parser("show", help="Ver archivos base")
    workspace_show.set_defaults(func=command_workspace_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argv = argv or sys.argv[1:]
    if not argv:
        config = load_config()
        ensure_runtime_layout(config)
        state = load_runtime_state(Path(config.runtime_state_path))
        agent = EcoNovaAgent(config, state)
        try:
            return _interactive_chat(agent)
        finally:
            save_runtime_state(state, Path(config.runtime_state_path))

    known_commands = {
        "start",
        "status",
        "onboard",
        "doctor",
        "chat",
        "say",
        "see",
        "listen",
        "architecture",
        "route",
        "connect",
        "tg",
        "gateway",
        "config",
        "workspace",
    }
    if argv[0] not in known_commands:
        argv = ["chat", " ".join(argv)]

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    config = load_config()
    paths = ensure_runtime_layout(config)
    append_command_log(paths, " ".join(argv))
    return args.func(args)
