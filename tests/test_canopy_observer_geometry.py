"""Phase 4A characterization of pinned APIs, including known counterexamples.

Passing characterization does NOT accept arbitrary-point tracing. No production
observer adapter or VoxCity patch is supplied here.
"""
import numpy as np
import pytest

from ouem.canopy_shadow_sensitivity import build_isotropic, geometry


@pytest.fixture(scope="module", autouse=True)
def pinned_source():
    from numba import set_num_threads
    from ouem.komae_integration import voxcity_provenance
    assert voxcity_provenance()["verified"]
    set_num_threads(2)


def trace(voxels, origin, direction, size=1., k=.6, lad=1.):
    # Internal import for characterization only; same mode as ground solar.
    from voxcity.simulator.common.raytracing import trace_ray_generic
    return trace_ray_generic(voxels, np.asarray(origin, dtype=float),
        np.asarray(direction, dtype=float), (0,), size, k, lad, False)


@pytest.mark.parametrize("size", [1., .5])
@pytest.mark.parametrize("axis", [0, 1, 2])
def test_fractional_origin_counterexample_is_not_an_accepted_adapter(size, axis):
    v = np.zeros((5,5,5), dtype=np.int8)
    slab = [slice(None)]*3; slab[axis] = 2; v[tuple(slab)] = -2
    q = np.full(3, 1.5); q[axis] = 2.25
    origin = q-.5  # candidate inverse for the actual continuous start q
    direction = np.zeros(3); direction[axis] = 1
    hit, transmission = trace(v, origin, direction, size)
    assert not hit
    # Start at 2.25, within slab [2,3): geometric length is 0.75*s.
    # But initialization int(origin)=1 conflicts with floor(q)=2.
    assert int(origin[axis]) != int(np.floor(q[axis]))
    assert transmission == pytest.approx(np.exp(-.6*size))
    assert transmission != pytest.approx(np.exp(-.6*.75*size))


@pytest.mark.parametrize("size", [1., .5])
@pytest.mark.parametrize("qz", [2.5, 2.75])
def test_consistent_initial_voxel_can_match_partial_analytic_length(size, qz):
    v = np.zeros((3,3,5), dtype=np.int8); v[:,:,2] = -2
    origin = np.array([1.,1.,qz-.5])
    hit, transmission = trace(v, origin, [0,0,1], size)
    assert not hit
    assert int(origin[2]) == int(np.floor(qz))
    assert transmission == pytest.approx(np.exp(-.6*(3-qz)*size))


@pytest.mark.parametrize("size", [1., .5])
@pytest.mark.parametrize("az,rotation,k,lad", [
    (0.,0.,.6,1.), (90.,0.,.6,1.), (270.,-90.,.3,2.), (180.,.2,0.,1.)])
def test_low_level_matches_ground_api_at_its_integer_origin(size, az, rotation, k, lad):
    from voxcity.simulator.solar import get_direct_solar_irradiance_map
    from voxcity.utils.orientation import direction_to_axis_vector
    n = int(7/size)
    dem = np.full((n,n), 10.)
    top = np.zeros_like(dem); bottom = top.copy()
    top[n//2,n//2] = 4.; bottom[n//2,n//2] = 1.
    pair = build_isotropic(dem,top,bottom,(0,0,7,7),rotation,size)
    city = pair.b; h = 1.5; el = 45.
    mapped = get_direct_solar_irradiance_map(city, az, el, 800., tree_k=k,
        tree_lad=lad, view_point_height=h, include_building_roofs=False)
    direction = direction_to_axis_vector(az,el,rotation)
    g = np.argmax(city.voxels.classes == 1, axis=2)+1
    expected = np.empty_like(mapped)
    for i,j in np.ndindex(mapped.shape):
        hit,t = trace(city.voxels.classes, [i,j,g[i,j]+int(h/size)], direction,size,k,lad)
        expected[i,j] = 0 if hit else t*800*direction[2]
    assert np.isfinite(mapped).all()
    assert np.array_equal(mapped,expected)


def test_outside_solid_and_inside_tree_have_no_semantic_observer_status():
    v = np.zeros((3,3,5), dtype=np.int8); v[1,1,1] = -1; v[1,1,2] = -2
    # Outside positive bound returns unattenuated transmission, not OUTSIDE.
    assert trace(v,[3,1,1],[0,0,1]) == (False,1.)
    # Ground is a hit; returned T is still 1. Do not interpret T alone as light.
    assert trace(v,[1,1,1],[0,0,1]) == (True,1.)
    hit,t = trace(v,[1,1,2],[0,0,1])
    assert not hit and t == pytest.approx(np.exp(-.6*.5))
    # Normal domain exit returns the same pair as an initially outside origin.
    assert trace(np.zeros_like(v),[1,1,1],[0,0,1]) == (False,1.)


@pytest.mark.parametrize("size", [1., .5])
def test_plus_one_rounding_precision_and_thin_expansion_decompose(size):
    d = np.array([[10.,10.31],[10.74,11.01]])
    top = np.array([[1.12,3.26],[2.,4.78]])
    bottom = np.array([[1.11,.66],[1.1,2.38]])
    pair = build_isotropic(d,top,bottom,(0,0,2*size,2*size),0,size)
    actual = geometry(pair,1.5)
    delta_d = d-d.min()
    d32 = delta_d.astype(np.float32).astype(float)
    ground_round = size*np.floor(d32/size+.5)-d32
    ground_precision = d32-delta_d
    lo = np.floor(bottom.astype(np.float32).astype(float)/size+.5)
    hi = np.floor(top.astype(np.float32).astype(float)/size+.5)
    thin = (lo == hi) & (lo > 0)
    for name,h in (("bottom",bottom),("top",top)):
        h32 = h.astype(np.float32).astype(float)
        h_round = size*np.floor(h32/size+.5)-h32
        h_precision = h32-h
        expansion = -size*thin if name == "bottom" else 0.
        predicted = size+ground_precision+ground_round+h_precision+h_round+expansion
        assert np.allclose(actual[name+"_error"],predicted,rtol=0,atol=2e-15)


def test_public_building_face_path_is_not_a_matching_sensor_switch():
    import trimesh
    from voxcity.simulator.solar import get_building_solar_irradiance
    d = np.full((3,3),10.)
    pair = build_isotropic(d,d*0+2,d*0+1,(0,0,3,3),0,1.)
    mesh = trimesh.Trimesh(vertices=[[.5,.5,2.],[1.5,.5,2.],[1.,2.,2.]],
                           faces=[[0,1,2]],process=False)
    mesh.metadata['svf'] = np.array([0.])
    slow = get_building_solar_irradiance(pair.b,mesh,0,90,800.,0.,fast_path=False)
    fast = get_building_solar_irradiance(pair.b,mesh,0,90,800.,0.,fast_path=True)
    # Face centre z=2 -> +0.1 normal offset -> generic +0.5 => z=2.6.
    # Actual TREE is [2,3). Generic path length .4m; masked path counts one voxel.
    assert slow.metadata['direct'][0] == pytest.approx(800*np.exp(-.6*.4))
    assert fast.metadata['direct'][0] == pytest.approx(800*np.exp(-.6))
    assert slow.metadata['direct'][0] != pytest.approx(fast.metadata['direct'][0])


def building_and_tree(dem, size, end=4.):
    from voxcity.generator.voxelizer import Voxelizer
    shape = dem.shape
    heights = np.zeros(shape); heights[0,0] = end
    ids = np.zeros(shape,dtype=np.int64); ids[0,0] = 1
    segments = np.empty(shape,dtype=object)
    for index in np.ndindex(shape): segments[index] = []
    segments[0,0] = [[1.,end]]
    top = np.full(shape,end); bottom = top*0+1.
    vox = Voxelizer(size,'Standard').generate_combined(heights,segments,ids,
            np.ones(shape,dtype=np.int64),dem,top,bottom,print_class_info=False)
    return vox


@pytest.mark.parametrize("size", [1., .5])
def test_flat_building_and_tree_share_ground_and_building_overwrites_tree(size):
    v = building_and_tree(np.full((2,2),10.),size)
    start,end = 1+int(1./size+.5),1+int(4./size+.5)
    assert np.array_equal(np.flatnonzero(v[0,0] == -3),np.arange(start,end))
    assert np.array_equal(np.flatnonzero(v[0,1] == -2),np.arange(start,end))
    assert not np.any(v[0,0] == -2)
    assert np.array_equal(v[0,0] == 1,v[0,1] == 1)


def test_building_and_canopy_precision_can_round_same_input_differently():
    # Building packed segments round float64; crown kernel receives float32.
    v = building_and_tree(np.full((2,2),10.),1.,end=3.4999999)
    building_end = np.flatnonzero(v[0,0] == -3).max()+1
    canopy_end = np.flatnonzero(v[0,1] == -2).max()+1
    assert building_end == 4 and canopy_end == 5


def test_building_ground_processing_can_change_minimum_reference():
    from voxcity.generator.voxelizer import Voxelizer
    d = np.array([[10.,12.],[11.,13.]])
    ids = np.array([[1,1],[0,0]],dtype=np.int64)
    segments = np.empty(d.shape,dtype=object)
    for index in np.ndindex(d.shape): segments[index] = []
    v = Voxelizer(1.,'Standard').generate_combined(np.zeros_like(d),segments,ids,
            np.ones_like(ids),d,np.full_like(d,2.),np.full_like(d,1.),print_class_info=False)
    ground = np.argmax(v == 1,axis=2)+1
    # Absolute effective ground [[11,11],[11,13]] has minimum 11, not raw 10.
    assert np.array_equal(ground,[[1,1],[1,3]])
    assert np.array_equal(11.+ground,[[12,12],[12,14]])
    assert not np.array_equal(10.+ground,[[12,12],[12,14]])
