"""Helper orchestration/preflight tests; no real Standard regeneration."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ouem import terrain_local_acceptance as helper


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    source = tmp_path / "Tama Raw with spaces" / "09LD3451.tif"
    source.parent.mkdir()
    source.write_bytes(b"synthetic identified input")
    monkeypatch.setattr(helper, "TIFF_SHA256", hashlib.sha256(source.read_bytes()).hexdigest())
    monkeypatch.setattr(helper, "validate_original", lambda path: {"synthetic": True})
    return source, tmp_path / "fresh outputs" / "run"


def test_check_plans_correct_provenance_without_processing(inputs, monkeypatch):
    source, out = inputs
    def forbidden(*args, **kwargs):
        pytest.fail("Read-only preflight must not execute subprocesses")
    monkeypatch.setattr(helper.subprocess, "run", forbidden)
    report = helper.run(source, out, check=True)
    assert not out.parent.exists()
    assert source.read_bytes() == b"synthetic identified input"
    assert report["status"] == "READY_FOR_LOCAL_PROCESSING_NOT_ACCEPTED"
    test, native, standard = report["commands"]
    assert test == [sys.executable, "-m", "pytest", "-q"]
    assert native[2:4] == ["ouem.native.terrain", str(source)]
    assert native[native.index("--vertical-reference-status") + 1] == "source-declared"
    assert native[native.index("--vertical-reference") + 1] == helper.VERTICAL_NAME
    evidence = native[native.index("--vertical-reference-source") + 1]
    assert "Tama" in evidence and "t000029d0000000020" in evidence and "23-ku" not in evidence
    assert native[native.index("--output") + 1] == str(out / "native.json")
    assert standard[2:4] == ["ouem.standardize.terrain", str(out / "native.json")]
    assert standard[standard.index("--output") + 1] == str(out / "standard.tif")


@pytest.mark.parametrize("existing", ["directory", "file", "manifest"])
def test_existing_outputs_refused_unchanged(inputs, existing):
    source, out = inputs
    out.parent.mkdir()
    if existing == "file":
        out.write_bytes(b"keep file")
    else:
        out.mkdir()
        if existing == "manifest":
            (out / "native.json").write_bytes(b"keep historical manifest")
    before = [(p, p.read_bytes()) for p in out.parent.rglob("*") if p.is_file()]
    with pytest.raises(ValueError, match="must be new"):
        helper.preflight(source, out)
    assert all(p.read_bytes() == data for p, data in before)


@pytest.mark.parametrize("missing", [False, True])
def test_wrong_or_missing_source_blocks_before_outputs(inputs, missing):
    source, out = inputs
    if missing:
        source.unlink()
    else:
        source.write_bytes(b"different candidate")
    with pytest.raises(ValueError, match="SHA-256"):
        helper.preflight(source, out)
    assert not out.parent.exists()


def test_execution_calls_unchanged_clis_and_uses_fresh_paths(inputs, monkeypatch):
    source, out = inputs
    calls = []
    def execute(command, *, cwd, check):
        assert cwd == helper.ROOT and check is True
        calls.append(command)
    monkeypatch.setattr(helper.subprocess, "run", execute)
    report = helper.run(source, out)
    assert calls == report["commands"]
    assert report["status"] == "PROCESSING_COMPLETED_PENDING_REVIEW"
    assert out.is_dir()
    assert source.read_bytes() == b"synthetic identified input"


def test_failed_tests_do_not_create_output_run(inputs, monkeypatch):
    source, out = inputs
    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(helper.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        helper.run(source, out)
    assert not out.parent.exists()


def test_source_is_rechecked_after_tests(inputs, monkeypatch):
    source, out = inputs
    monkeypatch.setattr(helper.subprocess, "run", lambda *a, **kw: source.write_bytes(b"changed during tests"))
    with pytest.raises(ValueError, match="SHA-256"):
        helper.run(source, out)
    assert not out.parent.exists()


def test_cli_check_and_failure_status(inputs, monkeypatch, capsys):
    source, out = inputs
    assert helper.main([str(source), "--run-dir", str(out), "--check"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "READY_FOR_LOCAL_PROCESSING_NOT_ACCEPTED"
    source.unlink()
    assert helper.main([str(source), "--run-dir", str(out), "--check"]) == 2
    assert "FAILED" in capsys.readouterr().err


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe launcher executes only on Windows")
def test_windows_launcher_requires_explicit_arguments_and_checks_without_writes(inputs):
    source, out = inputs
    launcher = helper.ROOT / "scripts/work/terrain_komae_local_acceptance.cmd"
    result = subprocess.run(["cmd", "/d", "/c", str(launcher)], cwd=helper.ROOT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2 and "required" in result.stderr
    # A separate process uses the real fixed hash, so synthetic bytes must fail.
    result = subprocess.run(["cmd", "/d", "/c", str(launcher), str(source),
                             "--run-dir", str(out), "--check"], cwd=helper.ROOT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2 and "SHA-256" in result.stderr
    assert not out.parent.exists()
