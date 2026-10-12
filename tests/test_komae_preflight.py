"""Synthetic inputs only; GIS import/version subprocess is mocked on both OSes."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import rasterio

from ouem import komae_integration as runner
from ouem import komae_preflight as preflight
from test_komae_integration import setup, frame, write_json  # shared synthetic fixture


@pytest.fixture
def ready(setup, monkeypatch):
    native = Path(setup.args.native_building)
    native.unlink()  # replace only this test's synthetic placeholder
    data = frame().to_crs(4979)
    data['id'] = ['synthetic']
    data.to_file(native, layer='building', driver='GPKG')
    monkeypatch.setattr(preflight, 'gis_probe', lambda path: {'python': 'synthetic GIS'})
    def forbidden(*a, **kw):
        pytest.fail('preflight must not create a run or execute a processing stage')
    monkeypatch.setattr(runner, 'safe_run_path', forbidden)
    monkeypatch.setattr(runner, 'execute', forbidden)
    return setup


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_pass_is_read_only_and_explicitly_not_acceptance(ready):
    before = snapshot(ready.inputs)
    report = preflight.preflight(ready.args)
    assert report['status'] == 'PASS', report['checks']
    assert report['checks']['gis_runtime']['status'] == 'PASS'
    assert report['checks']['a3_actual_bounds_and_quality']['status'] == 'NOT_CHECKED'
    assert report['checks']['historical_building_identity']['status'] == 'NOT_CHECKED'
    assert report['checks']['output_writability']['status'] == 'NOT_CHECKED'
    assert all(report['input_integrity'].values())
    assert report['inputs']['raw_terrain']['sha256']
    assert snapshot(ready.inputs) == before
    assert not (ready.repo / 'data').exists()
    assert not ready.commands


@pytest.mark.parametrize('target', ['native_building', 'native_terrain', 'reference_standard_building', 'study_area', 'gis_runtime'])
def test_missing_input_blocks_without_output(ready, target):
    Path(getattr(ready.args, target)).unlink()
    result = preflight.preflight(ready.args)
    assert result['status'] == 'BLOCKED'
    assert result['checks']['input_inventory']['action']
    assert result['checks']['gis_runtime']['status'] == 'NOT_CHECKED'
    assert not (ready.repo / 'data').exists()


def test_corrupt_raw_hash_blocks(ready):
    with ready.raw.open('ab') as stream:
        stream.write(b'changed')
    result = preflight.preflight(ready.args)
    assert result['checks']['native_terrain']['status'] == 'BLOCKED'
    assert result['checks']['reference_dem_coverage']['status'] == 'NOT_CHECKED'


def test_nodata_coverage_blocks(ready):
    # Keep the registered metadata/hash honest; the coverage check must still fail.
    from ouem.native.terrain import accept_native_terrain
    with rasterio.open(ready.raw, 'r+') as raster:
        values = raster.read(1)
        values[22, 17] = -9999
        raster.write(values, 1)
    Path(ready.args.native_terrain).unlink()
    accept_native_terrain(ready.raw, ready.args.native_terrain, provider='synthetic', source_dataset='synthetic',
        vertical_reference_status='source-declared', vertical_reference='T.P.', vertical_reference_source='fixture')
    result = preflight.preflight(ready.args)
    assert result['checks']['native_terrain']['status'] == 'PASS'
    assert result['checks']['reference_dem_coverage']['status'] == 'BLOCKED'


@pytest.mark.parametrize('case', ['existing', 'traversal', 'ancestor_file', 'reparse'])
def test_output_rejected_without_writes(ready, monkeypatch, case):
    root = Path(ready.args.run_dir)
    if case == 'existing':
        root.mkdir(parents=True)
        (root / 'evidence').write_bytes(b'keep')
    elif case == 'traversal':
        ready.args.run_dir = str(root.parent / '..' / 'integration' / root.name)
    elif case == 'ancestor_file':
        (ready.repo / 'data').write_bytes(b'keep')
    else:
        # Windows junction/reparse semantics without requiring link privilege.
        original = runner.check_links
        def reparse(path):
            if Path(path) == ready.repo / 'data':
                raise runner.Blocked('linked output path is forbidden (synthetic reparse point)')
            original(path)
        monkeypatch.setattr(runner, 'check_links', reparse)
    before = snapshot(ready.repo)
    result = preflight.preflight(ready.args)
    assert result['checks']['output_path']['status'] == 'BLOCKED'
    assert snapshot(ready.repo) == before


def test_unverified_voxcity_is_blocked(ready, monkeypatch):
    monkeypatch.setattr(runner, 'environment', lambda: {'voxcity': {'verified': False}})
    assert preflight.preflight(ready.args)['checks']['ouem_environment']['status'] == 'BLOCKED'


def test_changed_input_during_probe_is_detected(ready, monkeypatch):
    def change(path):
        with Path(ready.args.study_area).open('a', encoding='utf-8') as stream:
            stream.write('\n# simulated concurrent writer\n')
    monkeypatch.setattr(preflight, 'gis_probe', change)
    result = preflight.preflight(ready.args)
    assert result['checks']['inputs_unchanged']['status'] == 'BLOCKED'


def test_sqlite_sidecars_are_not_opened_or_deleted(ready):
    sidecar = Path(ready.args.native_building + '-wal')
    sidecar.write_bytes(b'evidence')
    result = preflight.preflight(ready.args)
    assert result['checks']['input_inventory']['status'] == 'BLOCKED'
    assert sidecar.read_bytes() == b'evidence'


def test_cli_json_and_exit_status(ready, capsys):
    flags = ['preflight']
    for key, value in vars(ready.args).items():
        flags.extend(['--' + key.replace('_', '-'), str(value)])
    assert runner.main(flags) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'PASS'
    flags[flags.index('--meshsize') + 1] = 'nan'
    assert runner.main(flags) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'BLOCKED'


@pytest.fixture
def gis_snapshot(tmp_path):
    files = {name: tmp_path / (name + '.exe') for name in ('python', 'ogr2ogr', 'ogrinfo')}
    for path in files.values():
        path.write_bytes(b'synthetic, never executed')
    value = {'schema': 'ouem-gis-runtime/v0.1', **{k: str(v) for k, v in files.items()},
             'environment': {'PATH': str(tmp_path), 'TOKEN': 'do-not-disclose'}, 'output_encoding': 'utf-8'}
    path = tmp_path / 'snapshot.json'
    write_json(path, value)
    return path, value


def test_gis_probe_uses_snapshot_in_separate_read_only_child(gis_snapshot, monkeypatch):
    path, value = gis_snapshot
    def probe(command, **kwargs):
        assert command[:3] == [value['python'], '-B', '-c']
        assert kwargs['env'] == value['environment']
        assert kwargs['timeout'] == 30
        assert 'ogr2ogr' not in command
        return SimpleNamespace(returncode=0, stdout=json.dumps({'python': value['python'], 'version': '3.12', 'gdal': 'GDAL synthetic'}).encode())
    monkeypatch.setattr(subprocess, 'run', probe)
    result = preflight.gis_probe(path)
    assert 'do-not-disclose' not in json.dumps(result)


@pytest.mark.parametrize('mode', ['timeout', 'permission', 'exit', 'identity', 'invalid_json'])
def test_gis_probe_failures_are_not_pass(gis_snapshot, monkeypatch, mode):
    path, value = gis_snapshot
    def probe(*args, **kwargs):
        if mode == 'timeout':
            raise subprocess.TimeoutExpired('synthetic', 30)
        if mode == 'permission':
            error = PermissionError('synthetic Windows access denied')
            error.winerror = 5
            raise error
        return SimpleNamespace(returncode=1 if mode == 'exit' else 0,
            stdout=b'invalid' if mode == 'invalid_json' else json.dumps({'python': sys.executable, 'version': 'x', 'gdal': 'x'}).encode(),
            stderr=b'do-not-disclose')
    monkeypatch.setattr(subprocess, 'run', probe)
    with pytest.raises((runner.Blocked, subprocess.TimeoutExpired, PermissionError)):
        preflight.gis_probe(path)


@pytest.mark.parametrize('field,value', [('schema', 'wrong'), ('environment', {}), ('output_encoding', 'not-a-codec'), ('python', 'relative.exe')])
def test_invalid_gis_snapshot_never_starts_child(gis_snapshot, monkeypatch, field, value):
    path, data = gis_snapshot
    data[field] = value
    write_json(path, data)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('invalid snapshot launched'))
    with pytest.raises((runner.Blocked, LookupError)):
        preflight.gis_probe(path)


@pytest.mark.parametrize('case,check', [
    ('native_manifest', 'native_building'), ('reference_manifest', 'reference_building'),
    ('count', 'reference_building'), ('native_count', 'native_building'),
    ('study_crs', 'study_area'), ('study_nan', 'study_area'), ('vertical', 'vertical_reference'),
])
def test_prerequisite_mismatches_block(ready, case, check):
    if case == 'native_manifest':
        write_json(runner.adjacent(ready.args.native_building), {'schema': 'wrong'})
    elif case == 'reference_manifest':
        write_json(runner.adjacent(ready.args.reference_standard_building), {'schema': 'wrong'})
    elif case == 'count':
        ready.args.expected_buildings = 111
    elif case == 'native_count':
        ready.args.expected_native_buildings = 3637
    elif case.startswith('study_'):
        path = Path(ready.args.study_area)
        text = path.read_text(encoding='utf-8')
        text = text.replace('6677', '4326') if case == 'study_crs' else text.replace('-23600', 'nan')
        path.write_text(text, encoding='utf-8')
    else:
        path = runner.adjacent(ready.args.reference_standard_building)
        value = runner.read_json(path)
        value['z_reference'] = 'unknown'
        write_json(path, value)
    report = preflight.preflight(ready.args)
    assert report['checks'][check]['status'] == 'BLOCKED'
    assert report['status'] == 'BLOCKED'
    assert not (ready.repo / 'data').exists()


def test_dependency_failure_is_blocked_and_not_dumped(ready, monkeypatch):
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1, stderr=b'secret'))
    result = preflight.preflight(ready.args)
    assert result['checks']['ouem_environment']['status'] == 'BLOCKED'
    assert 'secret' not in json.dumps(result)
