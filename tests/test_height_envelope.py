"""Synthetic height-envelope tests; no real canopy or accepted Komae claims."""
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin, from_bounds
from rasterio.warp import transform_bounds

from ouem import height_envelope as env
from ouem.native.terrain import accept_native_terrain
from ouem.standardize.terrain import standardize_native_terrain

ROOT = Path(__file__).resolve().parents[1]
X, Y = -23600, -40500


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def raster(path, values, *, transform=None, crs=6677, nodata=-9999):
    values = np.asarray(values, dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0],
                       count=1, dtype="float32", crs=crs,
                       transform=transform or from_origin(X, Y, 1, 1), nodata=nodata) as dst:
        dst.write(values, 1)


@pytest.fixture
def inputs(tmp_path):
    config = tmp_path/"area.yaml"
    config.write_text(f"study_area:\n  id: synthetic\ncrs:\n  epsg: 6677\nextent:\n  xmin: {X}\n  ymin: {Y-2}\n  xmax: {X+4}\n  ymax: {Y}\n")
    raw, native, terrain = tmp_path/"raw.tif", tmp_path/"native.json", tmp_path/"terrain.tif"
    raster(raw, np.full((4, 8), 10), transform=from_origin(X, Y, .5, .5))
    accept_native_terrain(raw, native, provider="SYNTHETIC ONLY", source_dataset="Synthetic DEM",
                          vertical_reference_status="source-declared", vertical_reference="Synthetic T.P.",
                          vertical_reference_source="synthetic provider statement, not real acceptance")
    standardize_native_terrain(native, terrain, study_area_config=config)
    chm, acq, evidence = tmp_path/"chm.tif", tmp_path/"acq.json", tmp_path/"evidence.json"
    raster(chm, [[0, 1, 2, 5], [10, 20, 30, 40]])
    snapshot = tmp_path/"source.txt"
    statement = "Synthetic test dataset contains height above local ground in metres."
    snapshot.write_text(statement)
    acceptance = tmp_path/"synthetic-acceptance.md"
    data = dict(chm=chm, acquisition_record=acq, chm_evidence=evidence, terrain=terrain,
                terrain_manifest=tmp_path/"terrain.tif.manifest.json", terrain_acceptance=acceptance,
                study_area=config)
    write_json(evidence, {"schema": "ouem-height-envelope-evidence/v0.1",
        "height_semantics": "height_above_ground_m", "height_reference": "local_ground",
        "dem_quantity": "absolute_elevation_m", "evidence": {"source": "synthetic fixture",
          "citation": "synthetic://height-semantics", "statement": statement,
          "snapshot_path": snapshot.name, "snapshot_sha256": env.sha256(snapshot)},
        "compatibility_review": {"reviewer": "synthetic-test-only", "reviewed_at": "test-date",
          "basis": "synthetic local-ground height and synthetic absolute DEM",
          "vertical_combination": "relative_height_plus_dem_no_offset", "dem_vertical_reference": "Synthetic T.P."}})
    sync(data)
    return data


def sync(data):
    """Rebind synthetic declarations after deliberately changing a fixture."""
    terrain_hash = env.sha256(data["terrain"])
    manifest = env.read_json(data["terrain_manifest"])
    manifest["standard"]["sha256"] = terrain_hash
    write_json(data["terrain_manifest"], manifest)
    data["terrain_acceptance"].write_text(f"SYNTHETIC TEST ONLY\n| Status | **ACCEPTED** |\n| Standard output SHA-256 | `{terrain_hash}` |\n")
    acq = {"schema": "ouem-chmv2-acquisition-poc/v0.1", "status": "COMPLETED",
           "output": {"sha256": env.sha256(data["chm"])},
           "tiles": [{"quadkey": "0000000000", "sha256": "0"*64}]}
    write_json(data["acquisition_record"], acq)
    evidence = env.read_json(data["chm_evidence"])
    evidence.update(chm_sha256=env.sha256(data["chm"]), acquisition_record_sha256=env.sha256(data["acquisition_record"]))
    evidence["compatibility_review"]["dem_sha256"] = terrain_hash
    write_json(data["chm_evidence"], evidence)


def read_outputs(directory):
    arrays = []
    for name in ("canopy_top_z.tif", "canopy_bottom_z.tif", "height_envelope_state.tif"):
        with rasterio.open(directory/name) as src: arrays.append(src.read(1))
    return arrays


def test_exact_komae_grid_centres_and_half_metre_dem_sampling(inputs):
    grid = env.GridSpec.from_study_area(ROOT/"config/study_areas/komae_09LD3451.yaml")
    assert (grid.height, grid.width) == (300, 400)
    assert tuple(grid.transform)[:6] == (1, 0, -23600, 0, -1, -40500)
    xs, ys = grid.centres()
    assert (xs[0, 0], ys[0, 0]) == (-23599.5, -40500.5)
    assert (xs[-1, -1], ys[-1, -1]) == (-23200.5, -40799.5)
    small = env.GridSpec.from_study_area(inputs["study_area"])
    raster(inputs["chm"], np.arange(32).reshape(4, 8), transform=from_origin(X, Y, .5, .5))
    sampled = env.sample_raster(inputs["chm"], small)
    assert sampled.values.tolist() == [[9, 11, 13, 15], [25, 27, 29, 31]]
    with pytest.raises(env.EnvelopeBlocked, match="bilinear"):
        env.sample_raster(inputs["terrain"], small, method="bilinear")


def test_absolute_envelope_cr_changes_and_zero_is_valid(inputs, tmp_path):
    for cr in (.60, .25, 1):
        out = tmp_path/f"cr-{cr}"
        manifest = env.generate(**inputs, output_dir=out, model=env.ConstantCR(cr))
        top, bottom, state = read_outputs(out)
        heights = np.array([[0, 1, 2, 5], [10, 20, 30, 40]])
        assert np.array_equal(top, 10+heights)
        assert np.allclose(bottom, 10+heights*(1-cr))
        assert np.all(state == env.VALID)
        assert manifest["qa"]["state_counts"]["zero_height_valid"] == 1
        assert manifest["qa"]["dem_le_bottom_le_top"]
        with rasterio.open(out/"canopy_top_z.tif") as src:
            assert src.dtypes == ("float32",) and src.nodata == -9999
            assert src.transform == from_origin(X, Y, 1, 1)


@pytest.mark.parametrize("cr", [0, -.1, 1.1, float("nan"), float("inf")])
def test_invalid_constant_cr_blocks(cr):
    with pytest.raises(env.EnvelopeBlocked): env.ConstantCR(cr)


def test_missing_and_invalid_values_are_distinct_and_combined(inputs, tmp_path):
    raster(inputs["chm"], [[-9999, -1, np.nan, np.inf], [0, 1, 2, 3]])
    with rasterio.open(inputs["terrain"], "r+") as src:
        values = src.read(1)
        values[1, 1] = -9999  # same first output centre as missing CHM
        values[3, 3] = np.nan
        src.write(values, 1)
    sync(inputs)
    result = env.generate(**inputs, output_dir=tmp_path/"out")
    top, bottom, state = read_outputs(tmp_path/"out")
    assert state[0].tolist() == [2|4, 8, 8, 8]
    assert state[1].tolist() == [1, 16, 1, 1]
    assert top[0, 0] == bottom[0, 0] == -9999
    assert result["qa"]["state_counts"]["missing_chm"] == 1
    assert result["qa"]["state_counts"]["missing_dem"] == 1


def test_internal_mask_and_nan_nodata_are_missing_not_zero(inputs, tmp_path):
    raster(inputs["chm"], [[np.nan, 0, 2, 3], [4, 5, 6, 7]], nodata=np.nan)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(inputs["terrain"], "r+") as src:
            mask = np.full((4, 8), 255, dtype="uint8"); mask[1, 3] = 0; src.write_mask(mask)
    sync(inputs)
    env.generate(**inputs, output_dir=tmp_path/"out")
    _, _, state = read_outputs(tmp_path/"out")
    assert state[0, 0] == 2 and state[0, 1] == 4


def test_outside_source_coverage_is_not_missing_or_absent(inputs, tmp_path):
    raster(inputs["chm"], [[1, 2, 3], [4, 5, 6]], transform=from_origin(X+1, Y, 1, 1))
    sync(inputs)
    env.generate(**inputs, output_dir=tmp_path/"out")
    top, _, state = read_outputs(tmp_path/"out")
    assert state[:, 0].tolist() == [32, 32]
    assert np.all(top[:, 0] == -9999) and np.all(state[:, 1:] == 1)


def test_chm_in_epsg3857_is_reprojected_only_for_centre_lookup(inputs, tmp_path):
    grid = env.GridSpec.from_study_area(inputs["study_area"])
    bounds = transform_bounds(6677, 3857, *grid.bounds, densify_pts=21)
    values = np.arange(8).reshape(2, 4)
    raster(inputs["chm"], values, crs=3857, transform=from_bounds(*bounds, 4, 2))
    sync(inputs)
    env.generate(**inputs, output_dir=tmp_path/"out")
    top, _, state = read_outputs(tmp_path/"out")
    assert np.array_equal(top, 10+values) and np.all(state == 1)


@pytest.mark.parametrize("problem", ["legacy", "missing_evidence", "snapshot", "datum", "absolute", "acceptance", "terrain_hash", "chm_hash", "acquisition_hash", "offset"])
def test_semantics_and_provenance_fail_closed(inputs, tmp_path, problem):
    ev = env.read_json(inputs["chm_evidence"])
    dem = env.read_json(inputs["terrain_manifest"])
    if problem == "legacy": ev["schema"] = "ouem-meta-chm-provenance/v0.1"
    if problem == "missing_evidence": ev.pop("evidence")
    if problem == "snapshot": ev["evidence"]["snapshot_sha256"] = "0"*64
    if problem == "datum": dem["vertical_reference"]["status"] = "unresolved"
    if problem == "absolute": ev["dem_quantity"] = "ellipsoidal_height_assumed_from_crs"
    if problem == "acceptance": inputs["terrain_acceptance"].write_text("NOT ACCEPTED")
    if problem == "terrain_hash": dem["standard"]["sha256"] = "0"*64
    if problem == "chm_hash": ev["chm_sha256"] = "0"*64
    if problem == "acquisition_hash": ev["acquisition_record_sha256"] = "0"*64
    if problem == "offset": ev["compatibility_review"]["vertical_combination"] = "add_37_metres"
    write_json(inputs["chm_evidence"], ev); write_json(inputs["terrain_manifest"], dem)
    with pytest.raises(env.EnvelopeBlocked): env.generate(**inputs, output_dir=tmp_path/"blocked")
    assert not (tmp_path/"blocked").exists()


def test_replaceable_spatial_cr_model_and_float32_overflow():
    grid = env.GridSpec((0, 0, 3, 1))
    zeros = np.zeros((1, 3), dtype=bool)
    chm = env.Samples(np.array([[10., 10., 3e38]]), zeros, zeros, {})
    dem = env.Samples(np.array([[10., 10., 3e38]]), zeros, zeros, {})
    class SpatialCR:
        def specification(self): return {"model_id": "synthetic_spatial", "version": "test"}
        def ratios(self, grid, chm, dem): return np.array([[.5, 1., .6]])
    top, bottom, state, qa = env.calculate(grid, chm, dem, SpatialCR())
    assert bottom[0, :2].tolist() == [15, 10]
    assert state.tolist() == [[1, 1, 128]]
    assert top[0, 2] == bottom[0, 2] == -9999


def test_deterministic_outputs_provenance_and_existing_artifacts_untouched(inputs, tmp_path):
    import geopandas as gpd
    from shapely.geometry import Polygon
    building = tmp_path/"building.gpkg"
    geometry = Polygon([(X, Y, 20), (X+1, Y, 20), (X+1, Y-1, 20), (X, Y, 20)])
    gpd.GeoDataFrame({"ouem_id": ["synthetic-building"]}, geometry=[geometry], crs=6677).to_file(building, layer="building", driver="GPKG")
    protected = [*inputs.values(), building]
    before = {str(p): env.sha256(p) for p in protected}
    first = env.generate(**inputs, output_dir=tmp_path/"one")
    second = env.generate(**inputs, output_dir=tmp_path/"two")
    assert first["outputs"] == second["outputs"]
    assert first["reproducibility_sha256"] == second["reproducibility_sha256"]
    assert before == {str(p): env.sha256(p) for p in protected}
    with rasterio.open(inputs["terrain"]) as src: assert src.res == (.5, .5)
    with pytest.raises(env.EnvelopeBlocked): env.generate(**inputs, output_dir=tmp_path/"one")


def test_output_verification_failure_does_not_publish_bundle(inputs, tmp_path, monkeypatch):
    def fail(*a, **k): raise env.EnvelopeBlocked("simulated verification failure")
    monkeypatch.setattr(env, "write_verified", fail)
    with pytest.raises(env.EnvelopeBlocked): env.generate(**inputs, output_dir=tmp_path/"out")
    assert not list((tmp_path/"out").glob("*.tif"))
    assert not (tmp_path/"out/height_envelope_manifest.json").exists()


def test_dem_outside_coverage_has_its_own_flag(inputs, tmp_path):
    raw = tmp_path/"narrow-raw.tif"
    native = tmp_path/"narrow-native.json"
    raster(raw, np.full((4, 4), 10), transform=from_origin(X, Y, .5, .5))
    accept_native_terrain(raw, native, provider="SYNTHETIC", source_dataset="Synthetic narrow DEM",
                          vertical_reference_status="source-declared", vertical_reference="Synthetic T.P.",
                          vertical_reference_source="synthetic only")
    standardize_native_terrain(native, inputs["terrain"], study_area_config=inputs["study_area"])
    sync(inputs)
    env.generate(**inputs, output_dir=tmp_path/"narrow")
    _, _, state = read_outputs(tmp_path/"narrow")
    assert np.all(state[:, :2] == 1) and np.all(state[:, 2:] == 64)


def test_nonzero_source_offset_is_blocked_not_silently_added(inputs, tmp_path):
    with rasterio.open(inputs["chm"], "r+") as src: src.offsets = (37.0,)
    sync(inputs)
    with pytest.raises(env.EnvelopeBlocked, match="offset"):
        env.generate(**inputs, output_dir=tmp_path/"blocked")
    assert not (tmp_path/"blocked").exists()


def test_partial_bundle_publication_failure_rolls_back_outputs(inputs, tmp_path, monkeypatch):
    original = env.os.link
    calls = 0
    def fail_second(*args):
        nonlocal calls
        calls += 1
        if calls == 2: raise OSError("simulated publication failure")
        return original(*args)
    monkeypatch.setattr(env.os, "link", fail_second)
    with pytest.raises(OSError, match="publication"):
        env.generate(**inputs, output_dir=tmp_path/"out")
    assert not list((tmp_path/"out").glob("*.tif"))
    assert not (tmp_path/"out/height_envelope_manifest.json").exists()


def test_incompatible_vertical_name_and_evidence_bound_to_another_dem_block(inputs, tmp_path):
    packet = env.read_json(inputs["chm_evidence"])
    original_review = packet["compatibility_review"].copy()
    for key, value in (("dem_vertical_reference", "Other datum"), ("dem_sha256", "0"*64)):
        packet["compatibility_review"] = {**original_review, key: value}
        write_json(inputs["chm_evidence"], packet)
        with pytest.raises(env.EnvelopeBlocked, match="incompatible"):
            env.generate(**inputs, output_dir=tmp_path/"blocked")


def test_spatial_model_can_replace_constant_without_changing_output_contract(inputs, tmp_path):
    class ClassModel:
        def specification(self):
            return {"model_id": "synthetic_class_cr", "version": "test-v1", "parameters": {"left": .5, "right": 1}}
        def ratios(self, grid, chm, dem):
            return np.tile([.5, .5, 1., 1.], (grid.height, 1))
    record = env.generate(**inputs, output_dir=tmp_path/"class", model=ClassModel())
    _, bottom, state = read_outputs(tmp_path/"class")
    assert bottom[1].tolist() == [15, 20, 10, 10] and np.all(state == 1)
    assert record["cr_model"]["model_id"] == "synthetic_class_cr"
    assert sorted(record["outputs"]) == ["canopy_bottom_z.tif", "canopy_top_z.tif", "height_envelope_state.tif"]


def test_partial_invalid_cr_model_cells_and_empty_envelope_are_explicit(inputs, tmp_path):
    class InvalidModel:
        def specification(self): return {"model_id": "synthetic_bad_cr", "version": "test", "parameters": {}}
        def ratios(self, grid, chm, dem): return np.full((grid.height, grid.width), np.nan)
    record = env.generate(**inputs, output_dir=tmp_path/"invalid-cr", model=InvalidModel())
    top, bottom, state = read_outputs(tmp_path/"invalid-cr")
    assert np.all(state == 128) and np.all(top == -9999) and np.all(bottom == -9999)
    assert record["qa"]["state_counts"]["valid"] == 0 and record["qa"]["top_range"] is None


def test_changing_an_input_before_publication_blocks_bundle(inputs, tmp_path, monkeypatch):
    original = env.write_verified
    changed = False
    def mutate_input(*args):
        nonlocal changed
        result = original(*args)
        if not changed:
            with rasterio.open(inputs["chm"], "r+") as src:
                data = src.read(1); data[0, 0] = 42; src.write(data, 1)
            changed = True
        return result
    monkeypatch.setattr(env, "write_verified", mutate_input)
    with pytest.raises(env.EnvelopeBlocked, match="Input changed"):
        env.generate(**inputs, output_dir=tmp_path/"out")
    assert not list((tmp_path/"out").glob("*.tif"))
    assert not (tmp_path/"out/height_envelope_manifest.json").exists()
