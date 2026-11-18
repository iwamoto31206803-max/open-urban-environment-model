import numpy as np
import pytest

from ouem.komae_saved_tree_comparison import summarize


def test_saved_tree_comparison_preserves_presence_and_roi():
    present = np.array([[True, True, True, True, False, False]])
    absent = np.array([[False, False, False, False, True, False]])
    unknown = ~(present | absent)
    mapped = dict(present=present, absent=absent, unknown=unknown,
                  source_support=np.ones_like(present), assessed_domain=~unknown)
    canopy = dict(valid=np.array([[True, True, True, False, True, True]]),
                  candidate=np.array([[True, True, False, False, False, False]]))
    no_canopy = np.zeros((1, 6, 3), dtype=np.int8)
    no_canopy[..., 0] = 1
    current = no_canopy.copy()
    current[0, 0, 1:] = -2
    roi = np.array([[True, True, False, False, True, False]])
    previous = current.copy()
    result = summarize(mapped, canopy, current, no_canopy, roi)
    whole, cropped = result["scene"], result["roi"]
    assert whole["presence_vs_tree_columns"] == {
        "present": {"occupied": 1, "empty": 3},
        "absent": {"occupied": 0, "empty": 1},
        "unknown": {"occupied": 0, "empty": 1},
    }
    assert whole["present_without_tree"] == {
        "invalid_z": 1, "valid_no_candidate": 1, "candidate_unresolved": 1,
    }
    assert (whole["source_valid"], whole["z_valid"], whole["tree_candidate"]) == (5, 5, 2)
    assert (cropped["cells"], cropped["tree_columns"], cropped["tree_voxels"]) == (3, 1, 2)
    np.testing.assert_array_equal(current, previous)
    current[0, 5, 0] = 0
    with pytest.raises(ValueError, match="non-TREE"):
        summarize(mapped, canopy, current, no_canopy, roi)
