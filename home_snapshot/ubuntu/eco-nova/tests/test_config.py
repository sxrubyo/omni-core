import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eco_nova.config import AgentConfig, RuntimeState, append_session_message, save_config, load_config


class ConfigTests(unittest.TestCase):
    def test_roundtrip_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            config = AgentConfig()
            config.workflows_dir = "/tmp/workflows"
            config.telegram.bot_token = "token"
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded.workflows_dir, "/tmp/workflows")
            self.assertEqual(loaded.telegram.bot_token, "token")

    def test_session_history_limit(self) -> None:
        state = RuntimeState()
        for index in range(5):
            append_session_message(state, "s1", "user", f"m{index}", history_limit=3)
        self.assertEqual(len(state.sessions["s1"]), 3)
        self.assertEqual(state.sessions["s1"][0]["content"], "m2")


if __name__ == "__main__":
    unittest.main()
