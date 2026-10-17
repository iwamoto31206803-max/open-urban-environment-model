"""Synthetic Komae repair checks; never runs local real-data processing."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import venv

import pytest
from shapely.geometry import Polygon, mapping

from ouem import komae_integration as runner
from test_komae_integration import REAL_ROOT, setup, write_json


TARGET = runner.KOMAE_REPAIR_OUEM_ID


def repair_case(tmp_path):
    geometry = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    adapter = tmp_path / "adapter.geojson"
    write_json(adapter, {"features": [{"properties": {"ouem_id": TARGET},
                                       "geometry": mapping(geometry)}]})
    metrics = {key: 1.0 for key in ("source_footprint_area_m2", "before_nominal_area_m2",
              "after_area_m2", "area_change_before_to_after_nominal_m2",
              "area_difference_vs_source_m2", "area_difference_vs_source_percent",
              "symmetric_difference_vs_source_m2", "hausdorff_vs_source_m")}
    metrics.update(crs="EPSG:6677", after_projected_valid=True)
    diagnostic = {"before": {"valid": False, "geometry_type": "Polygon", "polygons": 1, "rings": 1, "vertices": 5},
                  "after": {"valid": True, "geometry_type": "Polygon", "polygons": 1, "rings": 1, "vertices": 5},
                  "projected_comparison": metrics}
    manifest = {"post_crs_repair": {"repaired_count": 1, "affected_ouem_ids": [TARGET]},
                "buildings": [{"ouem_id": TARGET, "post_crs_repair": diagnostic},
                              {"ouem_id": "other"}]}
    return manifest, adapter


def test_komae_repair_evidence_and_projected_metrics(tmp_path):
    manifest, adapter = repair_case(tmp_path)
    checks, evidence = runner.contained_repair_quality(manifest, adapter, [TARGET, "other"])
    assert all(checks.values())
    assert evidence["buildings"][0]["post_crs_repair"]["projected_comparison"]["hausdorff_vs_source_m"] == 1
    assert runner.content_hash(evidence) == runner.content_hash(copy.deepcopy(evidence))


@pytest.mark.parametrize("mutation,failed", [
    (lambda m: m["post_crs_repair"].update(repaired_count=0), "summary"),
    (lambda m: m["post_crs_repair"].update(affected_ouem_ids=["other"]), "summary"),
    (lambda m: m["buildings"][0].pop("post_crs_repair"), "diagnostics"),
    (lambda m: m["buildings"][1].update(post_crs_repair={}), "diagnostics"),
    (lambda m: m["buildings"][0]["post_crs_repair"]["projected_comparison"].update(crs="EPSG:4326"), "projected_metrics"),
    (lambda m: m["buildings"][0]["post_crs_repair"]["projected_comparison"].update(hausdorff_vs_source_m=float("nan")), "projected_metrics"),
    (lambda m: m["buildings"][0]["post_crs_repair"]["after"].update(geometry_type="GeometryCollection"), "geometry"),
])
def test_komae_repair_rejects_missing_extra_or_invalid_evidence(tmp_path, mutation, failed):
    manifest, adapter = repair_case(tmp_path)
    mutation(manifest)
    checks, _ = runner.contained_repair_quality(manifest, adapter, [TARGET, "other"])
    assert checks[failed] is False


def test_komae_repair_rejects_invalid_output_geometry(tmp_path):
    manifest, adapter = repair_case(tmp_path)
    document = runner.read_json(adapter)
    document["features"][0]["geometry"] = mapping(Polygon([(0, 0), (1, 1), (0, 1), (1, 0)]))
    write_json(adapter, document)
    checks, _ = runner.contained_repair_quality(manifest, adapter, [TARGET, "other"])
    assert checks["geometry"] is False


def test_top_level_repair_summary_changes_repeat_semantics(setup, monkeypatch):
    original = setup.execute
    def execute(command, log, **kwargs):
        result = original(command, log, **kwargs)
        if "repeat-2-a3" in str(log):
            path = runner.adjacent(Path(command[command.index("--adapter-output") + 1]))
            manifest = runner.read_json(path)
            manifest["post_crs_repair"] = {"repaired_count": 1, "affected_ouem_ids": [TARGET]}
            write_json(path, manifest)
        return result
    monkeypatch.setattr(runner, "execute", execute)
    assert runner.run(setup.args) == 1
    report = runner.read_json(setup.report)
    assert report["quality"] == "PASS" and report["reproducibility"] == "FAIL"
    assert report["comparisons"]["adapter_semantics_sha256"] is False


@pytest.mark.parametrize("name", ["CON", "LPT1", "bad.name", "bad name", "é", "a" * 65])
def test_contained_runner_rejects_nonportable_ids_before_creating_run(setup, name):
    setup.args.contained_poc = True
    setup.args.run_dir = str(setup.repo / "data/work/integration" / name)
    with pytest.raises(runner.Blocked, match="portable"):
        runner.run(setup.args)
    assert not Path(setup.args.run_dir).exists()
    assert not setup.commands


def test_windows_launcher_has_canonical_inputs_and_runner_guards():
    launcher = REAL_ROOT / "scripts/work/run_komae_contained_e2e.cmd"
    source = launcher.read_text(encoding="utf-8")
    for value in ("%~dp0", ".venv\\Scripts\\python.exe", "-m ouem.komae_integration run",
                  "--contained-poc", "--expected-buildings 92", "--expected-native-buildings 3637",
                  "--meshsize 1", "data\\native\\building\\komae.gpkg",
                  "data\\native\\terrain\\komae_09LD3451.json",
                  "data\\standard\\building\\komae.gpkg",
                  "config\\study_areas\\komae_09LD3451.yaml",
                  "scripts\\work\\.runtime\\plateau_komae_gis.json",
                  "data\\work\\integration\\!OUEM_RUN_ID!", "integration-report.json", "exit /b %RUN_EXIT%"):
        assert value in source
    assert "data\\work\\integration\\%~1" not in source
    assert source.index("sys.exit(0 if re.fullmatch") < source.index("if exist \"data\\work\\integration\\!OUEM_RUN_ID!\"")


@pytest.fixture(scope="module")
def windows_launcher(tmp_path_factory):
    if os.name != "nt":
        pytest.skip("cmd.exe launcher executes only on Windows")
    tmp_path = tmp_path_factory.mktemp("launcher")
    repo = tmp_path / "synthetic-repo"
    scripts = repo / "scripts/work"
    scripts.mkdir(parents=True)
    shutil.copy2(REAL_ROOT / "scripts/work/run_komae_contained_e2e.cmd", scripts)
    venv.EnvBuilder(with_pip=False).create(repo / ".venv")
    package = repo / "ouem"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "komae_integration.py").write_text(
        "import pathlib, sys\n"
        "args=sys.argv[1:]\n"
        "assert args[0]=='run' and '--contained-poc' in args\n"
        "out=pathlib.Path(args[args.index('--run-dir')+1])\n"
        "out.mkdir(parents=True)\n"
        "(out/'integration-report.json').write_text('{}')\n"
        "sys.exit(7)\n", encoding="utf-8")
    return repo, scripts / "run_komae_contained_e2e.cmd"


def test_windows_launcher_preserves_runner_exit_and_displays_report(tmp_path, windows_launcher):
    repo, launcher = windows_launcher
    result = subprocess.run(["cmd", "/d", "/c", str(launcher), "fresh-run"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 7
    assert "integration-report.json" in result.stdout
    assert (repo / "data/work/integration/fresh-run/integration-report.json").exists()
    again = subprocess.run(["cmd", "/d", "/c", str(launcher), "fresh-run"],
                           cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert again.returncode == 2


@pytest.mark.parametrize("unsafe", ["bad&name", "bad|name", "bad>name", "bad<name",
                                    "bad^name", "bad%name", "bad!name", "bad.name",
                                    "bad name", 'bad"name', "CON", "a" * 65])
def test_windows_launcher_rejects_unsafe_run_id_without_side_effects(tmp_path, windows_launcher, unsafe):
    repo, launcher = windows_launcher
    runs = repo / "data/work/integration"
    before = set(runs.iterdir()) if runs.exists() else set()
    result = subprocess.run(["cmd", "/d", "/c", str(launcher), unsafe],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, (unsafe, result.stdout, result.stderr)
    assert (set(runs.iterdir()) if runs.exists() else set()) == before


def test_windows_launcher_rejects_embedded_quote_injection(tmp_path, windows_launcher):
    repo, launcher = windows_launcher
    runs = repo / "data/work/integration"
    before = set(runs.iterdir()) if runs.exists() else set()
    marker = tmp_path / "injected.txt"
    payload = f'bad" & echo INJECTED>"{marker}" & rem "'
    result = subprocess.run(["cmd", "/d", "/c", str(launcher), payload],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert not marker.exists()
    assert not (repo / "injected.txt").exists()
    assert (set(runs.iterdir()) if runs.exists() else set()) == before
