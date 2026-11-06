"""Small authored saved pairs; pinned public Solar API, never GVI."""
import json

import numpy as np
import pytest
import rasterio

from ouem import candidate_b_solar as m
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_candidate_b_canopy_run import bundle as canopy_bundle


@pytest.fixture
def scene():
    shape = (14, 9, 12)
    base = np.zeros(shape, dtype="int8")
    base[..., 0] = 1
    base[4, 4, 1:7] = -3
    current = base.copy()
    current[7, 2, 2] = -2  # Observer itself is in TREE; it must not move.
    ids = np.zeros(shape[:2], int)
    ids[4, 4] = 17
    segments = np.empty(ids.shape, object)
    for ij in np.ndindex(ids.shape):
        segments[ij] = [[0., 6.]] if ids[ij] else []
    a = dict(building_ids=ids, building_heights=np.where(ids > 0, 6., 0.),
             building_segments=segments, effective_dem=np.zeros(ids.shape))
    i, j = np.indices(ids.shape)
    xy = np.stack((j+.5, i+.5), axis=2)
    grid = dict(axis0_true_azimuth_deg=0., rectangle_vertices_lonlat=[[139., 35.], [139., 35.001], [139.001, 35.001], [139.001, 35.]])
    return current, base, a, grid, np.full(ids.shape, 3.), np.full(ids.shape, 2.), xy, 25.


def test_public_solar_geometry_tree_transmittance_and_common_observers(scene, monkeypatch):
    import voxcity.simulator.solar.radiation as radiation
    original = radiation.get_direct_solar_irradiance_map
    calls = []
    def capture(city, azimuth, elevation, dni, **kwargs):
        calls.append((azimuth, elevation, dni, kwargs.copy(), city.buildings.ids.copy(), city.dem.elevation.copy()))
        return original(city, azimuth, elevation, dni, **kwargs)
    monkeypatch.setattr(radiation, "get_direct_solar_irradiance_map", capture)
    result, qa = m.calculate_pair(*scene)
    full = 800*np.sin(np.pi/4)
    assert len(calls) == 2
    assert calls[0][:4] == calls[1][:4]
    np.testing.assert_array_equal(calls[0][4], calls[1][4])
    np.testing.assert_array_equal(calls[0][5], calls[1][5])
    assert calls[0][:3] == (180., 45., 800.)
    assert calls[0][3]["view_point_height"] == 1.5 and not calls[0][3]["include_building_roofs"]
    assert calls[0][3]["tree_k"] == .6 and calls[0][3]["tree_lad"] == 1.
    # Independent geometry: toward-south/up ray sees the wall from north, not south.
    assert result["no_canopy"][6, 4] == 0
    assert result["no_canopy"][2, 4] == pytest.approx(full)
    assert result["no_canopy"][11, 4] == pytest.approx(full)  # Beyond roof's 45-degree reach.
    assert np.isnan(result["current"][4, 4])
    assert result["observer_index"][7, 2] == 2
    assert result["observer_xyz"][7, 2, 2] == 27.5
    assert result["origin_class_current"][7, 2] == -2
    assert result["origin_class_no_canopy"][7, 2] == 0
    # Half-cell diagonal path through observer's TREE: exp(-k*LAD*sqrt(.5)).
    assert result["current"][7, 2] == pytest.approx(full*np.exp(-.6*np.sqrt(.5)))
    assert (result["reduction"][result["observer_valid"]] >= -1e-9).all()
    assert qa["beyond_tolerance_cells"] == 0


def test_no_tree_exact_equality_and_reproducibility(scene):
    current, absent, *rest = scene
    a, _ = m.calculate_pair(absent, absent, *rest)
    b, _ = m.calculate_pair(absent, absent, *rest)
    np.testing.assert_array_equal(a["current"], a["no_canopy"])
    np.testing.assert_array_equal(a["current"], b["current"])
    assert not a["reduction"][a["observer_valid"]].any()


def test_sun_direction_rotated_and_observer_rejection(scene):
    direction, _ = m.shadow.sun_direction(dict(shape=[14, 9, 12], origin_lonlat=[139.6, 35.65],
        u_step_lonlat=[0., 1e-5], v_step_lonlat=[1e-5, 0.]))
    np.testing.assert_allclose(direction, [-2**-.5, 0, 2**-.5], atol=1e-14)
    current, absent, a, _, _, _, xy, d0 = scene
    bad = current.copy()
    bad[0, 0, 0] = 0
    with pytest.raises(GeometryValidationError):
        m.common_observers(bad, absent, a["building_ids"], xy, d0)
    # Out-of-Z observer is rejected, not moved or assigned finite zero.
    with pytest.raises(GeometryValidationError, match="outside Z"):
        m.common_observers(current[..., :2], absent[..., :2], a["building_ids"], xy, d0)


@pytest.mark.parametrize("fault", ["negative", "increase", "above", "nan", "finite_excluded"])
def test_invalid_solar_rejected(fault):
    valid = np.array([[True, False]])
    now, absent = np.array([[100., np.nan]]), np.array([[200., np.nan]])
    if fault == "negative": now[0, 0] = -1e-15
    if fault == "increase": now[0, 0] = 201
    if fault == "above": absent[0, 0] = 801
    if fault == "nan": now[0, 0] = np.nan
    if fault == "finite_excluded": now[0, 1] = 0
    with pytest.raises(GeometryValidationError):
        m.validate_solar(now, absent, valid)


def test_small_negative_difference_reported_without_clamping():
    delta, qa = m.validate_solar(np.array([[100.+5e-10]]), np.array([[100.]]), np.ones((1, 1), bool))
    assert delta[0, 0] < 0 and qa["negative_reduction_cells"] == 1
    assert qa["beyond_tolerance_cells"] == 0


def test_actual_centres_non_square_export_values_masks_and_corners(tmp_path):
    i, j = np.indices((5, 7))
    xy = np.stack((j+.501, i+.499), axis=2)
    roi = (i >= 1) & (i < 4) & (j >= 1) & (j < 6)
    values = (10*i+j).astype(float)
    values[3, 1] = np.nan
    report = m.export_raster(tmp_path/"solar.tif", values, xy, roi, [1, 1, 6, 4])
    with rasterio.open(tmp_path/"solar.tif") as ds:
        np.testing.assert_array_equal(ds.read(1), [[-9999, 32, 33, 34, 35], [21, 22, 23, 24, 25], [11, 12, 13, 14, 15]])
        assert ds.xy(0, 0) == (1.5, 3.5) and ds.xy(2, 4) == (5.5, 1.5)
        assert ds.units == ("W/m2",) and ds.crs.to_epsg() == 6677
    assert report["max_registration_error_m"] == pytest.approx(np.sqrt(2)*.001)
    codes = np.where(np.isfinite(values), 1, 0).astype("uint8")
    m.export_raster(tmp_path/"mask.tif", codes, xy, roi, [1, 1, 6, 4], mask=True)
    with rasterio.open(tmp_path/"mask.tif") as ds:
        assert ds.read(1)[0, 0] == 0 and ds.read_masks(1)[0, 0] == 255
    xy[1, 1] += .02
    with pytest.raises(GeometryValidationError, match=".01m"):
        m.export_raster(tmp_path/"bad.tif", values, xy, roi, [1, 1, 6, 4])


@pytest.fixture
def saved(scene, monkeypatch):
    current, absent, a, grid, high, low, xy, d0 = scene
    roi = np.zeros(xy.shape[:2], bool)
    roi[2:12, 1:8] = True
    valid = a["building_ids"] == 0
    baseline = np.where(valid, 1, 255).astype("uint8")
    data = dict(current=current, absent=absent, a=a, grid=grid, high=high, low=low,
        arrays=dict(centres_xy=xy, roi=roi), metadata=dict(d0_effective_abs_m=d0, evaluation_bounds=[1, 2, 8, 12]),
        direction=[-2**-.5, 0, 2**-.5], baseline=baseline, watches={})
    monkeypatch.setattr(m, "load_inputs", lambda *args: data)
    monkeypatch.setattr(m, "implementation_identity", lambda: dict(test="synthetic"))
    return data


def test_run_saved_arrays_geotiffs_and_reproducibility(saved, tmp_path):
    a = m.run("pair", "t5", "prior", tmp_path/"a")
    b = m.run("pair", "t5", "prior", tmp_path/"b")
    assert a["status"] == b["status"] == "COMPLETED" and a == b
    assert a["observer_qa"]["inside_TREE"] == 1
    assert a["statistics"]["evaluation"]["reduction_cells"] > 0
    assert a["step2a_comparison"]["domain"]["different"] > 0  # Diagnostic, not an equality gate.
    assert json.loads((tmp_path/"a/manifest.json").read_text())["status"] == "COMPLETED"
    with pytest.raises(GeometryValidationError, match="new run"):
        m.run("pair", "t5", "prior", tmp_path/"a")


@pytest.mark.parametrize("fault", ["save", "publish", "mutation"])
def test_failures_never_complete(saved, tmp_path, monkeypatch, fault):
    if fault == "save":
        monkeypatch.setattr(m, "export_raster", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    elif fault == "publish":
        monkeypatch.setattr(m.c2, "publish", lambda *a: (_ for _ in ()).throw(OSError("rename")))
    else:
        original = m.direct_solar_at_saved_grid
        def mutate(vox, a, *args, **kwargs):
            result = original(vox, a, *args, **kwargs)
            a["effective_dem"][0, 0] += 1
            return result
        monkeypatch.setattr(m, "direct_solar_at_saved_grid", mutate)
    result = m.run("pair", "t5", "prior", tmp_path/"out")
    assert result["status"] == "BLOCKED"
    path = tmp_path/"out"/("failure.json" if fault == "publish" else "manifest.json")
    assert json.loads(path.read_text())["status"] == "BLOCKED"


def saved_chain(canopy_bundle, tmp_path, monkeypatch):
    """Build only synthetic saved artifacts; loader must bind the complete chain."""
    args = canopy_bundle
    old = m.c2.load_candidate
    arrays, meta, probe, t5, watch = old(args["source_run"], m.c2.c1.T5_SHA)
    prior_path = args["step2a_run"]/"report.json"
    prior = json.loads(prior_path.read_text())
    classes = np.where(arrays["ids"] == 0, 1, 255).astype("uint8")
    np.save(args["step2a_run"]/"domain_classes.npy", classes, allow_pickle=False)
    prior.update(settings=dict(azimuth_true_deg=180., elevation_deg=45.),
        outputs={"domain_classes.npy":m.env.sha256(args["step2a_run"]/"domain_classes.npy")})
    prior_path.write_text(json.dumps(prior))
    monkeypatch.setattr(m.c2, "STEP2A_SHA", m.env.sha256(prior_path))
    pair = tmp_path/"pair"
    assert m.c2.run(**args, output_dir=pair)["status"] == "COMPLETED"
    monkeypatch.setattr(m, "C2_SHA", m.env.sha256(pair/"manifest.json"))
    grid = dict(rectangle_lonlat=[[139., 35.], [139., 35.001], [139.001, 35.001], [139.001, 35.]])
    monkeypatch.setattr(m, "load_candidate", lambda *a, **k: (arrays, meta, probe, dict(t5, grid=grid), watch))
    return pair, args


def test_bound_loader_all_inputs_and_readonly_arrays(canopy_bundle, tmp_path, monkeypatch):
    pair, args = saved_chain(canopy_bundle, tmp_path, monkeypatch)
    loaded = m.load_inputs(pair, args["source_run"], args["step2a_run"])
    assert not loaded["current"].flags.writeable and not loaded["absent"].flags.writeable
    assert len(loaded["watches"]["pair"].identities) == 41
    for watch in loaded["watches"].values():
        watch.unchanged()


@pytest.mark.parametrize("fault", ["manifest", "current", "upstream"])
def test_saved_hash_mismatch_refused_before_solar(canopy_bundle, tmp_path, monkeypatch, fault):
    pair, args = saved_chain(canopy_bundle, tmp_path, monkeypatch)
    path = pair/("manifest.json" if fault == "manifest" else "current.npy") if fault != "upstream" else args["chm"]
    with path.open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(GeometryValidationError, match="SHA-256 mismatch|size mismatch"):
        m.load_inputs(pair, args["source_run"], args["step2a_run"])
