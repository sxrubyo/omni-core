import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eco_nova.config import AgentConfig, RuntimeState
from eco_nova.telegram_gateway import IncomingTelegramMessage, authorize_sender


class TelegramPolicyTests(unittest.TestCase):
    def build_message(self, text: str, user_id: str = "123") -> IncomingTelegramMessage:
        return IncomingTelegramMessage(
            update_id=1,
            chat_id=user_id,
            user_id=user_id,
            chat_type="private",
            text=text,
        )

    def test_allowlist_blocks_unknown_user(self) -> None:
        config = AgentConfig()
        config.telegram.dm_policy = "allowlist"
        config.telegram.allow_from = []
        allowed, message = authorize_sender(config, RuntimeState(), self.build_message("hola"))
        self.assertFalse(allowed)
        self.assertIn("Acceso bloqueado", message or "")

    def test_pairing_generates_code(self) -> None:
        config = AgentConfig()
        config.telegram.dm_policy = "pairing"
        allowed, message = authorize_sender(config, RuntimeState(), self.build_message("hola"))
        self.assertFalse(allowed)
        self.assertIn("/pair", message or "")

    def test_open_policy_allows_user(self) -> None:
        config = AgentConfig()
        config.telegram.dm_policy = "open"
        allowed, message = authorize_sender(config, RuntimeState(), self.build_message("hola"))
        self.assertTrue(allowed)
        self.assertIsNone(message)


if __name__ == "__main__":
    unittest.main()
