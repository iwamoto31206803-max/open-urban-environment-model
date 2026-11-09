"""Small independent point-interface fixtures, without executing the OUEM venv JIT."""
import numpy as np
import pytest
from types import SimpleNamespace

from ouem import p1_shadow_compare as p


@pytest.fixture
def saved():
    grid = dict(bounds=[10, 20, 13, 22], resolution=1., orientation="north-up")
    valid = np.ones((2, 3), dtype=bool); valid[0, 1] = False
    index = np.where(valid, 1, -1)
    r, c = np.indices(valid.shape)
    xyz = np.stack((10+c+.5, 22-r-.5, 24.25+index+.5), axis=-1)
    xyz[~valid] = np.nan
    vox = np.zeros((2, 3, 4), dtype=np.int8); vox[:, :, 0] = 1; vox[0, 1, :] = -3
    old = np.array([[1, 255, 1], [0, 0, 0]], dtype=np.uint8)
    return dict(grid=grid, d0=24.25, valid=valid, index=index, xyz=xyz,
                A=vox, B=vox.copy(), A_shadow=old, B_shadow=old.copy(),
                direction=[-.707104509, -.001792546, .707106781])


def fake_trace(voxels, origin, direction, hits, size, k, lad, inclusion):
    assert hits == (0, -1, 1) and size == 1 and (k, lad, inclusion) == (.6, 1., False)
    assert np.isclose(np.linalg.norm(direction), 1., atol=1e-15, rtol=0)
    return origin[0] == 0, 1.


def test_explicit_origin_axes_and_kernel_delegate(saved):
    seen = []
    def trace(*args):
        seen.append(args[1].copy())
        np.testing.assert_array_equal(args[0], saved["A"][::-1])
        return fake_trace(*args)
    result, qa = p.control(saved, "A", trace)
    np.testing.assert_array_equal(result, [[1, 255, 1], [0, 0, 0]])
    np.testing.assert_array_equal(seen, [[1, 0, 1], [1, 2, 1], [0, 0, 1], [0, 1, 1], [0, 2, 1]])
    assert qa["status"] == "PASS" and qa["evaluated_saved_valid_points"] == 5


def test_one_mismatch_is_not_tolerated_or_hidden(saved):
    saved["A_shadow"][0, 0] = 0
    _, qa = p.control(saved, "A", fake_trace)
    assert qa["status"] == "BLOCKED" and qa["mismatch_count"] == 1
    assert qa["mismatch_row_col"] == [[0, 0]]
    saved["valid"][0, 0] = False
    with pytest.raises(ValueError, match="shrink"):
        p.control(saved, "A", fake_trace)


@pytest.mark.parametrize("fault", ["XYZ", "capacity", "axis", "class"])
def test_invalid_origins_direction_or_classes_rejected(saved, fault):
    if fault == "XYZ": saved["xyz"][1, 0, 2] += 1e-8
    if fault == "capacity": saved["index"][1, 0] = 4
    if fault == "axis": saved["direction"][0] *= -1
    if fault == "class": saved["A"][1, 0, 2] = -2
    with pytest.raises(ValueError):
        p.control(saved, "A", fake_trace)


def test_failed_start_leaves_C_gates_unexecuted(tmp_path, monkeypatch):
    monkeypatch.setattr(p.sys, "prefix", p.sys.base_prefix)
    result = p.run(tmp_path / "missing", tmp_path / "failed")
    assert result["status"] == "BLOCKED" and result["gates"]["Gate_1"] == "BLOCKED"
    assert all(result["gates"]["Gate_"+str(n)] == "NOT_EXECUTED" for n in range(2, 6))
    assert not list((tmp_path / "failed").rglob("*.npy"))


def test_D0_is_grid_origin_and_only_AIR_can_extend(saved):
    vertices = np.array([[11., 21., 24.65], [12., 21., 27.25]])
    original = vertices.copy()
    grid = p.common_grid(saved, vertices)
    assert grid["min_z"] == 24.25 and grid["n_z"] == 5
    np.testing.assert_array_equal(vertices, original)
    extended = p.air_pad(saved["A"], 5)
    np.testing.assert_array_equal(extended[:, :, :4], saved["A"])
    assert not extended[:, :, 4:].any()
    with pytest.raises(ValueError, match="truncate"):
        p.air_pad(saved["A"], 3)
    vertices[0, 2] = 24.
    with pytest.raises(ValueError, match="no clipping"):
        p.common_grid(saved, vertices)


def test_common_mask_preserves_excluded_position_and_rejects_capacity(saved):
    voxels = np.zeros((2, 3, 4), np.int8); voxels[1, 0, 1] = -3
    xyz = saved["xyz"].copy()
    mask, reasons, occupied, qa = p.fixed_mask(saved, voxels)
    assert qa["common_valid"] == 4 and qa["C_origin_occupied_excluded"] == 1
    assert qa["excluded_row_col"] == [[1, 0]] and reasons[1, 0] == 2 and reasons[0, 1] == 0
    assert occupied[1, 0] and not mask[1, 0]
    np.testing.assert_array_equal(saved["xyz"], xyz)
    with pytest.raises(ValueError, match="capacity"):
        p.fixed_mask(saved, voxels[:, :, :1])
    voxels[:, :, 1] = -3
    with pytest.raises(ValueError, match="empty"):
        p.fixed_mask(saved, voxels)


def test_both_change_directions_and_empty_union():
    mask = np.ones((2, 2), bool)
    first = np.array([[0, 1], [1, 0]], np.uint8)
    second = np.array([[1, 0], [1, 0]], np.uint8)
    classes, qa = p.compare(first, second, mask)
    np.testing.assert_array_equal(classes, [[3, 4], [1, 2]])
    assert qa["changed_cells"] == 2 and qa["discrete_area_delta_m2_second_minus_first"] == 0
    assert qa["first_only_shadow"] == qa["second_only_shadow"] == 1
    assert qa["shadow_IoU"] == 1/3
    _, qa = p.compare(np.ones((2, 2), np.uint8), np.ones((2, 2), np.uint8), mask)
    assert qa["empty_union"] and qa["shadow_IoU"] == 1.
    mask[0, 0] = False
    with pytest.raises(ValueError):
        p.compare(first, second, mask)  # Invalid points must be explicitly 255.


def test_conservative_context_reach_rejects_boundary_shadow():
    valid = np.ones((12, 12), bool)
    xyz = np.zeros((12, 12, 3)); xyz[..., 2] = 1.5
    saved = dict(grid={"bounds": [0, 0, 12, 12]}, d0=0., valid=valid, xyz=xyz,
                 direction=[-1/np.sqrt(2), 0., 1/np.sqrt(2)])
    voxels = np.zeros((12, 12, 6), np.int8); voxels[7, 5, 1:4] = -3
    qa = p.context_qa(voxels, saved)
    assert qa["highest_occupied_upper_H"] == 4. and qa["AIR_layers_above_highest_occupied"] == 2
    assert qa["conservative_shadow_bbox_XY"] == [5., 4., 6., 7.5]
    voxels[1, 5, 1:4] = -3
    with pytest.raises(ValueError, match="reach outside"):
        p.context_qa(voxels, saved)


def test_gate1_mismatch_prevents_C_loading_and_generation(saved, tmp_path, monkeypatch):
    # A complete in-memory fixture, with a single real control mismatch.
    # No real dataset, GML engine, or installed JIT is used by this test.
    saved["A_shadow"][0, 0] = 0
    monkeypatch.setattr(p.sys, "prefix", str(tmp_path / "ouem-voxcitygml-p1"))
    monkeypatch.setattr(p.b, "environment_inventory", lambda prefix: {})
    monkeypatch.setattr(p.f, "guard", lambda *args: [])
    monkeypatch.setattr(p, "runtime", lambda watches: {})
    monkeypatch.setattr(p, "load_baseline", lambda *args: {"F": saved})
    original = p.control
    monkeypatch.setattr(p, "control", lambda item, model: original(item, model, fake_trace))
    monkeypatch.setitem(p.sys.modules, "numba", SimpleNamespace(get_num_threads=lambda: 1, set_num_threads=lambda n: None))
    def forbidden(*args, **kwargs):
        raise AssertionError("C must never be reached")
    monkeypatch.setattr(p.mesh, "verify_mesh", forbidden)
    monkeypatch.setattr(p.mesh, "traced_voxelize", forbidden)
    output = tmp_path / "mismatch"
    report = p.run(tmp_path / "unused", output)
    assert report["status"] == "BLOCKED" and report["gates"]["Gate_1"] == "BLOCKED"
    assert all(report["gates"]["Gate_"+str(n)] == "NOT_EXECUTED" for n in range(2, 6))
    assert report["buildings"]["F"]["controls"]["A"]["mismatch_count"] == 1
    assert not list(output.rglob("C*"))
