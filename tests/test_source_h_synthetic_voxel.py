"""Actual pinned raster + Voxelizer integration; no fabricated 3D outputs."""
import numpy as np
from pyproj import Transformer

from integration.source_h_25d_fixture import build_chain
from ouem.adapters import source_h_synthetic_voxel as a


def execute(tmp_path):
    standard,config,terrain = build_chain(tmp_path)
    before = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    model = a.voxelize_synthetic_source_h(standard['manifest'],tmp_path,config,terrain=terrain,
        synthetic_source_ids=['synthetic_tokyo','synthetic_niigata'])
    assert before=={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    return model


def test_actual_two_building_voxelization_height_ids_ground_and_position(tmp_path):
    result = execute(tmp_path)
    m = result.metadata
    assert m['consumer_validation']==m['technical_validation']=='PASS'
    assert m['voxcity']['commit']==a.PIN
    assert result.voxels.shape==(64,64,16) and result.voxels.dtype==np.int8
    assert set(np.unique(result.voxels))=={-3,0,1}
    assert set(np.unique(result.building_ids))=={0,1,2}
    assert np.all(result.terrain_H==10.25) and np.all(result.effective_dem==0)
    assert np.all(result.voxels[:,:,0]==1)
    assert not np.any(result.voxels[result.building_ids==0]==-3)
    geo = m['grid'];origin=np.array(geo['origin_lonlat'])
    u=np.array(geo['u_vector_lonlat_per_m']);v=np.array(geo['v_vector_lonlat_per_m'])
    du,dv=geo['adjusted_horizontal_mesh_m']
    to_xy=Transformer.from_crs(4326,6677,always_xy=True)
    centres={}
    for row in m['buildings']:
        mask=result.building_ids==row['id']
        levels=15 if row['source_id']=='synthetic_niigata' else 10
        assert row['horizontal_cells']==96 and row['building_voxels']==96*levels
        assert row['ground_H_m']==10.25 and row['k_start_inclusive']==1
        assert row['k_end_exclusive']==1+levels
        assert np.all(result.voxels[mask,1:1+levels]==-3)
        assert np.all(result.voxels[mask,1+levels:]==0)
        assert row['occupied_thickness_m']-row['relative_height_m']==row['height_rounding_delta_m']
        assert row['top_edge_minus_input_H_m']==1+row['height_rounding_delta_m']
        i,j=np.argwhere(mask).mean(axis=0)
        lon,lat=origin+(i+.5)*du*u+(j+.5)*dv*v
        centres[row['source_id']]=to_xy.transform(lon,lat)
    # Authored separated boxes, same ground and approximately same northing.
    x1,y1=centres['synthetic_tokyo'];x2,y2=centres['synthetic_niigata']
    assert abs(x1-(-23846.6))<2 and abs(y1-(-41012.))<2
    assert 25<x2-x1<30 and abs(y2-y1)<2
    assert m['grid']['layout'].startswith('uv_m/SOUTH_UP')
    assert m['vertical']['D0_effective_H_m']==10.25 and m['vertical']['ground_level_exclusive']==1
    assert m['source_h_eligibility']=='NOT_ESTABLISHED'
    assert m['human_review']==m['formal_acceptance']=='NOT_VERIFIED'
    assert set(m['phase5_gates'].values())=={'OPEN'}


def test_projected_diagnostic_arrays_are_not_engine_inputs(tmp_path,monkeypatch):
    actual=a.adapt_synthetic_source_h
    def poisoned(*args,**kwargs):
        model=actual(*args,**kwargs)
        model.terrain_H=np.full((1,1),np.nan)
        model.building_ids=np.full((1,1),999)
        return model
    monkeypatch.setattr(a,'adapt_synthetic_source_h',poisoned)
    result=execute(tmp_path)
    assert result.voxels.shape==(64,64,16)
    assert result.metadata['grid']['projected_diagnostic_arrays_used'] is False
    assert int(np.count_nonzero(result.voxels==-3))==2400
