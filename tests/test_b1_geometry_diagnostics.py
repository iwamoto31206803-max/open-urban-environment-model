"""Small authored saved-array diagnostics, without engine or real-data execution."""
import copy

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from ouem import b1_geometry_diagnostics as m
from ouem.native.building.source_h_geometry import GeometryValidationError


def authored():
    shape=(3,5); nz=9
    ids=np.zeros(shape,int);ids[1,1]=1
    base=np.zeros((*shape,nz),np.int8);base[:,:,0]=1;base[1,1,1:4]=-3
    current=base.copy();current[0,0,1:2]=-2;current[1,1,4:6]=-2
    ground=np.full(shape,20.)
    roi=np.zeros(shape,bool);roi[1:,:]=True
    a=dict(voxels=base,building_ids=ids,ground_indices=np.ones(shape,int),terrain_H=ground,
           effective_ground_H=ground.copy(),effective_dem=np.zeros(shape),roi_mask=roi)
    top,bottom=ground.copy(),ground.copy()
    for ij,t,b in [((0,0),21.2,21.1),((0,1),23.,19.9),((0,2),20.2,20.1),((1,1),25.4,22.)]:
        top[ij],bottom[ij]=t,b
    valid=ids==0;now=np.where(valid,20.,np.nan);absent=np.where(valid,50.,np.nan)
    s=dict(current_voxels=current,no_canopy_voxels=base.copy(),tree_mask=current==-2,
           observer_index_k=np.full(shape,2,int),observer_valid=valid,
           canopy_top_H=top,canopy_bottom_H=bottom,canopy_candidate=top>bottom,
           canopy_missing=np.zeros(shape,bool),canopy_outside=np.zeros(shape,bool),envelope_state=np.ones(shape),
           solar_current=now,solar_no_canopy=absent,solar_difference=absent-now)
    grid=dict(shape=[*shape,nz],D0_effective_H_m=20.,nominal_voxel_size_m=1.)
    cells=[dict(i=1,j=1,owner_id=1,contributor_ids=[1],segments=[[0.,3.4]])]
    buildings=[dict(id=1,height=3.4,z_top_abs=23.4,source_id='source-1',ouem_id='ouem-1')]
    return a,s,grid,cells,buildings


def test_observers_rounding_priority_and_inputs_unchanged():
    a,s,g,c,b=authored(); before={k:v.copy() for k,v in s.items()}
    summary,maps,flags,rows=m.analyze(a,s,g,c,b,numba=True)
    assert all(v==0 for v in summary['checks'].values())
    assert summary['distributions']['roi_valid']['observer_minus_dem']['median']==2.5
    assert summary['distributions']['domain_valid']['observer_minus_surface']['median']==1.5
    assert summary['distributions']['roi_excluded']['observer_H']['count']==1
    assert summary['counts']['thin_expanded']==1 and summary['counts']['rounded_vanished']==1
    assert summary['counts']['below_effective_ground']==1
    assert summary['counts']['priority_removed_voxels']==1
    assert flags['thin_expanded'][0,0] and flags['rounded_vanished'][0,2]
    assert maps['tree_bottom_error_pre_priority'][1,1]==1.
    assert maps['tree_bottom_error_actual'][1,1]==2.  # partial Building exclusion, not rounding alone
    assert rows[0]['top_error_m']==pytest.approx(.6)
    assert all(np.array_equal(s[k],v,equal_nan=True) for k,v in before.items())


@pytest.mark.parametrize('fault',['tree','observer','pair','source_height','shape'])
def test_corruption_is_reported_or_rejected_without_repair(fault):
    a,s,g,c,b=authored()
    if fault=='tree':s['current_voxels'][0,4,0]=-2
    if fault=='observer':s['observer_index_k'][2,3]+=1
    if fault=='pair':s['no_canopy_voxels'][2,3,5]=-3
    if fault=='source_height':b[0]['height']=4.4
    if fault=='shape':s['observer_valid']=s['observer_valid'][:1]
    if fault in ('source_height','shape'):
        with pytest.raises(GeometryValidationError):m.analyze(a,s,g,c,b,numba=True)
    else:
        result,*_=m.analyze(a,s,g,c,b,numba=True)
        key={'tree':'TREE_interval_mismatch','observer':'current_observer_transition_mismatch',
             'pair':'pair_non_TREE_mismatch'}[fault]
        assert result['checks'][key]>0


def test_footprint_fractions_on_non_square_translated_grid():
    g=dict(shape=[3,5,9],origin_lonlat=[100.,20.],u_step_lonlat=[0.,1.],v_step_lonlat=[1.,0.])
    feature=dict(geometry=mapping(box(101.,20.,102.,21.)),properties={'id':7})
    cells=[dict(i=0,j=1,contributor_ids=[7])]
    assert not m.footprint_check(g,[feature],cells)['mismatch_cells']
    wrong=copy.deepcopy(cells);wrong[0]['contributor_ids']=[8]
    assert m.footprint_check(g,[feature],wrong)['mismatch_cells'][0]['i']==0


def test_source_chm_is_sampled_at_envelope_pixel_centres(tmp_path):
    paths=[tmp_path/n for n in ('envelope.tif','chm.tif','dem.tif')]
    for p,values,res in [(paths[0],np.zeros((2,2)),1.),(paths[1],np.arange(16.).reshape(4,4),.5),
                          (paths[2],np.array([[20.,21.],[22.,23.]]),1.)]:
        with rasterio.open(p,'w',driver='GTiff',height=values.shape[0],width=values.shape[1],count=1,
                           dtype='float64',crs=6677,transform=from_origin(0,2,res,res)) as ds:ds.write(values,1)
    chm,dem=m.source_samples(*paths,np.array([[.1,1.1]]),np.array([[1.1,1.1]]))
    np.testing.assert_array_equal(chm,[[5.,7.]])  # direct original centres would give 4,6
    np.testing.assert_array_equal(dem,[[20.,21.]])
    with pytest.raises(GeometryValidationError,match='outside'):
        m.source_samples(*paths,np.array([[-1.]]),np.array([[1.]]))


def test_existing_output_is_rejected_before_any_run_read(tmp_path):
    with pytest.raises(GeometryValidationError,match='new directory'):
        m.generate(tmp_path,tmp_path)
