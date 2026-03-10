import subprocess
import sys
import unittest
from pathlib import Path


class TestObsScript(unittest.TestCase):
    def test_obs_demo_script_runs_without_import_error(self):
        script_path = Path(__file__).resolve().parents[1] / "src" / "obs" / "testObs.py"

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
