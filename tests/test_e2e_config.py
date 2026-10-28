"""Strict settings and authored end-to-end public-engine fixtures, never real-city runs."""
import copy
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from ouem import e2e_config as config
from ouem import real_komae_voxel as voxel
from ouem import real_komae_solar as solar
from ouem import height_envelope as envelope
from ouem.consumers.source_h_standard import Watch
from ouem.native.building.source_h_geometry import GeometryValidationError
from ouem.native.terrain import accept_native_terrain
from ouem.standardize.terrain import standardize_native_terrain
from test_source_h_ingestion import plan, source_faces
from test_source_h_standard import native, run as standard_buildings
from test_real_komae_voxel import terrain, box_tree


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data), encoding='utf8')


def record(root, path):
    return dict(path=Path(path).relative_to(root).as_posix(), sha256=sha(path))


@pytest.fixture
def settings(tmp_path):
    area = tmp_path/'area.yaml'
    area.write_text('study_area:\n  id: authored\ncrs:\n  epsg: 6677\nextent:\n  xmin: -24000\n  ymin: -42000\n  xmax: -23000\n  ymax: -40000\n')
    files = {}
    for key,name in [('building_manifest','building.json'),('terrain','terrain.tif'),
                     ('terrain_manifest','terrain.tif.manifest.json'),('envelope_manifest','envelope.json')]:
        path = tmp_path/name; path.write_text('synthetic identity only')
        files[key] = record(tmp_path,path)
    (tmp_path/'outputs').mkdir()
    data = dict(schema=config.SCHEMA, artifact_root='.', study_area=record(tmp_path,area),
                analysis_extent=list(config.ROI), context_buffer_m=32,
                inputs=files, output_parent='outputs', run_id='authored-01')
    path = tmp_path/'run.json'; save(path,data)
    return path,data


def test_exact_defaults_confined_bindings_and_shared_arguments(settings):
    path,data = settings
    cfg = config.RunConfig.load(path)
    assert cfg.extent.domain == config.DOMAIN
    assert cfg.arguments('voxel').config.record() == cfg.arguments('solar').config.record()
    assert cfg.arguments('voxel').run_dir == cfg.arguments('solar').base_run
    assert not cfg.run_root.exists()  # Loading has no output side effect.
    cfg.capture(Watch(cfg.root))


@pytest.mark.parametrize('case', ['unknown','unknown_input','unknown_binding','missing','duplicate','nan','infinity',
    'overflow','huge_integer','bool_coordinate','inverted','empty','zero_buffer','negative_buffer','outside_study','escape_input',
    'absolute_input','escape_output','bad_sha','changed_input','reserved_id','traversal_id','foreign_crs'])
def test_invalid_config_is_rejected_before_output(settings, case):
    path,original = settings; data = copy.deepcopy(original)
    if case=='unknown': data['resolution']=2
    if case=='unknown_input': data['inputs']['extra']=data['inputs']['terrain']
    if case=='unknown_binding': data['study_area']['size_bytes']=1
    if case=='missing': del data['inputs']['terrain']
    if case=='nan': data['analysis_extent'][0]=float('nan')
    if case=='infinity': data['context_buffer_m']=float('inf')
    if case=='overflow': data['analysis_extent'][0]=float('-inf')
    if case=='huge_integer': data['analysis_extent'][0]=10**400
    if case=='bool_coordinate': data['analysis_extent'][0]=True
    if case=='inverted': data['analysis_extent'][2]=data['analysis_extent'][0]-1
    if case=='empty': data['analysis_extent'][2]=data['analysis_extent'][0]
    if case=='zero_buffer': data['context_buffer_m']=0
    if case=='negative_buffer': data['context_buffer_m']=-1
    if case=='outside_study': data['analysis_extent']=[0,0,20,20]
    if case=='escape_input': data['inputs']['terrain']['path']='../outside'
    if case=='absolute_input': data['inputs']['terrain']['path']=str((path.parent/'terrain.tif').resolve())
    if case=='escape_output': data['output_parent']='../outputs'
    if case=='bad_sha': data['inputs']['terrain']['sha256']='0'*64
    if case=='changed_input': (path.parent/'terrain.tif').write_bytes(b'changed')
    if case=='reserved_id': data['run_id']='CON'
    if case=='traversal_id': data['run_id']='../old'
    if case=='foreign_crs':
        area=path.parent/'area.yaml';area.write_text(area.read_text().replace('6677','3857'))
        data['study_area']=record(path.parent,area)
    save(path,data)
    if case=='duplicate': path.write_text(path.read_text().replace('"schema":', '"schema":"duplicate", "schema":',1))
    with pytest.raises((GeometryValidationError,ValueError,KeyError)):
        config.RunConfig.load(path)
    assert not (path.parent/'outputs/authored-01').exists()


def test_nested_duplicate_and_between_stage_changes_fail(settings):
    path,data=settings
    path.write_text(path.read_text().replace('"sha256":', '"sha256":"duplicate", "sha256":',1))
    with pytest.raises(GeometryValidationError): config.RunConfig.load(path)
    save(path,data);cfg=config.RunConfig.load(path)
    data['analysis_extent'][0]-=1;save(path,data)
    with pytest.raises(GeometryValidationError): cfg.capture(Watch(cfg.root))


@pytest.mark.parametrize('name',['study_area','building_manifest','terrain','terrain_manifest','envelope_manifest'])
def test_each_expected_input_identity_is_mandatory(settings,name):
    path,data=settings
    binding=data['study_area'] if name=='study_area' else data['inputs'][name]
    binding['sha256']='0'*64;save(path,data)
    with pytest.raises(GeometryValidationError,match='SHA-256'):config.RunConfig.load(path)


def test_cli_config_cannot_be_mixed_with_legacy_paths(settings):
    path,_=settings;parser=argparse.ArgumentParser()
    with pytest.raises(GeometryValidationError,match='mixed'):
        config.configured_arguments(parser,argparse.Namespace(config=path,run_dir=Path('override')),'voxel')
    args=config.configured_arguments(parser,argparse.Namespace(config=path,run_dir=None),'solar')
    assert args.run_dir.name=='solar'
    with pytest.raises(SystemExit):
        config.configured_arguments(parser,argparse.Namespace(config=None,run_dir=None),'voxel')


def test_receipt_requires_complete_exact_config_and_bound_report(settings):
    path,data=settings;cfg=config.RunConfig.load(path).prepare('voxel')
    (cfg.run_root/'voxel').mkdir()
    report=dict(status='FAILED',input_immutability='PASS',run_config=cfg.record())
    save(cfg.run_root/'voxel/report.json',report)
    with pytest.raises(GeometryValidationError): cfg.seal_voxel()
    report['status']='COMPLETED';save(cfg.run_root/'voxel/report.json',report);cfg.seal_voxel()
    watch=Watch(cfg.root);expected=cfg.model_sha(watch)
    assert expected==sha(cfg.run_root/'voxel/report.json')
    with pytest.raises(FileExistsError):cfg.prepare('voxel')
    save(cfg.run_root/'voxel/report.json',dict(report, status='FAILED'))
    with pytest.raises(GeometryValidationError):
        watch.capture('report',(cfg.run_root/'voxel/report.json').relative_to(cfg.root).as_posix(),expected)
    data['context_buffer_m']=31;save(path,data);other=config.RunConfig.load(path)
    with pytest.raises(GeometryValidationError): other.model_sha(Watch(other.root))


@pytest.mark.parametrize('shift,width,height',[(0,16,8),(16,16,8),(4,20,12)])
def test_translated_non_square_voxel_solar_and_gis(tmp_path, shift, width, height):
    extent=config.Extent((-23320+shift,-40760,-23320+shift+width,-40760+height),12.)
    dem=tmp_path/'dem.tif';bounds=extent.domain
    terrain(dem,np.full((int(bounds[3]-bounds[1]),int(bounds[2]-bounds[0])),10.),bounds)
    features={'authored':(box_tree(-23315+shift,-40756,4,top=24.),None,None)}
    a,meta,frame,cells=voxel.execute_model(features,dem,extent=extent)
    assert a['building_ids'].shape[0] != a['building_ids'].shape[1]
    assert a['roi_mask'].sum()==width*height
    assert meta['grid']['projected_evaluation_ROI_bounds']==list(extent.analysis)
    assert meta['qa']['building_id_bijection']=='PASS'
    sampled=dict(top=np.full(a['terrain_H'].shape,17.),bottom=np.full(a['terrain_H'].shape,12.),
                 candidate=np.ones(a['terrain_H'].shape,bool),valid=np.ones(a['terrain_H'].shape,bool))
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE
    current,absent,tree,high,low,qa=solar.integrate_canopy(a['voxels'],a,segments_grid(cells,a['building_ids'].shape),
                                                      sampled,meta['grid']['D0_effective_H_m'],numba=NUMBA_AVAILABLE)
    a['building_segments']=segments_grid(cells,a['building_ids'].shape)
    maps,stats=solar.solar_pair(current,absent,a,meta['grid'],high,low)
    assert np.array_equal(absent,a['voxels']) and not np.any(tree & (a['voxels']!=0))
    assert stats['canopy_effect_detected'] and stats['technical_calculation']=='COMPLETED'
    assert stats['halo']['context_buffer_m']==12 and 'UNVERIFIED' in stats['halo']['general_external_occluder_sufficiency']
    output=tmp_path/'solar';output.mkdir()
    solar.export(output,dict(current_voxels=current,no_canopy_voxels=absent,tree_mask=tree,roi_mask=a['roi_mask'],**maps),meta['grid'])
    with rasterio.open(output/'solar_difference.tif') as ds:
        assert ds.shape==a['building_ids'].shape and ds.crs.to_epsg()==4326
        assert np.array_equal(ds.read(1),maps['solar_difference'][::-1,:],equal_nan=True)
        lon,lat=ds.xy(3,7)
        assert lon==pytest.approx(a['centre_lon'][-4,7],abs=1e-12)
        assert lat==pytest.approx(a['centre_lat'][-4,7],abs=1e-12)
        assert math.isnan(ds.nodata)


def segments_grid(cells,shape):
    result=np.empty(shape,object)
    for ij in np.ndindex(shape):result[ij]=[]
    for cell in cells:result[cell['i'],cell['j']]=cell['segments']
    return result


def test_zero_effect_is_not_silently_reclassified_as_poc_success():
    from test_real_komae_solar import authored
    base,a,segments,sampled=authored()
    grid=dict(axis0_true_azimuth_deg=0.,rectangle_vertices_lonlat=[[139.,35.],[139.,35.001],[139.001,35.001],[139.001,35.]],D0_effective_H_m=10.)
    a['building_segments']=segments
    with pytest.raises(GeometryValidationError,match='no canopy reduction'):
        solar.solar_pair(base,base.copy(),a,grid,np.zeros(base.shape[:2]),np.zeros(base.shape[:2]))


@pytest.fixture
def complete_scene(tmp_path,native,monkeypatch,request):
    """Actual authored source-H/DEM/evidence chain; engine and validators are real."""
    pts=[p for f in source_faces()['synthetic_tokyo'] for r in f for p in r]
    x,y=Transformer.from_crs(6668,6677,always_xy=True).transform(*pts[0][:2]);x,y=math.floor(x),math.floor(y)
    area=tmp_path/'area.yaml'
    area.write_text(f'study_area:\n  id: authored-tokyo\ncrs:\n  epsg: 6677\nextent:\n  xmin: {x-64}\n  ymin: {y-64}\n  xmax: {x+64}\n  ymax: {y+64}\n')
    standard=standard_buildings(tmp_path,area)
    raw=tmp_path/'raw.tif';terrain(raw,np.full((256,256),10.),(x-64,y-64,x+64,y+64))
    native_dem=tmp_path/'native-terrain.json';dem=tmp_path/'terrain.tif'
    accept_native_terrain(raw,native_dem,provider='SYNTHETIC ONLY',source_dataset='authored',
        vertical_reference_status='source-declared',vertical_reference='T.P. (Tokyo Peil / Tokyo Bay mean sea level)',
        vertical_reference_source='synthetic test statement')
    standardize_native_terrain(native_dem,dem,study_area_config=area)
    dem_meta=json.loads(dem.with_suffix('.tif.manifest.json').read_text())
    chm=tmp_path/'chm.tif';terrain(chm,np.full((128,128),getattr(request,'param',7.)),(x-64,y-64,x+64,y+64))
    acq=tmp_path/'acquisition.json';snapshot=tmp_path/'statement.txt';snapshot.write_text('SYNTHETIC height above local ground in metres')
    review=tmp_path/'review.json';save(review,{'scope':'SYNTHETIC fixture only'})
    evidence=tmp_path/'evidence.json';acceptance=tmp_path/'synthetic-acceptance.md'
    acceptance.write_text(f'SYNTHETIC ONLY\n| Status | **ACCEPTED** |\n| Standard output SHA-256 | `{sha(dem)}` |\n')
    save(acq,dict(schema='ouem-chmv2-acquisition-poc/v0.1',status='COMPLETED',output=dict(sha256=sha(chm)),
        tiles=[dict(path=str(chm),sha256=sha(chm),bytes=chm.stat().st_size,quadkey='authored',url='synthetic://chm')]))
    save(evidence,dict(schema='ouem-height-envelope-evidence/v0.1',chm_sha256=sha(chm),acquisition_record_sha256=sha(acq),
        height_semantics='height_above_ground_m',height_reference='local_ground',dem_quantity='absolute_elevation_m',
        evidence=dict(source='SYNTHETIC ONLY',citation='synthetic://statement',statement=snapshot.read_text(),
                      snapshot_path=snapshot.name,snapshot_sha256=sha(snapshot)),
        compatibility_review=dict(reviewer='SYNTHETIC TEST',reviewed_at='test-only',basis='authored local ground',
            vertical_combination='relative_height_plus_dem_no_offset',dem_vertical_reference=dem_meta['vertical_reference']['name'],
            dem_sha256=sha(dem),approval_record_path=review.name,approval_record_sha256=sha(review))))
    generated=tmp_path/'envelope/generated'
    envelope.generate(chm,acq,evidence,dem,dem.with_suffix('.tif.manifest.json'),acceptance,area,generated)
    (tmp_path/'outputs').mkdir()
    data=dict(schema=config.SCHEMA,artifact_root='.',study_area=record(tmp_path,area),
        analysis_extent=[x-16,y-8,x,y],context_buffer_m=12.,
        inputs={name:record(tmp_path,p) for name,p in dict(building_manifest=Path(standard['manifest']),terrain=dem,
            terrain_manifest=dem.with_suffix('.tif.manifest.json'),envelope_manifest=generated/'height_envelope_manifest.json').items()},
        output_parent='outputs',run_id='left')
    # Capture exact tested code bytes within the synthetic artifact root, as real reports require.
    for mod in (voxel,solar,config):
        target=tmp_path/Path(mod.__file__).name;shutil.copyfile(mod.__file__,target)
        monkeypatch.setattr(mod,'__file__',str(target))
    path=tmp_path/'run.json';save(path,data)
    return path,data


def test_same_config_complete_source_chain_two_adjacent_rectangles(complete_scene):
    path,data=complete_scene
    for shift in (0,16):
        data['run_id']='left' if shift==0 else 'right'
        original=data['analysis_extent'];data['analysis_extent']=[original[0]+shift,original[1],original[2]+shift,original[3]]
        save(path,data);cfg=config.RunConfig.load(path)
        model=voxel.run(cfg.arguments('voxel'))
        assert model['status']=='COMPLETED' and model['consumer']['technical_validation']=='PASS'
        report=solar.run(cfg.arguments('solar'))
        cfg=config.RunConfig.load(cfg.run_root/'run-config.json')
        assert report['status']=='COMPLETED' and report['input_immutability']=='PASS'
        assert report['run_config']==model['run_config']==cfg.record()
        assert report['solar']['canopy_effect_detected']
        assert report['preflight']['source_model_report_sha256']==sha(cfg.run_root/'voxel/report.json')
        assert (cfg.run_root/'solar/solar_difference.tif').exists()
        assert report['preflight']['fresh_consumer']['technical_validation']=='PASS'
        data['analysis_extent']=original


@pytest.mark.parametrize('case',['domain','centres','occupancy'])
def test_independent_model_checks_reject_self_consistent_container_tampering(complete_scene,case):
    path,data=complete_scene
    cfg=config.RunConfig.load(path);voxel.run(cfg.arguments('voxel'))
    cfg=config.RunConfig.load(cfg.run_root/'run-config.json')
    model=cfg.run_root/'voxel';report=json.loads((model/'report.json').read_text())
    if case=='domain':
        file=model/'grid.json';grid=json.loads(file.read_text());grid['projected_domain_bounds'][0]-=1
        save(file,grid);report['model']['grid']=grid
    else:
        file=model/('centre_lon.npy' if case=='centres' else 'voxels.npy')
        array=np.load(file,allow_pickle=False)
        if case=='centres':array[0,0]+=.001
        else:array[0,0,0]=0
        np.save(file,array,allow_pickle=False)
    report['outputs'][file.name]=dict(sha256=sha(file),size_bytes=file.stat().st_size)
    save(model/'report.json',report)
    # Even a re-bound local receipt cannot disable the independent grid/voxel audit.
    (cfg.run_root/'voxel-receipt.json').unlink();cfg.seal_voxel()
    with pytest.raises(GeometryValidationError):solar.preflight(cfg.arguments('solar'),Watch(cfg.root))


def test_saved_config_survives_reusing_then_deleting_submission(complete_scene):
    path,data=complete_scene
    original=path.read_bytes()
    first=config.RunConfig.load(path)
    model=voxel.run(first.arguments('voxel'))
    saved_path=first.run_root/'run-config.json'
    saved_bytes=saved_path.read_bytes()
    assert (first.run_root/'submitted-config.json').read_bytes()==original
    assert model['run_config']['path']==saved_path.relative_to(first.root).as_posix()
    # Same editable file, different run and adjacent rectangle, same prepared inputs.
    data['run_id']='second'
    data['analysis_extent'][0]+=16;data['analysis_extent'][2]+=16
    save(path,data);second=config.RunConfig.load(path)
    voxel.run(second.arguments('voxel'));solar.run(second.arguments('solar'))
    path.unlink()
    saved=config.RunConfig.load(saved_path)
    assert saved_path.read_bytes()==saved_bytes
    assert saved.root==first.root and saved.extent==first.extent
    # Actual Solar preflight rechecks the prior report, every output/source hash,
    # Consumer, engine centres, DEM, ID/ground/occupancy and Envelope chain.
    watch=Watch(saved.root)
    _,_,_,_,checks=solar.preflight(saved.arguments('solar'),watch)
    watch.unchanged()
    assert checks['fresh_consumer']['technical_validation']=='PASS'
    report=solar.run(saved.arguments('solar'))
    assert report['status']=='COMPLETED' and report['input_immutability']=='PASS'
    assert report['run_config']==model['run_config']==saved.record()
    for result in (model,report):
        for identity in result['input_artifacts'].values():
            assert sha(saved.root/identity['path'])==identity['sha256']


@pytest.mark.parametrize('name',['run-config.json','submitted-config.json'])
def test_saved_configuration_tampering_is_rejected(complete_scene,name):
    path,_=complete_scene
    cfg=config.RunConfig.load(path);voxel.run(cfg.arguments('voxel'))
    saved=cfg.run_root/'run-config.json'
    target=cfg.run_root/name
    data=json.loads(target.read_text());data['analysis_extent'][0]-=1;save(target,data)
    with pytest.raises(GeometryValidationError):
        cfg=config.RunConfig.load(saved)
        solar.preflight(cfg.arguments('solar'),Watch(cfg.root))


@pytest.mark.parametrize('complete_scene',[40.],indirect=True)
def test_complete_configured_chain_exports_shared_vertical_domain(complete_scene):
    path,_=complete_scene;cfg=config.RunConfig.load(path)
    model=voxel.run(cfg.arguments('voxel'))
    base=np.load(cfg.run_root/'voxel/voxels.npy',allow_pickle=False)
    base_grid=json.loads((cfg.run_root/'voxel/grid.json').read_text())
    report=solar.run(cfg.arguments('solar'))
    grid=json.loads((cfg.run_root/'solar/grid.json').read_text())
    current=np.load(cfg.run_root/'solar/current_voxels.npy',allow_pickle=False)
    absent=np.load(cfg.run_root/'solar/no_canopy_voxels.npy',allow_pickle=False)
    assert grid['shape']==list(current.shape)==list(absent.shape)
    assert current.shape[2]>base.shape[2]
    assert grid==solar.shared_grid(base_grid,report['tree'])
    assert grid['D0_effective_H_m']==base_grid['D0_effective_H_m']
    assert np.array_equal(absent[:,:,:base.shape[2]],base)
    assert not absent[:,:,base.shape[2]:].any()
    assert np.array_equal(np.where(current==-2,0,current),absent)
    assert np.array_equal(np.load(cfg.run_root/'voxel/voxels.npy'),base)
    assert json.loads((cfg.run_root/'voxel/grid.json').read_text())==base_grid
    with rasterio.open(cfg.run_root/'solar/solar_difference.tif') as ds:
        assert list(ds.transform)[:6]==model['model']['GeoTIFF']['affine']
        assert ds.shape==base.shape[:2] and ds.crs.to_epsg()==4326 and np.isnan(ds.nodata)
    observer=np.load(cfg.run_root/'solar/observer_index_k.npy')
    ground=np.load(cfg.run_root/'voxel/ground_indices.npy')
    assert np.array_equal(observer,ground+1)
    assert report['solar']['invariants']['non_TREE_voxels_equal']=='PASS'
