"""Synthetic saved-run export tests; no Komae real data is read."""
import json
import os
from pathlib import Path
import subprocess
import venv

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import Point
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from ouem import komae_canopy_qgis_export as exporter
from ouem import komae_integration as runner


def _rectangle():
    transformer = Transformer.from_crs(6677, 4326, always_xy=True)
    return [transformer.transform(*xy) for xy in
            ((-23600, -40800), (-23596, -40800), (-23596, -40796), (-23600, -40796))]


def _synthetic_run(tmp_path):
    from voxcity.geoprocessor.raster import create_dem_grid_from_geotiff_polygon
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords
    root = tmp_path / "saved-run"
    root.mkdir()
    rectangle = _rectangle()
    grid = compute_cell_center_coords(rectangle, 1)
    nx, ny = grid["grid_size"]
    assert nx > 1 and ny > 1
    dem_data = np.full((12, 12), 20, dtype="float32")
    terrain = root / "terrain-source.tif"
    with rasterio.open(terrain, "w", driver="GTiff", height=12, width=12,
                       count=1, dtype="float32", crs="EPSG:6677",
                       transform=from_origin(-23604, -40792, 1, 1)) as dst:
        dst.write(dem_data, 1)
    dem = create_dem_grid_from_geotiff_polygon(terrain, 1, rectangle, dem_interpolation=False)
    assert np.isfinite(dem).all()
    current = np.zeros((nx, ny, 5), dtype=np.int8)
    bare = np.zeros_like(current)
    current[:, :, 0] = bare[:, :, 0] = 1
    current[0, 0, 2:4] = -2
    current[nx - 1, ny - 1, 3] = -2
    current[0, 1, 1] = bare[0, 1, 1] = -3
    current[0, 1, 3] = -2  # tree above a building; lower building voxel stays put
    evidence = {"dem": {"dtype": dem.dtype.str, "shape": list(dem.shape),
                         "sha256": exporter._array_digest(dem)}}
    stages = []
    for number in (1, 2):
        folder = root / f"repeat-{number}"
        folder.mkdir()
        adapter = folder / "adapter.geojson"
        centre = (float(grid["lons"][0, 1]), float(grid["lats"][0, 1]))
        geometry = box(centre[0] - 1e-6, centre[1] - 1e-6,
                       centre[0] + 1e-6, centre[1] + 1e-6)
        adapter.write_text(json.dumps({"type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
            "features": [{"type": "Feature", "properties": {"ouem_id": "synthetic-1", "height": 4},
                          "geometry": mapping(geometry)}]}), encoding="utf-8")
        (folder / "adapter.geojson.manifest.json").write_text(json.dumps({
            "schema": "ouem-standard-to-voxcity-building-adapter/v0.1",
            "voxcity": {"version": runner.VOXCITY_VERSION, "commit": runner.VOXCITY_COMMIT},
            "inputs": {"standard_terrain": {"path": str(terrain), "sha256": runner.sha256_file(terrain)}},
            "output": {"path": str(adapter), "sha256": runner.sha256_file(adapter)},
            "crs": {"source": "EPSG:6677", "target": "EPSG:4326"},
            "meshsize": 1, "voxcity_grid": {"rectangle_vertices_lonlat": rectangle}}), encoding="utf-8")
        (folder / "a3-report.json").write_text(json.dumps({"building_voxels_produced": True}), encoding="utf-8")
        (folder / "arrays.json").write_text(json.dumps({"first": evidence, "second": evidence}), encoding="utf-8")
        for name, array in (("current", current), ("no-canopy", bare)):
            np.save(folder / f"{name}-voxels.npy", array, allow_pickle=False)
        canopy = {"schema": "ouem-komae-meta-chm-canopy/v0.1", "status": "AUTOMATED_PASS",
                  "acceptance": "PENDING_LOCAL_REVIEW", "repeat_deterministic": True,
                  "component_evidence": evidence, "alignment": {"synthetic": True},
                  "current": {"dtype": current.dtype.str, "shape": list(current.shape),
                              "sha256": exporter._array_digest(current), "tree_voxels": 4,
                              "building_voxels": 1},
                  "no_canopy": {"dtype": bare.dtype.str, "shape": list(bare.shape),
                                "sha256": exporter._array_digest(bare), "tree_voxels": 0,
                                "building_voxels": 1},
                  "scenario_difference": {"tree_voxels_added": 4, "changed_voxels": 4},
                  "outputs": {name: runner.sha256_file(folder / name)
                              for name in ("current-voxels.npy", "no-canopy-voxels.npy")}}
        (folder / "canopy-report.json").write_text(json.dumps(canopy), encoding="utf-8")
        stages.append({"name": f"repeat-{number}-a3", "command": ["python", "scripts/work/voxcity_komae_a3_acceptance.py",
            str(folder / "building.gpkg"), str(terrain), "--adapter-output", str(adapter),
            "--report", str(folder / "a3-report.json"), "--array-evidence", str(folder / "arrays.json"),
            "--canopy-report", str(folder / "canopy-report.json")]})
    artifacts = {str(path.relative_to(root)).replace(os.sep, "/"): runner.fingerprint(path)
                 for path in root.rglob("*") if path.is_file()}
    report = {"schema": "ouem-komae-integration/v0.1", "status": "AUTOMATED_PASS",
              "quality": "PASS", "reproducibility": "PASS", "acceptance": "PENDING_LOCAL_REVIEW",
              "repeats": [{}, {}], "comparisons": {"canopy": True}, "stages": stages,
              "artifacts": artifacts}
    (root / "integration-report.json").write_text(json.dumps(report), encoding="utf-8")
    return root, grid


def _source_hashes(root):
    return {str(path.relative_to(root)): runner.sha256_file(path)
            for path in root.rglob("*") if path.is_file()}


def test_export_saved_synthetic_run_with_exact_uv_cells_and_heights(tmp_path):
    root, grid = _synthetic_run(tmp_path)
    before = _source_hashes(root)
    result, report = exporter.export_run(root, tmp_path / "qgis")
    assert _source_hashes(root) == before
    assert report.is_file() and not report.is_relative_to(root)
    assert result["status"] == "EXPORT_PASS" and result["acceptance"] == "PENDING_LOCAL_REVIEW"
    assert result["checks"]["tree_cells"] == 3
    assert result["checks"]["tree_voxels"] == result["checks"]["changed_voxels"] == 4
    assert result["checks"]["building_voxels"] == 1
    gpkg = Path(result["output"]["path"])
    spans = gpd.read_file(gpkg, layer="canopy_3d_spans")
    assert spans.voxel_count.sum() == 4
    assert all(spans.top_m - spans.base_m == spans.height_m)
    assert all(geometry.has_z and all(point[2] == base
               for polygon in (geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry])
               for point in polygon.exterior.coords)
               for geometry, base in zip(spans.geometry, spans.base_m))
    occupancy = gpd.read_file(gpkg, layer="canopy_occupancy")
    assert occupancy.crs.to_epsg() == 6677 and occupancy.tree_cells.tolist() == [3]
    centre = Transformer.from_crs(4326, 6677, always_xy=True).transform(
        float(grid["lons"][0, 0]), float(grid["lats"][0, 0]))
    assert occupancy.geometry.iloc[0].covers(Point(centre))
    assert len(gpd.read_file(gpkg, layer="adapter_buildings")) == 1
    second, _ = exporter.export_run(root, tmp_path / "qgis")
    assert second["output"]["path"] != result["output"]["path"]
    assert second["output"]["semantic_sha256"] == result["output"]["semantic_sha256"]


def test_rotated_voxcity_cell_orientation():
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords
    import math
    x, y = -23600, -40800
    angle = math.radians(31)
    u = (4 * math.cos(angle), 4 * math.sin(angle))
    v = (-4 * math.sin(angle), 4 * math.cos(angle))
    ll = Transformer.from_crs(6677, 4326, always_xy=True)
    rectangle = [ll.transform(*point) for point in
                 ((x, y), (x + u[0], y + u[1]),
                  (x + u[0] + v[0], y + u[1] + v[1]), (x + v[0], y + v[1]))]
    grid = compute_cell_center_coords(rectangle, 1)
    assert tuple(grid["grid_size"]) == (4, 4)
    p = exporter._cell_polygon(grid, 0, 3)
    assert p.covers(Point(float(grid["lons"][0, 3]), float(grid["lats"][0, 3])))
    assert not p.covers(Point(float(grid["lons"][3, 0]), float(grid["lats"][3, 0])))


def test_saved_array_change_blocks_export_without_output(tmp_path):
    root, _ = _synthetic_run(tmp_path)
    array = root / "repeat-1" / "current-voxels.npy"
    array.write_bytes(array.read_bytes() + b"x")
    with pytest.raises(runner.Blocked):
        exporter.export_run(root, tmp_path / "qgis")
    assert not (tmp_path / "qgis").exists()


def test_windows_launcher_structure_and_invalid_arguments():
    launcher = Path(__file__).resolve().parents[1] / "scripts/work/export_komae_canopy_qgis.cmd"
    text = launcher.read_text(encoding="utf-8")
    assert "DisableDelayedExpansion" in text and "OUEM_QGIS_RUN_ID" in text
    assert text.index("re.fullmatch") < text.index("-m ouem.komae_canopy_qgis_export")
    assert not exporter.RUN_ID.fullmatch("bad&id")


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe launcher executes only on Windows")
def test_windows_launcher_passes_valid_id_and_blocks_injection(tmp_path):
    import shutil
    repo = tmp_path / "repo"
    scripts = repo / "scripts/work"
    scripts.mkdir(parents=True)
    launcher = scripts / "export_komae_canopy_qgis.cmd"
    shutil.copy2(Path(__file__).resolve().parents[1] / "scripts/work/export_komae_canopy_qgis.cmd", launcher)
    venv.EnvBuilder(with_pip=False).create(repo / ".venv")
    package = repo / "ouem"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "komae_canopy_qgis_export.py").write_text(
        "import sys\nprint('RUN_ID=' + sys.argv[1])\nsys.exit(7)\n", encoding="utf-8")
    valid = subprocess.run(["cmd", "/d", "/c", str(launcher), "saved-run"],
                           cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert valid.returncode == 7 and "RUN_ID=saved-run" in valid.stdout
    caller = tmp_path / "caller.cmd"
    caller.write_text(f'@echo off\nsetlocal EnableDelayedExpansion\n"{launcher}" "!OUEM_TEST_ARG!"\n',
                      encoding="utf-8")
    marker = tmp_path / "injected.txt"
    for argument in ("bad&run", "bad|run", "bad>run", "bad!run", "bad%run", "CON",
                     "x" * 65, 'bad" & echo INJECTED>injected.txt & rem "'):
        env = {**os.environ, "OUEM_TEST_ARG": argument}
        result = subprocess.run(["cmd", "/d", "/c", str(caller)], cwd=tmp_path,
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 2, (argument, result.stdout, result.stderr)
        assert not marker.exists()
