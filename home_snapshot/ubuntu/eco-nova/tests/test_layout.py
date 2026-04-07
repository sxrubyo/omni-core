import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eco_nova.config import AgentConfig
from eco_nova.layout import ensure_runtime_layout


class LayoutTests(unittest.TestCase):
    def test_layout_creates_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AgentConfig(
                state_dir=tmpdir,
                config_path=str(Path(tmpdir) / "config.json"),
                runtime_state_path=str(Path(tmpdir) / "state.json"),
            )
            paths = ensure_runtime_layout(config)
            self.assertTrue(paths.workspace_dir.exists())
            self.assertTrue((paths.workspace_dir / "SOUL.md").exists())
            self.assertTrue(paths.telegram_dir.exists())
            self.assertTrue(paths.logs_dir.exists())


if __name__ == "__main__":
    unittest.main()
