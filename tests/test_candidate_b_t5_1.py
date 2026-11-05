import numpy as np

from ouem.candidate_b_t5_1 import coverage, domains, extension


def test_snap_outward_and_keep_evaluation_grid_origin():
    bounds = [-22575.2, -39925., -22472.1, -39823.5]
    assert domains(bounds) == {
        "aligned_minimum": [-22576., -39925., -22472., -39823.],
        "one_mesh_margin": [-22577., -39926., -22471., -39822.],
    }
    np.testing.assert_allclose(list(extension(bounds).values()), [.2, 0, 2.9, 1.5])


def test_priority_zero_nodata_and_ambiguous_tiles():
    values = np.array([[[2,0,np.nan,1]], [[np.nan,np.nan,np.nan,2]],
                       [[0,np.nan,np.nan,np.nan]], [[np.nan]*4]], dtype="float32")
    footprint = np.ones_like(values, dtype=bool)
    report, ids, heights, bits = coverage(values, footprint, (0,0,2,.5))
    np.testing.assert_array_equal(ids, [[3,1,0,2]])
    np.testing.assert_array_equal(bits, [[5,1,0,3]])
    np.testing.assert_array_equal(heights, [[0,0,np.nan,2]])
    assert report["neither"] == report["same_source_overlap"] == report["both"] == 1
    assert report["missing_within_tile_extent"] == 1
    assert report["missing_cell_edge_bounds"] == [1,0,1.5,.5]
