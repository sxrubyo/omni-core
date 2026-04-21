import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guide_ops import build_guide_entries, build_guide_payload  # noqa: E402


class GuideOpsTests(unittest.TestCase):
    def test_build_guide_entries_contains_expected_surfaces(self):
        entries = build_guide_entries()
        keys = {entry.key for entry in entries}
        self.assertEqual(len(entries), 5)
        self.assertIn("connect", keys)
        self.assertIn("briefcase", keys)
        self.assertIn("agent", keys)

    def test_build_guide_payload_is_serializable(self):
        payload = build_guide_payload()
        self.assertEqual(payload["title"], "Omni Guide")
        self.assertEqual(len(payload["entries"]), 5)


if __name__ == "__main__":
    unittest.main()

