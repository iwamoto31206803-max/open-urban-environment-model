from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from pyproj import Transformer
import rasterio
from rasterio.transform import from_origin

from ouem import candidate_b_t4b1 as t


def test_outside_aoi_blocks_before_engine():
    lon,lat = Transformer.from_crs(6677,4326,always_xy=True).transform(t.AOI[0]-1,t.AOI[1]+1)
    def engine(*args,**kwargs):
        pytest.fail("engine DEM called before coverage gate")
    with pytest.raises(ValueError,match="outside the T3 AOI"):
        t.sample_dem(None,dict(lons=[[lon]],lats=[[lat]],grid_size=(1,1)),[],engine)


@pytest.mark.parametrize("mode",["nearest","hull","masked","engine_mismatch"])
def test_dem_guard_and_lookup(tmp_path,mode):
    path = tmp_path/"tiny.tif"
    x,y = t.AOI[0],t.AOI[1]
    data = np.array([[1.,2.],[3.,4.]],dtype="float32")
    if mode=="masked":
        data[1,0] = -32767
    with rasterio.open(path,"w",driver="GTiff",width=2,height=2,count=1,dtype="float32",
                       crs="EPSG:6677",transform=from_origin(x,y+1,.5,.5),nodata=-32767) as ds:
        ds.write(data,1)
    lon,lat = Transformer.from_crs(6677,4326,always_xy=True).transform(
        x+(.1 if mode=="hull" else .25),y+.25)
    centres = dict(lons=[[lon]],lats=[[lat]],grid_size=(1,1))
    def engine(path,mesh,rectangle,*,dem_interpolation):
        assert mesh==1. and dem_interpolation is False
        assert mode not in ("hull","masked")
        return np.array([[99. if mode=="engine_mismatch" else 3.]])
    if mode=="nearest":
        dem,_,indices,_ = t.sample_dem(path,centres,[],engine)
        np.testing.assert_array_equal(dem,[[3.]])
        np.testing.assert_array_equal(indices,[[[1,0]]])
    else:
        with pytest.raises(ValueError,match={"hull":"extrapolate","masked":"invalid","engine_mismatch":"disagrees"}[mode]):
            t.sample_dem(path,centres,[],engine)


def test_zero_owner_retained_and_ground_is_owner_cell_mean():
    frame = pd.DataFrame(dict(id=[1,2],ouem_id=["a","b"],source_id=["raw-a","raw-b"],
                              source_lod=[1,2],height=[1.,1.]))
    calls = []
    def engine(buildings,mesh,rectangle,*,overlapping_footprint):
        assert mesh==1. and overlapping_footprint is True
        ids = np.full((1,2),buildings.id.iloc[0],dtype=float)
        segments = np.empty(ids.shape,dtype=object)
        segments.fill([])
        calls.append(tuple(buildings.id))
        return np.zeros_like(ids),segments,ids,buildings
    ids,_,claims,rows,result = t.grid_buildings(frame,[],engine,np.array([[24.,26.]]),
                                                {"a":[30.,32.],"b":[31.,35.]})
    np.testing.assert_array_equal(ids,[[1,1]])
    np.testing.assert_array_equal(claims,[[2,2]])
    assert calls==[(1,),(2,),(1,2),(1,2)]
    assert (rows[0]["g_eff_abs"],rows[0]["height"],rows[0]["min_height"])==(25.,7.,0.)
    assert rows[1]["g_eff_abs"] is None and rows[1]["isolated_cells"]==2
    assert rows[1]["flags"]==["NO_OWNED_ENGINE_CELL","LOST_OWNERSHIP_OR_REMAP"]
    assert result["converged"] and result["overlapping_candidate_cells"]==2
