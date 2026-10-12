"""Synthetic predicate diagnostics; never reads local Komae data."""
import copy
import json
import os
from pathlib import Path
import subprocess

import pytest
from shapely.geometry import Polygon, mapping

from ouem import komae_adapter_diagnostics as diagnostic
from ouem import komae_integration as runner
from test_komae_integration import setup, write_json, REAL_ROOT
from test_komae_contained import poc


@pytest.fixture
def adapter(tmp_path):
    features = []
    for index, identifier in enumerate(['a', 'b'], 1):
        features.append({'type': 'Feature', 'properties': {'ouem_id': identifier, 'id': index,
            'voxcity_id': index, 'height': 10., 'min_height': 0.},
            'geometry': mapping(Polygon([(139., 35.), (139.001,35.), (139.001,35.001), (139.,35.001)]))})
    document = {'type': 'FeatureCollection', 'crs': {'properties': {'name': 'urn:ogc:def:crs:EPSG::4326'}}, 'features': features}
    path = tmp_path / 'synthetic.geojson'
    write_json(path, document)
    return path, document


def check(path):
    result = diagnostic.diagnose_adapter(path, ['a', 'b'])
    assert result['predicate_parity'] == 'PASS'
    assert result['aggregate'] == runner.adapter_quality(path, ['a', 'b'])
    return result


def test_all_five_conditions_pass(adapter):
    path, _ = adapter
    before = path.read_bytes()
    result = check(path)
    assert result['status'] == 'PASS'
    assert all(c['status'] == 'PASS' for c in result['checks'].values())
    assert path.read_bytes() == before


def test_crs_value_is_reported(adapter):
    path, document = adapter
    document['crs']['properties']['name'] = 'EPSG:4326'
    write_json(path, document)
    result = check(path)['checks']['crs']
    assert result['status'] == 'FAIL'
    assert result['actual'] == 'EPSG:4326'


@pytest.mark.parametrize('case', ['missing', 'extra', 'order', 'duplicate'])
def test_id_differences_are_distinguished(adapter, case):
    path, document = adapter
    features = document['features']
    if case == 'missing':
        features.pop()
    elif case == 'extra':
        extra = copy.deepcopy(features[-1])
        extra['properties']['ouem_id'] = 'c'
        extra['properties']['id'] = extra['properties']['voxcity_id'] = 3
        features.append(extra)
    elif case == 'order':
        features.reverse()
        for i, feature in enumerate(features, 1):
            feature['properties']['id'] = feature['properties']['voxcity_id'] = i
    else:
        features[1]['properties']['ouem_id'] = 'a'
    write_json(path, document)
    result = check(path)['checks']['ouem_ids']
    assert result['status'] == 'FAIL'
    assert result['missing'] == (['b'] if case in ('missing', 'duplicate') else [])
    assert result['extra'] == (['c'] if case == 'extra' else ['a'] if case == 'duplicate' else [])
    assert result['order_only'] == (case == 'order')
    assert result['position_mismatches']


def test_numeric_sequence_reports_actual_and_expected(adapter):
    path, document = adapter
    document['features'][1]['properties']['voxcity_id'] = 7
    write_json(path, document)
    bad = check(path)['checks']['sequential_ids']['failures']
    assert bad == [{'position': 2, 'ouem_id': 'b', 'expected': 2, 'id': 2, 'voxcity_id': 7}]


@pytest.mark.parametrize('height', [0, -1, float('nan'), float('inf'), -float('inf')])
def test_abnormal_heights(adapter, height):
    path, document = adapter
    document['features'][0]['properties']['height'] = height
    write_json(path, document)
    result = check(path)
    bad = result['checks']['heights']['failures'][0]
    assert bad['ouem_id'] == 'a' and bad['min_height'] == 0
    assert 'height' in bad
    json.dumps(result, allow_nan=False)


def test_min_height(adapter):
    path, document = adapter
    document['features'][0]['properties']['min_height'] = 1
    write_json(path, document)
    assert check(path)['checks']['heights']['failures'][0]['min_height'] == 1


@pytest.mark.parametrize('geometry,reason', [
    ({'type': 'Polygon', 'coordinates': []}, 'empty'),
    (mapping(Polygon([(0,0), (1,1), (0,1), (1,0)])), 'invalid'),
    (mapping(Polygon([(0,0,1), (1,0,1), (1,1,1)])), 'has_z'),
    ({'type': 'LineString', 'coordinates': [[0,0],[1,1]]}, 'area_not_positive'),
])
def test_geometry_classifications(adapter, geometry, reason):
    path, document = adapter
    document['features'][1]['geometry'] = geometry
    write_json(path, document)
    bad = check(path)['checks']['geometry']['failures'][0]
    assert bad['ouem_id'] == 'b' and reason in bad['reasons']


def test_unreadable_geometry_does_not_claim_boolean_parity(adapter):
    path, document = adapter
    document['features'][0]['geometry'] = None
    write_json(path, document)
    result = diagnostic.diagnose_adapter(path, ['a', 'b'])
    assert result['status'] == 'ERROR'
    assert result['predicate_parity'] == 'NOT_CHECKED'
    assert result['checks']['geometry']['failures'][0]['reasons'] == ['unreadable_geometry']


def test_python_equality_is_not_silently_made_stricter(adapter):
    path, document = adapter
    document['features'][0]['properties'].update(id=True, voxcity_id=1.0, height=True, min_height=False)
    write_json(path, document)
    assert check(path)['status'] == 'PASS'


def test_empty_list_preserves_existing_vacuous_comparisons(adapter):
    path, document = adapter
    document['features'] = []
    write_json(path, document)
    result = diagnostic.diagnose_adapter(path, [])
    assert result['status'] == 'PASS' and result['predicate_parity'] == 'PASS'


@pytest.fixture
def failed_run(poc, monkeypatch):
    def execute(command, log, **kwargs):
        result = poc.poc_execute(command, log, **kwargs)
        if '--array-evidence' in command:
            path = Path(command[command.index('--adapter-output') + 1])
            document = runner.read_json(path)
            document['crs']['properties']['name'] = 'EPSG:4326'
            write_json(path, document)
            manifest = runner.read_json(runner.adjacent(path))
            manifest['output']['sha256'] = runner.sha256_file(path)
            write_json(runner.adjacent(path), manifest)
        return result
    monkeypatch.setattr(runner, 'execute', execute)
    assert runner.run(poc.args) == 1
    def forbidden(*args, **kwargs):
        pytest.fail('diagnostic attempted to execute a processing stage')
    monkeypatch.setattr(runner, 'execute', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    return poc


def tree_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_existing_run_read_only_comparison_and_recorded_parity(failed_run, capsys):
    root = failed_run.report.parent
    before = tree_bytes(root)
    inputs = tree_bytes(failed_run.inputs)
    result = diagnostic.diagnose_run(root)
    assert result['evidence_consistent']
    assert result['comparison']['same_diagnosis']
    for repeat in result['repeats']:
        assert repeat['diagnosis']['checks']['crs']['status'] == 'FAIL'
        assert repeat['diagnosis']['predicate_parity'] == 'PASS'
        assert repeat['recorded_parity']
        assert repeat['standard_building'].endswith('building-contained.gpkg')
    assert diagnostic.main([root.name]) == 1
    assert 'crs: FAIL' in capsys.readouterr().out
    assert tree_bytes(root) == before
    assert tree_bytes(failed_run.inputs) == inputs


def test_different_repeat_diagnoses(failed_run):
    root = failed_run.report.parent
    report = runner.read_json(failed_run.report)
    stage = next(s for s in report['stages'] if s['name'] == 'repeat-2-a3')
    path = Path(stage['command'][stage['command'].index('--adapter-output') + 1])
    document = runner.read_json(path)
    document['features'][0]['properties']['height'] = -1
    write_json(path, document)
    # Build a self-consistent synthetic record, not a repair by the diagnostic.
    report['artifacts'][path.relative_to(root).as_posix()] = runner.fingerprint(path)
    write_json(failed_run.report, report)
    result = diagnostic.diagnose_run(root)
    assert not result['comparison']['same_diagnosis']
    assert result['comparison']['conditions_equal']['crs']
    assert not result['comparison']['conditions_equal']['heights']


def test_artifact_names_are_discovered_from_recorded_command_and_inventory(failed_run):
    root = failed_run.report.parent
    report = runner.read_json(failed_run.report)
    for stage in report['stages']:
        if not stage['name'].endswith('-a3'):
            continue
        i = stage['command'].index('--adapter-output') + 1
        old = Path(stage['command'][i])
        new = old.with_name('unexpected-adapter-name.geojson')
        old.rename(new)
        report['artifacts'].pop(old.relative_to(root).as_posix())
        report['artifacts'][new.relative_to(root).as_posix()] = runner.fingerprint(new)
        stage['command'][i] = str(new)
    write_json(failed_run.report, report)
    result = diagnostic.diagnose_run(root)
    assert all(r['adapter'].endswith('unexpected-adapter-name.geojson') for r in result['repeats'])


@pytest.mark.parametrize('case', ['hash', 'outside_path', 'sidecar', 'missing_stage', 'recorded_mismatch'])
def test_untrustworthy_or_incomplete_evidence_is_not_passed(failed_run, case):
    root = failed_run.report.parent
    report = runner.read_json(failed_run.report)
    reference = Path(report['inputs']['poc_reference']['path'])
    if case == 'hash':
        with reference.open('ab') as stream:
            stream.write(b'changed')
    elif case == 'outside_path':
        record = report['artifacts'].pop(reference.relative_to(root).as_posix())
        report['artifacts']['../outside.gpkg'] = record
    elif case == 'sidecar':
        Path(str(reference) + '-wal').write_bytes(b'retain')
    elif case == 'missing_stage':
        report['stages'] = []
    else:
        report['repeats'][0]['quality']['adapter_content'] = True
    write_json(failed_run.report, report)
    before = tree_bytes(root)
    assert diagnostic.main([root.name]) == 2
    assert tree_bytes(root) == before


@pytest.mark.parametrize('run_id', ['../run', '.', '..', 'C:\\run', '/tmp/run'])
def test_cli_rejects_path_as_run_id(run_id):
    with pytest.raises(SystemExit) as error:
        diagnostic.main([run_id])
    assert error.value.code == 2


def test_windows_launcher_argument_validation():
    path = REAL_ROOT / 'scripts/work/diagnose_komae_adapter_content.cmd'
    content = path.read_text(encoding='utf-8')
    assert '-B -m ouem.komae_adapter_diagnostics' in content
    assert 'exit /b %ERRORLEVEL%' in content
    if os.name == 'nt':
        for args, expected in [([], b'Usage:'), (['one', 'two'], b'ERROR:')]:
            result = subprocess.run(['cmd', '/d', '/c', str(path), *args], capture_output=True, timeout=10)
            assert result.returncode == 2 and expected in result.stdout


def test_json_output_contains_all_observations_without_writing(failed_run, capsys):
    root = failed_run.report.parent
    before = tree_bytes(root)
    capsys.readouterr()
    assert diagnostic.main([root.name, '--json']) == 1
    result = json.loads(capsys.readouterr().out)
    observations = result['repeats'][0]['diagnosis']['checks']['heights']['observations']
    assert len(observations) == 1 and observations[0]['height'] == 10
    assert tree_bytes(root) == before


def test_predicate_drift_is_explicit_not_silently_accepted(adapter, monkeypatch):
    path, _ = adapter
    monkeypatch.setattr(runner, 'adapter_quality', lambda path, ids: False)
    result = diagnostic.diagnose_adapter(path, ['a', 'b'])
    assert result['predicate_parity'] == 'FAIL'
    assert result['status'] == 'ERROR'


def test_input_recheck_detects_concurrent_change(failed_run, monkeypatch):
    original = diagnostic.diagnose_adapter
    def change(path, expected):
        result = original(path, expected)
        with Path(path).open('ab') as stream:
            stream.write(b' ')
        return result
    monkeypatch.setattr(diagnostic, 'diagnose_adapter', change)
    with pytest.raises(runner.Blocked, match='changed during reading'):
        diagnostic.diagnose_run(failed_run.report.parent)
