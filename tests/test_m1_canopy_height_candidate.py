"""M1 synthetic-only candidate interchange: no live Meta/GSI, point data, or model."""
import numpy as np
import pytest
from rasterio.transform import Affine

from ouem import height_envelope as env
from ouem.canopy_height_candidate import review_synthetic_candidate as review


def samples(values, *, missing=(), outside=()):
    a = np.asarray([values], dtype="float64")
    miss = np.zeros(a.shape, dtype=bool)
    ext = np.zeros(a.shape, dtype=bool)
    if missing:
        miss[0, list(missing)] = True
    if outside:
        ext[0, list(outside)] = True
    return env.Samples(a, miss, ext, {"source": "SYNTHETIC_TEST_ONLY"})


def candidate(values, *, profile="meta_estimated_canopy_hag", missing=(),
              outside=(), dem=None, **extra):
    grid = env.GridSpec((0, 0, len(values), 1))
    hag = samples(values, missing=missing, outside=outside)
    terrain = samples([100.] * len(values)) if dem is None else dem
    kw = dict(grid=grid, hag=hag, dem=terrain, profile=profile,
              synthetic_assertion="SYNTHETIC_TEST_ONLY",
              vertical_compatible=True, hag_aligned_transform=grid.transform,
              dem_aligned_transform=grid.transform)
    kw.update(extra)
    return kw


def gsi(kw, mask, *, valid=None, probability=None):
    shape = (1, len(mask))
    kw.update(profile="gsi_point_surface_hag",
              presence_mask=np.asarray([mask], dtype=bool),
              inference_valid=(np.ones(shape, dtype=bool) if valid is None
                               else np.asarray([valid], dtype=bool)),
              presence_aligned_transform=kw["grid"].transform,
              canopy_probability=(None if probability is None
                                  else np.asarray([probability], dtype=float)))
    return kw


def test_meta_positive_zero_missing_and_outside_reuse_existing_core():
    kw = candidate([5., 0., -9999., 9.], missing=(2,), outside=(3,))
    before = kw["hag"].values.copy()
    result = review(**kw)
    expected = env.calculate(kw["grid"], kw["hag"], kw["dem"], env.ConstantCR(.6))
    assert np.array_equal(result["top_z"], expected[0])
    assert np.array_equal(result["bottom_z"], expected[1])
    assert result["height_state"].tolist() == [[1, 1, 2, 32]]
    assert result["top_z"][0, :2].tolist() == [105., 100.]
    assert result["bottom_z"][0, :2].tolist() == [102., 100.]
    assert result["height_qa"]["state_counts"]["zero_height_valid"] == 1
    assert result["predicted_canopy"] is None
    assert result["unknown_presence"].all()
    assert np.array_equal(kw["hag"].values, before)
    assert result["review_scope"] == "SYNTHETIC_ONLY_NOT_STANDARD_ACCEPTANCE"


def test_gsi_positive_missing_background_conflict_and_unknown_are_distinct():
    kw = gsi(candidate([8., 20., 12., 0., 4., 9.], missing=(1,)),
             [True, True, False, True, False, True],
             valid=[True, True, True, True, False, False],
             probability=[.95, .85, .1, .75, np.nan, np.nan])
    result = review(**kw)
    assert result["height_state"].tolist() == [[1, 2, 1, 1, 1, 1]]
    assert result["predicted_canopy_height_unavailable"].tolist() == [
        [False, True, False, False, False, False]]
    assert result["background_positive_height_conflict"].tolist() == [
        [False, False, True, False, False, False]]
    assert result["unknown_presence"].tolist() == [
        [False, False, False, False, True, True]]
    assert result["raw_hag"][0, 2] == 12
    assert result["top_z"][0, 2] == 112  # only numerical height, NOT TREE occupancy
    assert result["top_z"][0, 1] == env.NODATA
    assert result["top_z"][0, 3] == 100  # valid zero != missing
    assert np.isnan(result["canopy_probability"][0, 4])


def test_predicted_canopy_with_missing_ground_is_not_height_valid():
    kw = gsi(candidate([7., 4.], dem=samples([100., -9999.], missing=(1,))),
             [True, True])
    result = review(**kw)
    assert result["height_state"].tolist() == [[1, 4]]
    assert result["predicted_canopy"].all()
    assert result["predicted_canopy_height_unavailable"].tolist() == [[False, True]]
    assert result["top_z"][0, 1] == env.NODATA


@pytest.mark.parametrize("changed", [
    {"synthetic_assertion": "R1_ACCEPTED"},
    {"synthetic_assertion": ""},
    {"profile": "unknown"},
    {"vertical_compatible": False},
    {"vertical_compatible": 1},
])
def test_candidate_does_not_bypass_source_evidence(changed):
    kw = candidate([5.])
    kw.update(changed)
    with pytest.raises(env.EnvelopeBlocked):
        review(**kw)


def test_meta_cannot_fabricate_a_classification_from_hag():
    kw = candidate([5., 0.])
    kw["presence_mask"] = np.array([[True, False]])
    with pytest.raises(env.EnvelopeBlocked, match="not an independently classified"):
        review(**kw)


def test_gsi_requires_a_model_inference_mask_and_validity():
    kw = candidate([5.], profile="gsi_point_surface_hag")
    with pytest.raises(env.EnvelopeBlocked, match="requires mask"):
        review(**kw)


@pytest.mark.parametrize("field", ["hag_aligned_transform", "dem_aligned_transform",
                                   "presence_aligned_transform"])
def test_alignment_checks_real_affine_not_shape_only(field):
    kw = gsi(candidate([5., 6.]), [True, False])
    correct = kw["grid"].transform
    kw[field] = Affine(correct.a, 0, correct.c + .5,
                       0, correct.e, correct.f)
    with pytest.raises(env.EnvelopeBlocked, match="transform"):
        review(**kw)


def test_malformed_sample_masks_are_rejected_before_math():
    kw = candidate([5., 6.])
    kw["hag"].missing = np.zeros((1, 2), dtype="uint8")
    with pytest.raises(env.EnvelopeBlocked, match="explicit boolean"):
        review(**kw)


@pytest.mark.parametrize("wrong", [
    np.array([[1., 0.]]),
    np.array([True, False]),
])
def test_gsi_inferred_mask_must_be_explicit_boolean_and_aligned(wrong):
    kw = gsi(candidate([5., 6.]), [True, False])
    kw["presence_mask"] = wrong
    with pytest.raises(env.EnvelopeBlocked):
        review(**kw)


def test_probability_only_observed_cells_require_valid_probability():
    kw = gsi(candidate([3., 5.]), [True, False],
             valid=[True, False], probability=[1.1, np.nan])
    with pytest.raises(env.EnvelopeBlocked, match="probabilities"):
        review(**kw)


def test_distinct_image_and_point_epochs_are_preserved_without_reconciliation():
    epochs = {"imagery_acquired": "2025-01",
              "point_cloud_survey": "2023-04", "dem_epoch": "2024"}
    kw = gsi(candidate([5.], epochs=epochs), [True])
    result = review(**kw)
    assert result["epochs"] == epochs
    assert result["epochs"] is not epochs
    assert result["epochs"]["imagery_acquired"] != result["epochs"]["point_cloud_survey"]


def test_invalid_height_and_prediction_input_is_not_silent_background():
    kw = gsi(candidate([0., -1., 9.]), [False, True, False],
             valid=[False, True, True])
    result = review(**kw)
    assert result["unknown_presence"][0, 0]
    assert result["height_state"][0, 1] == 8  # nonfinite/negative HAG invalid
    assert result["predicted_canopy_height_unavailable"][0, 1]
    assert result["background_positive_height_conflict"][0, 2]
    assert np.array_equal(result["raw_hag"], np.array([[0., -1., 9.]]))
