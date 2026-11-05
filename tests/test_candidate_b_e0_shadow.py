"""CPU-only, synthetic feasibility checks for the pinned VoxCity solar kernel."""
from hashlib import sha256
from importlib.metadata import distribution
import json

import numpy as np
import pytest


PIN = "fa212656305328a9a657973bae26f352bfe813bc"


@pytest.fixture(scope="module")
def solar():
    installed = distribution("voxcity")
    assert installed.version == "1.7.0"
    assert json.loads(installed.read_text("direct_url.json"))["vcs_info"]["commit_id"] == PIN
    from voxcity.simulator.solar.kernels import compute_direct_solar_irradiance_map_binary
    from voxcity.utils.orientation import direction_to_axis_vector

    def run(voxels, azimuth=180., height=0., roofs=False, allowed=(0,)):
        direction = tuple(direction_to_axis_vector(azimuth, 45.))
        result = compute_direct_solar_irradiance_map_binary(
            voxels, direction, height, allowed, 1., .6, 1., False, roofs)
        assert result.shape == voxels.shape[:2]
        assert np.isin(result[np.isfinite(result)], [0., 1.]).all()
        classes = np.where(np.isnan(result), 255, result).astype("uint8")
        print(f"azimuth={azimuth} height={height} roofs={roofs} air_allowed={allowed} "
              f"input={sha256(voxels.tobytes()).hexdigest()} "
              f"classes={sha256(classes.tobytes()).hexdigest()} "
              f"shadow={np.count_nonzero(classes==0)} sun={np.count_nonzero(classes==1)} "
              f"invalid={np.count_nonzero(classes==255)}")
        return result

    return run


def model(building=True):
    voxels = np.zeros((19, 23, 12), dtype="int8")
    voxels[..., 0], voxels[..., 1] = -1, 1
    if building:
        voxels[7:10, 11:15, 2:6] = -3
    return voxels


@pytest.mark.parametrize("azimuth,shadow", [
    (180., np.s_[10:13, 11:15]),
    (90., np.s_[7:10, 8:11]),
])
def test_shadow_direction_and_discrete_length(solar, azimuth, shadow):
    # 4 m continuous shadow from the solid surface. With k=2 as the first
    # air centre and 45-degree simultaneous steps, only k=3..5 can block.
    expected = np.ones((19, 23))
    expected[7:10, 11:15] = np.nan
    expected[shadow] = 0.
    np.testing.assert_array_equal(solar(model(), azimuth), expected)


def test_open_ground_and_roof_policy(solar):
    assert (solar(model(False)) == 1).all()
    roofs = solar(model(), roofs=True)
    assert (roofs[7:10, 11:15] == 1).all()
    invalid = model(False)
    invalid[0, 0, 1] = 7  # water
    invalid[0, 1, 1] = -1  # subsurface code exposed to air
    invalid[0, 2, :] = 0  # no surface
    assert np.isnan(solar(invalid)[0, :3]).all()


def test_observer_height_truncation_and_above_model(solar):
    zero = solar(model(), height=0.)
    one = solar(model(), height=1.)
    np.testing.assert_array_equal(solar(model(), height=1.5), one)
    np.testing.assert_array_equal(zero[10:14, 12], [0., 0., 0., 1.])
    np.testing.assert_array_equal(one[10:14, 12], [0., 0., 1., 1.])
    above = solar(model(), height=12.)
    assert above[10, 12] == 1.  # The engine does not reject an out-of-volume start.
    assert np.isnan(above[7, 12])


def test_domain_exit_omits_external_blocker(solar):
    voxels = model(False)
    voxels[0, 11, 2:6] = -3
    assert solar(voxels)[2, 11] == 0.
    assert solar(voxels[1:].copy())[1, 11] == 1.


def test_ground_obstruction_depends_on_air_allow_list(solar):
    voxels = model(False)
    voxels[7, 11, :6] = -1
    voxels[7, 11, 6] = 1
    assert solar(voxels)[9, 11] == 0.
    assert solar(voxels, allowed=(0, -1, 1))[9, 11] == 1.
