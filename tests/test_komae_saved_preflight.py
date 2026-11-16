import hashlib
import json

import pytest

from ouem import komae_saved_preflight as audit, real_komae_solar as solar
from ouem.native.building.source_h_geometry import GeometryValidationError


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    def write(name, content):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = content if isinstance(content, bytes) else json.dumps(content).encode()
        path.write_bytes(data)
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

    def forbidden(*args, **kwargs):
        pytest.fail("model execution or data parser called")

    for name in ("run", "integrate_canopy", "solar_pair", "export", "preflight", "sample_canopy"):
        monkeypatch.setattr(solar, name, forbidden)

    grid = {"shape": [128, 128, 27], "layout": "uv_m/SOUTH_UP",
            "D0_effective_H_m": 19.586000442504883}
    terrain = write("terrain.tif", b"synthetic terrain identity only")
    base_voxels = write("base/voxels.npy", b"synthetic base identity only")
    implementation = write("src/voxel.py", b"historical voxel implementation")
    roi_definition = write("src/config.py", b"historical ROI implementation")
    solar_implementation = write("src/solar.py", b"historical solar implementation")
    (tmp_path / implementation["path"]).write_bytes(b"modern voxel implementation")
    (tmp_path / roi_definition["path"]).unlink()
    (tmp_path / solar_implementation["path"]).write_bytes(b"modern solar implementation")
    base = write("base/report.json", {
        "status": "COMPLETED", "input_immutability": "PASS",
        "model": {"grid": grid, "numba": True}, "consumer": {"technical_validation": "PASS"},
        "input_artifacts": {"terrain": terrain, "implementation": implementation,
                            "roi_definition": roi_definition}, "outputs": {"voxels.npy": base_voxels},
    })
    envelope = write("envelope/manifest.json", {
        "status": "COMPLETED", "schema": "ouem-height-envelope-poc/v0.1",
        "cr_model": {"parameters": {"cr": .6}}, "outputs": {},
        "input_files": {"terrain": dict(terrain, bytes=terrain["size_bytes"])},
    })
    outputs = {
        "grid.json": write("final/grid.json", grid),
        "current_voxels.npy": write("final/current_voxels.npy", b"synthetic current"),
        "no_canopy_voxels.npy": write("final/no_canopy_voxels.npy", b"synthetic base identity only"),
    }
    report = {
        "status": "COMPLETED", "input_immutability": "PASS",
        "preflight": {"status": "PASS", "source_model_report_sha256": base["sha256"], "source_CR": .6},
        "environment": {"voxcity": {"verified": True, "version": "1.7.0", "commit": audit.ENGINE_COMMIT}},
        "input_artifacts": {"PR98_report": base, "envelope_manifest": envelope,
                            "envelope_input:terrain": terrain,
                            "implementation": solar_implementation,
                            "base_input:implementation": dict(implementation),
                            "base_input:roi_definition": dict(roi_definition)}, "outputs": outputs,
    }

    base_sha, envelope_sha = base["sha256"], envelope["sha256"]

    def verify():
        final = write("final/report.json", report)
        snapshot = lambda: {p.relative_to(tmp_path): p.read_bytes() if p.is_file() else None
                            for p in tmp_path.rglob("*") if not p.is_symlink()}
        before = snapshot()
        result = audit._verify(tmp_path, final["path"], final["sha256"], base_sha,
                               envelope_sha, {k: v["sha256"] for k, v in outputs.items()})
        assert snapshot() == before
        return result

    return report, verify


def test_saved_identity_only(fixture):
    _, verify = fixture
    result = verify()
    assert result["status"] == "PASS"
    assert result["historical_code"] == "RECORDED_METADATA_ONLY"
    assert result["semantic_revalidation"] == "NOT_EXECUTED"


@pytest.mark.parametrize("problem", ["nonfinal", "stale_base", "stale_envelope", "missing",
                                     "hash", "escape", "symlink", "hardlink", "changed"])
def test_saved_identity_fails_closed(tmp_path, fixture, problem, monkeypatch):
    report, verify = fixture
    current = tmp_path / "final/current_voxels.npy"
    if problem == "nonfinal":
        report["status"] = "RUNNING"
    elif problem == "stale_base":
        report["input_artifacts"]["PR98_report"]["sha256"] = "0" * 64
    elif problem == "stale_envelope":
        report["input_artifacts"]["envelope_manifest"]["sha256"] = "0" * 64
    elif problem == "missing":
        current.unlink()
    elif problem == "hash":
        current.write_bytes(b"changed")
    elif problem == "escape":
        report["input_artifacts"]["terrain"] = dict(report["input_artifacts"]["envelope_input:terrain"],
                                                    path="../terrain.tif")
    elif problem in ("symlink", "hardlink"):
        target = current.with_name("target.npy")
        current.rename(target)
        try:
            if problem == "symlink":
                current.symlink_to(target)
            else:
                current.hardlink_to(target)
        except OSError:
            pytest.skip("link creation unavailable")
    else:
        scan = audit.FrozenWatch.scan

        def change_after_capture(self, locator, **kwargs):
            result = scan(self, locator, **kwargs)
            if locator == "final/current_voxels.npy" and not getattr(self, "changed", False):
                self.changed = True
                current.write_bytes(b"changed after capture")
            return result

        monkeypatch.setattr(audit.FrozenWatch, "scan", change_after_capture)

    with pytest.raises((GeometryValidationError, FileNotFoundError)):
        verify()


def test_cli_redacts_errors(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(audit.sys, "dont_write_bytecode", True)
    assert audit.main(["--artifact-root", str(tmp_path), "--final-report", "missing.json"]) == 1
    stdout = capsys.readouterr().out
    assert json.loads(stdout)["status"] == "BLOCKED"
    assert str(tmp_path) not in stdout


@pytest.mark.parametrize("key,field,value", [
    ("implementation", "sha256", "0" * 64),
    ("roi_definition", "size_bytes", 0),
    ("roi_definition", "path", "src/other.py"),
])
def test_conflicting_historical_code_records_block(fixture, key, field, value):
    report, verify = fixture
    report["input_artifacts"]["base_input:" + key][field] = value
    with pytest.raises(GeometryValidationError, match="PR #98 and PR #99 records differ"):
        verify()


def test_changed_data_still_blocks(tmp_path, fixture):
    _, verify = fixture
    (tmp_path / "terrain.tif").write_bytes(b"changed source terrain")
    with pytest.raises(GeometryValidationError, match="SHA-256 mismatch"):
        verify()
