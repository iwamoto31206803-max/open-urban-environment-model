"""Real pinned CPU API on small synthetic fixtures, not Komae acceptance."""
import numpy as np
import pytest

from ouem.canopy_shadow_poc import (relative_grids, build_pair, irradiance,
                                    grid_north, ShadowBlocked, load_inputs, stats, crop_pair)


@pytest.fixture(scope="module", autouse=True)
def pinned_engine():
    from ouem.komae_integration import voxcity_provenance
    from numba import set_num_threads
    assert voxcity_provenance()["verified"]
    set_num_threads(2)


def test_absolute_height_and_north_south_boundary():
    dem = np.array([[21., 22.], [10., 12.]])
    top = dem + [[3., 4.], [0., 6.]]
    bottom = dem + [[1., 2.], [0., 2.]]
    before = [a.copy() for a in (top, bottom, dem)]
    d, t, b = relative_grids(top, bottom, dem, np.ones((2, 2)))
    assert np.array_equal(d, [[10,12], [21,22]])
    assert np.array_equal(t, [[0,6], [3,4]])
    assert np.array_equal(b, [[0,2], [1,2]])
    assert all(np.array_equal(a, old) for a, old in zip((top,bottom,dem),before))


@pytest.mark.parametrize("kind", ["state", "nonfinite", "bottom"])
def test_invalid_boundary_blocks(kind):
    d=np.ones((2,2))*10; t=d+3; b=d+1; s=np.ones((2,2))
    if kind=="state": s[0,0]=2
    if kind=="nonfinite": t[0,0]=np.nan
    if kind=="bottom": b[0,0]=9
    with pytest.raises(ShadowBlocked): relative_grids(t,b,d,s)


def test_rounding_plus_one_thin_crown_padding_and_ground():
    d=np.array([[10.,10.49],[10.51,11.51]])
    t=np.array([[1.2,3.49],[0.,4.51]])
    b=np.array([[1.1,.51],[0.,2.49]])
    pair=build_pair(d,t,b,(0,0,2,2),0)
    a,v=pair.a.voxels.classes,pair.b.voxels.classes
    # Manual expected layers: g=1, b=t=1 expanded to b=0, TREE=[1,2).
    assert np.array_equal(np.flatnonzero(v[0,0]==-2),[1])
    # g=1, rounded b=1,t=3 -> [2,4).
    assert np.array_equal(np.flatnonzero(v[0,1]==-2),[2,3])
    # g=3, b=2,t=5 -> [5,8).
    assert np.array_equal(np.flatnonzero(v[1,1]==-2),[5,6,7])
    assert pair.qa['thin_crown_expanded_cells']==1
    assert pair.qa['original_z_lengths'][0] < a.shape[2]
    assert a.shape==v.shape
    assert not np.any(a==-2) and np.any(v==-2)
    assert np.array_equal(a==-1,v==-1) and np.array_equal(a==1,v==1)
    assert np.all(a[:,:,pair.qa['original_z_lengths'][0]:]==0)


@pytest.mark.parametrize("az,shadow,clear",[
    (0,(4,7),(10,7)), (90,(7,4),(7,10)),
    (180,(10,7),(4,7)), (270,(7,10),(7,4))])
def test_cardinal_sun_casts_shadow_opposite_direction(az,shadow,clear):
    d=np.full((15,15),10.); t=np.zeros_like(d);b=t.copy()
    t[7,7]=6;b[7,7]=3
    pair=build_pair(d,t,b,(0,0,15,15),0)
    a,north_b=irradiance(pair,az,45)
    south_b=np.flipud(north_b);south_a=np.flipud(a)
    assert south_b[shadow] < south_a[shadow]
    assert south_b[clear] == south_a[clear]
    assert np.isfinite(a).all() and np.isfinite(north_b).all()
    assert np.all(north_b<=a)
    assert np.allclose(a,800*np.sin(np.pi/4))


@pytest.mark.parametrize("rotation,az",[(90,90),(-90,270)])
def test_true_north_rotation_sign_in_real_cpu_api(rotation,az):
    d=np.zeros((15,15));t=d.copy();b=d.copy();t[7,7]=6;b[7,7]=3
    rotated=build_pair(d,t,b,(0,0,15,15),rotation)
    unrotated=build_pair(d,t,b,(0,0,15,15),0)
    a,x=irradiance(rotated,az,45);_,y=irradiance(unrotated,0,45)
    assert np.allclose(x,y,rtol=0,atol=1e-10)
    assert x[10,7]<a[10,7]  # south is row 10 after north-up output


def test_projected_grid_north_measured_against_geographic_north():
    from pyproj import Proj
    bounds=(-23320,-40760,-23256,-40696)
    rotation,lon,lat=grid_north(bounds)
    # Independent projection differential (meridian convergence).
    convergence=Proj('EPSG:6677').get_factors(lon,lat).meridian_convergence
    assert rotation<0
    assert rotation==pytest.approx(convergence,abs=1e-5)


def test_bad_manifest_hash_stops_before_reading_other_inputs(tmp_path):
    (tmp_path/'generated').mkdir()
    (tmp_path/'generated/height_envelope_manifest.json').write_text('{}')
    with pytest.raises(ShadowBlocked,match='manifest hash'):
        load_inputs(tmp_path,'0'*64,tmp_path/'missing.tif','0'*64)


def test_nan_is_not_zero_in_statistics():
    assert stats(np.array([np.nan,-5.,-1.]))['mean']==-3
    with pytest.raises(ShadowBlocked): stats(np.array([np.nan]))


def test_night_rejected_before_cpu_api():
    with pytest.raises(ShadowBlocked,match='daytime'):
        irradiance(None,180,-5)


def test_halo_removal_preserves_vertical_origin_and_all_inner_voxels():
    d=np.full((9,9),12.);d[0,0]=10.
    t=np.zeros_like(d);b=t.copy();t[4,4]=6;b[4,4]=2
    pair=build_pair(d,t,b,(0,0,9,9),0)
    cropped=crop_pair(pair,(2,2,7,7),margin=2)
    assert np.array_equal(cropped.a.voxels.classes,pair.a.voxels.classes[2:7,2:7])
    assert np.array_equal(cropped.b.voxels.classes,pair.b.voxels.classes[2:7,2:7])
    assert cropped.a.voxels.classes.shape==cropped.b.voxels.classes.shape
    assert cropped.a.voxels.classes[0,0,2]==1  # g=round(12-10)+1=3 retained
    assert cropped.a.voxels.meta.bounds==(2,2,7,7)
