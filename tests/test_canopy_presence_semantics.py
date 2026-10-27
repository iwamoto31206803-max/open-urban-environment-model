"""Phase 4B characterization; validity, estimated height and TREE are distinct.

No presence classifier or new Standard state encoding is implemented here.
"""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ouem import height_envelope as env
from ouem.canopy_shadow_poc import ShadowBlocked, relative_grids, build_pair
from ouem.canopy_shadow_sensitivity import build_isotropic


@pytest.fixture(scope="module", autouse=True)
def pinned_engine():
    from numba import set_num_threads
    from ouem.komae_integration import voxcity_provenance
    assert voxcity_provenance()["verified"]
    set_num_threads(2)


def raster(path, values, *, nodata=-9999., mask=None):
    values = np.asarray(values,dtype='float32')
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path,'w',driver='GTiff',width=values.shape[1],height=values.shape[0],
                count=1,dtype='float32',crs=6677,transform=from_origin(0,1,1,1),nodata=nodata) as ds:
            ds.write(values,1)
            if mask is not None: ds.write_mask(np.asarray(mask,dtype='uint8'))


def samples(values, *, missing=False, outside=False):
    a = np.asarray(values,dtype=float)
    return env.Samples(a,np.full(a.shape,missing),np.full(a.shape,outside),{})


def test_small_raster_matrix_keeps_zero_missing_invalid_and_support_separate(tmp_path):
    chm,dem = tmp_path/'chm.tif',tmp_path/'dem.tif'
    mask = [[255,255,0,0,255,255,255,255,255,255,255]]
    raster(chm,[[5.,0.,-9999.,0.,-1.,np.nan,np.inf,2.,1e-8,.1,3.]],mask=mask)
    raster(dem,[[10.,10.,10.,10.,10.,10.,10.,-9999.,10.,10.]])
    grid = env.GridSpec((0,0,12,1))
    c,d = env.sample_raster(chm,grid),env.sample_raster(dem,grid)
    top,bottom,state,qa = env.calculate(grid,c,d,env.ConstantCR(.6))
    assert state.tolist() == [[1,1,2,2,8,8,8,4,1,1,64,96]]
    assert c.values[0,1] == c.values[0,3] == 0
    assert not c.missing[0,1] and c.missing[0,3]
    assert c.outside[0,11] and d.outside[0,10] and d.outside[0,11]
    assert not c.missing[0,11]  # outside is not an inside-source mask observation
    nonvalid = state != 1
    assert np.all(top[nonvalid] == -9999) and np.all(bottom[nonvalid] == -9999)
    assert top[0,1] == bottom[0,1] == 10  # valid zero is not NoData
    assert c.values[0,8] > 0 and top[0,8] == bottom[0,8] == 10  # Float32 depth collapse
    assert qa['state_counts']['zero_height_valid'] == 1
    assert qa['state_counts']['missing_chm'] == 2
    assert qa['state_counts']['outside_chm'] == 1
    assert qa['state_counts']['outside_dem'] == 2
    with pytest.raises(ShadowBlocked,match='missing/invalid/outside'):
        relative_grids(top,bottom,d.values,state)


@pytest.mark.parametrize('nodata,expected',[(None,1),(0.,2)])
def test_zero_requires_mask_and_nodata_metadata_not_just_value(tmp_path,nodata,expected):
    p=tmp_path/'zero.tif';raster(p,[[0.]],nodata=nodata)
    grid=env.GridSpec((0,0,1,1));c=env.sample_raster(p,grid)
    _,_,state,_=env.calculate(grid,c,samples([[10.]]),env.ConstantCR())
    assert c.values.item() == 0
    assert state.item() == expected


@pytest.mark.parametrize('nodata,expected',[(None,8),(float('nan'),2)])
def test_unmasked_nan_is_invalid_but_declared_nan_nodata_is_missing(tmp_path,nodata,expected):
    p=tmp_path/'nan.tif';raster(p,[[np.nan]],nodata=nodata)
    grid=env.GridSpec((0,0,1,1));c=env.sample_raster(p,grid)
    top,_,state,_=env.calculate(grid,c,samples([[10.]]),env.ConstantCR())
    assert state.item() == expected and top.item() == -9999


@pytest.mark.parametrize('kind,expected',[
    ('both_missing',6),('both_outside',96),('negative_chm',8),
    ('dem_nonfinite',16),('negative_dem_valid',1),('overflow',128)])
def test_combined_error_bits_and_negative_dem_are_not_presence_classes(kind,expected):
    grid=env.GridSpec((0,0,1,1));c=samples([[2.]]);d=samples([[10.]])
    if kind=='both_missing': c.missing[:]=True;d.missing[:]=True
    if kind=='both_outside': c.outside[:]=True;d.outside[:]=True
    if kind=='negative_chm': c.values[:]=-1
    if kind=='dem_nonfinite': d.values[:]=np.inf
    if kind=='negative_dem_valid': d.values[:]=-2
    if kind=='overflow': c.values[:]=3e38;d.values[:]=3e38
    _,_,state,_=env.calculate(grid,c,d,env.ConstantCR())
    assert state.item()==expected
    assert bool(state.item())  # every nonvalid bitset is also truthy: never bool(state)


def test_state_raster_storage_mask_does_not_mean_envelope_validity(tmp_path):
    grid=env.GridSpec((0,0,4,1));state=np.array([[1,2,32,96]],dtype='uint8')
    path=tmp_path/'state.tif'
    env.write_verified(path,state,grid,None,'SYNTHETIC ONLY')
    with rasterio.open(path) as ds:
        assert ds.nodata is None and np.all(ds.read_masks(1)==255)
        assert (ds.read(1)==env.VALID).tolist()==[[True,False,False,False]]


@pytest.mark.parametrize('size',[1.,.5])
def test_positive_zero_float32_collapse_and_voxel_rounding_are_distinct(size):
    grid=env.GridSpec((0,0,5,1))
    chm=samples([[5.,0.,1e-8,.1,1.]])
    dem=samples([[10.,10.,10.,10.,10.]])
    top,bottom,state,qa=env.calculate(grid,chm,dem,env.ConstantCR())
    assert np.all(state==1)
    assert chm.values[0,2]>0 and top[0,2]==bottom[0,2]
    assert top[0,3]>bottom[0,3]  # positive depth but both relative faces round to zero
    d,t,b=relative_grids(top,bottom,dem.values,state)
    factor=int(1/size)
    d,t,b=(np.repeat(np.repeat(a,factor,axis=0),factor,axis=1) for a in (d,t,b))
    pair=build_isotropic(d,t,b,(0,0,5,1),0,size)
    columns=(pair.b.voxels.classes==-2).any(axis=2)
    assert columns[0,::factor].tolist()==[True,False,False,False,True]
    assert qa['state_counts']['zero_height_valid']==1
    assert np.count_nonzero(chm.values>0)==4 and columns.sum()==2*factor**2
    if size==1:
        previous=build_pair(d,t,b,(0,0,5,1),0)
        assert np.array_equal(previous.b.voxels.classes,pair.b.voxels.classes)


@pytest.mark.parametrize('size',[1.,.5])
def test_positive_thin_crown_can_be_expanded_without_a_presence_judgment(size):
    grid=env.GridSpec((0,0,1,1))
    top,bottom,state,_=env.calculate(grid,samples([[1.2]]),samples([[10.]]),env.ConstantCR(.1))
    d,t,b=relative_grids(top,bottom,np.array([[10.]]),state)
    factor=int(1/size)
    d,t,b=(np.repeat(np.repeat(a,factor,axis=0),factor,axis=1) for a in (d,t,b))
    pair=build_isotropic(d,t,b,(0,0,1,1),0,size)
    tree=np.flatnonzero(pair.b.voxels.classes[0,0]==-2)
    hi=int(float(np.float32(t[0,0]))/size+.5)
    assert tree.tolist()==[hi]  # ground 1 + (hi-1) -> single expanded layer
    assert len(tree)*size != pytest.approx(float(top[0,0]-bottom[0,0]))


def test_acquisition_keeps_valid_zero_and_masked_zero_distinct(tmp_path):
    from rasterio.shutil import copy as rio_copy
    from ouem.acquire.meta_chmv2 import mosaic_crop
    from ouem.study_area import StudyArea
    plain,cog,out=(tmp_path/n for n in ['plain.tif','cog.tif','out.tif'])
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(plain,'w',driver='GTiff',width=2,height=2,count=1,dtype='uint8',
                crs=3857,transform=from_origin(0,2,1,1),nodata=None) as ds:
            ds.write(np.zeros((2,2),dtype='uint8'),1)
            ds.write_mask(np.array([[255,0],[255,255]],dtype='uint8'))
        rio_copy(plain,cog,driver='COG')
    rec=mosaic_crop([cog],StudyArea('synthetic','synthetic',3857,0,0,2,2),out)
    with rasterio.open(out) as ds:
        assert ds.nodata is None and np.all(ds.read(1)==0)
        assert ds.read_masks(1).tolist()==[[255,0],[255,255]]
    assert rec['nodata_pixels']==1
