"""Synthetic rasters/geometries and mocked external stages; no local real data."""
import base64
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from ouem import komae_integration as runner
from ouem.native.terrain import accept_native_terrain
from ouem.standardize.terrain import standardize_native_terrain

REAL_ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    Path(path).write_text(json.dumps(value), encoding="utf-8")


def frame(height=20.0):
    return gpd.GeoDataFrame({"ouem_id": ["oub-synthetic"], "source_id": ["synthetic"],
        "source_dataset": ["PLATEAU CityGML"], "source_lod": [None], "measured_height": [10.0]},
        geometry=[Polygon([(-23585,-40785,height),(-23580,-40785,height),
                           (-23580,-40780,height),(-23585,-40780,height)])], crs=6677)


def synthetic_a3(report_path, arrays_path, count=1):
    write_json(report_path, {"input_buildings": count,
        "building_id_grid_produced": True, "building_voxels_produced": True,
        "no_unexplained_loss": True, "vertical_geometry_consistent": True,
        "ids_present": list(range(1,count+1)), "ids_expected": list(range(1,count+1)),
        "building_specific_absolute_invariant_max_error_m": 0.0,
        "max_absolute_roof_error_m": 1.0, "vertical_tolerance_m": 2.0,
        "adapter_serialization_deterministic": True, "grid_and_voxel_deterministic": True})
    arrays = {name: {"dtype": '<f8' if name != 'segments' else '|O',
                     "shape": [2,2,3] if name=='voxels' else [2,2],
                     "encoding": 'row-major cell segment JSON' if name=='segments' else 'C-order bytes',
                     "sha256": 'a'*64} for name in ('dem','heights','segments','ids','voxels')}
    write_json(arrays_path, {"schema":"ouem-voxcity-array-evidence/v0.1", "first":arrays,"second":arrays})


@pytest.fixture
def setup(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(runner, "REPOSITORY", repo)
    monkeypatch.setattr(runner, "validate_ouem_runtime", lambda path: None)
    monkeypatch.setattr(runner, "environment", lambda: {"voxcity": {"verified": True}, "python": "synthetic"})
    (repo / 'scripts/work').mkdir(parents=True)
    (repo / runner.A3_SCRIPT).write_text((REAL_ROOT / runner.A3_SCRIPT).read_text())
    (repo / 'pyproject.toml').write_text('[project]\nname="synthetic"\n')
    inputs = tmp_path / "accepted"
    inputs.mkdir()
    raw = inputs / "raw.tif"
    with rasterio.open(raw, 'w', driver='GTiff', width=40, height=40, count=1,
                       dtype='float32', crs=6677, transform=from_origin(-23600,-40760,1,1), nodata=-9999) as dst:
        dst.write(np.full((40,40),10,dtype='float32'),1)
    native_t = inputs / 'native.json'
    accept_native_terrain(raw, native_t, provider='synthetic', source_dataset='synthetic',
                          vertical_reference_status='source-declared', vertical_reference='T.P.',
                          vertical_reference_source='synthetic fixture')
    native_b = inputs / 'native.gpkg'
    native_b.write_bytes(b'synthetic external GIS input')
    write_json(runner.adjacent(native_b), {"schema":"ouem-plateau-native-ingest/v0.1","errors":[]})
    reference = inputs / 'reference.gpkg'
    frame().to_file(reference, layer='building', driver='GPKG')
    write_json(runner.adjacent(reference), {"schema":"ouem-standard-building-manifest/v0.1",
                                         "z_reference":"absolute T.P. elevation in metres"})
    area = inputs / 'area.yaml'
    area.write_text('study_area:\n  id: synthetic\ncrs:\n  epsg: 6677\nextent:\n  xmin: -23600\n  ymin: -40800\n  xmax: -23560\n  ymax: -40760\n')
    gis = inputs / 'gis.json'
    write_json(gis, {"python":"synthetic-gis", "ogr2ogr":"ogr2ogr", "ogrinfo":"ogrinfo"})
    args = SimpleNamespace(native_building=str(native_b), native_terrain=str(native_t),
        reference_standard_building=str(reference), study_area=str(area), gis_runtime=str(gis),
        run_dir=str(repo/'data/work/integration/test-run'), meshsize=1.0,
        expected_buildings=1, expected_native_buildings=1)
    commands = []

    def execute(command, log, **kwargs):
        commands.append(command)
        Path(log).write_text('synthetic stage log\n')
        if command[0]=='synthetic-gis':
            return 0
        def option(name):
            return Path(command[command.index(name)+1])
        if command[2]=='ouem.standardize.building':
            out=option('--output')
            frame().to_file(out, layer='building', driver='GPKG')
            write_json(runner.adjacent(out), {'schema':'ouem-standard-building-manifest/v0.1',
                'z_reference':'absolute T.P. elevation in metres',
                'validation': {'input_features':1,'output_features':1,'z_geometries':1,
                  'output_crs':'EPSG:6677','required_metadata':True,'z_preserved':True,
                  'max_z_delta':0.0,'deterministic_ids':True}})
        elif command[2]=='ouem.standardize.terrain':
            standardize_native_terrain(command[3], option('--output'), study_area_config=option('--study-area'))
        else:
            building,terrain=map(Path,command[2:4])
            out=option('--adapter-output')
            geojson=json.loads(frame().to_crs(4326).to_json())
            geojson['crs']={'type':'name','properties':{'name':'urn:ogc:def:crs:EPSG::4326'}}
            from shapely import force_2d
            from shapely.geometry import mapping
            geojson['features'][0]['geometry']=mapping(force_2d(frame().to_crs(4326).geometry.iloc[0]))
            geojson['features'][0]['properties'].update(id=1,voxcity_id=1,height=10.0,min_height=0.0)
            write_json(out,geojson)
            manifest = {key: {} for key in ('runtime','vertical_compatibility','buildings')}
            manifest.update(schema='ouem-standard-to-voxcity-building-adapter/v0.1',adapter_version='0.1',
                voxcity={'version':'1.7.0','commit':runner.VOXCITY_COMMIT},
                aoi=[1,2,3,4],meshsize=1,crs={'source':'EPSG:6677','target':'EPSG:4326'},
                height_derivation='synthetic',ground_derivation='synthetic',min_height_derivation='synthetic',
                id_derivation='synthetic',warnings=[],
                inputs={key:{'path':str(p),'sha256':runner.sha256_file(p)} for key,p in
                        (('standard_building',building),('standard_terrain',terrain))},
                output={'sha256':runner.sha256_file(out)},
                voxcity_grid={'rectangle_vertices_lonlat':runner.coverage(building,terrain)['rectangle_vertices_lonlat'],
                              'building_rasterization':'precise geometry intersection'})
            write_json(runner.adjacent(out),manifest)
            synthetic_a3(option('--report'),option('--array-evidence'))
        return 0
    monkeypatch.setattr(runner, 'execute', execute)
    return SimpleNamespace(args=args, repo=repo, inputs=inputs, raw=raw, execute=execute, commands=commands,
                           report=Path(args.run_dir)/'integration-report.json')


def test_two_complete_repeats_link_evidence_without_changing_inputs(setup):
    before={p:runner.sha256_file(p) for p in setup.inputs.iterdir()}
    assert runner.run(setup.args)==0
    report=runner.read_json(setup.report)
    assert report['status']=='AUTOMATED_PASS'
    assert report['quality']==report['reproducibility']=='PASS'
    assert report['acceptance']=='PENDING_LOCAL_REVIEW'
    assert len(report['repeats'])==2 and len(report['stages'])==7
    assert all(report['comparisons'].values())
    assert all(report['input_integrity'].values())
    assert before=={p:runner.sha256_file(p) for p in setup.inputs.iterdir()}
    assert 'repeat-1/arrays.json' in report['artifacts']
    with pytest.raises(runner.Blocked, match='already exists'):
        runner.run(setup.args)


@pytest.mark.parametrize('kind', ['symlink','hardlink','junction'])
def test_linked_output_cannot_be_used(setup, kind):
    root=runner.safe_run_path(setup.args.run_dir)
    identity=(root.stat().st_dev,root.stat().st_ino)
    target=setup.inputs/'native.gpkg'
    link=root/'injected.gpkg'
    if kind=='junction':
        if os.name!='nt':
            # Windows reparse-point branch is exercised using an lstat result.
            from unittest.mock import patch
            info=SimpleNamespace(st_mode=stat_mode_dir(),st_file_attributes=0x400)
            link.mkdir()
            with patch.object(Path,'lstat',return_value=info):
                with pytest.raises(runner.Blocked,match='linked output'):
                    runner.check_links(link)
            return
        pytest.skip('real Windows junction creation is outside Linux synthetic CI')
    if kind=='symlink':
        link.symlink_to(target)
    else:
        os.link(target,link)
    with pytest.raises(runner.Blocked):
        runner.guard_tree(root,identity)
    assert target.read_bytes()==b'synthetic external GIS input'


def stat_mode_dir():
    import stat
    return stat.S_IFDIR | 0o700


def test_symlink_ancestor_and_traversal_rejected(setup, tmp_path):
    (setup.repo/'data').symlink_to(setup.inputs, target_is_directory=True)
    with pytest.raises(runner.Blocked):
        runner.safe_run_path(setup.args.run_dir)
    with pytest.raises(runner.Blocked):
        runner.safe_run_path(setup.repo/'data/work/integration/../escape')
    assert not (setup.inputs/'work').exists()


@pytest.mark.parametrize('failure', ['exit','interrupt','hash','missing','quality'])
def test_failure_retains_logs_and_checkpoint(setup, monkeypatch, failure):
    def broken(command, log, **kwargs):
        rc=setup.execute(command,log,**kwargs)
        if '-m' in command and command[2]=='ouem.standardize.building':
            if failure=='exit': return 7
            if failure=='interrupt': raise KeyboardInterrupt()
            if failure=='hash': Path(setup.args.native_building).write_bytes(b'changed')
            if failure=='missing': Path(setup.args.study_area).unlink()
            if failure=='quality':
                p=runner.adjacent(command[command.index('--output')+1])
                m=runner.read_json(p); m['validation']['max_z_delta']=0.1; write_json(p,m)
        return rc
    monkeypatch.setattr(runner,'execute',broken)
    assert runner.run(setup.args)!=0
    report=runner.read_json(setup.report)
    assert report['status'] in ('FAILED','INTERRUPTED')
    assert report['reproducibility']=='NOT_COMPLETED'
    assert (setup.report.parent/'logs/repeat-1-a1.log').exists()
    assert len(report['stages'])==2
    if failure=='quality': assert report['quality']=='FAIL'
    if failure in ('hash','missing'): assert not all(report['input_integrity'].values())


def test_unverified_pin_blocks_all_stages(setup,monkeypatch):
    monkeypatch.setattr(runner,'environment',lambda:{'voxcity':{'verified':False,'reason':'no PEP610'}})
    assert runner.run(setup.args)==2
    report=runner.read_json(setup.report)
    assert report['status']=='BLOCKED' and report['stages']==[]


def test_quality_and_reproducibility_are_independent(setup,monkeypatch):
    def different(command,log,**kwargs):
        rc=setup.execute(command,log,**kwargs)
        if '--array-evidence' in command and 'repeat-2' in str(log):
            p=Path(command[command.index('--array-evidence')+1])
            e=runner.read_json(p)
            for attempt in ('first','second'): e[attempt]['voxels']['sha256']='b'*64
            write_json(p,e)
        return rc
    monkeypatch.setattr(runner,'execute',different)
    assert runner.run(setup.args)==1
    report=runner.read_json(setup.report)
    assert report['quality']=='PASS' and report['reproducibility']=='FAIL'


def test_reproducible_bad_roof_is_not_quality_pass(setup,monkeypatch):
    def bad(command,log,**kwargs):
        rc=setup.execute(command,log,**kwargs)
        if '--report' in command:
            p=Path(command[command.index('--report')+1]); e=runner.read_json(p)
            e['max_absolute_roof_error_m']=3.0; e['vertical_geometry_consistent']=False
            write_json(p,e)
            return 1
        return rc
    monkeypatch.setattr(runner,'execute',bad)
    assert runner.run(setup.args)==1
    report=runner.read_json(setup.report)
    assert report['quality']=='FAIL' and report['reproducibility']=='PASS'


def test_standard_manifest_mutation_by_a3_fails(setup,monkeypatch):
    def mutate(command,log,**kwargs):
        rc=setup.execute(command,log,**kwargs)
        if '--report' in command: runner.adjacent(command[2]).write_text('{}')
        return rc
    monkeypatch.setattr(runner,'execute',mutate)
    assert runner.run(setup.args)!=0
    assert 'changed a Standard' in runner.read_json(setup.report)['error']


@pytest.mark.parametrize('problem', ['nodata','outside'])
def test_coverage_stops_before_a3(setup,monkeypatch,problem):
    if problem=='nodata':
        with rasterio.open(setup.raw,'r+') as dst:
            values=dst.read(1); values[20,20]=-9999; dst.write(values,1)
        # Register the synthetic modified raster as the fixture input.
        accept_native_terrain(setup.raw,setup.args.native_terrain,provider='synthetic',source_dataset='synthetic',
            vertical_reference_status='source-declared',vertical_reference='T.P.',vertical_reference_source='fixture')
    else:
        f=frame(); f.geometry=f.geometry.translate(xoff=100)
        f.to_file(setup.args.reference_standard_building,layer='building',driver='GPKG')
        original=setup.execute
        def shift(command,log,**kwargs):
            rc=original(command,log,**kwargs)
            if '-m' in command and command[2]=='ouem.standardize.building':
                f.to_file(command[command.index('--output')+1],layer='building',driver='GPKG')
            return rc
        monkeypatch.setattr(runner,'execute',shift)
    assert runner.run(setup.args)!=0
    report=runner.read_json(setup.report)
    assert report['status']=='BLOCKED'
    assert not any(s['name'].endswith('-a3') for s in report['stages'])


def test_building_semantics_ignore_container_bytes_but_detect_xyz_and_attributes(tmp_path):
    first,second=tmp_path/'a.gpkg',tmp_path/'b.gpkg'
    frame().to_file(first,layer='building',driver='GPKG')
    frame().to_file(second,layer='building',driver='GPKG')
    import sqlite3
    with sqlite3.connect(second) as db:
        db.execute("UPDATE gpkg_contents SET last_change='2000-01-01T00:00:00.000Z'")
    assert runner.sha256_file(first)!=runner.sha256_file(second)
    assert runner.building_semantics(first)==runner.building_semantics(second)
    frame(21).to_file(second,layer='building',driver='GPKG')
    assert runner.building_semantics(first)!=runner.building_semantics(second)


@pytest.mark.parametrize('problem',['none','wrong','modified','shadowed','ok'])
def test_pin_provenance_requires_origin_and_installed_integrity(tmp_path,monkeypatch,problem):
    package=tmp_path/'voxcity'; package.mkdir()
    source=package/'__init__.py'; source.write_text('VERSION="1.7.0"')
    checksum=base64.urlsafe_b64encode(hashlib.sha256(source.read_bytes()).digest()).decode().rstrip('=')
    record=SimpleNamespace(hash=SimpleNamespace(mode='sha256',value=checksum))
    class Entry:
        hash=record.hash
        def __str__(self): return 'voxcity/__init__.py'
    origin={'url':'https://github.com/kunifujiwara/VoxCity.git','vcs_info':{'vcs':'git','commit_id':runner.VOXCITY_COMMIT}}
    if problem=='wrong': origin['vcs_info']['commit_id']='0'*40
    if problem=='modified': source.write_text('modified')
    dist=SimpleNamespace(version='1.7.0',files=[Entry()],locate_file=lambda p:tmp_path/p,
                         read_text=lambda name: None if problem=='none' else json.dumps(origin))
    monkeypatch.setattr(runner.metadata,'distribution',lambda name:dist)
    monkeypatch.setattr(runner.importlib.util,'find_spec',lambda name:SimpleNamespace(origin=str(source if problem!='shadowed' else tmp_path/'other.py')))
    assert runner.voxcity_provenance()['verified']==(problem=='ok')


def test_execute_preserves_log_on_nonzero_exit(tmp_path):
    import sys
    log=tmp_path/'failure.log'
    assert runner.execute([sys.executable,'-c','print("diagnostic"); raise SystemExit(7)'],log,cwd=tmp_path)==7
    assert 'diagnostic' in log.read_text()


def test_actual_synthetic_a2_and_a3_with_only_gis_mocked(setup,monkeypatch):
    # Only external GIS execution is mocked; A2 and pinned A3 run on synthetic data.
    def mixed(command,log,**kwargs):
        if '--array-evidence' in command:
            return ORIGINAL_EXECUTE(command,log,**kwargs)
        return setup.execute(command,log,**kwargs)
    monkeypatch.setattr(runner,'execute',mixed)
    assert runner.run(setup.args)==0, setup.report.read_text()
    report=runner.read_json(setup.report)
    assert report['quality']==report['reproducibility']=='PASS'
    assert report['repeats'][0]['comparison_evidence']['arrays']['voxels']['shape'][2]>0


ORIGINAL_EXECUTE = runner.execute


def test_execute_stops_child_group_on_interrupt(tmp_path,monkeypatch):
    calls=[]
    class Child:
        pid=12345
        def wait(self):
            calls.append('wait')
            if calls.count('wait')==1: raise KeyboardInterrupt()
            return -9
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**k:Child())
    if os.name=='nt':
        monkeypatch.setattr(runner.subprocess,'run',lambda command,**kwargs:calls.append(command))
    else:
        monkeypatch.setattr(runner.os,'killpg',lambda pid,sig:calls.append((pid,sig)))
    with pytest.raises(KeyboardInterrupt):
        ORIGINAL_EXECUTE(['fake'],tmp_path/'interrupt.log',cwd=tmp_path)
    assert calls.count('wait')==2 and len(calls)==3


def test_broken_manifest_lineage_fails_even_when_quality_numbers_pass(setup,monkeypatch):
    def bad(command,log,**kwargs):
        rc=setup.execute(command,log,**kwargs)
        if '--adapter-output' in command:
            p=runner.adjacent(command[command.index('--adapter-output')+1])
            m=runner.read_json(p);m['inputs']['standard_building']['sha256']='0'*64;write_json(p,m)
        return rc
    monkeypatch.setattr(runner,'execute',bad)
    assert runner.run(setup.args)==1
    assert runner.read_json(setup.report)['quality']=='FAIL'


def test_environment_change_stops_before_next_stage(setup, monkeypatch):
    state = {'voxcity': {'verified': True}}
    monkeypatch.setattr(runner, 'environment', lambda: json.loads(json.dumps(state)))
    def changed(command, log, **kwargs):
        rc = setup.execute(command, log, **kwargs)
        state['voxcity']['verified'] = False
        return rc
    monkeypatch.setattr(runner, 'execute', changed)
    assert runner.run(setup.args) != 0
    report = runner.read_json(setup.report)
    assert report['status'] == 'FAILED'
    assert not report['environment_integrity']['voxcity']
    assert len(report['stages']) == 1


def test_output_link_substitution_does_not_touch_accepted_data(setup, monkeypatch):
    before = Path(setup.args.native_building).read_bytes()
    def substituted(command, log, **kwargs):
        rc = setup.execute(command, log, **kwargs)
        if '-m' in command and command[2] == 'ouem.standardize.building':
            output = Path(command[command.index('--output') + 1])
            output.unlink()
            output.symlink_to(setup.args.native_building)
        return rc
    monkeypatch.setattr(runner, 'execute', substituted)
    assert runner.run(setup.args) != 0
    assert Path(setup.args.native_building).read_bytes() == before
    # An unsafe output tree must not be followed to finalize evidence.
    report = runner.read_json(setup.report)
    assert report['status'] == 'RUNNING'
    assert len(report['stages']) == 2


def test_symlink_input_retarget_is_detected(setup):
    original = Path(setup.args.native_building)
    link = setup.inputs / 'input-alias'
    other = setup.inputs / 'other'
    other.write_bytes(original.read_bytes())
    link.symlink_to(original)
    recorded = {'alias': runner.fingerprint(link)}
    link.unlink()
    link.symlink_to(other)
    assert runner.verify_inputs(recorded) == {'alias': False}


def test_building_semantics_detect_attribute_difference(tmp_path):
    first, second = tmp_path / 'a.gpkg', tmp_path / 'b.gpkg'
    frame().to_file(first, layer='building', driver='GPKG')
    changed = frame()
    changed['measured_height'] = 10.000000000000002
    changed.to_file(second, layer='building', driver='GPKG')
    assert runner.building_semantics(first) != runner.building_semantics(second)
