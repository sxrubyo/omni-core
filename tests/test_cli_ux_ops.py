import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cli_ux_ops import collect_host_snapshot  # noqa: E402


class CliUxOpsTests(unittest.TestCase):
    def test_collect_host_snapshot_exposes_core_runtime_keys(self):
        payload = collect_host_snapshot()
        self.assertIn("system", payload)
        self.assertIn("shell", payload)
        self.assertIn("cpu_cores", payload)
        self.assertIn("disk_free_gb", payload)
        self.assertGreaterEqual(payload["cpu_cores"], 0)


if __name__ == "__main__":
    unittest.main()

