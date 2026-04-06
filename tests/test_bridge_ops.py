import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bridge_ops import build_host_rewrite_context, load_capture_summary, summarize_bundle_pair, write_capture_summary  # noqa: E402
from bundle_ops import create_secrets_bundle, create_state_bundle  # noqa: E402


class BridgeOpsTests(unittest.TestCase):
    def test_capture_summary_writes_metadata_for_bundle_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home" / "ubuntu"
            state_dir = home / "melissa"
            secret_file = state_dir / ".env"
            state_file = state_dir / "keep.txt"
            state_dir.mkdir(parents=True)
            state_file.write_text("hola", encoding="utf-8")
            secret_file.write_text("TOKEN=abc\n", encoding="utf-8")

            manifest = {
                "host_root": str(home),
                "profile": "production-clean",
                "version": 1,
                "state_paths": [str(state_dir)],
                "secret_paths": [str(secret_file)],
                "exclude_patterns": [],
            }
            bundles_dir = root / "bundles"
            state_bundle = create_state_bundle(bundles_dir, manifest)
            secrets_bundle = create_secrets_bundle(bundles_dir, manifest, passphrase="secret")

            summary_path = write_capture_summary(
                bundle_dir=bundles_dir,
                manifest_path=root / "manifest.json",
                state_bundle=state_bundle,
                secrets_bundle=secrets_bundle,
            )

            self.assertTrue(summary_path.exists())
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["state_bundle"]["archive_kind"], "state")
            self.assertTrue(payload["secrets_bundle"]["encrypted"])
            self.assertIn("source_identity", payload)

            loaded = load_capture_summary(bundles_dir)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["state_bundle"]["sha256"], payload["state_bundle"]["sha256"])

    def test_summarize_bundle_pair_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundles_dir = Path(tmp)
            summary = summarize_bundle_pair(bundle_dir=bundles_dir)
            self.assertFalse(summary["ok"])
            self.assertIsNone(summary["state_bundle"])
            self.assertIsNone(summary["secrets_bundle"])

    def test_build_host_rewrite_context_uses_summary_and_current_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundles_dir = Path(tmp)
            summary_path = bundles_dir / "capture_summary_20260406_000000.json"
            summary_payload = {
                "source_identity": {
                    "public_ip": "54.160.79.60",
                    "private_ip": "172.31.0.10",
                    "hostname": "old-host",
                    "fqdn": "old-host.local",
                }
            }
            summary_path.write_text(json.dumps(summary_payload), encoding="utf-8")

            fake_identity = mock.Mock(
                public_ip="203.0.113.10",
                private_ip="10.0.0.12",
                hostname="new-host",
                fqdn="new-host.local",
            )

            with mock.patch("bridge_ops.detect_host_identity", return_value=fake_identity):
                context = build_host_rewrite_context(bundles_dir)

            self.assertTrue(context["summary_found"])
            self.assertEqual(context["source_identity"]["hostname"], "old-host")
            self.assertEqual(context["target_identity"]["hostname"], "new-host")
            self.assertEqual(context["replacements"]["54.160.79.60"], "203.0.113.10")
            self.assertEqual(context["replacements"]["old-host"], "new-host")


if __name__ == "__main__":
    unittest.main()
