from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


DEFAULT_STATE_DIR = Path.home() / ".eco-nova"
DEFAULT_CONFIG_PATH = DEFAULT_STATE_DIR / "config.json"
DEFAULT_RUNTIME_STATE_PATH = DEFAULT_STATE_DIR / "state.json"


@dataclass
class BackendConfig:
    type: str = "auto"
    openai_model: str = "gpt-5"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_api_key_env: str = "OPENAI_API_KEY"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    codex_model: str = ""
    codex_workdir: str = "/home/ubuntu"
    codex_sandbox: str = "workspace-write"
    codex_search: bool = True
    timeout_seconds: int = 180


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    api_root: str = "https://api.telegram.org"
    dm_policy: str = "allowlist"
    allow_from: list[str] = field(default_factory=list)
    poll_interval_seconds: float = 2.0
    send_typing: bool = True


@dataclass
class AgentConfig:
    state_dir: str = str(DEFAULT_STATE_DIR)
    config_path: str = str(DEFAULT_CONFIG_PATH)
    runtime_state_path: str = str(DEFAULT_RUNTIME_STATE_PATH)
    workflows_dir: str = "/home/ubuntu/Workflows-n8n"
    workspace_root: str = "/home/ubuntu"
    persona_root: str = "/home/ubuntu/eco-nova"
    assistant_name: str = "Eco Nova"
    history_limit: int = 12
    backend: BackendConfig = field(default_factory=BackendConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


@dataclass
class PairingEntry:
    code: str
    expires_at: str


@dataclass
class RuntimeState:
    telegram_offset: int = 0
    pairing_codes: dict[str, PairingEntry] = field(default_factory=dict)
    sessions: dict[str, list[dict[str, str]]] = field(default_factory=dict)


def ensure_state_dir(path: Path | None = None) -> Path:
    target = path or DEFAULT_STATE_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_state_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _merge_dataclass(default: Any, data: dict[str, Any]) -> Any:
    values = {}
    for item in fields(default):
        current_value = getattr(default, item.name)
        raw_value = data.get(item.name, current_value)
        if is_dataclass(current_value) and isinstance(raw_value, dict):
            values[item.name] = _merge_dataclass(current_value, raw_value)
        else:
            values[item.name] = raw_value
    return type(default)(**values)


def load_config(path: Path | None = None) -> AgentConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    default = AgentConfig()
    raw = _read_json(config_path)
    merged = _merge_dataclass(default, raw)
    ensure_state_dir(Path(merged.state_dir))
    return merged


def save_config(config: AgentConfig, path: Path | None = None) -> Path:
    config_path = path or Path(config.config_path)
    payload = asdict(config)
    _write_json(config_path, payload)
    return config_path


def load_runtime_state(path: Path | None = None) -> RuntimeState:
    state_path = path or DEFAULT_RUNTIME_STATE_PATH
    raw = _read_json(state_path)
    pairing = {
        key: PairingEntry(**value)
        for key, value in raw.get("pairing_codes", {}).items()
        if isinstance(value, dict) and {"code", "expires_at"} <= set(value)
    }
    sessions = raw.get("sessions", {})
    if not isinstance(sessions, dict):
        sessions = {}
    return RuntimeState(
        telegram_offset=int(raw.get("telegram_offset", 0)),
        pairing_codes=pairing,
        sessions={key: value for key, value in sessions.items() if isinstance(value, list)},
    )


def save_runtime_state(state: RuntimeState, path: Path | None = None) -> Path:
    state_path = path or DEFAULT_RUNTIME_STATE_PATH
    payload = {
        "telegram_offset": state.telegram_offset,
        "pairing_codes": {
            key: {"code": value.code, "expires_at": value.expires_at}
            for key, value in state.pairing_codes.items()
        },
        "sessions": state.sessions,
    }
    _write_json(state_path, payload)
    return state_path


def append_session_message(
    state: RuntimeState,
    session_id: str,
    role: str,
    content: str,
    history_limit: int,
) -> None:
    messages = state.sessions.setdefault(session_id, [])
    messages.append({"role": role, "content": content})
    overflow = len(messages) - history_limit
    if overflow > 0:
        del messages[:overflow]


def resolve_nested_value(target: Any, dotted_path: str) -> Any:
    current = target
    for part in dotted_path.split("."):
        if not hasattr(current, part):
            raise KeyError(dotted_path)
        current = getattr(current, part)
    return current


def set_nested_value(target: Any, dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    current = target
    for part in parts[:-1]:
        if not hasattr(current, part):
            raise KeyError(dotted_path)
        current = getattr(current, part)
    leaf = parts[-1]
    if not hasattr(current, leaf):
        raise KeyError(dotted_path)
    setattr(current, leaf, value)
