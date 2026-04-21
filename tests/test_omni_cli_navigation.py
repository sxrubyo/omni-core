import os
import pty
import select
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omni_core import apply_digit_jump, ALIASES  # noqa: E402


class OmniCliNavigationTests(unittest.TestCase):
    def test_apply_digit_jump_waits_for_multidigit_indexes(self) -> None:
        buffer, selected, should_return = apply_digit_jump("", "1", option_count=16)
        self.assertEqual(buffer, "1")
        self.assertEqual(selected, 0)
        self.assertFalse(should_return)

        buffer, selected, should_return = apply_digit_jump(buffer, "4", option_count=16)
        self.assertEqual(buffer, "")
        self.assertEqual(selected, 13)
        self.assertTrue(should_return)

    def test_apply_digit_jump_immediately_selects_unambiguous_option(self) -> None:
        buffer, selected, should_return = apply_digit_jump("", "9", option_count=16)
        self.assertEqual(buffer, "")
        self.assertEqual(selected, 8)
        self.assertTrue(should_return)

    def test_commands_alias_routes_to_help(self) -> None:
        self.assertEqual(ALIASES["commands"], "help")

    def test_select_menu_redraws_in_place_when_navigation_changes(self) -> None:
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(SRC)!r})
            from omni_core import select_menu
            try:
                select_menu(
                    ["SSH Connect", "Maleta", "Restore", "Migrate Sync", "Doctor"],
                    title="¿Qué quieres hacer primero?",
                    descriptions=["uno", "dos", "tres", "cuatro", "cinco"],
                    default=3,
                    show_index=True,
                    footer="↑/↓ elegir flujo · Enter confirmar · número salto directo",
                )
            except KeyboardInterrupt:
                pass
            """
        )

        master, slave = pty.openpty()
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
        )
        os.close(slave)
        captured = bytearray()

        def drain_until(marker: str, timeout: float) -> bool:
            deadline = time.time() + timeout
            while time.time() < deadline:
                ready, _, _ = select.select([master], [], [], 0.1)
                if master not in ready:
                    if proc.poll() is not None and marker.encode() not in captured:
                        break
                    continue
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                captured.extend(chunk)
                if marker.encode() in captured:
                    return True
            return marker.encode() in captured

        try:
            self.assertTrue(
                drain_until("número salto directo", 1.5),
                captured.decode("utf-8", errors="ignore"),
            )
            self.assertIsNone(proc.poll(), captured.decode("utf-8", errors="ignore"))
            os.write(master, b"\x1b[B")
            self.assertTrue(
                drain_until("\x1b[16F", 1.5),
                captured.decode("utf-8", errors="ignore"),
            )
            os.write(master, b"\x03")
            drain_until("Doctor", 0.5)
            proc.wait(timeout=1)
        finally:
            if proc.poll() is None:
                proc.kill()
            try:
                os.close(master)
            except OSError:
                pass

        rendered = captured.decode("utf-8", errors="ignore")
        self.assertIn("\x1b[16F", rendered)
        self.assertIn("Doctor", rendered)


if __name__ == "__main__":
    unittest.main()
