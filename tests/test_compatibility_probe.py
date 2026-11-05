from copy import deepcopy

import numpy as np
from pyproj import Transformer
import pytest

from ouem.compatibility_probe import inspect
from ouem.native.building.source_h_geometry import GeometryValidationError


def snapshot():
    # Non-square authored grid. Known surface index 0 and observer index 2.
    voxels=np.zeros((4,6,8),dtype="int8")
    voxels[...,0]=1
    voxels[1,2,1:4]=-3
    ids=np.zeros((4,6),dtype="int32")
    ids[1,2]=17
    dem=np.full((4,6),25.)
    i,j=np.indices((4,6))
    lon=139.6+(j+.5)*1e-5
    lat=35.65+(i+.5)*1e-5
    x,y=Transformer.from_crs(4326,6677,always_xy=True).transform(lon,lat)
    xy=np.stack((x,y),axis=-1)
    roi=(i>=1)&(i<3)&(j>=1)&(j<5)
    meta=dict(shape=list(voxels.shape),axes=["north","east","up"],mesh_m=1.,xy_epsg=6677,
              canopy="NONE",d0_effective_abs_m=25.,numba=True,
              origin_lonlat=[139.6,35.65],u_step_lonlat=[0.,1e-5],v_step_lonlat=[1e-5,0.],
              domain_bounds=[x.min()-.1,y.min()-.1,x.max()+.1,y.max()+.1],
              evaluation_bounds=[x[1:3,1:5].min()-.01,y[1:3,1:5].min()-.01,
                                 x[1:3,1:5].max()+.01,y[1:3,1:5].max()+.01],
              observer_height_m=1.5,source_id_by_numeric_id={"17":"authored-building"})
    valid=ids==0
    index=np.where(valid,2,-1)
    xyz=np.concatenate((xy,np.full((4,6,1),27.5)),axis=-1)
    return [voxels,ids,dem,dem.copy(),xy,roi,meta,index,valid,xyz]


def test_authored_readonly_handoff():
    data=snapshot()
    before=deepcopy(data)
    for item in data:
        if isinstance(item,np.ndarray):
            item.flags.writeable=False
    result=inspect(*data)
    assert result["status"]=="NUMERICAL_HANDOFF_PASS"
    assert result["valid_observers"]==23 and result["roi_cells"]==8
    assert result["tree_voxels"]==0
    assert result["terrain_integration_ready"] is False
    for a,b in zip(data,before):
        if isinstance(a,np.ndarray):
            np.testing.assert_array_equal(a,b)
        else:
            assert a==b


def test_canopy_provenance_is_independent_of_lod():
    data=snapshot()
    data[0][2,3,2:4]=-2
    data[6]["canopy"]="ESTIMATED"
    result=inspect(*data)
    assert result["tree_voxels"]==2
    # LoD and height-model labels are irrelevant to this numeric handoff.
    for lod in (1,2,"mixed"):
        data[6]["source_lod"]=lod
        assert inspect(*data)==result


@pytest.mark.parametrize("fault",[
    "axes","shape","D0","ROI","class","canopy","xy","observer_xy","observer_z",
    "observer_index","owner","surface","ground","domain","dtype","source_id",
])
def test_inconsistent_snapshot_rejected(fault):
    data=snapshot()
    if fault=="axes":
        data[6]["axes"]=["east","north","up"]
    elif fault=="shape":
        data[6]["shape"]=[6,4,8]
    elif fault=="D0":
        data[6]["d0_effective_abs_m"]=24.
    elif fault=="ROI":
        data[5][0,0]=True
    elif fault=="class":
        data[0][0,0,3]=127
    elif fault=="canopy":
        data[0][0,0,2]=-2
    elif fault=="xy":
        data[4]=data[4][::-1].copy()
    elif fault=="observer_xy":
        data[9][0,0,0]+=1
    elif fault=="observer_z":
        data[9][0,0,2]+=.5
    elif fault=="observer_index":
        data[7][0,0]+=1
    elif fault=="owner":
        data[1][1,2]=0
    elif fault=="surface":
        data[0][0,0,0]=-1
    elif fault=="ground":
        data[3][0,0]+=1
    elif fault=="domain":
        data[6]["domain_bounds"][0]+=100
    elif fault=="dtype":
        data[0]=data[0].astype("int16")
    elif fault=="source_id":
        data[6]["source_id_by_numeric_id"]={}
    with pytest.raises(GeometryValidationError):
        inspect(*data)
