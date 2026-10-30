"""Pinned CPU characterization; analytic chords, never an engine-derived oracle.

See docs/experiments/b2_gvi/B2_CPU_GVI_Synthetic_Characterization_v0.1.md.
Private fast kernels are used only to diagnose the audited execution path.
"""
import math

import numpy as np
import pytest

ATOL = 1e-12


@pytest.fixture(scope="module", autouse=True)
def cpu_runtime():
    import matplotlib
    matplotlib.use("Agg")
    from numba import get_num_threads, set_num_threads
    from ouem.komae_integration import voxcity_provenance
    assert voxcity_provenance()["verified"]
    previous = get_num_threads()
    set_num_threads(2)
    yield
    set_num_threads(previous)


def score(length, k=0.5, lad=1.0):
    """Independent Beer-Lambert scalar, not a tracer."""
    return 1 - math.exp(-k * lad * length)


def point(a, origin=(1, 1, 2), rays=((1, 0, 0),), mesh=1., k=.5, lad=1.):
    from voxcity.simulator.visibility.view import compute_vi_generic
    return compute_vi_generic(np.array(origin, dtype=float), a,
                              np.array(rays, dtype=float), (-2,), mesh, k, lad, True)


def fast_point(a, origin, ray, mesh=1., k=.5, lad=1.):
    from voxcity.simulator.common.raytracing import (
        _prepare_masks_for_vi, _trace_ray_inclusion_masks,
    )
    tree, target, _, blocker = _prepare_masks_for_vi(a, (-2,), True)
    hit, trans = _trace_ray_inclusion_masks(
        tree, target, blocker, np.array(origin, dtype=float),
        np.array(ray, dtype=float), mesh, k, lad)
    return 1 - trans if hit else 0.


@pytest.mark.parametrize("case,length,k,lad,mesh", [
    ("no-tree", 0, .5, 1, 1), ("one", 1, .5, 1, 1),
    ("deep", 1, .5, 1, 1), ("distant", 1, .5, 1, 1),
    ("building", 0, .5, 1, 1), ("surface", 0, .5, 1, 1),
    ("inside", .5, .5, 1, 1), ("above", 0, .5, 1, 1),
    ("one", 1, 0, 1, 1), ("one", 1, 1, 1, 1),
    ("one", 1, .5, 2, 1), ("one", 1, .5, 0, 1),
    ("one", 2, .5, 1, 2), ("one", 1, 4.6, 1, 1),
    ("cutoff", 0, 4.61, 1, 1),
])
def test_axial_chords(case, length, k, lad, mesh):
    a = np.zeros((8, 4, 5), dtype=np.int8)
    origin = (1, 1, 2)
    if case != "no-tree":
        a[3, 1, 2] = -2
    if case == "deep":
        a[3:7, 1, 2] = -2
    if case == "distant":
        a[3, 1, 2] = 0
        a[6, 1, 2] = -2
    if case in ("building", "surface"):
        a[2, 1, 2] = -3 if case == "building" else 1
    if case == "inside":
        origin = (3, 1, 2)
    if case == "above":
        origin = (1, 1, 3)
    expected = score(length, k, lad)
    generic = point(a, origin, mesh=mesh, k=k, lad=lad)
    fast = fast_point(a, origin, (1, 0, 0), mesh, k, lad)
    print(f"{case} k={k} LAD={lad} mesh={mesh}: expected={expected:.15g} generic={generic:.15g} fast={fast:.15g}")
    assert generic == pytest.approx(expected, abs=ATOL, rel=0)
    assert fast == pytest.approx(expected, abs=ATOL, rel=0)


def test_diagonal_and_corner_obstruction():
    a = np.zeros((5, 5, 5), dtype=np.int8)
    a[2, 2, 2] = -2
    ray, origin = (1, 1, 0), (1, 1, 2)
    expected = score(math.sqrt(2))
    assert point(a, origin, (ray,)) == pytest.approx(expected, abs=ATOL, rel=0)
    assert fast_point(a, origin, ray) == pytest.approx(expected, abs=ATOL, rel=0)
    # Corner contact with the +y side cell: generic checks both sides;
    # fast selects +x first and never visits this +y-only side cell.
    a[1, 2, 2] = -3
    assert point(a, origin, (ray,)) == 0
    assert fast_point(a, origin, ray) == pytest.approx(expected, abs=ATOL, rel=0)


@pytest.mark.parametrize("ray", [(1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                      (0, -1, 0), (0, 0, 1), (0, 0, -1)])
def test_domain_exit(ray):
    a = np.zeros((4, 4, 4), dtype=np.int8)
    assert point(a, rays=(ray,)) == 0
    assert fast_point(a, (1, 1, 2), ray) == 0


def test_all_ray_denominator():
    a = np.zeros((6, 5, 5), dtype=np.int8)
    a[3, 1, 2], a[1, 0, 2] = -2, -3
    # One target, one building, one side exit, one top exit.
    rays = ((1, 0, 0), (0, -1, 0), (-1, 0, 0), (0, 0, 1))
    assert point(a, rays=rays) == pytest.approx(score(1)/4, abs=ATOL, rel=0)


def public_map(a, fast, monkeypatch, **kwargs):
    import matplotlib.pyplot as plt
    from voxcity.models import VoxCity, VoxelGrid, GridMetadata
    from voxcity.simulator.visibility import view
    # Spies delegate to the real kernels; record completion, including fallback.
    calls = []
    with monkeypatch.context() as patch:
        for name in ("_compute_vi_map_generic_fast", "compute_vi_map_generic"):
            original = getattr(view, name)
            def spy(*args, _name=name, _original=original, **kw):
                try:
                    result = _original(*args, **kw)
                except Exception as exc:
                    calls.append((_name, type(exc).__name__, str(exc)))
                    raise
                calls.append(_name)
                return result
            patch.setattr(view, name, spy)
        scene = VoxCity(VoxelGrid(a, GridMetadata("synthetic", (0, 0, 6, 3), 1.)),
                        None, None, None, None)
        before = set(plt.get_fignums())
        original_array = a.copy()
        try:
            result = view.get_view_index(
                scene, mode=None, hit_values=(-2,), inclusion_mode=True,
                fast_path=fast, N_azimuth=kwargs.pop("N_azimuth", 1), N_elevation=1,
                elevation_min_degrees=0, elevation_max_degrees=0,
                tree_k=.5, tree_lad=1., obj_export=False, **kwargs)
            assert set(plt.get_fignums()) - before  # API really creates a plot.
        finally:
            for number in set(plt.get_fignums()) - before:
                plt.close(number)
        assert set(plt.get_fignums()) == before
        np.testing.assert_array_equal(a, original_array)
    if fast:
        # Characterize the observed failure rather than label fallback fast success.
        assert len(calls) == 2, calls
        name, error, message = calls[0]
        assert name == "_compute_vi_map_generic_fast"
        assert error == "TypingError"
        assert "getitem(array(bool, 1d, C), UniTuple(int64 x 3))" in message
        assert calls[1] == "compute_vi_map_generic"
    else:
        assert calls == ["compute_vi_map_generic"]
    return result


@pytest.mark.parametrize("fast", [False, True])
@pytest.mark.parametrize("height", [0., .9, 1., 1.5, 2., 9.])
def test_public_height_and_full_map(fast, height, monkeypatch):
    a = np.zeros((6, 3, 5), dtype=np.int8)
    a[:, :, 0] = 1
    a[3, :, 2] = -2
    expected = np.zeros((6, 3))
    if int(height) == 1:  # base transition z=1, origin z-index=2
        expected[:3, :] = score(1)
        expected[3, :] = score(.5)
    result = public_map(a, fast, monkeypatch, view_point_height=height)
    assert result.dtype == np.float64
    np.testing.assert_allclose(result, expected, atol=ATOL, rtol=0)
    print(f"map fast={fast} height={height}: finite={np.isfinite(result).sum()} sum={result.sum():.15g}")


@pytest.mark.parametrize("fast", [False, True])
@pytest.mark.parametrize("roofs", [False, True])
def test_public_surface_mask(fast, roofs, monkeypatch):
    a = np.zeros((6, 3, 5), dtype=np.int8)
    # Each column explicitly authored; no engine observer helper as oracle.
    a[:, :, 0] = 1
    a[0, 0, :] = 0  # no surface
    a[1, 0, 0] = 7  # water
    a[2, 0, 0] = -1  # negative support
    a[3, 0, :2] = -3  # roof only
    a[4, 0, 0] = 14  # positive No Data code is not automatically masked
    expected = np.zeros((6, 3))
    expected[0:3, 0] = np.nan
    if not roofs:
        expected[3, 0] = np.nan
    result = public_map(a, fast, monkeypatch, include_building_roofs=roofs)
    np.testing.assert_allclose(result, expected, atol=ATOL, rtol=0, equal_nan=True)


@pytest.mark.parametrize("fast", [False, True])
def test_public_four_ray_aggregation(fast, monkeypatch):
    a = np.zeros((6, 3, 5), dtype=np.int8)
    a[:, :, 0] = 1
    a[3, 1, 2] = -2
    result = public_map(a, fast, monkeypatch, N_azimuth=4)
    # At (1,1,2), +u hits TREE; -u and +/-v leave the domain.
    assert result[1, 1] == pytest.approx(score(1)/4, abs=ATOL, rel=0)


def test_direct_fast_map_with_shaped_unused_mask():
    """Diagnostic only: bypass wrapper's 1D placeholder, not a production fix."""
    from voxcity.simulator.common.raytracing import (
        _prepare_masks_for_vi, _compute_vi_map_generic_fast,
    )
    a = np.zeros((6, 3, 5), dtype=np.int8)
    a[:, :, 0] = 1
    a[3, :, 2] = -2
    tree, target, _, blocker = _prepare_masks_for_vi(a, (-2,), True)
    result = _compute_vi_map_generic_fast(
        a, np.array([[1., 0., 0.]]), 1, 1., .5, 1.,
        tree, target, np.zeros(a.shape, dtype=np.bool_), blocker, True, True, False)
    expected = np.zeros((6, 3))
    expected[:3] = score(1)
    expected[3] = score(.5)
    np.testing.assert_allclose(result, expected, atol=ATOL, rtol=0)
