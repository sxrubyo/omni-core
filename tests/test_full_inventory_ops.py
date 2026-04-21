import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_inventory_ops import collect_full_inventory  # noqa: E402
from platform_ops import PlatformInfo  # noqa: E402


class FullInventoryOpsTests(unittest.TestCase):
    def test_collect_full_inventory_captures_dotfiles_public_keys_and_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home_root = Path(tmp)
            (home_root / ".ssh").mkdir()
            (home_root / ".ssh" / "id_ed25519.pub").write_text("ssh-ed25519 AAAATEST user@test\n", encoding="utf-8")
            (home_root / ".bashrc").write_text("export TEST=1\n", encoding="utf-8")
            (home_root / ".gitconfig").write_text("[user]\n\tname = Omni\n", encoding="utf-8")

            platform_info = PlatformInfo(
                system="linux",
                release="6.8.0",
                version="test",
                machine="x86_64",
                shell="bash",
                shell_family="posix",
                package_manager="apt-get",
                interactive=True,
                home=str(home_root),
                terminal="xterm-256color",
            )

            command_map = {
                ("dpkg-query", "-W", "-f=${binary:Package}\n"): "git\nrsync\n",
                ("python3", "-m", "pip", "list", "--format=json"): '[{"name":"rich","version":"15.0.0"}]',
                ("npm", "list", "-g", "--depth=0", "--json"): '{"dependencies":{"pm2":{"version":"5.4.0"}}}',
                ("cargo", "install", "--list"): "ripgrep v14.0.0:\n    rg\n",
                ("brew", "list", "--formula"): "wget\n",
                ("brew", "list", "--cask"): "visual-studio-code\n",
                ("snap", "list"): "Name Version Rev Tracking Publisher Notes\nlxd 5.0 1 latest/stable canonical -\n",
                ("flatpak", "list", "--app", "--columns=application"): "com.visualstudio.code\n",
                ("code", "--list-extensions"): "ms-python.python\n",
                ("git", "config", "--global", "--list"): "user.name=Omni\nuser.email=omni@example.com\n",
                ("crontab", "-l"): "0 * * * * /usr/bin/true\n",
                ("systemctl", "list-unit-files", "--type=service", "--state=enabled", "--no-pager"): "UNIT FILE STATE PRESET\nssh.service enabled enabled\n",
                ("docker", "ps", "-a", "--format", "{{json .}}"): '{"Image":"postgres:16","Names":"db"}',
                ("docker", "images", "--format", "{{json .}}"): '{"Repository":"postgres","Tag":"16"}',
            }

            def fake_run(args, *, timeout=120):
                return command_map.get(tuple(args), "")

            with mock.patch("full_inventory_ops._run", side_effect=fake_run):
                payload = collect_full_inventory(home_root=str(home_root), platform_info=platform_info)

            self.assertEqual(payload["packages"]["system"], ["git", "rsync"])
            self.assertEqual(payload["packages"]["python"], ["rich==15.0.0"])
            self.assertEqual(payload["packages"]["node_global"], ["pm2"])
            self.assertEqual(payload["packages"]["cargo"], ["ripgrep"])
            self.assertEqual(payload["vscode_extensions"], ["ms-python.python"])
            self.assertEqual(payload["git"]["global_config"]["user.name"], "Omni")
            self.assertEqual(len(payload["ssh"]["public_keys"]), 1)
            self.assertEqual(len(payload["dotfiles"]), 2)
            self.assertEqual(payload["cron"]["user"], ["0 * * * * /usr/bin/true"])
            self.assertEqual(payload["systemd"]["enabled_services"], ["ssh.service"])
            self.assertEqual(payload["counts"]["docker_containers"], 1)


if __name__ == "__main__":
    unittest.main()
