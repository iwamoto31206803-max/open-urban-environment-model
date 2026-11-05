from pathlib import Path

import numpy as np

from ouem import candidate_b_t5 as t5


def test_coordinate_mask_half_open_and_non_rectangular():
    points = np.array([[[-22575.,-39925.],[-22475.,-39924.]],
                       [[-22574.,-39825.],[-22574.,-39826.]]])
    np.testing.assert_array_equal(t5.evaluation_mask(points), [[True,False],[False,True]])


def test_zero_owner_requires_review_and_invalid_grid_fails():
    row = dict(owner_outside_isolated=0, flags=[], owned_cells=1)
    assert t5.grid_gate({"converged":True},[row]) == "PASS"
    assert t5.grid_gate({"converged":True},[row | {"owned_cells":0}]) == "REVIEW_REQUIRED"
    assert t5.grid_gate({"converged":False},[row]) == "FAIL"
    assert t5.grid_gate({"converged":True},[row | {"owner_outside_isolated":1}]) == "FAIL"


def test_t4_comparison_uses_source_and_geography():
    shared = dict(source_id="source",ouem_id="ouem",z_top_abs=30.)
    old = shared | dict(id=2,g_eff_abs=24.,height=6.)
    new = shared | dict(id=7,g_eff_abs=25.,height=5.)
    report, nearest = t5.compare_t4(
        [old],[new],np.array([[[10.,20.]]]),np.array([[2]]),
        {"centres_xy":np.array([[[11.,20.],[10.125,20.]]]),"building_ids":np.array([[2,7]])})
    assert nearest.tolist() == [1]
    assert report["max_nearest_centre_distance_m"] == .125
    assert report["buildings"] == [dict(source_id="source",t4_id=2,t5_id=7,old_cells=1,
                                       same_source_nearest_cells=1,ground_delta_m=1.,height_delta_m=-1.)]


def test_invalid_inputs_never_reach_voxel_phase(tmp_path, monkeypatch):
    def unexpected(*args):
        raise AssertionError("unexpected voxel phase")

    monkeypatch.setattr(t5,"voxel_phase",unexpected)
    out = tmp_path/"run"
    result = t5.run(*(Path("missing"),)*7,out)
    assert (result["gate1"],result["gate2"]) == ("FAIL","NOT_RUN")
    assert "unexpected voxel phase" not in result["error"]
    assert not (out/"t5-3").exists()
