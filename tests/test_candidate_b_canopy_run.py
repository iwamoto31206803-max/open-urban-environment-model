"""Saved synthetic bundles; public canopy voxelization only, no Solar/GVI."""
import json

import numpy as np
import pytest
import rasterio

from ouem import candidate_b_canopy_run as m
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_candidate_b_canopy import authored


def raster(path, values, grid):
    with rasterio.open(path, "w", driver="GTiff", count=1, width=values.shape[1], height=values.shape[0],
                       dtype="float32", crs=6677, transform=grid.transform, nodata=-9999) as ds:
        ds.write(values.astype("float32"), 1)


def test_segment_restoration_is_exact_and_independent():
    value = [[[], [[0, 3.5], [1, 2]]]]
    restored = m.restore_segments(value, (1, 2), np.array([[0, 17]]))
    assert restored.shape == (1, 2) and restored.dtype == object
    assert restored[0, 1] == [[0., 3.5], [1., 2.]]
    restored[0, 1][0][1] = 9
    assert value[0][1][0][1] == 3.5


@pytest.mark.parametrize("value", [[], [[]], [[None]], [[[None]]], [[[[0]]]], [[[[0, 2, 3]]]],
    [[[[False, 2]]]], [[[["0", 2]]]], [[[[0, float("nan")]]]], [[[[0, float("inf")]]]],
    [[[[-1, 2]]]], [[[[2, 1]]]], [[[[0, 0]]]], [[[]]]])
def test_invalid_saved_segments_rejected(value):
    with pytest.raises(GeometryValidationError):
        m.restore_segments(value, (1, 1), np.ones((1, 1), int))


def test_AB_difference_at_native_pixel_boundary_and_zero_unknown(tmp_path):
    north = m.env.GridSpec((0, 0, 2, 2))
    native = m.env.GridSpec((0, 0, 2, 2), .5)
    chm, dem = tmp_path/"chm.tif", tmp_path/"dem.tif"
    raster(chm, np.array([[0, 5, -9999, 5], [5, 5, 5, 5], [5]*4, [5]*4]), native)
    raster(dem, np.array([[25, 26, 25, 26], [27, 28, 27, 28], [25]*4, [25]*4]), native)
    sampled, _, _, _ = m.direct_samples(chm, dem, north)
    paths = []
    for key in ("top", "bottom", "state"):
        path = tmp_path/(key+".tif")
        m.env.write_verified(path, sampled[key], north, None if key == "state" else -9999., m.c1.VERTICAL)
        paths.append(path)
    # 1 mm displacement crosses a 0.5 m input boundary; no snapping.
    xy = np.array([[[.499, 1.501], [1.499, 1.501], [2.1, 1.501]]])
    grid = m.c1.point_grid(xy)
    a = m.sample_canopy(paths, *grid.centres())
    b, _, source_dem, _ = m.direct_samples(chm, dem, grid)
    assert a["top"][0, 0] == 33 and a["bottom"][0, 0] == 30
    assert b["top"][0, 0] == b["bottom"][0, 0] == source_dem[0, 0] == 25
    assert a["candidate"][0, 0] and not b["candidate"][0, 0]
    assert b["valid"][0, 0] and b["missing"][0, 1] and not b["outside"][0, 1]
    assert b["state"][0, 1] == 2 and b["state"][0, 2] == 96
    assert b["outside"][0, 2] and not b["valid"][0, 2]


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    arrays, metadata, segments, _, _, height = authored()
    source, canopy, raw, step2a = [tmp_path/p for p in ("t5", "c1", "raw", "step2a")]
    for p in (source/"t5-2", source/"t5-3", canopy, raw, step2a):
        p.mkdir(parents=True, exist_ok=True)
    data = {"t5-3/voxels": arrays["voxels"], "t5-2/building_ids": arrays["ids"],
        "t5-2/building_height": height, "t5-2/dem": arrays["raw_dem"],
        "t5-3/effective_dem_abs": arrays["ground_abs"], "t5-2/centres_xy": arrays["centres_xy"],
        "t5-2/evaluation_mask": arrays["roi"]}
    outputs = {}
    for key, values in data.items():
        path = source/(key+".npy")
        np.save(path, values, allow_pickle=False)
        outputs[key+".npy"] = m.env.sha256(path)
    path = source/"t5-3/segments.json"
    path.write_text(json.dumps(segments.tolist()))
    outputs["t5-3/segments.json"] = m.env.sha256(path)
    xy = arrays["centres_xy"]
    bounds = (float(np.floor(xy[..., 0].min())), float(np.floor(xy[..., 1].min())),
              float(np.ceil(xy[..., 0].max())), float(np.ceil(xy[..., 1].max())))
    grid = m.env.GridSpec(bounds)
    dem, chm = source/"t5-2/terrain.tif", raw/"chm.tif"
    raster(dem, np.full((grid.height, grid.width), 25.), grid)
    raster(chm, np.full((grid.height, grid.width), 5.), grid)
    outputs["t5-2/terrain.tif"] = m.env.sha256(dem)
    report_path = source/"report.json"
    report_path.write_text(json.dumps(dict(outputs=outputs)))
    watch = m.Watch(source)
    watch.capture("report", "report.json", m.env.sha256(report_path))
    for key, sha in outputs.items():
        watch.capture(key, key, sha)
    monkeypatch.setattr(m, "load_candidate", lambda *a: (arrays, metadata, {}, dict(outputs=outputs), watch))
    snap = raw/"hag.txt"
    snap.write_text("synthetic HAG metres")
    acq, evidence = raw/"acq.json", raw/"evidence.json"
    acq.write_text("{}")
    evidence.write_text("{}")
    constants = dict(T5_SHA=m.env.sha256(report_path), DEM_SHA=m.env.sha256(dem), CHM_SHA=m.env.sha256(chm),
                     ACQUISITION_SHA=m.env.sha256(acq), EVIDENCE_SHA=m.env.sha256(evidence))
    for key, value in constants.items():
        monkeypatch.setattr(m.c1, key, value)
    north, _, _, _ = m.direct_samples(chm, dem, grid)
    files = {}
    for key, name in (("top", "canopy_top_z.tif"), ("bottom", "canopy_bottom_z.tif"), ("state", "height_envelope_state.tif")):
        files[name] = m.env.write_verified(canopy/name, north[key], grid, None if key == "state" else -9999., m.c1.VERTICAL)
    refs = dict(watch.identities)
    refs.update({p.name: dict(sha256=m.env.sha256(p)) for p in (chm, acq, evidence)})
    record = dict(status="COMPLETED", schema="ouem-candidate-b-experimental-height-envelope/v0.1",
        terrain_integration_ready=False, terrain_identity=dict(terrain_sha256=constants["DEM_SHA"]),
        cr_model=m.env.ConstantCR(.6).specification(), vertical_reference=dict(working_assumption=m.c1.VERTICAL),
        inputs=[refs], outputs=files, grid_spec=grid.metadata(), formulas=dict(top="DEM+CHM", bottom="DEM+.4*CHM"),
        chm_lineage=dict(hag_evidence=dict(snapshot_path=snap.name, snapshot_sha256=m.env.sha256(snap))))
    manifest = canopy/"manifest.json"
    manifest.write_text(json.dumps(record))
    monkeypatch.setattr(m, "C1_SHA", m.env.sha256(manifest))
    (step2a/"report.json").write_text(json.dumps(dict(outputs={}, inputs=watch.identities, source_report_sha256=constants["T5_SHA"])))
    monkeypatch.setattr(m, "STEP2A_SHA", m.env.sha256(step2a/"report.json"))
    monkeypatch.setattr(m, "implementation_identity", lambda: dict(test="synthetic"))
    return dict(source_run=source, envelope_manifest=manifest, chm=chm,
                acquisition_record=acq, chm_evidence=evidence, step2a_run=step2a)


def test_saved_pair_public_api_and_reproducibility(bundle, tmp_path):
    a = m.run(**bundle, output_dir=tmp_path/"a")
    b = m.run(**bundle, output_dir=tmp_path/"b")
    assert a["status"] == b["status"] == "COMPLETED"
    assert a == b
    assert a["derived_profile"] == m.DERIVED_PROFILE
    assert a["integration_qa"]["tree_voxels"] > 0
    base = np.load(bundle["source_run"]/"t5-3/voxels.npy")
    current = np.load(tmp_path/"a/current.npy")
    absent = np.load(tmp_path/"a/no_canopy.npy")
    tree = np.load(tmp_path/"a/tree_mask.npy")
    np.testing.assert_array_equal(np.where(tree, 0, current), absent)
    np.testing.assert_array_equal(absent, base)
    assert not (tree & (absent != 0)).any()
    assert a["input_immutability"] == "PASS" and a["independent_pair_qa"] == "PASS"


@pytest.mark.parametrize("key", ["chm", "envelope_manifest", "acquisition_record", "chm_evidence"])
def test_hash_mismatch_blocks(bundle, tmp_path, key):
    with bundle[key].open("ab") as stream:
        stream.write(b" ")
    result = m.run(**bundle, output_dir=tmp_path/"out")
    assert result["status"] == "BLOCKED" and "SHA-256 mismatch" in result["error"]
    assert not (tmp_path/"out/current.npy").exists()


@pytest.mark.parametrize("fault", ["write", "mutation", "publication", "engine_pair"])
def test_failure_never_marks_completed(bundle, tmp_path, monkeypatch, fault):
    original = m.write_array
    def write(out, name, values):
        if fault == "write" and name == "current":
            raise OSError("injected disk failure")
        if fault == "mutation" and name == "B/source_chm":
            with bundle["chm"].open("ab") as stream:
                stream.write(b" ")
        return original(out, name, values)
    monkeypatch.setattr(m, "write_array", write)
    if fault == "publication":
        monkeypatch.setattr(m, "publish", lambda *a: (_ for _ in ()).throw(OSError("injected rename failure")))
    if fault == "engine_pair":
        original_integrate = m.integrate
        def integrate(*args, **kwargs):
            result = original_integrate(*args, **kwargs)
            result[0][0, 0, 0] = -2
            return result
        monkeypatch.setattr(m, "integrate", integrate)
    result = m.run(**bundle, output_dir=tmp_path/"out")
    assert result["status"] == "BLOCKED"
    marker = tmp_path/"out"/("failure.json" if fault == "publication" else "manifest.json")
    assert json.loads(marker.read_text())["status"] == "BLOCKED"
    if fault == "mutation":
        assert result["input_immutability"].startswith("FAILED")


def test_existing_and_nested_output_rejected(bundle, tmp_path):
    (tmp_path/"out").mkdir()
    with pytest.raises(FileExistsError):
        m.run(**bundle, output_dir=tmp_path/"out")
    with pytest.raises(GeometryValidationError):
        m.run(**bundle, output_dir=bundle["source_run"]/"out")
