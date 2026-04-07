from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .config import AgentConfig, PairingEntry, RuntimeState, save_config
from .runtime import EcoNovaAgent


BOGOTA = ZoneInfo("America/Bogota")
TELEGRAM_LIMIT = 4000


@dataclass
class IncomingTelegramMessage:
    update_id: int
    chat_id: str
    user_id: str
    chat_type: str
    text: str


class TelegramGatewayError(RuntimeError):
    """Telegram API failure."""


def _telegram_api_url(config: AgentConfig, method: str) -> str:
    return (
        f"{config.telegram.api_root.rstrip('/')}/"
        f"bot{config.telegram.bot_token.strip()}/{method}"
    )


def _telegram_request(config: AgentConfig, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url=_telegram_api_url(config, method),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise TelegramGatewayError(f"Telegram HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise TelegramGatewayError(f"No pude conectar con Telegram: {error}") from error

    if not data.get("ok"):
        raise TelegramGatewayError(str(data))
    return data


def telegram_get_me(config: AgentConfig) -> dict[str, Any]:
    return _telegram_request(config, "getMe", {})


def telegram_get_updates(config: AgentConfig, offset: int) -> list[dict[str, Any]]:
    data = _telegram_request(
        config,
        "getUpdates",
        {"timeout": 30, "offset": offset, "allowed_updates": ["message", "callback_query"]},
    )
    result = data.get("result", [])
    return result if isinstance(result, list) else []


def _split_telegram_chunks(text: str) -> list[str]:
    if len(text) <= TELEGRAM_LIMIT:
        return [text]
    chunks = []
    current = text
    while len(current) > TELEGRAM_LIMIT:
        cut = current.rfind("\n", 0, TELEGRAM_LIMIT)
        if cut <= 0:
            cut = TELEGRAM_LIMIT
        chunks.append(current[:cut].strip())
        current = current[cut:].strip()
    if current:
        chunks.append(current)
    return chunks


def telegram_send_message(config: AgentConfig, chat_id: str, text: str) -> None:
    for chunk in _split_telegram_chunks(text):
        _telegram_request(
            config,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
        )


def telegram_send_typing(config: AgentConfig, chat_id: str) -> None:
    _telegram_request(config, "sendChatAction", {"chat_id": chat_id, "action": "typing"})


def _parse_update(update: dict[str, Any]) -> IncomingTelegramMessage | None:
    if "message" in update:
        message = update["message"]
        text = message.get("text") or message.get("caption") or ""
        from_user = message.get("from", {})
        chat = message.get("chat", {})
    elif "callback_query" in update:
        callback_query = update["callback_query"]
        text = callback_query.get("data") or ""
        from_user = callback_query.get("from", {})
        chat = callback_query.get("message", {}).get("chat", {})
    else:
        return None

    if not text:
        return None

    return IncomingTelegramMessage(
        update_id=int(update.get("update_id", 0)),
        chat_id=str(chat.get("id", "")),
        user_id=str(from_user.get("id", "")),
        chat_type=str(chat.get("type", "private")),
        text=text.strip(),
    )


def _pairing_code_expired(entry: PairingEntry) -> bool:
    expires_at = datetime.fromisoformat(entry.expires_at)
    return datetime.now(BOGOTA) >= expires_at


def _ensure_pairing_code(state: RuntimeState, user_id: str) -> PairingEntry:
    current = state.pairing_codes.get(user_id)
    if current and not _pairing_code_expired(current):
        return current
    entry = PairingEntry(
        code=secrets.token_hex(3).upper(),
        expires_at=(datetime.now(BOGOTA) + timedelta(hours=1)).isoformat(),
    )
    state.pairing_codes[user_id] = entry
    return entry


def authorize_sender(
    config: AgentConfig,
    state: RuntimeState,
    message: IncomingTelegramMessage,
) -> tuple[bool, str | None]:
    policy = config.telegram.dm_policy.strip().lower()
    if message.chat_type != "private":
        return False, "Por ahora el gateway solo acepta mensajes privados de Telegram."
    if policy == "open":
        return True, None

    normalized_allowlist = {entry.strip() for entry in config.telegram.allow_from if entry.strip()}
    if message.user_id in normalized_allowlist:
        return True, None

    if policy == "allowlist":
        return (
            False,
            "Acceso bloqueado. Agrega tu user id de Telegram a `telegram.allow_from` o cambia la politica.",
        )

    if policy != "pairing":
        return False, f"Politica de DM no soportada: {config.telegram.dm_policy}"

    lowered = message.text.lower()
    if lowered.startswith("/pair "):
        supplied_code = message.text.split(" ", 1)[1].strip().upper()
        entry = state.pairing_codes.get(message.user_id)
        if not entry or _pairing_code_expired(entry):
            return False, "Tu codigo ya vencio. Escribeme otra vez para generar uno nuevo."
        if supplied_code != entry.code:
            return False, "Ese codigo no coincide. Revisa el codigo y vuelve a intentarlo."
        config.telegram.allow_from.append(message.user_id)
        config.telegram.allow_from = sorted(set(config.telegram.allow_from))
        save_config(config)
        del state.pairing_codes[message.user_id]
        return False, "Vinculacion completada. Ya puedes escribirme normalmente."

    entry = _ensure_pairing_code(state, message.user_id)
    return (
        False,
        "Necesito vincular este chat antes de responder.\n"
        f"Codigo: {entry.code}\n"
        f"Responde: /pair {entry.code}",
    )


def run_telegram_gateway(agent: EcoNovaAgent) -> None:
    config = agent.config
    state = agent.state
    if not config.telegram.bot_token.strip():
        raise TelegramGatewayError("Falta telegram.bot_token en la configuracion.")

    while True:
        updates = telegram_get_updates(config, state.telegram_offset)
        for raw_update in updates:
            incoming = _parse_update(raw_update)
            update_id = int(raw_update.get("update_id", 0))
            state.telegram_offset = max(state.telegram_offset, update_id + 1)
            if not incoming:
                continue

            allowed, auth_message = authorize_sender(config, state, incoming)
            if not allowed:
                if auth_message:
                    telegram_send_message(config, incoming.chat_id, auth_message)
                continue

            if config.telegram.send_typing:
                try:
                    telegram_send_typing(config, incoming.chat_id)
                except TelegramGatewayError:
                    pass

            session_id = f"telegram:{incoming.chat_id}"
            reply = agent.handle_text(incoming.text, session_id=session_id, channel="telegram")
            telegram_send_message(config, incoming.chat_id, reply.text)

        time.sleep(max(0.2, config.telegram.poll_interval_seconds))
