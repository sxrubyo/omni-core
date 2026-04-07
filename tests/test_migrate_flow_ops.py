import sys
import unittest
from pathlib import Path
from unittest import mock
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omni_core import OmniCore  # noqa: E402


class MigrateFlowOpsTests(unittest.TestCase):
    def test_bundle_search_dirs_include_backup_root(self):
        core = OmniCore()

        with tempfile.TemporaryDirectory() as tmp:
            backup_dir = Path(tmp) / "backups"
            host_dir = backup_dir / "host-bundles"
            auto_dir = backup_dir / "auto-bundles"
            host_dir.mkdir(parents=True)
            auto_dir.mkdir(parents=True)
            core.bundle_dir = host_dir

            with mock.patch("omni_core.BACKUP_DIR", backup_dir), \
                 mock.patch.object(core, "auto_backup_dir", return_value=auto_dir):
                dirs = core.bundle_search_dirs(include_auto=False)

        self.assertEqual(dirs, [host_dir, backup_dir])

    def test_migrate_host_cmd_stops_when_restore_fails(self):
        core = OmniCore()

        with mock.patch.object(core, "restore_host_cmd", return_value={"success": False}), \
             mock.patch.object(core, "run_backup") as backup_mock, \
             mock.patch("omni_core.render_action_summary") as render_mock:
            core.migrate_host_cmd(accept_all=True)

        backup_mock.assert_not_called()
        render_mock.assert_not_called()

    def test_build_host_drift_report_uses_configured_server_when_summary_missing(self):
        core = OmniCore()
        core.servers = [{"name": "main-ubuntu", "host": "172.31.99.10"}]

        fake_identity = mock.Mock(
            public_ip="54.1.2.3",
            private_ip="172.31.34.176",
            hostname="new-host",
            fqdn="new-host.local",
            ip_candidates=["172.31.34.176"],
            source="local",
        )

        with mock.patch("omni_core.build_host_rewrite_context", return_value={
            "summary": None,
            "summary_found": False,
            "source_identity": {},
            "target_identity": {
                "public_ip": fake_identity.public_ip,
                "private_ip": fake_identity.private_ip,
                "hostname": fake_identity.hostname,
                "fqdn": fake_identity.fqdn,
            },
            "replacements": {},
        }), mock.patch("omni_core.detect_host_identity", return_value=fake_identity):
            drift = core.build_host_drift_report(root="/tmp")

        self.assertTrue(drift["context"]["summary_found"])
        self.assertEqual(drift["context"]["replacements"]["172.31.99.10"], "54.1.2.3")

    def test_restore_host_cmd_ignores_implicit_auto_bundles_during_bootstrap(self):
        core = OmniCore()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_dir = root / "host-bundles"
            auto_dir = root / "auto-bundles"
            host_dir.mkdir()
            auto_dir.mkdir()
            (auto_dir / "state_bundle_20260406_231509.tar.gz").write_text("state", encoding="utf-8")
            (auto_dir / "secrets_bundle_20260406_231509.tar.gz").write_text("secrets", encoding="utf-8")

            core.bundle_dir = host_dir

            with mock.patch.object(core, "auto_backup_dir", return_value=auto_dir), \
                 mock.patch.object(core, "init_workspace"), \
                 mock.patch.object(core, "resolve_manifest", return_value=(root / "manifest.json", {"profile": "full-home"})), \
                 mock.patch.object(core, "read_passphrase", return_value=""), \
                 mock.patch.object(core, "confirm_step", return_value=True), \
                 mock.patch("omni_core.resolve_installed_inventory_across_dirs", return_value=None), \
                 mock.patch("omni_core.reconcile_host", return_value={"steps": []}) as reconcile_mock:
                result = core.restore_host_cmd(
                    accept_all=True,
                    show_summary=False,
                    auto_backup=False,
                    allow_missing_bundles=True,
                )

        self.assertTrue(result["success"])
        self.assertTrue(result["bootstrap_only"])
        self.assertFalse(result["used_bundles"])
        reconcile_mock.assert_called_once()
        _, kwargs = reconcile_mock.call_args
        self.assertEqual(kwargs["bundle_path"], "")
        self.assertEqual(kwargs["secrets_path"], "")

    def test_restore_host_cmd_hydrates_from_remote_source_in_bootstrap_mode(self):
        core = OmniCore()
        core.servers = [{"name": "main-ubuntu", "host": "172.31.99.10"}]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_dir = root / "host-bundles"
            auto_dir = root / "auto-bundles"
            host_dir.mkdir()
            auto_dir.mkdir()
            core.bundle_dir = host_dir

            with mock.patch.object(core, "auto_backup_dir", return_value=auto_dir), \
                 mock.patch.object(core, "init_workspace"), \
                 mock.patch.object(core, "resolve_manifest", return_value=(root / "manifest.json", {"profile": "full-home"})), \
                 mock.patch.object(core, "read_passphrase", return_value=""), \
                 mock.patch.object(core, "confirm_step", return_value=True), \
                 mock.patch.object(core, "hydrate_from_remote_servers", return_value={"success": True, "results": [{"success": True}]} ) as hydrate_mock, \
                 mock.patch("omni_core.resolve_installed_inventory_across_dirs", return_value=None), \
                 mock.patch("omni_core.reconcile_host", return_value={"steps": []}) as reconcile_mock:
                result = core.restore_host_cmd(
                    accept_all=True,
                    show_summary=False,
                    auto_backup=False,
                    allow_missing_bundles=True,
                )

        self.assertTrue(result["success"])
        hydrate_mock.assert_called_once()
        reconcile_mock.assert_called_once()
        self.assertEqual(result["hydration_result"]["results"][0]["success"], True)

    def test_hydrate_from_remote_servers_uses_host_root_for_full_home_profile(self):
        core = OmniCore()
        core.servers = [{"name": "main-ubuntu", "host": "172.31.99.10", "paths": ["/home/ubuntu/melissa"]}]

        with tempfile.TemporaryDirectory() as tmp:
            host_root = str(Path(tmp) / "source-home")
            target_root = str(Path(tmp) / "restore")
            expanded = [
                {"path": f"{host_root}/melissa", "kind": "dir"},
                {"path": f"{host_root}/nova-os", "kind": "dir"},
            ]
            with mock.patch("omni_core.build_remote_sync_command", return_value="echo ok") as build_mock, \
                 mock.patch.object(core, "list_remote_directory_entries", return_value=expanded) as list_mock, \
                 mock.patch.object(core, "_run_transfer_cmd_visible", return_value=(0, "", "")):
                result = core.hydrate_from_remote_servers(
                    target_root=target_root,
                    manifest={"profile": "full-home", "host_root": host_root},
                )

        list_mock.assert_called_once_with(core.servers[0], host_root)
        self.assertEqual(build_mock.call_count, 2)
        self.assertEqual(build_mock.call_args_list[0][0][1], expanded[0]["path"])
        self.assertEqual(build_mock.call_args_list[1][0][1], expanded[1]["path"])
        self.assertEqual(result["results"][0]["status"], "empty_import")

    def test_hydrate_from_remote_servers_supports_file_entries(self):
        core = OmniCore()
        core.servers = [{"name": "main-ubuntu", "host": "172.31.99.10", "paths": ["/home/ubuntu"]}]

        with tempfile.TemporaryDirectory() as tmp:
            target_root = str(Path(tmp) / "restore")
            file_entry = [{"path": "/home/ubuntu/.bash_history", "kind": "file"}]
            restore_root = Path(target_root)

            def fake_transfer(_cmd, _label):
                file_path = restore_root / "home" / "ubuntu" / ".bash_history"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text("history", encoding="utf-8")
                return 0, "", ""

            with mock.patch.object(core, "list_remote_directory_entries", return_value=file_entry), \
                 mock.patch("omni_core.build_remote_sync_command", return_value="echo ok") as build_mock, \
                 mock.patch.object(core, "_run_transfer_cmd_visible", side_effect=fake_transfer):
                result = core.hydrate_from_remote_servers(
                    target_root=target_root,
                    manifest={"profile": "full-home", "host_root": "/home/ubuntu"},
                )

        self.assertTrue(result["success"])
        self.assertEqual(build_mock.call_args.kwargs["source_kind"], "file")
        self.assertEqual(result["results"][0]["status"], "ok")
        self.assertEqual(result["results"][0]["after"]["entries"], 1)

    def test_hydrate_from_remote_servers_skips_remote_omni_home_target(self):
        core = OmniCore()
        core.servers = [{"name": "main-ubuntu", "host": "172.31.99.10", "paths": [str(Path(core.root_dir))]}]

        with mock.patch.object(core, "_run_transfer_cmd_visible") as transfer_mock:
            result = core.hydrate_from_remote_servers(target_root="/")

        transfer_mock.assert_not_called()
        self.assertEqual(result["results"][0]["status"], "skipped_omni_home")

    def test_hydrate_from_remote_servers_marks_empty_import_as_incomplete(self):
        core = OmniCore()
        core.servers = [{"name": "main-ubuntu", "host": "172.31.99.10", "paths": ["/home/ubuntu/melissa"]}]

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("omni_core.build_remote_sync_command", return_value="echo ok"), \
                 mock.patch.object(core, "_run_transfer_cmd_visible", return_value=(0, "", "")):
                result = core.hydrate_from_remote_servers(target_root=tmp)

        self.assertFalse(result["success"])
        self.assertEqual(result["results"][0]["status"], "empty_import")


if __name__ == "__main__":
    unittest.main()
