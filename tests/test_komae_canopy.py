"""Synthetic Komae canopy tests; no local Meta CHM or accepted artifacts."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from ouem.komae_canopy import CanopyBlocked, convert_chm, scenario_arrays


def fixture_chm(tmp_path, values, *, nodata=-9999, semantics="height_above_ground_m"):
    tif = tmp_path / "synthetic-chm.tif"
    with rasterio.open(tif, "w", driver="GTiff", height=2, width=2, count=1,
                       dtype="float32", crs="EPSG:6677", transform=from_origin(0, 2, 1, 1),
                       nodata=nodata) as dst:
        dst.write(np.asarray(values, dtype="float32"), 1)
    provenance = tmp_path / "synthetic-provenance.json"
    provenance.write_text(json.dumps({
        "schema": "ouem-meta-chm-provenance/v0.1",
        "raster_sha256": hashlib.sha256(tif.read_bytes()).hexdigest(),
        "height_semantics": semantics,
        "evidence": {"source": "synthetic fixture", "citation": "test-only",
                     "height_statement": "height above local ground, metres"},
    }), encoding="utf-8")
    tx = Transformer.from_crs(6677, 4326, always_xy=True)
    rectangle = [tx.transform(x, y) for x, y in ((0, 0), (0, 2), (2, 2), (2, 0))]
    return tif, provenance, rectangle


def test_chm_alignment_threshold_and_determinism(tmp_path):
    tif, provenance, rectangle = fixture_chm(tmp_path, [[5, 0], [3, 2.99]])
    dem = np.array([[10., 11.], [12., 13.]])
    top, bottom, info = convert_chm(tif, provenance, rectangle, 1, dem)
    assert top.tolist() == [[3, 0], [5, 0]]  # north-up TIFF → uv_m south-up
    assert np.allclose(bottom, top * 0.4)
    assert info["active_cells"] == 2
    assert info["uncovered_cells"] == info["nodata_cells"] == 0
    again = convert_chm(tif, provenance, rectangle, 1, dem)
    assert np.array_equal(top, again[0]) and np.array_equal(bottom, again[1])
    assert info == again[2]


def test_rotated_grid_samples_actual_centres(tmp_path):
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords

    tif = tmp_path / "rotated.tif"
    values = np.arange(25, dtype="float32").reshape(5, 5)
    transform = from_origin(-1, 3, 1, 1)
    with rasterio.open(tif, "w", driver="GTiff", width=5, height=5, count=1,
                       dtype="float32", crs="EPSG:6677", transform=transform) as dst:
        dst.write(values, 1)
    provenance = tmp_path / "rotated.tif.provenance.json"
    provenance.write_text(json.dumps({
        "schema": "ouem-meta-chm-provenance/v0.1",
        "raster_sha256": hashlib.sha256(tif.read_bytes()).hexdigest(),
        "height_semantics": "height_above_ground_m",
        "evidence": {"source": "synthetic", "citation": "test-only",
                     "height_statement": "canopy height above ground in metres"},
    }), encoding="utf-8")
    tx = Transformer.from_crs(6677, 4326, always_xy=True)
    p = 2 ** 0.5
    rectangle = [tx.transform(x, y) for x, y in ((0, 0), (p, p), (2*p, 0), (p, -p))]
    grid = compute_cell_center_coords(rectangle, 1)
    assert grid["grid_size"] == (2, 2)
    xy = Transformer.from_crs(4326, 6677, always_xy=True)
    expected = np.empty((2, 2))
    for i, j in np.ndindex(expected.shape):
        x, y = xy.transform(grid["lons"][i, j], grid["lats"][i, j])
        row, col = rasterio.transform.rowcol(transform, x, y)
        expected[i, j] = values[row, col]
    top, _, info = convert_chm(tif, provenance, rectangle, 1, np.full((2, 2), 10.))
    assert np.array_equal(top, expected)
    assert info["uncovered_cells"] == 0


@pytest.mark.parametrize("values,semantics,dem", [
    ([[5, -9999], [3, 0]], "height_above_ground_m", [[10., 11.], [12., 13.]]),
    ([[5, float("nan")], [3, 0]], "height_above_ground_m", [[10., 11.], [12., 13.]]),
    ([[5, -1], [3, 0]], "height_above_ground_m", [[10., 11.], [12., 13.]]),
    ([[5, 0], [3, 0]], "absolute_elevation_m", [[10., 11.], [12., 13.]]),
    ([[5, 0], [3, 0]], "height_above_ground_m", [[10., -9999.], [12., 13.]]),
])
def test_invalid_input_blocks(tmp_path, values, semantics, dem):
    tif, provenance, rectangle = fixture_chm(tmp_path, values, semantics=semantics)
    with pytest.raises(CanopyBlocked):
        convert_chm(tif, provenance, rectangle, 1, np.asarray(dem))


def test_uncovered_and_empty_canopy_are_reported(tmp_path):
    tif, provenance, rectangle = fixture_chm(tmp_path, [[0, 0], [0, 0]])
    with pytest.raises(CanopyBlocked, match="no canopy cells") as error:
        convert_chm(tif, provenance, rectangle, 1, np.full((2, 2), 10.))
    assert error.value.diagnostics["active_cells"] == 0
    shifted = [(lon + 0.001, lat) for lon, lat in rectangle]
    with pytest.raises(CanopyBlocked, match="uncovered=4") as error:
        convert_chm(tif, provenance, shifted, 1, np.full((2, 2), 10.))
    assert error.value.diagnostics["uncovered_cells"] == 4


def test_nan_nodata_diagnostics_and_hash_bound_provenance(tmp_path):
    tif, provenance, rectangle = fixture_chm(tmp_path, [[5, np.nan], [3, 0]], nodata=np.nan)
    with pytest.raises(CanopyBlocked) as error:
        convert_chm(tif, provenance, rectangle, 1, np.full((2, 2), 10.))
    assert error.value.diagnostics["nodata"] == "NaN"
    assert error.value.diagnostics["nodata_cells"] == 1
    json.dumps(error.value.diagnostics, allow_nan=False)
    provenance.write_text(provenance.read_text().replace("height_above_ground_m", "absolute_elevation_m"))
    with pytest.raises(CanopyBlocked, match="hash-matched provenance"):
        convert_chm(tif, provenance, rectangle, 1, np.full((2, 2), 10.))
    provenance.write_text(provenance.read_text().replace("absolute_elevation_m", "height_above_ground_m"))
    tif.write_bytes(tif.read_bytes() + b"changed")
    with pytest.raises(CanopyBlocked, match="hash-matched provenance"):
        convert_chm(tif, provenance, rectangle, 1, np.full((2, 2), 10.))


def test_real_pinned_engine_overlap_and_component_preservation():
    """Exercise installed VoxCity 1.7.0, not a replacement voxelizer or mock."""
    from voxcity.generator.voxelizer import Voxelizer
    from ouem.komae_integration import voxcity_provenance

    assert voxcity_provenance()["verified"]

    dem = np.array([[10., 11.], [12., 13.]])
    heights = np.zeros((2, 2)); heights[0, 0] = 6
    segments = np.empty((2, 2), dtype=object)
    for index in np.ndindex(segments.shape):
        segments[index] = []
    segments[0, 0] = [[0., 6.]]
    ids = np.zeros((2, 2), dtype=int); ids[0, 0] = 1
    cover = np.ones((2, 2), dtype=int)
    zeros = np.zeros((2, 2))
    baseline = Voxelizer(1, "Standard").generate_combined(
        heights, segments, ids, cover, dem, zeros, zeros, print_class_info=False)
    top = np.array([[5., 3.4], [0., 0.]])
    bottom = 0.4 * top
    rectangle = [(0., 0.), (0., 1.), (1., 1.), (1., 0.)]
    original = [item.copy() for item in (dem, heights, ids, cover, baseline)]
    first = scenario_arrays(dem, heights, segments, ids, cover, baseline, top, bottom, 1, rectangle)
    second = scenario_arrays(dem, heights, segments, ids, cover, baseline, top, bottom, 1, rectangle)
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    assert np.array_equal(first[1], baseline)
    assert np.count_nonzero(first[0] == -2) > 0
    assert np.array_equal(first[0][:, :, :baseline.shape[2]] == -3, baseline == -3)
    assert not np.any(first[0][:, :, baseline.shape[2]:] == -3)
    assert not np.any(first[0][0, 0] == -2)  # overlapping canopy overwritten by building
    assert all(np.array_equal(a, b) for a, b in zip((dem, heights, ids, cover, baseline), original))


def test_windows_launcher_uses_isolated_existing_komae_workflow():
    launcher = (Path(__file__).resolve().parents[1] / "scripts/work/run_komae_meta_chm_e2e.cmd").read_text()
    for token in ('.venv\\Scripts\\python.exe', 'ouem.komae_integration run',
                  '--contained-poc', '--expected-buildings 92',
                  '--expected-native-buildings 3637', '--meshsize 1',
                  '--meta-chm', '--chm-provenance',
                  'data\\work\\integration\\!OUEM_RUN_ID!'):
        assert token in launcher
