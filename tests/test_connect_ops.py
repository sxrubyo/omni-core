import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from connect_ops import SSHDestination, build_rsync_command, build_sftp_command, parse_remote_probe_output  # noqa: E402


class ConnectOpsTests(unittest.TestCase):
    def test_parse_remote_probe_output_detects_fresh_server(self):
        payload = parse_remote_probe_output(
            "system=Linux\npackage_manager=apt-get\nhome_entries=2\ngit_repos=0\npackage_count=80\nfresh_server=true\n"
        )
        self.assertEqual(payload["system"], "Linux")
        self.assertEqual(payload["package_manager"], "apt-get")
        self.assertTrue(payload["fresh_server"])

    def test_build_rsync_command_uses_ssh_port_and_identity(self):
        destination = SSHDestination(host="example.com", user="ubuntu", port=2222, key_path="/tmp/id_ed25519")
        command = build_rsync_command(["/tmp/briefcase.json"], destination, remote_path="~/omni-transfer")
        self.assertEqual(command[0], "rsync")
        self.assertIn("ssh -p 2222 -i /tmp/id_ed25519", command)
        self.assertEqual(command[-1], "ubuntu@example.com:~/omni-transfer/")

    def test_build_sftp_command_creates_batch(self):
        destination = SSHDestination(host="example.com", user="ubuntu")
        command, batch = build_sftp_command(["/tmp/briefcase.json"], destination, remote_path="~/omni-transfer")
        self.assertEqual(command[0], "sftp")
        self.assertIn("put /tmp/briefcase.json", batch)


if __name__ == "__main__":
    unittest.main()

