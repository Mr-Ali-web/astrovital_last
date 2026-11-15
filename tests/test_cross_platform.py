"""Cross-platform startup checks that do not require a Windows runner."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import start


class CrossPlatformLauncherTests(unittest.TestCase):
    def test_virtualenv_python_path_windows(self):
        self.assertEqual(str(start.venv_python(Path("C:/AstroMed/.venv-windows"), True)).replace("\\", "/"),
                         "C:/AstroMed/.venv-windows/Scripts/python.exe")

    def test_virtualenv_python_path_linux(self):
        self.assertEqual(start.venv_python(Path("/tmp/AstroMed/.venv-linux"), False),
                         Path("/tmp/AstroMed/.venv-linux/bin/python"))

    def test_windows_and_linux_scripts_present(self):
        self.assertTrue((ROOT / "run_windows.bat").is_file())
        self.assertTrue((ROOT / "run_linux.sh").is_file())
        self.assertTrue((ROOT / "requirements.txt").is_file())
        self.assertIn('cd /d "%~dp0"', (ROOT / "run_windows.bat").read_text())
        self.assertIn('"$@"', (ROOT / "run_linux.sh").read_text())

    @patch.object(start, "prepare_environment", return_value=Path("/venv/python"))
    def test_install_only_does_not_start_server(self, prepare):
        self.assertEqual(start.main(["--install-only", "--offline"]), 0)
        prepare.assert_called_once_with(offline=True)

    @patch.object(start, "prepare_environment", side_effect=RuntimeError("dependencies unavailable"))
    def test_missing_offline_deps_fails_closed(self, prepare):
        self.assertEqual(start.main(["--offline"]), 1)
        prepare.assert_called_once_with(offline=True)

    @patch.object(start.subprocess, "Popen")
    @patch.object(start, "prepare_environment", return_value=Path("/env/python"))
    def test_only_localhost_is_exposed(self, _prepare, popen):
        popen.return_value.wait.return_value = 0
        self.assertEqual(start.main(["--no-browser", "--port", "8118"]), 0)
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd[cmd.index("--host") + 1], "127.0.0.1")
        self.assertEqual(cmd[cmd.index("--port") + 1], "8118")

    def test_port_validation_happens_before_install(self):
        with patch.object(start, "prepare_environment") as prepare:
            with self.assertRaises(SystemExit):
                start.main(["--port", "0"])
            prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
