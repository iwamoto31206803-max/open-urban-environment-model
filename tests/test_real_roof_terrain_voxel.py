"""Small independent terrain fixtures; no real data or older test-fixture imports."""
from copy import deepcopy

import numpy as np
import pytest
import rasterio
from rasterio import Affine

from ouem import real_roof_terrain_voxel as t


def vertical():
    return t.vertical_conditions(t.roof.VERTICAL, dict(vertical="CONDITIONAL", vertical_evidence=dict(
        ward_tp="INFERRED_FROM_SOURCE_LINEAGE", epoch="NOT_VERIFIED", accuracy="NOT_VERIFIED", datum_realization="NOT_VERIFIED")))


def fixture():
    grid=t.roof.geometry.GridSpec((0,0,3,1))
    identity=dict(profile=t.roof.PROFILE,vertical=deepcopy(t.roof.VERTICAL),grid=t.roof.grid_metadata(grid),
        ground_faces=[dict(standard_xyz_rings=[[[0,0,8],[2,0,8],[2,1,8],[0,1,8],[0,0,8]]])],
        label="F",source_id="terrain-fixture",ouem_id="test")
    maps=dict(top=np.array([[15.,18.,np.nan]]),state=np.array([[1,1,0]],dtype=np.uint8),
              roof_coverage=np.array([[1.,.5,0.]]),footprint_fraction=np.array([[1.,.5,0.]]))
    baseline,qa=t.base.prepare(identity,maps)
    old=np.zeros((1,3,11),dtype=np.int8)
    old[:,:,0]=1
    old[0,0,1:8]=-3
    old[0,1,1:11]=-3
    source=dict(inputs=baseline,maps=maps,qa=qa)
    inputs,q=t.prepare(source,np.array([[10.,14.,9.]]),vertical())
    return dict(source,inputs=inputs,qa=q,baseline_inputs=baseline,baseline_voxels=old,
                baseline_upper=np.array([[16.,19.,np.nan]]),sampling={})


def test_real_api_owner_ground_d0_and_absolute_H_comparison():
    item=fixture()
    before=t.voxel.input_identity(item["inputs"])
    a,b=t.execute(item),t.execute(item)
    expected=np.zeros((1,3,10),dtype=np.int8)
    expected[0,:2,:3]=-1
    expected[0,:2,3]=1
    expected[0,2,0]=1
    expected[0,0,4:7]=-3
    expected[0,1,4:10]=-3
    np.testing.assert_array_equal(a["voxels"],expected)
    np.testing.assert_array_equal(a["voxels"],b["voxels"])
    assert before==t.voxel.input_identity(item["inputs"])
    assert a["qa"]["d0"]==9
    assert a["qa"]["effective_ground"]==[[12,12,9]]
    np.testing.assert_allclose(a["upper"][0,:2],[16,19])
    comparison=a["qa"]["comparison"]
    assert comparison["upper_H_minus_B1_m"]==[0,0]
    assert comparison["bottom_H_minus_B1_m"]==[4,4]
    assert comparison["absolute_interval_symmetric_difference_m3"]==8
    item["inputs"]["dem"][0,0]+=1
    with pytest.raises(ValueError,match="handoff"):t.execute(item)


def test_vertical_conflict_and_invalid_ground_are_not_corrected():
    with pytest.raises(ValueError,match="vertical"):t.vertical_conditions(dict(t.roof.VERTICAL,source_vertical_epsg=5773),dict())
    item=fixture()
    source=dict(item,inputs=item["baseline_inputs"],qa=dict(anchor_H=8.))
    with pytest.raises(ValueError,match="below"):t.prepare(source,np.full((1,3),30.),vertical())
    with pytest.raises(ValueError,match="DEM"):t.prepare(source,np.full((1,3),np.nan),vertical())


def test_half_metre_sampling_boundary_ties_and_NoData_outside(tmp_path):
    p=tmp_path/"dem.tif"
    raw=np.arange(24,dtype=np.float32).reshape(4,6)
    def write():
        with rasterio.open(p,"w",driver="GTiff",height=4,width=6,count=1,dtype="float32",crs="EPSG:6677",
                           transform=Affine(.5,0,0,0,-.5,2),nodata=-9999) as dst:dst.write(raw,1)
    write()
    grid=t.roof.geometry.GridSpec((0,0,3,2))
    dem,indices,qa=t.sample_dem(p,grid)
    np.testing.assert_array_equal(dem,[[7,9,11],[19,21,23]])
    assert indices[0,0].tolist()==[1,1]
    assert qa["boundary_ties"]==6
    assert qa["x_offset_from_selected_source_centre_m"]==[-.25,-.25]
    assert qa["y_offset_from_selected_source_centre_m"]==[.25,.25]
    raw[1,1]=-9999
    write()
    with pytest.raises(ValueError,match="NoData"):t.sample_dem(p,grid)
    with pytest.raises(ValueError):t.sample_dem(p,t.roof.geometry.GridSpec((10,10,11,11)))


def test_missing_data_bad_B1_sha_and_partial_failure_no_completion(tmp_path,monkeypatch):
    result=t.run(tmp_path,tmp_path/"absent",tmp_path,tmp_path,tmp_path/"missing",tmp_path)
    assert result["technical_execution"]=="NOT_EXECUTED" and not (tmp_path/"missing/manifest.json").exists()
    b1=tmp_path/"B1"
    b1.mkdir()
    (b1/"manifest.json").write_text('{}')
    from ouem.consumers.source_h_standard import Watch
    monkeypatch.setattr(t.base,"load_inputs",lambda *args:({},Watch(tmp_path),{}))
    result=t.run(tmp_path,tmp_path,b1,tmp_path,tmp_path/"sha",tmp_path)
    assert result["technical_execution"]=="BLOCKED" and result["stopped_at"]=="B2-0"
    class Frozen:
        identities={}
        def unchanged(self):pass
    monkeypatch.setattr(t,"load_inputs",lambda *args:({"F":fixture()},Frozen(),{}))
    def fail(*args,**kwargs):raise OSError("injected output failure")
    monkeypatch.setattr(t.base,"save_building",fail)
    result=t.run(tmp_path,tmp_path,tmp_path,tmp_path,tmp_path/"partial",tmp_path)
    assert result["technical_execution"]=="BLOCKED" and result["stopped_at"]=="B2-1"
    assert not (tmp_path/"partial/manifest.json").exists()
