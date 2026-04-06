import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from watch_ops import capture_watch_snapshot, summarize_snapshot_diff  # noqa: E402


class WatchOpsTests(unittest.TestCase):
    def test_capture_watch_snapshot_tracks_state_and_secret_but_skips_excluded_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state_dir = home / "melissa"
            secret_dir = home / ".ssh"
            auto_bundles = home / "omni-core" / "backups" / "auto-bundles"
            state_dir.mkdir(parents=True)
            secret_dir.mkdir(parents=True)
            auto_bundles.mkdir(parents=True)
            (state_dir / "notes.txt").write_text("hola", encoding="utf-8")
            (secret_dir / "id_rsa").write_text("PRIVATE", encoding="utf-8")
            (auto_bundles / "state_bundle.tar.gz").write_text("bundle", encoding="utf-8")

            manifest = {
                "host_root": str(home),
                "profile": "full-home",
                "state_paths": [str(home)],
                "secret_paths": [str(secret_dir)],
                "state_exclude_paths": [str(auto_bundles)],
                "exclude_patterns": [],
            }

            snapshot = capture_watch_snapshot(manifest, str(home))

            self.assertIn("melissa/notes.txt", snapshot["entries"])
            self.assertIn(".ssh/id_rsa", snapshot["entries"])
            self.assertNotIn("omni-core/backups/auto-bundles/state_bundle.tar.gz", snapshot["entries"])

    def test_summarize_snapshot_diff_detects_added_modified_and_removed(self):
        previous = {
            "fingerprint": "old",
            "entries": {
                "melissa/a.txt": {"size": 5, "mtime_ns": 1},
                "melissa/b.txt": {"size": 8, "mtime_ns": 1},
            },
        }
        current = {
            "fingerprint": "new",
            "entries": {
                "melissa/a.txt": {"size": 7, "mtime_ns": 2},
                "melissa/c.txt": {"size": 4, "mtime_ns": 1},
            },
        }

        diff = summarize_snapshot_diff(previous, current)

        self.assertTrue(diff["changed"])
        self.assertEqual(diff["changed_files"], 3)
        self.assertEqual(diff["added"], 1)
        self.assertEqual(diff["modified"], 1)
        self.assertEqual(diff["removed"], 1)
        self.assertIn("melissa/a.txt", diff["samples"])
        self.assertIn("melissa/b.txt", diff["samples"])
        self.assertIn("melissa/c.txt", diff["samples"])


if __name__ == "__main__":
    unittest.main()
