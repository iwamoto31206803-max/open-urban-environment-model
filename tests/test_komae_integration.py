"""Synthetic rasters/geometries and mocked external stages; no local real data."""
import base64
from contextlib import closing
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


def create_symlink_or_skip(link, target, *, target_is_directory=False):
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows symlink creation requires Developer Mode or privilege (WinError 1314)')
        raise


@pytest.fixture
def require_symlinks(tmp_path):
    # Probe before entering runner.run(), which catches ordinary OSError failures.
    probe = tmp_path / 'symlink-probe'
    create_symlink_or_skip(probe, tmp_path, target_is_directory=True)
    probe.unlink()


@pytest.mark.parametrize('winerror', [1314, 5])
def test_symlink_probe_skips_only_missing_windows_privilege(tmp_path, monkeypatch, request, winerror):
    error = OSError('simulated Windows symlink failure')
    error.winerror = winerror
    def denied(*args, **kwargs):
        raise error
    monkeypatch.setattr(Path, 'symlink_to', denied)
    expected = pytest.skip.Exception if winerror == 1314 else OSError
    with pytest.raises(expected):
        request.getfixturevalue('require_symlinks')


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
def setup(tmp_path, monkeypatch, request):
    suffix = getattr(request, 'param', '')
    repo = tmp_path / f"repo{suffix}"
    repo.mkdir()
    monkeypatch.setattr(runner, "REPOSITORY", repo)
    monkeypatch.setattr(runner, "validate_ouem_runtime", lambda path: None)
    monkeypatch.setattr(runner, "environment", lambda: {"voxcity": {"verified": True}, "python": "synthetic"})
    (repo / 'scripts/work').mkdir(parents=True)
    (repo / runner.A3_SCRIPT).write_bytes((REAL_ROOT / runner.A3_SCRIPT).read_bytes())
    (repo / 'pyproject.toml').write_text('[project]\nname="synthetic"\n', encoding='utf-8')
    inputs = tmp_path / f"accepted{suffix}"
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
    area.write_text('study_area:\n  id: synthetic\ncrs:\n  epsg: 6677\nextent:\n  xmin: -23600\n  ymin: -40800\n  xmax: -23560\n  ymax: -40760\n', encoding='utf-8')
    gis = inputs / 'gis.json'
    write_json(gis, {"python":"synthetic-gis", "ogr2ogr":"ogr2ogr", "ogrinfo":"ogrinfo"})
    args = SimpleNamespace(native_building=str(native_b), native_terrain=str(native_t),
        reference_standard_building=str(reference), study_area=str(area), gis_runtime=str(gis),
        run_dir=str(repo/'data/work/integration/test-run'), meshsize=1.0,
        expected_buildings=1, expected_native_buildings=1)
    commands = []

    def execute(command, log, **kwargs):
        commands.append(command)
        Path(log).write_text('synthetic stage log\n', encoding='utf-8')
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
    for repeat in (1, 2):
        key = f'repeat-{repeat}/arrays.json'
        evidence = setup.report.parent / key
        assert evidence.is_file()
        assert report['artifacts'][key]['sha256'] == runner.sha256_file(evidence)
    assert all('\\' not in key for key in report['artifacts'])
    with pytest.raises(runner.Blocked, match='already exists'):
        runner.run(setup.args)


@pytest.mark.parametrize('kind', ['symlink','hardlink','junction'])
def test_linked_output_cannot_be_used(setup, kind, request):
    if kind == 'symlink':
        request.getfixturevalue('require_symlinks')
    root=runner.safe_run_path(setup.args.run_dir)
    identity=(root.stat().st_dev,root.stat().st_ino)
    target=setup.inputs/'native.gpkg'
    link=root/'injected.gpkg'
    if kind=='junction':
        # Exercise the Windows reparse-point check on every platform, without privileges.
        from unittest.mock import patch
        info=SimpleNamespace(st_mode=stat_mode_dir(),st_file_attributes=0x400)
        link.mkdir()
        with patch.object(Path,'lstat',return_value=info):
            with pytest.raises(runner.Blocked,match='linked output'):
                runner.check_links(link)
        return
    if kind=='symlink':
        create_symlink_or_skip(link, target)
    else:
        os.link(target,link)
    with pytest.raises(runner.Blocked):
        runner.guard_tree(root,identity)
    assert target.read_bytes()==b'synthetic external GIS input'


def stat_mode_dir():
    import stat
    return stat.S_IFDIR | 0o700


def test_symlink_ancestor_rejected(setup, require_symlinks):
    create_symlink_or_skip(setup.repo/'data', setup.inputs, target_is_directory=True)
    with pytest.raises(runner.Blocked):
        runner.safe_run_path(setup.args.run_dir)
    assert not (setup.inputs/'work').exists()


def test_traversal_rejected(setup):
    with pytest.raises(runner.Blocked):
        runner.safe_run_path(setup.repo/'data/work/integration/../escape')
    assert not (setup.repo/'data').exists()


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


@pytest.mark.parametrize('winerror', [None, 5, 32, 33])
def test_reproducible_bad_roof_is_not_quality_pass(setup,monkeypatch,winerror):
    original_replace = Path.replace
    denied = []
    def transient_lock(path, target):
        if winerror is not None and Path(target) == setup.report and setup.report.exists() and not denied:
            denied.append(path)
            error = PermissionError('simulated Windows report replacement lock')
            error.winerror = winerror
            raise error
        return original_replace(path, target)
    monkeypatch.setattr(Path, 'replace', transient_lock)
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
    assert bool(denied) == (winerror is not None)
    assert not list(setup.report.parent.glob('*.tmp'))


def test_standard_manifest_mutation_by_a3_fails(setup,monkeypatch):
    def mutate(command,log,**kwargs):
        rc=setup.execute(command,log,**kwargs)
        if '--report' in command: runner.adjacent(command[2]).write_text('{}', encoding='utf-8')
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
    # The connection context commits/rolls back but does not close the file handle.
    with closing(sqlite3.connect(second)) as db:
        with db:
            db.execute("UPDATE gpkg_contents SET last_change='2000-01-01T00:00:00.000Z'")
    assert runner.sha256_file(first)!=runner.sha256_file(second)
    assert runner.building_semantics(first)==runner.building_semantics(second)
    frame(21).to_file(second,layer='building',driver='GPKG')
    assert runner.building_semantics(first)!=runner.building_semantics(second)


@pytest.mark.parametrize('problem',['none','wrong','modified','shadowed','ok'])
def test_pin_provenance_requires_origin_and_installed_integrity(tmp_path,monkeypatch,problem):
    package=tmp_path/'voxcity'; package.mkdir()
    source=package/'__init__.py'; source.write_text('VERSION="1.7.0"', encoding='utf-8')
    checksum=base64.urlsafe_b64encode(hashlib.sha256(source.read_bytes()).digest()).decode().rstrip('=')
    record=SimpleNamespace(hash=SimpleNamespace(mode='sha256',value=checksum))
    class Entry:
        hash=record.hash
        def __str__(self): return 'voxcity/__init__.py'
    origin={'url':'https://github.com/kunifujiwara/VoxCity.git','vcs_info':{'vcs':'git','commit_id':runner.VOXCITY_COMMIT}}
    if problem=='wrong': origin['vcs_info']['commit_id']='0'*40
    if problem=='modified': source.write_text('modified', encoding='utf-8')
    dist=SimpleNamespace(version='1.7.0',files=[Entry()],locate_file=lambda p:tmp_path/p,
                         read_text=lambda name: None if problem=='none' else json.dumps(origin))
    monkeypatch.setattr(runner.metadata,'distribution',lambda name:dist)
    monkeypatch.setattr(runner.importlib.util,'find_spec',lambda name:SimpleNamespace(origin=str(source if problem!='shadowed' else tmp_path/'other.py')))
    assert runner.voxcity_provenance()['verified']==(problem=='ok')


def test_execute_preserves_log_on_nonzero_exit(tmp_path):
    import sys
    log=tmp_path/'failure.log'
    assert runner.execute([sys.executable,'-c','print("diagnostic"); raise SystemExit(7)'],log,cwd=tmp_path)==7
    assert b'diagnostic' in log.read_bytes()


@pytest.mark.parametrize('setup', ['', ' space 狛江'], indirect=True, ids=['plain-paths', 'unicode-spaces'])
def test_actual_synthetic_a2_and_a3_with_only_gis_mocked(setup,monkeypatch):
    # Only external GIS execution is mocked; A2 and pinned A3 run on synthetic data.
    def mixed(command,log,**kwargs):
        if '--array-evidence' in command:
            return ORIGINAL_EXECUTE(command,log,**kwargs)
        return setup.execute(command,log,**kwargs)
    monkeypatch.setattr(runner,'execute',mixed)
    assert runner.run(setup.args)==0, setup.report.read_text(encoding='utf-8')
    report=runner.read_json(setup.report)
    assert report['quality']==report['reproducibility']=='PASS'
    assert report['repeats'][0]['comparison_evidence']['arrays']['voxels']['shape'][2]>0


ORIGINAL_EXECUTE = runner.execute


@pytest.mark.parametrize('platform', ['posix', 'nt'])
def test_execute_stops_child_group_on_interrupt(tmp_path,monkeypatch,platform):
    calls=[]
    class Child:
        pid=12345
        def wait(self):
            calls.append('wait')
            if calls.count('wait')==1: raise KeyboardInterrupt()
            return -9
    options = []
    def popen(*args, **kwargs):
        options.append(kwargs)
        return Child()
    monkeypatch.setattr(runner.subprocess,'Popen',popen)
    # Replace only the runner's os reference, not global os.name used by pathlib.
    monkeypatch.setattr(runner, 'os', SimpleNamespace(name=platform,
                        killpg=lambda pid,sig:calls.append((pid,sig))))
    monkeypatch.setattr(runner, 'signal', SimpleNamespace(SIGKILL=9))
    if platform=='nt':
        monkeypatch.setattr(runner.subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200, raising=False)
        monkeypatch.setattr(runner.subprocess,'run',lambda command,**kwargs:calls.append(command))
    with pytest.raises(KeyboardInterrupt):
        ORIGINAL_EXECUTE(['fake'],tmp_path/'interrupt.log',cwd=tmp_path)
    assert calls.count('wait')==2 and len(calls)==3
    if platform == 'nt':
        assert options[0]['creationflags'] == 0x200
        assert calls[1] == ['taskkill', '/PID', '12345', '/T', '/F']
    else:
        assert options[0]['start_new_session'] is True
        assert calls[1] == (12345, runner.signal.SIGKILL)


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


def prepare_substitution_link(link, target, kind):
    # Create the actual file link outside runner.run(), not just a directory probe.
    if kind == 'symlink':
        create_symlink_or_skip(link, target)
    else:
        # Hardlink failures are not evidence of missing symlink privilege.
        os.link(target, link)


@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
@pytest.mark.parametrize('winerror', [1314, 5])
def test_substitution_link_setup_classifies_errors(setup, monkeypatch, kind, winerror):
    target = Path(setup.args.native_building)
    before = target.read_bytes()
    link = setup.repo / 'prepared-link.gpkg'
    error = OSError('simulated link creation failure')
    error.winerror = winerror
    def denied(*args, **kwargs):
        raise error
    if kind == 'symlink':
        monkeypatch.setattr(Path, 'symlink_to', denied)
    else:
        monkeypatch.setattr(os, 'link', denied)
    expected = pytest.skip.Exception if kind == 'symlink' and winerror == 1314 else OSError
    with pytest.raises(expected):
        prepare_substitution_link(link, target, kind)
    assert target.read_bytes() == before
    assert not os.path.lexists(link)
    assert not setup.report.parent.exists()


@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_output_link_substitution_does_not_touch_accepted_data(setup, monkeypatch, kind):
    before = Path(setup.args.native_building).read_bytes()
    prepared = setup.repo / 'prepared-link.gpkg'
    prepare_substitution_link(prepared, setup.args.native_building, kind)
    injected = []
    def substituted(command, log, **kwargs):
        rc = setup.execute(command, log, **kwargs)
        if '-m' in command and command[2] == 'ouem.standardize.building':
            output = Path(command[command.index('--output') + 1])
            prepared.replace(output)
            injected.append(output)
        return rc
    monkeypatch.setattr(runner, 'execute', substituted)
    assert runner.run(setup.args) != 0
    assert len(injected) == 1
    with pytest.raises(runner.Blocked, match='linked output'):
        runner.check_links(injected[0])
    assert Path(setup.args.native_building).read_bytes() == before
    # An unsafe output tree must not be followed to finalize evidence.
    report = runner.read_json(setup.report)
    assert report['status'] == 'RUNNING'
    assert len(report['stages']) == 2


def test_link_creation_failure_retains_failed_report(setup, monkeypatch):
    before = Path(setup.args.native_building).read_bytes()
    def denied(command, log, **kwargs):
        rc = setup.execute(command, log, **kwargs)
        if '-m' in command and command[2] == 'ouem.standardize.building':
            Path(command[command.index('--output') + 1]).unlink()
            error = PermissionError('simulated symlink creation denied: WinError 1314')
            error.winerror = 1314
            raise error
        return rc
    monkeypatch.setattr(runner, 'execute', denied)
    assert runner.run(setup.args) == 1
    assert Path(setup.args.native_building).read_bytes() == before
    report = runner.read_json(setup.report)
    assert report['status'] == 'FAILED'
    assert 'WinError 1314' in report['error']
    assert report['stages'][-1]['status'] == 'INTERRUPTED_OR_ERROR'
    assert len(report['stages']) == 2
    assert 'logs/repeat-1-a1.log' in report['artifacts']
    assert all(report['input_integrity'].values())


def test_symlink_input_retarget_is_detected(setup, require_symlinks):
    original = Path(setup.args.native_building)
    link = setup.inputs / 'input-alias'
    other = setup.inputs / 'other'
    other.write_bytes(original.read_bytes())
    create_symlink_or_skip(link, original)
    recorded = {'alias': runner.fingerprint(link)}
    link.unlink()
    create_symlink_or_skip(link, other)
    assert runner.verify_inputs(recorded) == {'alias': False}


def test_building_semantics_detect_attribute_difference(tmp_path):
    first, second = tmp_path / 'a.gpkg', tmp_path / 'b.gpkg'
    frame().to_file(first, layer='building', driver='GPKG')
    changed = frame()
    changed['measured_height'] = 10.000000000000002
    changed.to_file(second, layer='building', driver='GPKG')
    assert runner.building_semantics(first) != runner.building_semantics(second)


@pytest.fixture
def checkpoint_state(setup):
    root = runner.safe_run_path(setup.args.run_dir)
    info = root.stat()
    identity = (info.st_dev, info.st_ino)
    runner.checkpoint(root, identity, {'status': 'RUNNING'})
    return SimpleNamespace(root=root, identity=identity, report=setup.report)


@pytest.mark.parametrize('winerror', [None, 17, 5, 32, 33])
def test_checkpoint_failed_replace_retains_candidate_and_allows_later_save(checkpoint_state, monkeypatch, winerror):
    state = checkpoint_state
    previous = state.report.read_bytes()
    legacy = state.root / 'integration-report.json.tmp'
    legacy.write_bytes(b'existing evidence must not be removed')
    error = PermissionError('simulated persistent replacement failure')
    if winerror is not None:
        error.winerror = winerror
    attempts, sleeps = [], []
    def denied(path, target):
        attempts.append(path)
        raise error
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'replace', denied)
        patch.setattr(runner.time, 'sleep', sleeps.append)
        with pytest.raises(PermissionError) as caught:
            runner.checkpoint(state.root, state.identity, {'quality': 'FAIL', 'reproducibility': 'PASS'})
    assert caught.value is error
    assert len(attempts) == (5 if winerror in (5, 32, 33) else 1)
    assert sleeps == ([0.05, 0.1, 0.2, 0.4] if winerror in (5, 32, 33) else [])
    assert state.report.read_bytes() == previous
    candidates = list(state.root.glob('integration-report-*.json.tmp'))
    assert len(candidates) == 1 and set(attempts) == set(candidates)
    candidate = candidates[0].read_bytes()
    assert json.loads(candidate) == {'quality': 'FAIL', 'reproducibility': 'PASS'}
    runner.checkpoint(state.root, state.identity, {'status': 'FAILED', 'error': str(error)})
    assert runner.read_json(state.report)['status'] == 'FAILED'
    assert candidates[0].read_bytes() == candidate
    assert legacy.read_bytes() == b'existing evidence must not be removed'


def test_checkpoint_serialization_failure_creates_no_candidate(checkpoint_state):
    state = checkpoint_state
    previous = state.report.read_bytes()
    with pytest.raises(ValueError):
        runner.checkpoint(state.root, state.identity, {'invalid': float('nan')})
    assert state.report.read_bytes() == previous
    assert not list(state.root.glob('*.tmp'))


@pytest.mark.parametrize('newline', [None, '\n', '\r\n'], ids=['native', 'lf', 'crlf'])
def test_checkpoint_write_failure_closes_handle_and_retains_partial_evidence(checkpoint_state, monkeypatch, newline):
    from contextlib import contextmanager
    state = checkpoint_state
    previous = state.report.read_bytes()
    original_fdopen = os.fdopen
    streams = []
    fragments = []
    failed_report = {'説明': '書き込み失敗', 'status': 'FAILED'}
    @contextmanager
    def partial_write(*args, **kwargs):
        kwargs['newline'] = newline
        with original_fdopen(*args, **kwargs) as stream:
            streams.append(stream)
            def write(payload):
                fragments.append(payload[:10])
                stream.write(fragments[-1])
                raise OSError('simulated disk write failure')
            yield SimpleNamespace(fileno=stream.fileno, write=write)
    with monkeypatch.context() as patch:
        patch.setattr(os, 'fdopen', partial_write)
        with pytest.raises(OSError, match='disk write failure'):
            runner.checkpoint(state.root, state.identity, failed_report)
    assert streams[0].closed
    assert state.report.read_bytes() == previous
    candidate, = state.root.glob('integration-report-*.json.tmp')
    partial = candidate.read_bytes()
    fragment, = fragments
    assert len(fragment) == 10  # Characters, not UTF-8 bytes or translated line endings.
    line_ending = os.linesep if newline is None else newline
    assert partial == fragment.replace('\n', line_ending).encode('utf-8')
    runner.checkpoint(state.root, state.identity, failed_report)
    assert runner.read_json(state.report) == failed_report
    assert candidate.read_bytes() == partial


@pytest.mark.parametrize('victim', ['candidate', 'report'])
@pytest.mark.parametrize('kind', ['hardlink', 'reparse'])
def test_checkpoint_rechecks_links_before_retry(setup, checkpoint_state, monkeypatch, victim, kind):
    state = checkpoint_state
    accepted = Path(setup.args.native_building)
    before = accepted.read_bytes()
    original_lstat = Path.lstat
    attempts, substituted = [], []
    def attributes(path, *args, **kwargs):
        info = original_lstat(path, *args, **kwargs)
        if kind == 'reparse' and path in substituted:
            return SimpleNamespace(st_mode=info.st_mode, st_nlink=info.st_nlink,
                                   st_file_attributes=0x400)
        return info
    def denied(path, target):
        attempts.append(path)
        attacked = path if victim == 'candidate' else Path(target)
        substituted.append(attacked)
        if kind == 'hardlink':
            attacked.unlink()
            os.link(accepted, attacked)
        error = PermissionError('simulated sharing violation during substitution')
        error.winerror = 32
        raise error
    monkeypatch.setattr(Path, 'replace', denied)
    monkeypatch.setattr(Path, 'lstat', attributes)
    monkeypatch.setattr(runner.time, 'sleep', lambda delay: None)
    with pytest.raises(runner.Blocked, match='linked output'):
        runner.checkpoint(state.root, state.identity, {'status': 'FAILED'})
    assert len(attempts) == 1
    assert accepted.read_bytes() == before
    assert attempts[0].exists()  # No unconditional cleanup of a substituted candidate.


def test_checkpoint_rejects_replaced_regular_candidate(checkpoint_state, monkeypatch):
    state = checkpoint_state
    previous = state.report.read_bytes()
    original_replace = Path.replace
    def substituted(path, target):
        other = state.root / 'other-file'
        other.write_bytes(path.read_bytes())
        original_replace(other, path)
        error = PermissionError('simulated sharing violation')
        error.winerror = 32
        raise error
    monkeypatch.setattr(Path, 'replace', substituted)
    monkeypatch.setattr(runner.time, 'sleep', lambda delay: None)
    with pytest.raises(runner.Blocked, match='temporary file identity changed'):
        runner.checkpoint(state.root, state.identity, {'status': 'FAILED'})
    assert state.report.read_bytes() == previous


def test_checkpoint_interrupted_replace_retains_candidate(checkpoint_state, monkeypatch):
    state = checkpoint_state
    previous = state.report.read_bytes()
    def interrupted(path, target):
        raise KeyboardInterrupt()
    monkeypatch.setattr(Path, 'replace', interrupted)
    with pytest.raises(KeyboardInterrupt):
        runner.checkpoint(state.root, state.identity, {'status': 'INTERRUPTED'})
    assert state.report.read_bytes() == previous
    candidate, = state.root.glob('integration-report-*.json.tmp')
    assert runner.read_json(candidate)['status'] == 'INTERRUPTED'


def test_persistent_final_report_lock_never_announces_success(setup, monkeypatch, capsys):
    original_replace = Path.replace
    attempts = []
    def locked(path, target):
        if Path(target) == setup.report and runner.read_json(path)['status'] == 'AUTOMATED_PASS':
            attempts.append(path)
            error = PermissionError('simulated persistent final report lock')
            error.winerror = 32
            raise error
        return original_replace(path, target)
    monkeypatch.setattr(Path, 'replace', locked)
    monkeypatch.setattr(runner.time, 'sleep', lambda delay: None)
    assert runner.run(setup.args) == 1
    output = capsys.readouterr()
    assert 'REPORT_SAVE_FAILED:' in output.out and 'AUTOMATED_PASS:' not in output.out
    assert 'persistent final report lock' in output.err and 'File exists' not in output.err
    assert len(attempts) == 5
    assert runner.read_json(setup.report)['status'] == 'RUNNING'
    candidate, = setup.report.parent.glob('integration-report-*.json.tmp')
    result = runner.read_json(candidate)
    assert result['quality'] == result['reproducibility'] == 'PASS'
