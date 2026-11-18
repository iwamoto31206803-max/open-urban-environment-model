"""Synthetic Meta model presence and numeric/voxel boundary checks."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ouem import canopy_height_candidate as candidate
from ouem import height_envelope as env
from ouem.canopy_shadow_poc import relative_grids


def review(grid, chm, dem, **overrides):
    options = dict(profile="meta_estimated_canopy_hag",
                   synthetic_assertion="SYNTHETIC_TEST_ONLY", vertical_compatible=True,
                   hag_aligned_transform=grid.transform, dem_aligned_transform=grid.transform)
    return candidate.review_synthetic_candidate(grid, chm, dem, **(options | overrides))


def test_meta_presence_keeps_support_height_and_terrain_independent(tmp_path):
    grid = env.GridSpec((0, 0, 10, 1))

    def sample(name, values, mask):
        path = tmp_path / name
        with rasterio.open(path, "w", driver="GTiff", width=len(values), height=1,
                           count=1, crs="EPSG:6677", transform=from_origin(0, 1, 1, 1),
                           dtype="float64") as dst:
            dst.write(np.array([values], dtype=float), 1)
            dst.write_mask(np.array([mask], dtype="uint8") * 255)
        return env.sample_raster(path, grid)

    chm = sample("chm.tif", [4, 0, 0, 7, -1, np.nan, np.inf, 5, 6], [1, 1, 0, 0, 1, 1, 1, 1, 1])
    dem = sample("dem.tif", [10]*10, [0, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    snapshots = [a.copy() for samples in (chm, dem)
                 for a in (samples.values, samples.missing, samples.outside)]
    result = review(grid, chm, dem)
    repeat = review(grid, chm, dem)
    model = result["meta_modelled_presence"]
    assert model["source_support"].tolist() == [[True]*9 + [False]]
    assert np.flatnonzero(model["present"]).tolist() == [0, 7, 8]
    assert np.flatnonzero(model["absent"]).tolist() == [1]
    assert np.flatnonzero(model["unknown"]).tolist() == [2, 3, 4, 5, 6, 9]
    assert model["surveyed_coverage"] is None
    assert result["predicted_canopy"] is None
    assert result["unknown_presence"].all()
    for key, indices in (("hag_valid", [0, 1, 7, 8]), ("dem_valid", list(range(1, 10))),
                         ("absolute_z_valid", [1, 7, 8])):
        assert np.flatnonzero(result[key]).tolist() == indices
    np.testing.assert_array_equal(model["assessed_domain"], result["hag_valid"])
    assert np.flatnonzero(model["tree_candidate"]).tolist() == [7, 8]
    for key, value in model.items():
        np.testing.assert_array_equal(value, repeat["meta_modelled_presence"][key])
    top, bottom, state, _ = env.calculate(grid, chm, dem, env.ConstantCR(.60))
    for key, expected in zip(("top_z", "bottom_z", "height_state"), (top, bottom, state)):
        np.testing.assert_array_equal(result[key], expected)
    assert top[0, 1] == bottom[0, 1] == 10
    with pytest.raises(ValueError, match="no filling"):
        relative_grids(top, bottom, dem.values, state)
    for actual, snapshot in zip((a for samples in (chm, dem)
                                 for a in (samples.values, samples.missing, samples.outside)), snapshots):
        np.testing.assert_array_equal(actual, snapshot)


def test_all_unknown_and_alignment_guards():
    grid = env.GridSpec((0, 0, 2, 1))
    zero = np.zeros((1, 2))
    missing = np.ones_like(zero, dtype=bool)
    inside = np.zeros_like(missing)
    chm = env.Samples(zero, missing, inside, {})
    dem = env.Samples(zero, inside, inside, {})
    model = review(grid, chm, dem)["meta_modelled_presence"]
    assert model["unknown"].all()
    assert not model["assessed_domain"].any()
    assert not model["tree_candidate"].any()
    for overrides, message in (
        ({"hag_aligned_transform": from_origin(1, 1, 1, 1)}, "transforms differ"),
        ({"profile": "unreviewed"}, "Unknown synthetic"),
        ({"presence_mask": inside}, "independently classified"),
    ):
        with pytest.raises(env.EnvelopeBlocked, match=message):
            review(grid, chm, dem, **overrides)
    with pytest.raises(env.EnvelopeBlocked, match="shape differs"):
        review(grid, env.Samples(zero.T, missing, inside, {}), dem)
    with pytest.raises(env.EnvelopeBlocked, match="metadata mapping"):
        review(grid, env.Samples(zero, missing, inside, None), dem)


def test_meta_mapping_uses_envelope_cells_in_engine_order(tmp_path):
    from types import SimpleNamespace

    grid = env.GridSpec((0, 0, 3, 2))
    path = tmp_path / "synthetic_chm.tif"
    with rasterio.open(path, "w", driver="GTiff", width=4, height=2,
                       count=1, crs=6677, transform=from_origin(0, 2, .75, 1),
                       dtype="float32", nodata=-9999) as dst:
        dst.write(np.array([[5., 1., -1., 0.], [4., 0., 0., -9999.]], dtype="float32"), 1)
    chm = env.sample_raster(path, grid)
    dem = env.Samples(np.full((2, 3), 10.),
                      np.array([[True, False, False], [False, False, False]]),
                      np.zeros((2, 3), dtype=bool), {})
    reviewed = review(grid, chm, dem)
    heights_before = {name: reviewed[name].copy() for name in ("top_z", "bottom_z", "height_state")}

    # South-up engine rows with shifted XY centres. At x=1 the Envelope
    # tie goes east. A centre on the right outer edge is out of bounds.
    x = np.array([[.9, 1., 2.3, 3.], [.8, 1.2, 2.4, np.nan]])
    y = np.array([[.6, .5, .4, .3], [1.6, 1.5, 1.4, 1.3]])
    mapped = candidate.map_synthetic_meta_to_engine(reviewed, x, y, centre_epsg=6677)
    assert mapped["present"].tolist() == [[True, False, False, False], [True, False, False, False]]
    assert mapped["absent"].tolist() == [[False, True, False, False], [False, False, True, False]]
    assert mapped["unknown"].tolist() == [[False, False, True, True], [False, True, False, True]]
    assert mapped["source_support"].tolist() == [[True, True, True, False]] * 2
    assert mapped["outside_envelope"].tolist() == [[False, False, False, True]] * 2
    assert mapped["tree_candidate"].tolist() == [[True, False, False, False], [False] * 4]
    assert mapped["absolute_z_valid"].tolist() == [[True, True, False, False], [False, False, True, False]]

    # Direct source sampling would classify the first south-up cell as zero.
    direct = env.sample_raster(path, SimpleNamespace(
        epsg=6677, width=4, height=2, centres=lambda: (x, y)))
    assert direct.values[0, 0] == 0 and not direct.missing[0, 0]
    for name, original in heights_before.items():
        np.testing.assert_array_equal(reviewed[name], original)
    with pytest.raises(env.EnvelopeBlocked, match="Envelope CRS"):
        candidate.map_synthetic_meta_to_engine(reviewed, x, y, centre_epsg=4326)
