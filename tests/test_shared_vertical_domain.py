"""Synthetic public API tests; no historical/real data are used as model inputs."""
import copy
import numpy as np
import pytest

from ouem import real_komae_solar as m
from ouem.real_komae_voxel import effective_ground, audit_voxels
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_real_komae_solar import authored


def scene(building_height=4., raised_ground=0.):
    from voxcity.generator.voxelizer import Voxelizer, NUMBA_AVAILABLE
    _,a,segments,sampled=authored()
    a['terrain_H'][8:,:]+=raised_ground
    ids=a['building_ids'];a['building_heights']=np.where(ids,building_height,0.)
    for ij in np.ndindex(ids.shape):segments[ij]=[[0.,building_height]] if ids[ij] else []
    ground,d0=effective_ground(ids,a['terrain_H'])
    a.update(effective_ground_H=ground,effective_dem=ground-d0)
    base=Voxelizer(1.,'Standard').generate_combined(a['building_heights'],segments,ids,np.ones(ids.shape,int),
        a['terrain_H'],np.zeros(ids.shape),print_class_info=False)
    _,a['ground_indices']=audit_voxels(base,ids,a['terrain_H'],segments,a['effective_dem'],d0,numba=NUMBA_AVAILABLE)
    sampled.update(top=ground+7.,bottom=ground+2.)
    return base,a,segments,sampled,d0


def integrate(data):
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE
    base,a,segments,sampled,d0=data
    return m.integrate_canopy(base,a,segments,sampled,d0,numba=NUMBA_AVAILABLE)


@pytest.mark.parametrize('height,raised,one_column',[(15.,0.,False),(4.,0.,False),(4.,2.49,True)])
def test_occupied_positions_and_origin_survive_shared_extension(height,raised,one_column):
    data=scene(height,raised);base,a,segments,sampled,d0=data
    if one_column:
        sampled['top']=sampled['bottom']=a['effective_ground_H'].copy()
        sampled['top']=sampled['top'].copy();sampled['top'][10,10]+=30.
        sampled['candidate']=sampled['top']>sampled['bottom']
    before=copy.deepcopy(a);base_before=base.copy()
    current,absent,tree,hi,lo,qa=integrate(data)
    assert current.shape==absent.shape==tree.shape
    assert np.array_equal(absent[:,:,:base.shape[2]],base) and not absent[:,:,base.shape[2]:].any()
    assert np.array_equal(np.where(tree,0,current),absent)
    assert not np.any(tree & (absent!=0)) and np.array_equal(base_before,base)
    for key,value in before.items():assert np.array_equal(value,a[key])
    assert qa['vertical_domain']['D0_H_m']==d0==10.
    assert qa['vertical_domain']['base_prefix_equal']
    if height==15.:
        assert current.shape==base.shape  # No unnecessary expansion for taller Building.
    else:
        assert current.shape[2]>base.shape[2]
    if one_column:
        assert a['effective_ground_H'][10,10]!=d0 and a['building_ids'][10,10]==0
        assert tree[10,10].any() and tree.any(axis=2).sum()==1
        assert qa['vertical_domain']['required_TREE_end_index']==current.shape[2]


@pytest.mark.parametrize('relative_top,relative_bottom',[
    (float(np.nextafter(np.float32(.5),np.float32(0))),0.),(.5,0.),
    (float(np.nextafter(np.float32(.5),np.float32(1))),0.),(2.51,2.5),(2.499999,2.499998)])
def test_rounding_and_thin_crown_rules_match_installed_api(relative_top,relative_bottom):
    data=scene();base,a,segments,sampled,d0=data
    sampled['top'][10,10]=10.+relative_top;sampled['bottom'][10,10]=10.+relative_bottom
    current,absent,tree,hi,lo,qa=integrate(data)
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE
    dtype=np.float32 if NUMBA_AVAILABLE else float
    start,end=(int(float(dtype(v))+.5) for v in (relative_bottom,relative_top))
    if start==end and start>0:start-=1
    expected=np.zeros(current.shape[2],bool);g=int(a['ground_indices'][10,10])
    expected[g+start:g+end]=True
    assert np.array_equal(tree[10,10],expected)


def test_public_allocator_rounding_under_capacity_is_rejected():
    # API ceil(D_eff+tree)+1 = 6, actual g+round(tree) = 2+5 = 7.
    data=scene(raised_ground=.5);base,a,segments,sampled,d0=data
    sampled['bottom']=a['effective_ground_H'].copy();sampled['top']=sampled['bottom'].copy()
    sampled['top'][10,10]+=4.5;sampled['candidate']=sampled['top']>sampled['bottom']
    with pytest.raises(GeometryValidationError,match='public allocation cannot contain'):
        integrate(data)


@pytest.mark.parametrize('case',['nan','infinite','kernel_overflow','inverted','mask','shape','height','ids','D0','ground','indices','base'])
def test_invalid_input_is_rejected(case):
    base,a,segments,sampled,d0=scene()
    if case=='nan':sampled['top'][10,10]=np.nan
    if case=='infinite':sampled['top'][10,10]=np.inf
    if case=='kernel_overflow':sampled['top'][10,10]=1e300
    if case=='inverted':sampled['bottom'][10,10]=100.
    if case=='mask':sampled['candidate'][10,10]=False
    if case=='shape':sampled['bottom']=sampled['bottom'][:-1]
    if case=='height':a['building_heights'][4,4]=np.nan
    if case=='ids':a['building_ids']=a['building_ids'].astype(float)
    if case=='D0':d0+=1
    if case=='ground':a['effective_ground_H'][10,10]+=1
    if case=='indices':a['ground_indices'][10,10]+=1
    if case=='base':base[0,0,0]=0
    with pytest.raises(GeometryValidationError):integrate((base,a,segments,sampled,d0))


def test_only_required_observer_air_is_added_without_moving_observer():
    data=scene(raised_ground=3.49);base,a,segments,sampled,d0=data
    sampled['bottom']=a['effective_ground_H'].copy();sampled['top']=sampled['bottom'].copy()
    sampled['top'][0,0]+=1.;sampled['candidate']=sampled['top']>sampled['bottom']
    current,absent,tree,hi,lo,qa=integrate(data)
    assert base.shape[2]==5 and current.shape[2]==6
    assert a['ground_indices'][10,10]+1==5  # Same index; now inside the shared domain.
    assert qa['vertical_domain']['required_observer_layers']==6
    assert qa['vertical_domain']['required_TREE_end_index']==2
    assert not absent[:,:,5:].any() and not tree[:,:,5:].any()


@pytest.mark.parametrize('fault',['allocation','ground','tree_hole','outside'])
def test_incorrect_api_output_is_not_repaired(monkeypatch,fault):
    from voxcity.generator.voxelizer import Voxelizer
    data=scene();original=Voxelizer.generate_combined
    def changed(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        if fault=='allocation':return result[:,:,:7]
        if fault=='ground':result[0,0,0]=0
        if fault=='tree_hole':result[0,0,4]=0
        if fault=='outside':result[0,0,-1]=-2
        return result
    monkeypatch.setattr(Voxelizer,'generate_combined',changed)
    with pytest.raises(GeometryValidationError):integrate(data)


def test_expanded_solar_uses_same_observers_and_pair_grid():
    data=scene();base,a,segments,sampled,d0=data
    current,absent,tree,hi,lo,qa=integrate(data)
    grid=dict(shape=list(base.shape),axis0_true_azimuth_deg=0.,
        rectangle_vertices_lonlat=[[139.,35.],[139.,35.001],[139.001,35.001],[139.001,35.]],D0_effective_H_m=d0)
    shared=m.shared_grid(grid,qa)
    assert grid['shape']==list(base.shape) and shared['shape']==list(current.shape)
    maps,report=m.solar_pair(current,absent,a,shared,hi,lo)
    assert np.array_equal(maps['observer_index_k'],a['ground_indices']+1)
    assert np.array_equal(maps['observer_valid'],a['building_ids']==0)
    assert report['invariants']['irradiance_increase_cells']==0
    assert report['observer']['nominal_H']=='D0_effective+g+1.5; identical in both cases; not measured 1.5m above source ground'
    with pytest.raises(GeometryValidationError,match='grid'):m.solar_pair(current,absent[:,:,:-1],a,shared,hi,lo)
    with pytest.raises(GeometryValidationError,match='grid'):m.solar_pair(current,absent,a,grid,hi,lo)
    changed=absent.copy();changed[0,0,0]=0
    with pytest.raises(GeometryValidationError,match='pair'):m.solar_pair(current,changed,a,shared,hi,lo)
