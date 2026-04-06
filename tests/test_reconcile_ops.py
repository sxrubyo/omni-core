import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reconcile_ops import build_compose_up_command, detect_compose_command  # noqa: E402


class ReconcileOpsTests(unittest.TestCase):
    def test_detect_compose_command_prefers_plugin(self):
        with mock.patch("reconcile_ops.command_exists", side_effect=lambda name: name == "docker"), \
             mock.patch("reconcile_ops.run_cmd", return_value=(0, "Docker Compose version v2.27.0", "")):
            self.assertEqual(detect_compose_command(), "docker compose")

    def test_detect_compose_command_falls_back_to_docker_compose(self):
        def fake_exists(name: str) -> bool:
            return name in {"docker", "docker-compose"}

        with mock.patch("reconcile_ops.command_exists", side_effect=fake_exists), \
             mock.patch("reconcile_ops.run_cmd", return_value=(1, "", "unknown shorthand flag: 'f' in -f")):
            self.assertEqual(detect_compose_command(), "docker-compose")

    def test_build_compose_up_command_uses_classic_binary_when_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            compose_file = Path(tmp) / "docker-compose.yml"
            compose_file.write_text("services: {}\n", encoding="utf-8")

            with mock.patch("reconcile_ops.detect_compose_command", return_value="docker-compose"):
                command = build_compose_up_command(compose_file)

            self.assertEqual(command, f"docker-compose -f {str(compose_file)} up -d --build")


if __name__ == "__main__":
    unittest.main()
