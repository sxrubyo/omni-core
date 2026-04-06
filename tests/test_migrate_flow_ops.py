import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omni_core import OmniCore  # noqa: E402


class MigrateFlowOpsTests(unittest.TestCase):
    def test_migrate_host_cmd_stops_when_restore_fails(self):
        core = OmniCore()

        with mock.patch.object(core, "restore_host_cmd", return_value={"success": False}), \
             mock.patch.object(core, "run_backup") as backup_mock, \
             mock.patch("omni_core.render_action_summary") as render_mock:
            core.migrate_host_cmd(accept_all=True)

        backup_mock.assert_not_called()
        render_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
