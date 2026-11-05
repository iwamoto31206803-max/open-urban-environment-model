from pathlib import Path

import numpy as np
import pytest

from ouem.candidate_b_t4b2 import audit_voxels, run


def fixture():
    # Owner 2 averages 10 and 11 m. Owner 1 has 10 m and a 4 m building.
    dem = np.array([[10., 10., 11., 11.]])
    ids = np.array([[1, 2, 2, 0]])
    segments = np.empty(ids.shape, dtype=object)
    segments[0, 0] = [[0, 4]]
    segments[0, 1] = [[0, 4], [0, 2]]
    segments[0, 2] = [[0, 2]]
    segments[0, 3] = []
    voxels = np.array([[[1,-3,-3,-3,-3,0], [-1,1,-3,-3,-3,-3],
                        [-1,1,-3,-3,0,0], [-1,1,0,0,0,0]]])
    rows = [dict(id=1, g_eff_abs=10., height=4., z_top_abs=14.),
            dict(id=2, g_eff_abs=10.5, height=2., z_top_abs=12.5)]
    return voxels, dem, ids, segments, rows, [dict(index=[0,1])]


def test_distinct_owner_and_segment_occupancy():
    effective, report = audit_voxels(*fixture())
    np.testing.assert_array_equal(effective, [[10, 10.5, 10.5, 11]])
    assert report["z_reference_abs_m"] == 10
    assert report["effective_ground_error_m"]["max_abs"] == 0.5
    assert report["raw_dem_ground_error_m"]["max_abs"] == 1
    assert report["buildings"][1]["unambiguous_voxels"] == 2
    assert report["buildings"][1]["roof_error_m"]["max_abs"] == 0.5
    assert report["conflicts"][0]["owner"] == 2
    assert report["conflicts"][0]["spans_k"] == [[2,6],[2,4]]
    assert report["conflicts"][0]["occupied_k"] == [2,3,4,5]


@pytest.mark.parametrize("index,value,message", [
    ((0,1,0),0,"ground or land-cover"),
    ((0,1,2),0,"floating"),
    ((0,1,5),0,"class occupancy"),
    ((0,3,4),-3,"class occupancy"),
])
def test_rejects_wrong_voxel_column(index, value, message):
    fixture_args = fixture()
    fixture_args[0][index] = value
    with pytest.raises(ValueError, match=message):
        audit_voxels(*fixture_args)


def test_missing_receipt_never_publishes_completion(tmp_path):
    out = tmp_path/"new"
    result = run(*(Path("missing"),)*4, out)
    assert result["status"] == "BLOCKED"
    assert (out/"failure.json").is_file()
    assert not (out/"report.json").exists()
    with pytest.raises(FileExistsError):
        run(*(Path("missing"),)*4, out)
