"""Authored canopy samples + actual pinned Voxelizer/solar; no real acceptance."""
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ouem import real_komae_solar as m
from ouem.native.building.source_h_geometry import GeometryValidationError
from ouem.consumers.source_h_standard import Watch


@pytest.mark.parametrize('case', ['valid', 'nodata', 'state', 'outside', 'crs'])
def test_saved_centre_sampling_state_is_not_presence(tmp_path, case):
    paths = [tmp_path/n for n in ('top.tif','bottom.tif','state.tif')]
    values = [np.array([[14.,10.],[16.,18.]]), np.array([[12.,10.],[13.,14.]]), np.ones((2,2))]
    if case=='nodata': values[0][0,0] = -9999
    if case=='state': values[2][0,0] = 2
    for path, value in zip(paths,values):
        with rasterio.open(path,'w',driver='GTiff',width=2,height=2,count=1,dtype='float32',
                           crs=3857 if case=='crs' else 6677,transform=from_origin(-23352,-40788,1,1),
                           nodata=None if path==paths[2] else -9999.) as ds: ds.write(value.astype('float32'),1)
    x=np.array([[-23351.5,-23350.5],[-23351.5,-23350.5]])
    y=np.array([[-40788.5,-40788.5],[-40789.5,-40789.5]])
    if case=='outside': x[0,0]-=10
    if case=='crs':
        with pytest.raises(GeometryValidationError,match='CRS'): m.sample_canopy(paths,x,y)
    else:
        result=m.sample_canopy(paths,x,y)
        assert not result['candidate'][0,1]  # Valid state1, zero height: no TREE candidate.
        assert bool(result['candidate'][0,0]) is (case=='valid')
        assert bool(result['missing'][0,0]) is (case=='nodata')
        assert bool(result['outside'][0,0]) is (case=='outside')


def authored():
    from voxcity.generator.voxelizer import Voxelizer
    shape=(16,16); ids=np.zeros(shape,dtype=int);ids[4:7,4:7]=1
    heights=np.where(ids,4.,0.);segments=np.empty(shape,object)
    for ij in np.ndindex(shape): segments[ij]=[[0.,4.]] if ids[ij] else []
    dem=np.full(shape,10.)
    base=Voxelizer(1.,'Standard').generate_combined(heights,segments,ids,np.ones(shape,dtype=int),dem,np.zeros(shape),print_class_info=False)
    base=np.pad(base,((0,0),(0,0),(0,14-base.shape[2])))
    roi=np.zeros(shape,bool);roi[4:12,4:12]=True
    a=dict(building_ids=ids,building_heights=heights,terrain_H=dem,effective_ground_H=dem.copy(),
           effective_dem=np.zeros(shape),ground_indices=np.ones(shape,dtype=int),roi_mask=roi,building_segments=segments)
    sampled=dict(top=np.full(shape,17.),bottom=np.full(shape,12.),candidate=np.ones(shape,bool),valid=np.ones(shape,bool))
    return base,a,segments,sampled


@pytest.mark.parametrize('case', ['normal','below','too_high'])
def test_absolute_h_building_priority_and_unchanged_pair(case):
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE
    base,a,segments,sampled=authored()
    if case=='below': sampled['bottom'][0,0]=9.
    if case=='too_high': sampled['top'][:]=40.
    if case=='too_high':
        current,absent,mask,high,low,qa=m.integrate_canopy(base,a,segments,sampled,10.,numba=NUMBA_AVAILABLE)
        assert current.shape==absent.shape==(16,16,31)
        assert np.array_equal(absent[:,:,:base.shape[2]],base) and not absent[:,:,base.shape[2]:].any()
        assert qa['vertical_domain']['added_upper_air_layers']==17
    else:
        current,absent,mask,high,low,qa=m.integrate_canopy(base,a,segments,sampled,10.,numba=NUMBA_AVAILABLE)
        assert np.array_equal(absent,base) and np.array_equal(current[base==-3],base[base==-3])
        assert not np.any(mask & (base!=0)) and qa['building_priority_removed_tree_voxels']>0
        assert mask[10,10,3:8].all() and not mask[10,10,:3].any()
        assert qa['below_effective_ground_excluded_columns']==int(case=='below')


def test_common_canopy_places_tree_and_preserves_legacy_scene(monkeypatch):
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE
    from ouem.canopy_height_candidate import effective_hag, meta_presence_fields
    from ouem.height_envelope import Samples

    base, ground, segments, sampled = authored()
    hag = np.zeros(base.shape[:2])
    hag[0, 0] = hag[4, 4] = 2.
    present = hag > 0
    blank = np.zeros_like(present)
    samples = Samples(hag, blank, blank, {})
    fields = meta_presence_fields(samples, effective_hag(samples))
    top = 10. + hag
    bottom = np.where(present, 11., 10.)
    valid = sampled["valid"]
    expected = m.integrate_canopy(base, ground, segments,
                                 dict(top=top, bottom=bottom, valid=valid, candidate=present),
                                 10., numba=NUMBA_AVAILABLE)
    options = dict(profile="meta_estimated_canopy_hag", provenance="synthetic fixture",
                   numba=NUMBA_AVAILABLE)
    current, control, tree, high, low, qa = m.integrate_common_canopy(
        base, ground, segments, fields, top, bottom, valid, 10., **options)
    for actual, legacy in zip((current, control, tree, high, low), expected[:5]):
        np.testing.assert_array_equal(actual, legacy)
    np.testing.assert_array_equal(control, base)
    assert tree[0, 0, 2] and tree.sum() == 1
    assert fields["present"][4, 4] and not tree[4, 4].any() and base[4, 4, 2] == -3
    assert fields["absent"][0, 1] and not tree[0, 1].any()
    assert qa["building_priority_removed_tree_voxels"] == 1

    def unexpected_engine(*args, **kwargs):
        pytest.fail("incompatible common input reached placement")

    monkeypatch.setattr(m, "integrate_canopy", unexpected_engine)
    unknown = fields["unknown"].copy()
    unknown[0, 0] = True
    invalid = valid.copy()
    invalid[0, 0] = False
    for mask, heights_valid in ((dict(fields, unknown=unknown), valid), (fields, invalid)):
        with pytest.raises(GeometryValidationError, match="complete assessed domain"):
            m.integrate_common_canopy(
                base, ground, segments, mask, top, bottom, heights_valid, 10., **options)
    inconsistent_top = top.copy()
    inconsistent_top[0, 1] = 12.
    with pytest.raises(GeometryValidationError, match="conflicts with modelled absence"):
        m.integrate_common_canopy(
            base, ground, segments, fields, inconsistent_top, bottom, valid, 10., **options)


def test_real_solar_common_observers_sign_and_crop_diagnostic():
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE
    base,a,segments,sampled=authored()
    current,absent,mask,high,low,qa=m.integrate_canopy(base,a,segments,sampled,10.,numba=NUMBA_AVAILABLE)
    grid=dict(axis0_true_azimuth_deg=0.,rectangle_vertices_lonlat=[[139.,35.],[139.,35.001],[139.001,35.001],[139.001,35.]],D0_effective_H_m=10.)
    arrays,report=m.solar_pair(current,absent,a,grid,high,low)
    valid=arrays['observer_valid']
    assert np.array_equal(valid,a['building_ids']==0)
    assert np.all(arrays['solar_difference'][valid]>=-1e-9)
    assert np.array_equal(arrays['solar_difference'],arrays['solar_no_canopy']-arrays['solar_current'],equal_nan=True)
    assert np.array_equal(arrays['observer_index_k'],a['ground_indices']+1)
    assert report['ROI']['reduction_cells']>0 and report['actual_api_calls']==5
    assert report['invariants']['irradiance_increase_cells']==0


def test_preflight_rejects_unbound_previous_success(tmp_path):
    base=tmp_path/'base';base.mkdir();(base/'report.json').write_text('{"status":"COMPLETED"}')
    with pytest.raises(GeometryValidationError):
        m.preflight(SimpleNamespace(base_run=base),Watch(tmp_path))
