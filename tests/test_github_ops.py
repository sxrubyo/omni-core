import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from github_ops import latest_briefcase_entry, load_global_config, parse_repo_slug, save_global_config  # noqa: E402


class GitHubOpsTests(unittest.TestCase):
    def test_parse_repo_slug_accepts_owner_repo_and_default_owner(self) -> None:
        target = parse_repo_slug("sxrubyo/omnisync")
        self.assertEqual(target.owner, "sxrubyo")
        self.assertEqual(target.repo, "omnisync")

        target_default = parse_repo_slug("omni-private", default_owner="sxrubyo")
        self.assertEqual(target_default.slug, "sxrubyo/omni-private")

    def test_save_and_load_global_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            payload = {"github": {"repo": "sxrubyo/omni-private", "token": "secret"}}
            save_global_config(path, payload)
            loaded = load_global_config(path)
            self.assertEqual(loaded["github"]["repo"], "sxrubyo/omni-private")

    def test_latest_briefcase_entry_prefers_newest_filename(self) -> None:
        entries = [
            {"name": "20260420-120000-host.json", "path": "briefcases/20260420-120000-host.json"},
            {"name": "20260421-120000-host.restore.sh", "path": "briefcases/20260421-120000-host.restore.sh"},
            {"name": "20260421-120000-host.json", "path": "briefcases/20260421-120000-host.json"},
        ]
        latest = latest_briefcase_entry(entries)
        self.assertEqual(latest["name"], "20260421-120000-host.json")


if __name__ == "__main__":
    unittest.main()
