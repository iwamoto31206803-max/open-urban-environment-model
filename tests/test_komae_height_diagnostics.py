"""Synthetic evidence for height diagnosis; no Komae real data."""
import os
from pathlib import Path
import subprocess
import venv
import json

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import Polygon, mapping

from ouem import komae_height_diagnostics as diagnosis
from ouem import komae_integration as runner
from ouem.adapters.voxcity import VOXCITY_PRECISE_RASTERIZATION


def _raster(tmp_path):
    path = tmp_path / "terrain.tif"
    data = np.full((12, 12), 20, dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", width=12, height=12, count=1,
                       dtype="float32", nodata=-9999, crs="EPSG:6677",
                       transform=from_origin(-23604, -40792, 1, 1)) as dst:
        dst.write(data, 1)
    ll = Transformer.from_crs(6677, 4326, always_xy=True)
    rectangle = [ll.transform(*p) for p in ((-23600, -40800), (-23600, -40796),
                                            (-23596, -40796), (-23596, -40800))]
    return path, data, rectangle


def test_pinned_nearest_dem_zero_fill_and_building_record(tmp_path):
    from voxcity.geoprocessor.raster import create_dem_grid_from_geotiff_polygon
    path, data, rectangle = _raster(tmp_path)
    first = diagnosis._source_pixels(path, rectangle, 1)
    r, c = int(first["nearest_rows"][0, 0]), int(first["nearest_cols"][0, 0])
    data[r, c] = -9999
    with rasterio.open(path, "r+") as dst:
        dst.write(data, 1)
    raw_info, _, _ = diagnosis._raster(path)
    assert raw_info["nodata_cells"] == 1 and raw_info["valid"]["median"] == 20
    pixels = diagnosis._source_pixels(path, rectangle, 1)
    dem = create_dem_grid_from_geotiff_polygon(path, 1, rectangle, dem_interpolation=False)
    expected = np.where(data < -1000, 0, data)[pixels["nearest_rows"], pixels["nearest_cols"]]
    assert np.array_equal(dem, expected) and dem[0, 0] == 0
    ids = np.zeros(dem.shape, dtype=np.int32)
    ids[0, 0] = 1
    roof = Polygon([(-23600, -40800, 50), (-23599, -40800, 50),
                    (-23599, -40799, 50), (-23600, -40799, 50)])
    frame = gpd.GeoDataFrame([{"ouem_id": "synthetic-1", "geometry": roof}], crs=6677)
    manifest = {"buildings": [{"ouem_id": "synthetic-1", "voxcity_id": 1,
                               "z_top_abs": 50, "ground_eff_abs": 0,
                               "ground_sample_min_abs": 0, "ground_sample_max_abs": 0,
                               "ground_sample_count": 1, "height": 50}]}
    rows = diagnosis._buildings(manifest, frame, ids, dem, pixels, pixels, True)
    assert rows[0]["height"] == 50
    assert rows[0]["engine_zero_filled_nodata_cells"] == 1
    assert rows[0]["standard_dem_nearest"]["nodata_fraction"] == 1
    assert rows[0]["grid_to_source_pixel_examples"][0]["engine_dem_m"] == 0
    assert rows[0]["classification"]["level"] == "CONFIRMED"
    assert rows[0]["evidence_matches_saved_adapter"]


def test_classification_does_not_invent_roof_cause():
    record = {"height": 42, "evidence_matches_saved_adapter": True,
              "engine_nearest_replay_matches": True, "engine_zero_filled_nodata_cells": 0,
              "engine_zero_filled_valid_low_cells": 0, "direct_outside_raster_cells": 0,
              "engine_zero_cells": 0, "engine_vs_direct_median_m": 0.0}
    assert diagnosis._classification(record)["level"] == "UNRESOLVED"
    record["engine_vs_direct_median_m"] = -5
    assert diagnosis._classification(record)["level"] == "LIKELY"
    record["engine_nearest_replay_matches"] = False
    assert diagnosis._classification(record)["level"] == "UNRESOLVED"
    record["engine_nearest_replay_matches"] = True
    record["engine_vs_direct_median_m"] = 0
    record["engine_zero_cells"] = 2
    assert diagnosis._classification(record)["level"] == "LIKELY"


def test_saved_run_report_is_read_only_and_links_all_stages(tmp_path):
    from tests.test_komae_canopy_qgis_export import _synthetic_run, _source_hashes
    from voxcity.geoprocessor.raster import (create_building_height_grid_from_gdf_polygon,
                                             create_dem_grid_from_geotiff_polygon)
    from ouem import komae_canopy_qgis_export as qgis_export
    root, grid = _synthetic_run(tmp_path)
    terrain = root / "terrain-source.tif"
    raw_info, _, _ = diagnosis._raster(terrain)
    native = root / "native.json"
    native.write_text(json.dumps({"schema": "ouem-native-terrain-manifest/v0.1",
                                  "terrain": {"source_path": str(terrain),
                                              "valid_cells": raw_info["valid_cells"],
                                              "nodata_cells": raw_info["nodata_cells"]}}), encoding="utf-8")
    (root / "terrain-source.tif.manifest.json").write_text(
        json.dumps({"source": {"sha256": runner.sha256_file(terrain)}}), encoding="utf-8")
    report_path = root / "integration-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["inputs"] = {"raw_terrain": runner.fingerprint(terrain),
                        "native_terrain": runner.fingerprint(native)}
    for number in (1, 2):
        folder = root / f"repeat-{number}"
        adapter_path = folder / "adapter.geojson"
        collection = json.loads(adapter_path.read_text(encoding="utf-8"))
        collection["features"][0]["properties"].update(id=1, voxcity_id=1, min_height=0)
        collection["features"][0]["geometry"] = mapping(qgis_export._cell_polygon(grid, 0, 1))
        adapter_path.write_text(json.dumps(collection), encoding="utf-8")
        feature = collection["features"][0]["geometry"]["coordinates"][0]
        centre_lon = sum(p[0] for p in feature[:-1]) / (len(feature)-1)
        centre_lat = sum(p[1] for p in feature[:-1]) / (len(feature)-1)
        x, y = Transformer.from_crs(4326, 6677, always_xy=True).transform(centre_lon, centre_lat)
        roof = Polygon([(x-0.2, y-0.2, 24), (x+0.2, y-0.2, 24),
                        (x+0.2, y+0.2, 24), (x-0.2, y+0.2, 24)])
        building = folder / "building.gpkg"
        gpd.GeoDataFrame([{"ouem_id": "synthetic-1", "geometry": roof}], crs=6677).to_file(
            building, layer="building", driver="GPKG")
        manifest_path = folder / "adapter.geojson.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rectangle = manifest["voxcity_grid"]["rectangle_vertices_lonlat"]
        dem = create_dem_grid_from_geotiff_polygon(terrain, 1, rectangle, dem_interpolation=False)
        adapter_frame = gpd.read_file(adapter_path)
        _, _, ids, _ = create_building_height_grid_from_gdf_polygon(
            adapter_frame, 1, rectangle, overlapping_footprint=VOXCITY_PRECISE_RASTERIZATION)
        assert np.any(ids == 1)
        samples = dem[ids == 1]
        ground = float(np.mean(samples))
        manifest["inputs"]["standard_building"] = {"path": str(building),
                                                     "sha256": runner.sha256_file(building)}
        manifest["output"]["sha256"] = runner.sha256_file(adapter_path)
        manifest["buildings"] = [{"ouem_id": "synthetic-1", "voxcity_id": 1,
                                  "z_top_abs": 24, "ground_eff_abs": ground,
                                  "ground_sample_min_abs": float(np.min(samples)),
                                  "ground_sample_max_abs": float(np.max(samples)),
                                  "ground_sample_count": int(samples.size), "height": 24-ground}]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        arrays_path = folder / "arrays.json"
        arrays = json.loads(arrays_path.read_text(encoding="utf-8"))
        ids_record = {"dtype": ids.dtype.str, "shape": list(ids.shape),
                      "sha256": __import__("hashlib").sha256(ids.tobytes(order="C")).hexdigest()}
        arrays["first"]["ids"] = ids_record
        arrays["second"]["ids"] = ids_record
        arrays_path.write_text(json.dumps(arrays), encoding="utf-8")
    report["artifacts"] = {str(p.relative_to(root)).replace(os.sep, "/"): runner.fingerprint(p)
                           for p in root.rglob("*") if p.is_file() and p != report_path}
    report_path.write_text(json.dumps(report), encoding="utf-8")
    before = _source_hashes(root)
    folder, result = diagnosis.export_run(root, tmp_path / "diagnostics")
    assert _source_hashes(root) == before and not folder.is_relative_to(root)
    assert result["repeat_diagnostics_equal"] and result["high_building_count"] == 0
    assert result["raw_terrain"]["valid"]["median"] == 20
    assert result["repeats"][0]["standard_terrain"]["valid"]["zero_count"] == 0
    assert result["repeats"][0]["buildings"][0]["evidence_matches_saved_adapter"]
    assert result["repeats"][0]["engine_nearest_replay_matches"]
    assert (folder / "diagnosis.json").is_file() and (folder / "summary.md").is_file()


def test_launcher_and_run_id_validation():
    launcher = Path(__file__).resolve().parents[1] / "scripts/work/diagnose_komae_building_heights.cmd"
    content = launcher.read_text(encoding="utf-8")
    assert content.index("re.fullmatch") < content.index("-m ouem.komae_height_diagnostics")
    assert "DisableDelayedExpansion" in content and "EnableDelayedExpansion" in content
    for value in ("bad&id", 'bad"id', "x" * 65):
        assert not diagnosis.RUN_ID.fullmatch(value)


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe launcher executes only on Windows")
def test_windows_launcher_rejects_injection_and_forwards_valid_id(tmp_path):
    import shutil
    repo = tmp_path / "repo"
    scripts = repo / "scripts/work"
    scripts.mkdir(parents=True)
    launcher = scripts / "diagnose_komae_building_heights.cmd"
    shutil.copy2(Path(__file__).resolve().parents[1] / "scripts/work/diagnose_komae_building_heights.cmd", launcher)
    venv.EnvBuilder(with_pip=False).create(repo / ".venv")
    package = repo / "ouem"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "komae_height_diagnostics.py").write_text(
        "import sys\nprint('RUN_ID=' + sys.argv[1])\nsys.exit(7)\n", encoding="utf-8")
    valid = subprocess.run(["cmd", "/d", "/c", str(launcher), "saved-run"], cwd=tmp_path,
                           capture_output=True, text=True, timeout=30)
    assert valid.returncode == 7 and "RUN_ID=saved-run" in valid.stdout
    caller = tmp_path / "caller.cmd"
    caller.write_text(f'@echo off\nsetlocal EnableDelayedExpansion\n"{launcher}" "!OUEM_TEST_ARG!"\n',
                      encoding="utf-8")
    for argument in ("bad&run", "bad|run", "bad%run", "CON", 'bad" & echo INJECTED>injected.txt & rem "'):
        result = subprocess.run(["cmd", "/d", "/c", str(caller)], cwd=tmp_path,
                                env={**os.environ, "OUEM_TEST_ARG": argument},
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 2, (result.stdout, result.stderr)
        assert not (tmp_path / "injected.txt").exists()
