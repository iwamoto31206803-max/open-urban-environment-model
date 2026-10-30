"""Independent box-intersection oracles for the pinned public CPU solar API.

Expected geometry, formula and tolerances are fixed before execution in
docs/experiments/real_komae_solar/B1_PHYSICAL_SANITY_PHASE1.md.
No raytracing, orientation or solar kernel internals are called as an oracle.
"""
import math

import numpy as np
import pytest

from ouem import real_komae_solar as runner


SHAPE = (32, 32, 20)
D0 = 20.0
AZIMUTH, ELEVATION, DNI = 135.0, 35.0, 800.0
ATOL = 1e-9  # Absolute W/m2; no relative tolerance.
FLAT = DNI * math.sin(math.radians(ELEVATION))
# Independent north/east/up formula, not VoxCity's direction helper.
SUN = np.array([math.cos(math.radians(ELEVATION)) * math.cos(math.radians(AZIMUTH)),
                math.cos(math.radians(ELEVATION)) * math.sin(math.radians(AZIMUTH)),
                math.sin(math.radians(ELEVATION))])
BUILDING_XY = (12, 16, 12, 16)
TREE_XY = (8, 24, 8, 24)


@pytest.fixture(scope="module", autouse=True)
def pinned_engine():
    from numba import get_num_threads, set_num_threads
    from ouem.komae_integration import voxcity_provenance
    assert voxcity_provenance()["verified"]
    previous = get_num_threads()
    set_num_threads(2)
    yield
    set_num_threads(previous)


def scene(*, building=0, tree_top=0):
    """Public allocator, then append only air to a fixed synthetic test domain."""
    from voxcity.generator.voxelizer import Voxelizer
    shape = SHAPE[:2]
    ids = np.zeros(shape, dtype=int)
    if building:
        x0, x1, y0, y1 = BUILDING_XY
        ids[x0:x1, y0:y1] = 1
    heights = np.where(ids, float(building), 0.)
    segments = np.empty(shape, dtype=object)
    for ij in np.ndindex(shape):
        segments[ij] = [[0., float(building)]] if ids[ij] else []
    dem = np.full(shape, D0)
    top, bottom = np.zeros(shape), np.zeros(shape)
    if tree_top:
        x0, x1, y0, y1 = TREE_XY
        top[x0:x1, y0:y1] = tree_top
        bottom[x0:x1, y0:y1] = 3.
    classes = Voxelizer(1., 'Standard').generate_combined(
        heights, segments, ids, np.ones(shape, dtype=int), dem, top, bottom,
        print_class_info=False)
    assert classes.shape[2] <= SHAPE[2]
    classes = np.pad(classes, ((0, 0), (0, 0), (0, SHAPE[2]-classes.shape[2])))
    assert classes.dtype == np.int8
    roi = np.zeros(shape, dtype=bool)
    roi[4:28, 4:28] = True
    data = dict(building_ids=ids, building_heights=heights, building_segments=segments,
                terrain_H=dem, effective_ground_H=dem.copy(), effective_dem=np.zeros(shape),
                ground_indices=np.ones(shape, dtype=int), roi_mask=roi)
    return classes, data, top, bottom


def irradiance(classes, data, top, bottom):
    from voxcity.models import (VoxCity, VoxelGrid, GridMetadata, BuildingGrid,
                                LandCoverGrid, DemGrid, CanopyGrid)
    from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
    # CPU geometry is local metric u=north/v=east; CRS bounds do not drive rays.
    meta = GridMetadata('EPSG:6677', (0., 0., 32., 32.), 1.)
    model = VoxCity(VoxelGrid(classes, meta),
                    BuildingGrid(data['building_heights'], data['building_segments'],
                                 data['building_ids'], meta),
                    LandCoverGrid(np.ones(SHAPE[:2], dtype=int), meta),
                    DemGrid(data['effective_dem'], meta),
                    CanopyGrid(top, meta, bottom=bottom), extras={'rotation_angle': 0.})
    before = classes.copy()
    result = get_direct_solar_irradiance_map(
        model, AZIMUTH, ELEVATION, DNI, show_plot=False,
        tree_k=.6, tree_lad=1., view_point_height=1.5, include_building_roofs=False)
    assert np.array_equal(classes, before)
    return result


def box_length(ij, bounds):
    """Analytic slab intersection in metres, not voxel traversal/DDA.

    bounds are lower/upper edges in north/east/z above D0. Observer centre
    is (i+.5, j+.5, 2.5); all fixed sun-vector components are nonzero.
    """
    origin = np.array([ij[0]+.5, ij[1]+.5, 2.5])
    lower, upper = np.asarray(bounds[0]), np.asarray(bounds[1])
    times = np.vstack(((lower-origin)/SUN, (upper-origin)/SUN))
    enter = max(0., float(times.min(axis=0).max()))
    leave = float(times.max(axis=0).min())
    return max(0., leave-enter)


def tree_oracle(top):
    # Allocator adds one surface layer: bottom 3 -> edge 4; top -> top+1.
    bounds = ((8., 8., 4.), (24., 24., top+1.))
    lengths = np.array([[box_length((i, j), bounds) for j in range(32)] for i in range(32)])
    transmission = np.exp(-.6 * 1. * lengths)
    expected = FLAT * np.where(transmission < .01, 0., transmission)
    return lengths, transmission, expected


def test_unobstructed_flat_horizontal_irradiance():
    classes, data, top, bottom = scene()
    result = irradiance(classes, data, top, bottom)
    assert np.isfinite(result).all()
    np.testing.assert_allclose(result, FLAT, rtol=0, atol=ATOL)
    print(f'flat: expected={FLAT:.12f}, min={result.min():.12f}, '
          f'max={result.max():.12f}, max_error={np.max(np.abs(result-FLAT)):.3g}')


def test_building_direction_shadow_length_and_exact_box_oracle():
    classes, data, top, bottom = scene(building=8)
    assert np.all(classes[12:16, 12:16, 1:9] == -3)
    assert not np.any(classes[:, :, 9:] == -3)
    result = irradiance(classes, data, top, bottom)
    valid = data['building_ids'] == 0
    bounds = ((12., 12., 1.), (16., 16., 9.))
    blocked = np.array([[box_length((i, j), bounds) > 0 for j in range(32)] for i in range(32)])
    assert np.array_equal(np.isfinite(result), valid)
    np.testing.assert_allclose(result[valid], np.where(blocked[valid], 0., FLAT), rtol=0, atol=ATOL)
    # NW from corner (north=16,east=12): successive centres separated by sqrt(2).
    reach = (9.-2.5)/math.tan(math.radians(35.))
    distances = np.array([(n+.5)*math.sqrt(2.) for n in range(10)])
    actual = np.array([result[16+n, 11-n] == 0 for n in range(10)])
    assert np.array_equal(actual, distances < reach)
    last, first = distances[actual].max(), distances[~actual].min()
    assert last <= reach <= first and first-last <= math.sqrt(2.)+1e-12
    assert result[11, 16] == pytest.approx(FLAT, abs=ATOL, rel=0)  # SE is sunward.
    assert np.isfinite(result[16, 11]) and result[16, 11] == 0
    assert np.isnan(result[12, 12])  # Roof excluded, not zero irradiance.
    print(f'building: shadow_bearing=315deg, analytic_reach={reach:.12f}m, '
          f'last_shadow={last:.12f}m, first_clear={first:.12f}m, '
          f'valid={valid.sum()}, zero={(result[valid]==0).sum()}, '
          f'max_error={np.max(np.abs(result[valid]-np.where(blocked[valid],0.,FLAT))):.3g}')


@pytest.mark.parametrize('top', [5., 9.])
def test_homogeneous_tree_path_attenuation_and_cutoff(top):
    classes, data, high, low = scene(tree_top=top)
    assert np.all(classes[8:24, 8:24, 4:int(top)+1] == -2)
    current = irradiance(classes, data, high, low)
    absent = np.where(classes == -2, 0, classes).astype(classes.dtype)
    no_canopy = irradiance(absent, data, np.zeros_like(high), np.zeros_like(low))
    lengths, transmission, expected = tree_oracle(top)
    assert np.isfinite(current).all() and np.isfinite(no_canopy).all()
    np.testing.assert_allclose(current, expected, rtol=0, atol=ATOL)
    np.testing.assert_allclose(no_canopy, FLAT, rtol=0, atol=ATOL)
    assert np.array_equal(np.where(classes == -2, 0, classes), absent)
    assert np.all(no_canopy-current >= -ATOL)
    if top == 9.:
        below = transmission < .01
        above = (transmission >= .01) & (transmission < 1.)
        assert below.any() and above.any()
        assert np.all(current[below] == 0) and np.all(current[above] > 0)
        print(f'cutoff: zero_cells={below.sum()}, largest_T_cut={transmission[below].max():.12f}, '
              f'smallest_T_retained={transmission[above].min():.12f}')
    ij = (20, 10)
    print(f'tree top={top:g}: probe={ij}, L={lengths[ij]:.12f}m, '
          f'T={transmission[ij]:.12f}, expected={expected[ij]:.12f}, '
          f'actual={current[ij]:.12f}, max_error={np.max(np.abs(current-expected)):.3g}')


def test_observer_height_indices_and_low_occluder_discrimination():
    # Flat source/effective DEM H=20. g=1, surface edge H=21, observer k=2.
    for height in (1, 2):
        classes, data, top, bottom = scene(building=height)
        column = classes[16, 11]
        g = int(np.flatnonzero((column[1:] == 0) & (column[:-1] == 1))[0])+1
        assert g == 1 and column[g-1] == 1
        k = g+int(1.5/1.)
        observer_H = D0+(k+.5)
        assert k == 2 and observer_H == 22.5
        assert observer_H-(D0+g) == 1.5
        assert observer_H-data['terrain_H'][16, 11] == 2.5
        assert observer_H-data['effective_ground_H'][16, 11] == 2.5
        result = irradiance(classes, data, top, bottom)
        # At the nearest NW centre, the ray reaches the box at z=2.99512...;
        # top=2 cannot block it; top=3 can. This independently distinguishes
        # the actual origin from a hypothetical original-DEM+1.5m observer.
        expected = 0. if box_length((16, 11), ((12.,12.,1.),(16.,16.,height+1.))) else FLAT
        assert result[16, 11] == pytest.approx(expected, abs=ATOL, rel=0)
        print(f'observer: building_height={height}, g={g}, k={k}, H={observer_H}, '
              f'source_dem_offset=2.5m, surface_offset=1.5m, probe={result[16,11]:.12f}')


def test_ouem_pair_matches_independent_geometry_and_difference():
    classes, data, high, low = scene(building=8, tree_top=9.)
    absent = np.where(classes == -2, 0, classes).astype(classes.dtype)
    before = classes.copy(), absent.copy()
    assert (runner.AZIMUTH, runner.ELEVATION, runner.DNI) == (AZIMUTH, ELEVATION, DNI)
    grid = dict(shape=list(SHAPE), axis0_true_azimuth_deg=0., D0_effective_H_m=D0,
                rectangle_vertices_lonlat=[[139.,35.],[139.,35.001],[139.001,35.001],[139.001,35.]],
                halo_m=4.)
    arrays, qa = runner.solar_pair(classes, absent, data, grid, high, low)
    valid = data['building_ids'] == 0
    building_box = ((12.,12.,1.),(16.,16.,9.))
    blocked = np.array([[box_length((i,j), building_box)>0 for j in range(32)] for i in range(32)])
    _, _, tree_expected = tree_oracle(9.)
    expected_current = np.where(blocked, 0., tree_expected)
    expected_absent = np.where(blocked, 0., FLAT)
    for name, expected in [('solar_current', expected_current), ('solar_no_canopy', expected_absent)]:
        assert np.array_equal(np.isfinite(arrays[name]), valid)
        np.testing.assert_allclose(arrays[name][valid], expected[valid], rtol=0, atol=ATOL)
    np.testing.assert_array_equal(arrays['observer_valid'], valid)
    np.testing.assert_array_equal(arrays['observer_index_k'], np.full(SHAPE[:2], 2))
    np.testing.assert_array_equal(arrays['solar_difference'], arrays['solar_no_canopy']-arrays['solar_current'])
    assert np.all(arrays['solar_difference'][valid] >= -ATOL)
    assert np.all(arrays['solar_difference'][~valid] != arrays['solar_difference'][~valid])
    assert np.array_equal(classes, before[0]) and np.array_equal(absent, before[1])
    assert qa['invariants']['non_TREE_voxels_equal'] == 'PASS'
    assert qa['actual_api_calls'] == 5
    print(f'OUEM pair: valid={valid.sum()}, excluded={(~valid).sum()}, '
          f'ROI_reduction_cells={qa["ROI"]["reduction_cells"]}, '
          f'current_max_error={np.max(np.abs(arrays["solar_current"][valid]-expected_current[valid])):.3g}, '
          f'absent_max_error={np.max(np.abs(arrays["solar_no_canopy"][valid]-expected_absent[valid])):.3g}')
