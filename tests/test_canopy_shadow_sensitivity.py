"""Pinned public API fixtures precede the real-data resolution sensitivity run."""
import numpy as np
import pytest

from ouem.canopy_shadow_poc import ShadowBlocked, build_pair
from ouem.canopy_shadow_sensitivity import (
    area_mean, build_isotropic, crop_isotropic, direct, geometry, subdivide,
)


@pytest.fixture(scope="module", autouse=True)
def pin():
    from ouem.komae_integration import voxcity_provenance
    from numba import set_num_threads
    assert voxcity_provenance()["verified"]
    set_num_threads(2)


def box(size):
    n = int(15/size)
    dem = np.full((n, n), 10.)
    top, bottom = np.zeros_like(dem), np.zeros_like(dem)
    # Same centred 1x1m horizontal footprint, 3..6m relative crown.
    start, end = int(7/size), int(8/size)
    top[start:end, start:end] = 6.
    bottom[start:end, start:end] = 3.
    return build_isotropic(dem, top, bottom, (0, 0, 15, 15), 0, size)


@pytest.mark.parametrize("size", [1., .5])
def test_known_box_faces_ground_layer_and_volume(size):
    pair = box(size)
    g = geometry(pair, 1.5)
    assert np.allclose(g["ground_top_error"], size)
    assert np.allclose(g["bottom_error"][g["occupied"]], size)
    assert np.allclose(g["top_error"][g["occupied"]], size)
    assert g["tree_count"].sum()*size**3 == 3.
    assert np.allclose(g["ray_z"], 10+size*(1+int(1.5/size)+.5))
    assert np.allclose(g["ray_height"], 2.5 if size == 1 else 2.25)


@pytest.mark.parametrize("size", [1., .5])
def test_ray_origin_confirmed_by_public_zenith_api(size):
    # Ray begins inside the known crown: attenuation uniquely checks origin Z.
    d = np.full((3, 3), 10.)
    pair = build_isotropic(d, d*0+6, d*0+1, (0, 0, 3*size, 3*size), 0, size)
    a, b = direct(pair, 0, 90, 1.5)
    # Independent analytic ray length: absolute crown top - actual ray centre.
    origin_z = 12.5 if size == 1 else 12.25
    crown_top_z = 16+size
    expected = 800*np.exp(-.6*(crown_top_z-origin_z))
    assert np.allclose(a, 800)
    assert np.allclose(b, expected, rtol=0, atol=1e-10)
    assert np.isfinite(a).all() and np.isfinite(b).all()


@pytest.mark.parametrize("size", [1., .5])
@pytest.mark.parametrize("az,dy,dx", [(0,-3,0), (90,0,-3), (180,3,0), (270,0,3)])
def test_cardinal_shadow_and_mask_at_each_resolution(size, az, dy, dx):
    pair = box(size)
    a, b = direct(pair, az, 45, 1.5)
    # API returns north-up from helper; convert to south-up for direction check.
    a, b = np.flipud(a), np.flipud(b)
    centre = int(7.5/size)
    y, x = centre+int(dy/size), centre+int(dx/size)
    cy, cx = centre-int(dy/size), centre-int(dx/size)
    assert b[y, x] < a[y, x]
    assert b[cy, cx] == a[cy, cx]
    assert np.array_equal(np.isfinite(a), np.isfinite(b))


@pytest.mark.parametrize("size", [1., .5])
def test_observer_parameter_quantization_and_fixed_geometry(size):
    pair = box(size)
    g0, g1 = geometry(pair, 1.5), geometry(pair, 1.5-size)
    assert np.allclose(g0["ray_z"]-g1["ray_z"], size)
    for key in ("bottom_error", "top_error", "tree_count"):
        assert np.array_equal(g0[key], g1[key])
    # Within the same API index bin, specifying a different h has no effect.
    a, b = direct(pair, 180, 45, 1.5)
    a2, b2 = direct(pair, 180, 45, 1.5+size/4)
    assert np.array_equal(a, a2) and np.array_equal(b, b2)


def test_parent_child_area_and_height_information_preservation():
    x = np.array([[1., 2.], [3., 5.]])
    child = subdivide(x, .5)
    assert child.shape == (4, 4)
    assert np.array_equal(child[:2, :2], np.full((2,2), 1.))
    assert np.array_equal(area_mean(child, 2), x)
    with pytest.raises(ShadowBlocked):
        area_mean(np.array([[np.nan, 1.], [2., 3.]]), 2)
    with pytest.raises(ShadowBlocked):
        subdivide(x, .25)


def test_one_metre_engine_reproduces_existing_adapter_voxels():
    d = np.array([[10., 10.49], [10.51, 11.51]])
    top = np.array([[1.2, 3.49], [0., 4.51]])
    bottom = np.array([[1.1, .51], [0., 2.49]])
    new = build_isotropic(d, top, bottom, (0,0,2,2), 0, 1.)
    old = build_pair(d, top, bottom, (0,0,2,2), 0)
    assert np.array_equal(new.a.voxels.classes, old.a.voxels.classes)
    assert np.array_equal(new.b.voxels.classes, old.b.voxels.classes)


@pytest.mark.parametrize("size", [1., .5])
def test_cropped_halo_preserves_size_z_origin_and_inner_classes(size):
    pair = box(size)
    cropped = crop_isotropic(pair, (2,2,13,13), margin_m=2)
    margin = int(2/size)
    for name in ("voxels", "buildings", "land_cover", "dem", "tree_canopy"):
        assert getattr(cropped.b, name).meta.meshsize == size
    assert np.array_equal(cropped.b.voxels.classes,
                          pair.b.voxels.classes[margin:-margin, margin:-margin])
    a, b = direct(cropped, 0, 90, 1.5)
    aa, bb = direct(pair, 0, 90, 1.5)
    assert np.array_equal(a, aa[margin:-margin, margin:-margin])
    assert np.array_equal(b, bb[margin:-margin, margin:-margin])


@pytest.mark.parametrize("size", [1., .5])
def test_rounded_faces_and_thin_crown_are_audited(size):
    d = np.array([[10.,10.31], [10.74,11.01]])
    t = np.array([[1.12,3.26],[0.,4.78]])
    b = np.array([[1.11,.66],[0.,2.38]])
    pair = build_isotropic(d, t, b, (0,0,2*size,2*size), 0, size)
    tree = np.flatnonzero(pair.b.voxels.classes[0,0] == -2)
    low = int(1.11/size+.5)-1
    high = int(1.12/size+.5)
    assert np.array_equal(tree, np.arange(1+low, 1+high))
    g = geometry(pair, 1.5)
    expected_top = 10+(int(float(np.float32(1.01))/size+.5)+1+int(float(np.float32(4.78))/size+.5))*size
    assert g["top_error"][1,1] == pytest.approx(expected_top-(11.01+4.78))
