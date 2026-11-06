"""Candidate B saved handoff; unchanged B2 settings and genuine small CPU probe."""
import json

import numpy as np
import pytest
import rasterio

from ouem import candidate_b_gvi as m
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_candidate_b_solar import scene as source_scene


@pytest.fixture
def inputs(source_scene, tmp_path, monkeypatch):
    current, absent, a, grid, _, _, xy, d0 = source_scene
    pair, sun, source, prior = [tmp_path/n for n in ("pair", "solar", "t5", "prior")]
    for root in (pair, sun, source, prior): root.mkdir()
    np.save(pair/"current.npy", current, allow_pickle=False)
    np.save(source/"base.npy", absent, allow_pickle=False)
    watches = {"pair":m.Watch(pair), "t5":m.Watch(source)}
    watches["pair"].capture("current", "current.npy")
    watches["t5"].capture("base", "base.npy")
    observer = m.solar.common_observers(current, absent, a["building_ids"], xy, d0)
    roi = np.zeros(xy.shape[:2], bool)
    roi[2:12, 1:8] = True
    values = dict(observer, roi=roi, centres_xy=xy, reduction=np.where(observer["observer_valid"], 0., np.nan))
    outputs = {}
    for name, data in values.items():
        outputs[name+".npy"] = m.c2.write_array(sun, name, data)
    target = m.env.GridSpec((1, 2, 8, 12))
    data = np.zeros((10, 7), dtype="float64")
    with rasterio.open(sun/"evaluation_current.tif", "w", driver="GTiff", count=1, width=7, height=10,
                       dtype="float64", crs=6677, transform=target.transform, nodata=-9999) as ds:
        ds.write(data, 1)
    checks = [dict(row=r, col=c, pixel_centre=[1+c+.5, 12-r-.5], actual_centre=[1+c+.5, 12-r-.5])
              for r, c in ((0, 0), (0, 6), (9, 0), (9, 6), (5, 3))]
    outputs["evaluation_current.tif"] = dict(sha256=m.env.sha256(sun/"evaluation_current.tif"),
        bytes=(sun/"evaluation_current.tif").stat().st_size, grid=target.metadata(), coordinate_checks=checks)
    record = dict(profile="ouem-candidate-b-real-solar/v0.1", status="COMPLETED", terrain_integration_ready=False,
        outputs=outputs, inputs={k:w.identities for k, w in watches.items()},
        input_roots=dict({k:str(w.root) for k, w in watches.items()}, step2a=str(prior)))
    def bind():
        (sun/"manifest.json").write_text(json.dumps(record))
        monkeypatch.setattr(m, "SOLAR_SHA", m.env.sha256(sun/"manifest.json"))
    bind()
    saved = dict(current=current, absent=absent, arrays=dict(ids=a["building_ids"], centres_xy=xy, roi=roi),
                 metadata=dict(d0_effective_abs_m=d0), grid=grid, watches=watches)
    monkeypatch.setattr(m.solar, "load_inputs", lambda *args: saved)
    monkeypatch.setattr(m, "implementation_identity", lambda: dict(test="synthetic"))
    monkeypatch.setattr(m.solar, "calculate_pair", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Solar forbidden")))
    return dict(pair_run=pair, solar_run=sun, source_run=source), record, bind


def test_small_public_probe_no_tree_and_two_thread_settings():
    before = m.settings()
    result = m.synthetic_probe(dict(rectangle_vertices_lonlat=[[139., 35.], [139.001, 35.001]]))
    assert result["no_canopy_public_zero"] and result["repeat_equal"]
    assert result["current"]["positive"] > 0 and result["no_canopy"]["max"] == 0
    assert result["current_timings"][0]["numba_threads"] == 2
    assert result["current_timings"][0]["sampled_peak_working_set_bytes"] > 0
    assert m.settings() == before and before["N_azimuth"]*before["N_elevation"] == 2400
    az = np.deg2rad(np.linspace(0, 360, 120, endpoint=False))[None, :]
    el = np.deg2rad(np.linspace(-30, 30, 20))[:, None]
    largest = np.maximum(np.maximum(abs(np.cos(el)*np.cos(az)), abs(np.cos(el)*np.sin(az))), abs(np.sin(el)))
    # Independent analytic path from centre of the first target unit cube.
    expected = np.mean(1-np.exp(-.5*(.5/largest)))
    assert result["current"]["max"] == pytest.approx(expected, abs=1e-12)


def test_bound_solar_observers_and_origin_strata(inputs):
    args, _, _ = inputs
    saved = m.load_inputs(**args)
    assert saved["observer"]["origin_class_current"][7, 2] == -2
    assert saved["observer"]["observer_index"][7, 2] == 2
    assert saved["observer"]["observer_xyz"][7, 2, 2] == 27.5
    values = np.where(saved["observer"]["observer_valid"], .2, np.nan)
    stats = m.statistics(values, saved["observer"]["observer_valid"], saved["arrays"]["roi"], saved["observer"]["origin_class_current"])
    assert stats["domain"]["TREE"]["count"] == 1
    assert stats["evaluation"]["positive_fraction"] == 1


@pytest.mark.parametrize("fault", ["manifest", "array", "index", "xyz", "roi"])
def test_hash_or_observer_mismatch_blocks(inputs, fault):
    args, record, bind = inputs
    if fault in ("manifest", "array"):
        path = args["solar_run"]/("manifest.json" if fault == "manifest" else "observer_valid.npy")
        with path.open("ab") as stream: stream.write(b" ")
    else:
        name = {"index":"observer_index", "xyz":"observer_xyz", "roi":"roi"}[fault]
        path = args["solar_run"]/(name+".npy")
        data = np.load(path)
        if fault == "xyz": data[0, 0, 2] += .01
        elif fault == "roi": data[0, 0] = True
        else: data[0, 0] += 1
        with path.open("wb") as stream: np.save(stream, data, allow_pickle=False)
        record["outputs"][name+".npy"].update(sha256=m.env.sha256(path), bytes=path.stat().st_size)
        bind()
    with pytest.raises(GeometryValidationError): m.load_inputs(**args)


def fake_calculation(voxels, grid, threads):
    assert threads == 2
    valid = m.b2.observers(voxels)[1]
    values = np.where(valid, .2 if np.any(voxels == -2) else 0., np.nan).astype("float64")
    return values, dict(wall_seconds=.01, process_cpu_seconds=.02, sampled_peak_working_set_bytes=100000, numba_threads=2)


def test_benchmark_gate_full_twice_then_roi_and_same_solar_grid(inputs, tmp_path, monkeypatch):
    args, _, _ = inputs
    calls = []
    def calculate(voxels, grid, threads):
        calls.append(voxels.shape)
        return fake_calculation(voxels, grid, threads)
    monkeypatch.setattr(m.b2, "calculate", calculate)
    bench = m.run(**args, output_dir=tmp_path/"bench", benchmark=True)
    assert bench["feasible"] and bench["status"] == "BENCHMARK_COMPLETED"
    calls.clear()
    report = m.run(**args, output_dir=tmp_path/"out", benchmark_report=tmp_path/"bench/manifest.json")
    assert report["status"] == "COMPLETED", report.get("error")
    assert calls == [(14, 9, 12), (14, 9, 12)]  # Full domain both times, never ROI-only.
    assert report["full_repeat_equal"] and not report["no_canopy"]["full_public_api_calculated"]
    assert report["observer_agreement"].startswith("PASS")
    derived = np.load(tmp_path/"out/no_canopy_theoretical_zero.npy")
    valid = np.load(tmp_path/"out/observer_valid.npy")
    assert (derived[valid] == 0).all() and np.isnan(derived[~valid]).all()
    with rasterio.open(tmp_path/"out/evaluation_gvi.tif") as ds:
        assert ds.crs.to_epsg() == 6677 and ds.shape == (10, 7) and ds.units == ("1",)
        assert ds.xy(0, 0) == (1.5, 11.5) and ds.xy(9, 6) == (7.5, 2.5)
    with rasterio.open(tmp_path/"out/evaluation_observer_origin_class.tif") as ds:
        assert set(np.unique(ds.read(1))) == {0, 1, 2}


@pytest.mark.parametrize("fault", ["missing_receipt", "infeasible", "range", "write", "publish", "repeat", "overload", "input_mutation"])
def test_gate_and_partial_failure_never_complete(inputs, tmp_path, monkeypatch, fault):
    args, _, _ = inputs
    monkeypatch.setattr(m.b2, "calculate", fake_calculation)
    m.run(**args, output_dir=tmp_path/"bench", benchmark=True)
    receipt = tmp_path/"bench/manifest.json"
    if fault == "infeasible":
        record = json.loads(receipt.read_text())
        record["feasible"] = False
        receipt.write_text(json.dumps(record))
    if fault in ("range", "repeat", "overload", "input_mutation"):
        calls = []
        def calculate(voxels, grid, threads):
            values, timing = fake_calculation(voxels, grid, threads)
            calls.append(1)
            if fault == "range": values[0, 0] = 2
            if fault == "repeat" and len(calls) == 2: values[0, 0] += .01
            if fault == "overload": timing["wall_seconds"] = 601
            if fault == "input_mutation" and len(calls) == 1:
                with (args["pair_run"]/"current.npy").open("ab") as stream: stream.write(b" ")
            return values, timing
        monkeypatch.setattr(m.b2, "calculate", calculate)
    if fault == "write": monkeypatch.setattr(m, "export_raster", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    if fault == "publish": monkeypatch.setattr(m.c2, "publish", lambda *a: (_ for _ in ()).throw(OSError("rename")))
    result = m.run(**args, output_dir=tmp_path/"out", benchmark_report=None if fault == "missing_receipt" else receipt)
    assert result["status"] == "BLOCKED"
    expected = dict(missing_receipt="receipt required", infeasible="receipt does not bind", range="outside dimensionless",
                    write="disk", publish="rename", repeat="arrays differ", overload="exceeded feasibility", input_mutation="input changed")
    assert expected[fault] in result["error"]
    if fault == "overload": assert len(calls) == 1
    name = "failure.json" if fault == "publish" else "manifest.json"
    assert json.loads((tmp_path/"out"/name).read_text())["status"] == "BLOCKED"
