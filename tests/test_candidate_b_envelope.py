"""Synthetic raster QA; no actual engine/model generation or network."""
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ouem import candidate_b_envelope as cb


def raster(path, values, *, resolution=1., nodata=-32767.):
    values = np.asarray(values, dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", count=1, width=values.shape[1],
                       height=values.shape[0], dtype="float32", crs=6677,
                       transform=from_origin(0, 127, resolution, resolution), nodata=nodata) as ds:
        ds.write(values, 1)


def test_coordinates_zero_missing_outside(tmp_path):
    ch, dem = tmp_path/"ch.tif", tmp_path/"dem.tif"
    raster(ch, [[0, 10, -32767], [20, 30, 40]])
    raster(dem, [[25, 26, 27], [28, 29, 30]])
    xy = np.array([[[.6, 126.6], [1.7, 126.2], [2.5, 126.5], [3.1, 126.5]],
                   [[.6, 125.6], [1.7, 125.2], [2.5, 125.5], [3.1, 125.5]]])
    top, bottom, state, qa, _, _ = cb.evaluate(ch, dem, cb.point_grid(xy))
    np.testing.assert_array_equal(state, [[1, 1, 2, 96], [1, 1, 1, 96]])
    np.testing.assert_array_equal(top[:, :2], [[25, 36], [48, 59]])
    np.testing.assert_array_equal(bottom[:, :2], [[25, 30], [36, 41]])
    assert top[0, 0] == bottom[0, 0] == 25
    assert qa["state_counts"]["zero_height_valid"] == 1
    assert qa["tree_candidate_cells"] == 4
    assert (top[state != 1] == cb.env.NODATA).all()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    source = tmp_path/"t5"
    (source/"t5-2").mkdir(parents=True)
    dem = source/"t5-2/terrain.tif"
    raster(dem, np.full((254, 254), 25.), resolution=.5)
    ch = tmp_path/"raw"/"chm.tif"
    ch.parent.mkdir()
    vals = np.full((127, 127), 10.)
    vals[0, 0] = 0
    raster(ch, vals)
    acq = ch.parent/"acq.json"
    sha = cb.env.sha256(ch)
    acq.write_text(json.dumps(dict(schema="ouem-chmv2-acquisition-poc/v0.1", status="COMPLETED",
        source="synthetic", tiles=[dict(quadkey="1330021123", sha256=sha)])))
    snap = ch.parent/"statement.txt"
    snap.write_text("Synthetic HAG metres")
    evidence = ch.parent/"evidence.json"
    evidence.write_text(json.dumps(dict(height_semantics="height_above_ground_m", height_reference="local_ground",
        evidence=dict(snapshot_path=snap.name, snapshot_sha256=cb.env.sha256(snap), statement=snap.read_text()))))
    domain = [0, 0, 127, 127]
    grid = cb.env.GridSpec(tuple(domain))
    x, y = grid.centres()
    xy = np.stack((x+.1, y+.1), axis=-1)[::-1].copy()
    report = dict(outputs={"t5-2/terrain.tif": cb.env.sha256(dem)}, terrain_integration_ready=False,
        terrain=dict(affine=list(from_origin(0, 127, .5, .5))[:6]), vertical_evidence="SYNTHETIC", profile="synthetic")
    from ouem.consumers.source_h_standard import Watch
    watch = Watch(source)
    watch.capture("terrain", "t5-2/terrain.tif", report["outputs"]["t5-2/terrain.tif"])
    monkeypatch.setattr(cb, "load_candidate", lambda *a: (
        dict(centres_xy=xy, raw_dem=np.full((127, 127), 25.)), dict(domain_bounds=domain), {}, report, watch))
    for key, value in dict(CHM_SHA=sha, DEM_SHA=cb.env.sha256(dem), ACQUISITION_SHA=cb.env.sha256(acq),
                           EVIDENCE_SHA=cb.env.sha256(evidence), DOMAIN=domain).items():
        monkeypatch.setattr(cb, key, value)
    monkeypatch.setattr(cb, "voxcity_provenance", lambda: dict(verified=True, scope="synthetic"))
    monkeypatch.setattr(cb, "implementation_identity", lambda: dict(test="synthetic"))
    return dict(source_run=source, chm=ch, acquisition_record=acq, chm_evidence=evidence)


def test_generation_reproducible_and_written_grid(bundle, tmp_path):
    a = cb.generate(**bundle, output_dir=tmp_path/"out1")
    b = cb.generate(**bundle, output_dir=tmp_path/"out2")
    assert a == b
    assert a["qa"]["state_counts"]["valid"] == 16129
    assert a["qa"]["state_counts"]["zero_height_valid"] == 1
    assert a["qa"]["tree_candidate_cells"] == 16128
    assert a["source_immutability"] == "PASS"
    assert a["correspondence"]["unique_envelope_cells"] == 16129
    assert a["correspondence"]["max_distance_to_envelope_centre_m"] == pytest.approx(2**.5*.1)
    for name in a["outputs"]:
        with rasterio.open(tmp_path/"out1"/name) as ds:
            assert ds.crs.to_epsg() == 6677 and ds.shape == (127, 127)
            assert ds.transform == from_origin(0, 127, 1, 1)
            assert ds.nodata == (None if "state" in name else -9999.)


@pytest.mark.parametrize("key", ["chm", "acquisition_record", "chm_evidence"])
def test_hash_mismatch_rejected(bundle, tmp_path, key):
    with bundle[key].open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        cb.generate(**bundle, output_dir=tmp_path/"out")
    assert not (tmp_path/"out").exists()


@pytest.mark.parametrize("fault", ["missing", "outside", "saved_dem", "terrain_sha", "existing"])
def test_incomplete_or_inconsistent_inputs_block(bundle, tmp_path, monkeypatch, fault):
    original = cb.evaluate
    def evaluate(chm, dem, grid):
        result = list(original(chm, dem, grid))
        if fault in ("missing", "outside"):
            result[2][0, 0] = cb.env.STATE_BITS[fault+"_chm"]
        if fault == "saved_dem":
            result[5].values[0, 0] += 1
        return result
    monkeypatch.setattr(cb, "evaluate", evaluate)
    if fault == "terrain_sha":
        monkeypatch.setattr(cb, "DEM_SHA", "0"*64)
    if fault == "existing":
        (tmp_path/"out").mkdir()
    with pytest.raises(ValueError):
        cb.generate(**bundle, output_dir=tmp_path/"out")
    assert not (tmp_path/"out/height_envelope_manifest.json").exists()


@pytest.mark.parametrize("failure", ["write", "publication", "mutation"])
def test_partial_failure_never_completed(bundle, tmp_path, monkeypatch, failure):
    original = cb.env.write_verified
    calls = []
    def write(*args):
        calls.append(args[0])
        if len(calls) == 2 and failure == "write":
            raise OSError("injected disk failure")
        result = original(*args)
        if len(calls) == 2 and failure == "mutation":
            with bundle["chm"].open("ab") as stream:
                stream.write(b" ")
        return result
    monkeypatch.setattr(cb.env, "write_verified", write)
    if failure == "publication":
        def fail(*args):
            raise OSError("injected publication failure")
        monkeypatch.setattr(cb.os, "rename", fail)
    with pytest.raises((OSError, ValueError)):
        cb.generate(**bundle, output_dir=tmp_path/"out")
    assert not (tmp_path/"out/height_envelope_manifest.json").exists()
    assert json.loads((tmp_path/"out/failure.json").read_text())["status"] == "BLOCKED"
