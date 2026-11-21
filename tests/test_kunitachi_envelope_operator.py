"""Run the Kunitachi operator's synthetic checks on Windows."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows operator wrapper")
def test_kunitachi_envelope_operator():
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell 7 is unavailable")

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            pwsh, "-NoProfile", "-NonInteractive", "-File",
            str(root / "tests/kunitachi_envelope_operator.ps1"),
            "-RunnerPath",
            str(root / "scripts/operations/run_kunitachi_envelope.ps1"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Synthetic operator checks PASS" in result.stdout
