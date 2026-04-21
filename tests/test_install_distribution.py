from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path("/home/ubuntu/omni-core")
INSTALL_SCRIPT = REPO_ROOT / "install.sh"


class InstallDistributionTests(unittest.TestCase):
    def test_install_script_supports_local_repo_override_and_creates_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            local_bin = home / ".local" / "bin"
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = f"{local_bin}:{env['PATH']}"
            env["OMNI_INSTALL_LOCAL_REPO"] = str(REPO_ROOT)
            env["OMNI_INSTALL_SKIP_DEPENDENCY_BOOTSTRAP"] = "1"

            result = subprocess.run(
                ["bash", str(INSTALL_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

            wrapper = local_bin / "omni"
            self.assertTrue(wrapper.exists())
            self.assertTrue(wrapper.stat().st_mode & stat.S_IXUSR)

            help_result = subprocess.run(
                [str(wrapper), "help"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(help_result.returncode, 0, msg=help_result.stderr or help_result.stdout)
            self.assertIn("Omni Core - Command Reference", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
