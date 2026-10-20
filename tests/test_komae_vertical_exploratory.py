"""Synthetic exploratory diagnosis: byte mismatch is visible, never accepted."""
import json
import os
from pathlib import Path
import subprocess

import geopandas as gpd
import pytest

from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem import komae_vertical_exploratory as exploratory
from tests.test_komae_geometry_provenance import SOURCE_ID, tree_bytes
from tests.test_komae_vertical_provenance import _saved_run


def _run_with_baseline(tmp_path):
    root, city = _saved_run(tmp_path, 24.44)
    report_path = root / "integration-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["repeats"] = []
    for number in (1, 2):
        command = provenance.command(report, number, "a1")
        full = Path(provenance.option(command, "--output"))
        frame = gpd.read_file(full, layer="standard_surfaces")
        report["repeats"].append({"comparison_evidence": {
            "full_a1_building": runner.building_frame_semantics(frame)}})
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return root, city


def _full(root, number):
    report = runner.read_json(root / "integration-report.json")
    return Path(provenance.option(provenance.command(report, number, "a1"), "--output"))


def test_extra_z_min_attribute_is_exploratory_but_semantically_equal(tmp_path):
    root, city = _run_with_baseline(tmp_path)
    full = _full(root, 1)
    frame = gpd.read_file(full, layer="standard_surfaces")
    frame["z_min"] = 20.0
    frame.to_file(full, layer="standard_surfaces", driver="GPKG")
    before = tree_bytes(tmp_path)
    report = exploratory.diagnose_run(root, SOURCE_ID[:10], city)
    assert tree_bytes(tmp_path) == before
    assert report["byte_provenance"]["status"] == "MISMATCH_EXPLORATORY"
    assert any(item["path"] == str(full) for item in report["byte_provenance"]["mismatches"])
    assert report["geometry_semantics"]["status"] == "MATCH_RECORDED_AND_REPEATS"
    assert report["geometry_semantics"]["full_a1"][0]["extra_columns"] == ["z_min"]
    assert report["vertical_coordinate_diagnosis"]["first_z_max_change"] == "citygml_to_converter"
    assert report["vertical_coordinate_diagnosis"]["status"] == "EXPLORATORY"
    assert report["root_cause"]["status"] == "UNRESOLVED"


def test_modified_geometry_is_not_labeled_semantically_equal(tmp_path):
    root, city = _run_with_baseline(tmp_path)
    full = _full(root, 1)
    frame = gpd.read_file(full, layer="standard_surfaces")
    from shapely import transform
    frame.geometry = frame.geometry.map(lambda shape: transform(
        shape, lambda coords: coords + [1, 0, 0], include_z=True))
    frame.to_file(full, layer="standard_surfaces", driver="GPKG")
    report = exploratory.diagnose_run(root, SOURCE_ID[:10], city)
    assert report["geometry_semantics"]["status"] == "MISMATCH_REPEATS"
    assert report["byte_provenance"]["status"] == "MISMATCH_EXPLORATORY"
    assert report["vertical_coordinate_diagnosis"]["status"] == "PARTIAL_EXPLORATORY"
    assert report["vertical_coordinate_diagnosis"]["repeats"][0]["lineage_issues"]
    assert report["root_cause"]["status"] == "UNRESOLVED"


def test_missing_target_and_changed_during_read_block(tmp_path, monkeypatch):
    root, city = _run_with_baseline(tmp_path)
    with pytest.raises(provenance.Inconclusive, match="target ID"):
        exploratory.diagnose_run(root, "missing-id", city)
    original = exploratory.ExploratoryEvidence.finish
    def changed(self):
        next(iter(self.before.values()))["sha256"] = "0" * 64
        return original(self)
    monkeypatch.setattr(exploratory.ExploratoryEvidence, "finish", changed)
    with pytest.raises(runner.Blocked, match="changed"):
        exploratory.diagnose_run(root, SOURCE_ID[:10], city)


def test_launcher_uses_venv_and_two_arguments():
    launcher = Path(__file__).resolve().parents[1] / "scripts/work/diagnose_komae_vertical_exploratory.cmd"
    source = launcher.read_text(encoding="utf-8")
    assert 'setlocal DisableDelayedExpansion' in source
    assert 'setlocal EnableDelayedExpansion' in source
    assert '".venv\\Scripts\\python.exe" -B -m ouem.komae_vertical_exploratory' in source
    assert "OUEM_EXPLORATORY_EXTRA" in source


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe launcher executes only on Windows")
@pytest.mark.parametrize("arguments", [(), ("run",), ("run", "target", "extra"),
                                      ("unsafe&run", "target"), ("run", "bad|target")])
def test_windows_launcher_rejects_invalid_arguments(arguments):
    launcher = Path(__file__).resolve().parents[1] / "scripts/work/diagnose_komae_vertical_exploratory.cmd"
    result = subprocess.run(["cmd.exe", "/d", "/c", str(launcher), *arguments],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
