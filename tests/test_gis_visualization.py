"""Authored saved-output contracts and one real synthetic producer chain; no city run."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer
import pytest
import rasterio
from affine import Affine

from ouem import gis_visualization as m
from ouem.native.building.source_h_geometry import GeometryValidationError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, allow_nan=False), encoding='utf-8')


def ref(path):
    return dict(sha256=sha(path), size_bytes=path.stat().st_size)


def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}


def authored_run(tmp_path, shape=(4,7), shift=0, integral=False):
    """Independent handoff/UV/affine fixture; no production exporter/style oracle."""
    root = tmp_path/'runs'/'authored'
    (root/'voxel').mkdir(parents=True)
    (root/'solar').mkdir()
    x0,y0 = -23320+shift,-40760
    lon,lat = Transformer.from_crs(6677,4326,always_xy=True).transform(x0,y0)
    origin = np.array([lon,lat]); u=np.array([1e-8,9e-6]); v=np.array([1.1e-5,-1e-8])
    i,j=np.indices(shape)
    centres=[origin[axis]+(i+.5)*u[axis]+(j+.5)*v[axis] for axis in (0,1)]
    x,y=Transformer.from_crs(4326,6677,always_xy=True).transform(*centres)
    bounds=[float(x.min())-.1,float(y.min())-.1,float(x.max())+.1,float(y.max())+.1]
    if integral:bounds=[math.floor(bounds[0]),math.floor(bounds[1]),math.ceil(bounds[2]),math.ceil(bounds[3])]
    config=dict(schema='ouem-e2e-run/v0.1',artifact_root='../..',study_area={'path':'missing-area.yaml','sha256':'a'*64},
        analysis_extent=bounds,context_buffer_m=2.,
        inputs={k:dict(path='missing-'+k,sha256='b'*64) for k in
                ('building_manifest','terrain','terrain_manifest','envelope_manifest')},
        output_parent='runs',run_id='authored')
    # Upstream files intentionally absent: presentation uses frozen results, not Raw/engine.
    save(root/'run-config.json',config)
    save(root/'submitted-config.json',dict(config,artifact_root='.'))
    domain=[float(bounds[0])-2,float(bounds[1])-2,float(bounds[2])+2,float(bounds[3])+2]
    grid=dict(shape=[*shape,9],layout='uv_m/SOUTH_UP',rectangle_crs='EPSG:4326',projected_reference_crs='EPSG:6677',
        nominal_voxel_size_m=1.,origin_lonlat=origin.tolist(),u_step_lonlat=u.tolist(),v_step_lonlat=v.tolist(),
        projected_evaluation_ROI_bounds=bounds,projected_domain_bounds=domain,halo_m=2.,D0_effective_H_m=10.)
    save(root/'voxel/grid.json',grid);save(root/'solar/grid.json',grid)
    for name,a in dict(centre_lon=centres[0],centre_lat=centres[1],roi_mask=np.ones(shape,bool),
                       building_ids=np.where((i==0)&(j==0),1,0)).items():
        np.save(root/'voxel'/f'{name}.npy',a,allow_pickle=False)
    valid=~((i==0)&(j==0))
    current=np.where(valid,0.,np.nan);absent=current.copy();absent[0,2:4]=20.
    building=np.where(valid,0.,np.nan);building[0,1]=10.;building[0,3]=10.
    categories=np.zeros(shape,'uint8');categories[0,:4]=[4,1,2,3]
    maps=dict(solar_current=current,solar_no_canopy=absent,solar_difference=absent-current,
        shadow_categories=categories,observer_valid=valid,canopy_candidate=(j%2==0),roi_mask=np.ones(shape,bool))
    start=origin+shape[0]*u
    affine=Affine(v[0],-u[0],start[0],v[1],-u[1],start[1])
    for name,a in maps.items():
        np.save(root/'solar'/f'{name}.npy',a,allow_pickle=False)
        raster=a[::-1,:].astype('uint8') if a.dtype==bool else a[::-1,:]
        with rasterio.open(root/'solar'/f'{name}.tif','w',driver='GTiff',count=1,crs=4326,
                           width=shape[1],height=shape[0],transform=affine,dtype=raster.dtype,
                           nodata=np.nan if raster.dtype.kind=='f' else None) as ds:ds.write(raster,1)
    np.save(root/'solar/building_solar_reduction.npy',building,allow_pickle=False)
    stats=dict(sun={'flat_horizontal_W_m2':800*math.sin(math.radians(35))},invariants={'tolerance_W_m2':1e-9})
    save(root/'solar/statistics.json',stats)
    record=dict(schema=config['schema'],path='runs/authored/run-config.json',sha256=sha(root/'run-config.json'),
        artifact_root=str(tmp_path),run_root=str(root),settings=config,computation_reference_bounds=domain)
    watches={key:dict(path='runs/authored/'+name,**ref(root/name)) for key,name in
             [('run_config','run-config.json'),('submitted_config','submitted-config.json')]}
    for stage in ('voxel','solar'):
        report=dict(status='COMPLETED',input_immutability='PASS',run_config=record,input_artifacts=watches.copy(),
                    outputs={p.name:ref(p) for p in (root/stage).iterdir()})
        if stage=='voxel':report.update(consumer={'technical_validation':'PASS'},model={'grid':grid})
        else:
            report.update(solar=stats,preflight={'source_model_report_sha256':sha(root/'voxel/report.json'),
                'fresh_consumer':{'technical_validation':'PASS'}})
            report['input_artifacts']['PR98_report']=dict(path='runs/authored/voxel/report.json',**ref(root/'voxel/report.json'))
        save(root/stage/'report.json',report)
    save(root/'voxel-receipt.json',dict(schema='ouem-e2e-voxel-receipt/v0.1',run_config_sha256=record['sha256'],
                                      report_sha256=sha(root/'voxel/report.json')))
    return root


@pytest.mark.parametrize('shape,shift,integral',[((4,7),0,False),((6,9),-64,False),((4,7),32,True)])
def test_generate_non_square_translated_preserves_inputs_and_styles(tmp_path,shape,shift,integral):
    root=authored_run(tmp_path,shape,shift,integral);before=inventory(root)
    out=tmp_path/'visual';manifest=m.generate(root,out)
    assert inventory(root)==before
    assert len(list(out.iterdir()))==8 and len(manifest['layers'])==7
    assert manifest==json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['spatial']['shape_uv']==list(shape) and manifest['spatial']['crs']=='EPSG:4326'
    assert manifest['validation']['qgis_load_display']=='NOT_VERIFIED'
    for source in manifest['sources'].values():
        assert sha(out/source['path'])==source['sha256']
    for layer in manifest['layers']:
        settings=layer['style'];qml=layer['qml'];assert sha(out/qml['path'])==qml['sha256']
        xml=ET.parse(out/qml['path']).getroot();renderer=xml.find('./pipe/rasterrenderer')
        assert renderer.get('type')==settings['renderer'] and renderer.get('band')=='1'
        tag='./rastershader/colorrampshader/item' if settings['interpolation']=='linear' else './colorPalette/paletteEntry'
        actual=[dict(value=float(e.get('value')),color=e.get('color'),alpha=int(e.get('alpha')),label=e.get('label'))
                for e in renderer.findall(tag)]
        assert actual==settings['stops']
        assert xml.find('./pipe/provider/resampling').get('enabled')=='false'
        if layer['name'].startswith('solar_'):
            assert layer['unit']=='W/m²' and float(renderer.get('classificationMax'))==settings['maximum']
            assert [s['value'] for s in actual]==[settings['maximum']*i/4 for i in range(5)]
            assert all(s['alpha']==255 for s in actual)  # Valid zero is opaque, never NoData.
            assert renderer.find('./rastershader/colorrampshader/rampLegendSettings').get('suffix')==' W/m²'
        if layer['name']=='shadow_categories':assert [s['value'] for s in actual]==list(range(5))
    layers={l['name']:l for l in manifest['layers']}
    assert layers['solar_current']['style']==layers['solar_no_canopy']['style']
    assert layers['solar_difference']['scenario']=='No-Canopy − Current'
    assert layers['observer_valid']['style']['stops'][0]['alpha']==255
    assert layers['observer_valid']['style']['stops'][1]['alpha']==0
    with rasterio.open(root/'solar/solar_current.tif') as ds:
        assert np.isnan(ds.nodata) and (ds.read_masks(1)==0).sum()==1
        assert np.count_nonzero(ds.read(1)==0)==shape[0]*shape[1]-1


@pytest.mark.parametrize('target',['run-config.json','submitted-config.json','voxel-receipt.json',
    'voxel/report.json','solar/report.json','solar/grid.json','voxel/grid.json','solar/solar_current.tif',
    'solar/solar_current.npy','voxel/centre_lon.npy','solar/statistics.json'])
def test_tampered_bindings_and_consumed_files_fail_before_output(tmp_path,target):
    root=authored_run(tmp_path);path=root/target
    if target.endswith('.json'):
        data=json.loads(path.read_text())
        if 'config' in target:data['analysis_extent'][0]-=1
        elif 'receipt' in target:data['run_config_sha256']='0'*64
        elif target=='solar/report.json':data['preflight']['source_model_report_sha256']='0'*64
        else:data['tampered']=True
        save(path,data)
    else:path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises((GeometryValidationError,KeyError,ValueError)):
        m.generate(root,tmp_path/'visual')
    assert not (tmp_path/'visual').exists()


def rebind_solar(root,name):
    path=root/'solar/report.json';data=json.loads(path.read_text())
    data['outputs'][name]=ref(root/'solar'/name);save(path,data)


@pytest.mark.parametrize('fault',['affine','crs','nodata','values','mask','sign','category','shared_grid'])
def test_rehashed_but_inconsistent_outputs_are_rejected(tmp_path,fault):
    root=authored_run(tmp_path)
    name='solar_current.tif'
    if fault in ('affine','crs','nodata','values'):
        with rasterio.open(root/'solar'/name,'r+') as ds:
            if fault=='affine':
                a,b,c,d,e,f=tuple(ds.transform)[:6];ds.transform=Affine(a,b,c+1e-5,d,e,f)
            if fault=='crs':ds.crs='EPSG:6677'
            if fault=='nodata':ds.nodata=0.
            if fault=='values':a=ds.read(1);a[0,0]=1;ds.write(a,1)
        rebind_solar(root,name)
    elif fault=='shared_grid':
        name='grid.json';data=json.loads((root/'solar'/name).read_text());data['origin_lonlat'][0]+=.01
        save(root/'solar'/name,data);rebind_solar(root,name)
    else:
        key={'mask':'observer_valid','sign':'solar_difference','category':'shadow_categories'}[fault]
        path=root/'solar'/f'{key}.npy';a=np.load(path)
        a[0,1]=False if fault=='mask' else (-10 if fault=='sign' else 7)
        np.save(path,a,allow_pickle=False);rebind_solar(root,path.name)
        with rasterio.open(root/'solar'/f'{key}.tif','r+') as ds:
            ds.write(a[::-1,:].astype(ds.dtypes[0]),1)
        rebind_solar(root,f'{key}.tif')
    with pytest.raises(GeometryValidationError):m.generate(root,tmp_path/'visual')
    assert not (tmp_path/'visual').exists()


@pytest.mark.parametrize('location',['run','child','ancestor','existing','missing_parent'])
def test_no_overwrite_or_source_overlap(tmp_path,location):
    root=authored_run(tmp_path);before=inventory(root)
    targets={'run':root,'child':root/'visual','ancestor':root.parent,'existing':tmp_path/'exists',
             'missing_parent':tmp_path/'absent'/'visual'}
    (tmp_path/'exists').mkdir()
    with pytest.raises(GeometryValidationError):m.generate(root,targets[location])
    assert inventory(root)==before


def test_source_change_during_export_leaves_no_success_manifest(tmp_path,monkeypatch):
    root=authored_run(tmp_path);original=m.qml_bytes
    def changed(*args):
        path=root/'solar/solar_current.tif'
        path.write_bytes(path.read_bytes()+b'changed')
        return original(*args)
    monkeypatch.setattr(m,'qml_bytes',changed)
    with pytest.raises(GeometryValidationError,match='input changed'):
        m.generate(root,tmp_path/'visual')
    assert not (tmp_path/'visual/manifest.json').exists()


def test_cli_fresh_process(tmp_path):
    root=authored_run(tmp_path)
    result=subprocess.run([sys.executable,'-m','ouem.gis_visualization','--run-root',str(root),'--output',str(tmp_path/'visual')],
                          capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'NOT_VERIFIED' in result.stdout


def test_import_does_not_load_engine_preparation_runners_or_qgis():
    code=('import sys; import ouem.gis_visualization; '
          'assert not any(n.split(".")[0] in ("voxcity","qgis") for n in sys.modules); '
          'assert not any(n in sys.modules for n in ("ouem.real_komae_voxel","ouem.real_komae_solar",'
          '"ouem.real_komae_source_h","ouem.e2e_config"))')
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


# Reuse the actual producer fixture once, separate from independent saved-output fault tests.
from test_e2e_config import complete_scene, native, plan


def test_actual_synthetic_e2e_handoff(complete_scene,tmp_path):
    from ouem.e2e_config import RunConfig
    from ouem import real_komae_voxel as voxel, real_komae_solar as solar
    cfg=RunConfig.load(complete_scene[0])
    voxel.run(cfg.arguments('voxel'));solar.run(cfg.arguments('solar'))
    before=inventory(cfg.run_root)
    manifest=m.generate(cfg.run_root,tmp_path/'visual')
    assert manifest['run_id']==cfg.document['run_id'] and inventory(cfg.run_root)==before
