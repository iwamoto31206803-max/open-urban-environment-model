"""Independent analytic solids and control fixtures; no real-data imports."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from ouem import p1_mesh_voxel as p


@pytest.fixture
def cube():
    v = np.array([[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.],
                  [0., 0., 1.], [1., 0., 1.], [1., 1., 1.], [0., 1., 1.]])
    t = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
                  [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    return v, t


@pytest.mark.parametrize("offset", [np.zeros(3), np.array([-22500., -39800., 25.])])
def test_solid_angle_analytic_cube_and_boundary(cube, offset):
    v, t = cube
    points = np.array([[.5, .5, .5], [2, .5, .5], [0, .5, .5], [0, 0, .5], [0, 0, 0]])
    labels = p.solid_angle_classify(v + offset, t, points + offset)
    np.testing.assert_array_equal(labels, [1, 0, -1, -1, -1])
    # Winding sign may reverse, inside/outside must not.
    np.testing.assert_array_equal(p.solid_angle_classify(v + offset, t[:, ::-1], points + offset), labels)


def test_cavity_is_not_convex_hull(cube):
    v, t = cube
    # Outer cube [-1,2]^3, oppositely oriented inner cube [0,1]^3.
    vertices = np.vstack((3 * v - 1, v))
    faces = np.vstack((t, t[:, ::-1] + len(v)))
    points = np.array([[-.5, .5, .5], [.5, .5, .5], [3, .5, .5]])
    np.testing.assert_array_equal(p.solid_angle_classify(vertices, faces, points), [1, 0, 0])


def test_analytic_sloping_tetrahedron():
    vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    points = np.array([[.1, .2, .3], [.5, .5, .5], [.25, .25, .5]])
    np.testing.assert_array_equal(p.solid_angle_classify(vertices, faces, points), [1, 0, -1])


def test_axis_grid_phase_and_resolution(cube):
    v, _ = cube
    g = p.grid_spec(v, 1.)
    assert (g['min_x'], g['max_y'], g['min_z']) == (-1., 2., -1.)
    points = p.points_at(g, np.array([[0, 0, 0], [1, 1, 1]]), np.full((2, 3), .5))
    np.testing.assert_array_equal(points, [[-.5, 1.5, -.5], [.5, .5, .5]])
    fine = p.grid_spec(v, .5)
    shifted = p.grid_spec(v, 1., .5)
    assert fine['n_rows'] == 2 * g['n_rows'] and fine['min_z'] == g['min_z']
    assert shifted['min_x'] == g['min_x'] + .5 and shifted['max_y'] == g['max_y'] + .5
    with pytest.raises(ValueError):
        p.grid_spec(v, .25)
    with pytest.raises(ValueError, match='resource'):
        p.grid_spec(v * 100, .5)


def unit_grid(n_cols=1, min_x=0.):
    return dict(n_rows=1, n_cols=n_cols, n_z=1, min_x=min_x, max_x=min_x + n_cols,
                min_y=0., max_y=1., min_z=0., max_z=1., voxel_size=1.)


def test_sample_overlap_analytic_volume_excess_and_miss(cube):
    v, t = cube
    result = p.sample_overlap(v, t, unit_grid(), np.ones((1, 1, 1), bool), 2)
    assert result['intersection_m3'] == [1., 1.]
    assert result['sampled_IoU'] == [1., 1.]
    result = p.sample_overlap(v, t, unit_grid(2, -1.), np.ones((1, 2, 1), bool), 2)
    assert result['excess_m3'] == [1., 1.] and result['sampled_IoU'] == [.5, .5]
    result = p.sample_overlap(v, t, unit_grid(), np.zeros((1, 1, 1), bool), 2)
    assert result['missed_m3'] == [1., 1.]


def test_boundary_samples_remain_uncertain(cube):
    v, t = cube
    result = p.sample_overlap(v * .5, t, unit_grid(), np.ones((1, 1, 1), bool), 3)
    assert result['sample_counts']['ambiguous_occupied'] > 0
    assert result['intersection_m3'][1] > result['intersection_m3'][0]


def test_traced_union_and_hook_restoration(cube):
    v, t = cube
    shape = (1, 1, 1)
    engine = SimpleNamespace(Grid3DParams=lambda **kw: SimpleNamespace(**kw))
    engine.make_watertight_mesh = lambda *a, **kw: SimpleNamespace(
        method='merge', is_watertight=True, vertices=v.copy(), faces=t.copy())
    engine._z_scanline_fill = lambda *a: np.zeros(shape, dtype=bool)
    engine._surface_voxelize_numba = lambda *a: np.ones(shape, dtype=bool)
    engine._voxelize_single_mesh = lambda *a: None
    def occupancy(v, t, gp, voxels, value, overwrite):
        interior = engine._z_scanline_fill(v, t, 0., 1., 0., 1., 0, 0, 0, 1, 1, 1)
        shell = engine._surface_voxelize_numba(v, t, 0., 1., 0., 1., 0, 0, 0, 0, 0, 0, 1, 1, 1, np.ones(3))
        voxels[interior | shell] = value
        return True
    engine._voxelize_by_occupancy = occupancy
    def voxelize(v, t, gp, voxels, value, overwrite):
        wt = engine.make_watertight_mesh(v, t)
        engine._voxelize_by_occupancy(wt.vertices, wt.faces, gp, voxels, value, overwrite)
    engine._voxelize_building_solid = voxelize
    original = engine._z_scanline_fill
    voxels, masks, trace = p.traced_voxelize(engine, v, t, v, t, unit_grid())
    assert voxels.item() == -3 and masks['shell'].all() and not masks['interior'].any()
    assert trace == ['repair:merge', 'occupancy:True'] and engine._z_scanline_fill is original
    engine._voxelize_building_solid = lambda *args: engine._voxelize_single_mesh()
    with pytest.raises(ValueError, match='fallback'):
        p.traced_voxelize(engine, v, t, v, t, unit_grid())
    assert engine._z_scanline_fill is original
    def changed_H(v, t, gp, voxels, value, overwrite):
        wt = engine.make_watertight_mesh(v, t)
        altered = wt.vertices.copy()
        altered[:, 2] += 1e-8
        engine._voxelize_by_occupancy(altered, wt.faces, gp, voxels, value, overwrite)
    engine._voxelize_building_solid = changed_H
    with pytest.raises(ValueError, match='geometry changed'):
        p.traced_voxelize(engine, v, t, v, t, unit_grid())
    assert engine._z_scanline_fill is original


def test_partial_failure_not_completed(tmp_path, monkeypatch):
    monkeypatch.setattr(p.sys, 'prefix', p.sys.base_prefix)
    missing = tmp_path / 'absent'
    result = p.run(missing, missing, missing, missing, missing, tmp_path / 'failed')
    assert result['status'] == 'BLOCKED' and 'buildings' not in result
    assert json.loads((tmp_path / 'failed/manifest.json').read_bytes())['status'] == 'BLOCKED'
