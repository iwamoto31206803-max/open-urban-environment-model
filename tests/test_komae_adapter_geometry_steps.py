"""Only synthetic in-memory geometry and temporary saved artifacts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

import geopandas as gpd
import pytest
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

from ouem import komae_adapter_geometry_steps as diagnostic
from ouem import komae_integration as runner
from ouem.adapters import voxcity as adapter

TARGET = 'oub-synthetic'
ROOT = Path(__file__).resolve().parents[1]


def source_frame(geometry=None):
    if geometry is None:
        geometry = Polygon([(-24000,-48000,20),(-23988,-48000,20),(-23988,-47988,20),(-24000,-47988,20)])
    return gpd.GeoDataFrame({'ouem_id': [TARGET]}, geometry=[geometry], crs=6677)


def production_geometry(frame):
    geometry, stats = adapter.build_normalized_footprint(frame.geometry.iloc[0], TARGET)
    assigned = adapter._set_normalized_footprints(frame, {TARGET: (geometry, stats)})
    transformed = adapter._to_voxcity_building_crs(assigned)
    saved = shape(json.loads(transformed.to_json(drop_id=True))['features'][0]['geometry'])
    return saved, {'ouem_id': TARGET, 'height': 10., 'voxcity_id': 1, 'footprint': stats}


def test_observation_preserves_production_output_and_operation_order():
    # Include a projected zero-area wall and an invalid positive-area surface;
    # production is allowed to use its original conditional make_valid here.
    valid = source_frame().geometry.iloc[0]
    wall = Polygon([(-24000,-48000,0),(-24000,-48000,20),(-23988,-48000,20)])
    crossing = Polygon([(-24000,-48000,20),(-23988,-47988,20),(-24000,-47988,20),(-23992,-48000,20)])
    frame = source_frame(MultiPolygon([valid, wall, crossing]))
    before = frame.geometry.iloc[0].wkb
    expected, record = production_geometry(frame)
    result = diagnostic.replay(frame, TARGET, record, expected)
    assert result['status'] == 'REPRODUCED' and result['instrumentation_equal']
    assert result['capture_complete'] and sys.getprofile() is None
    functions = [s['function'] for s in result['steps']]
    assert sum(f.endswith('force_2d') for f in functions) == 3
    assert sum(f.endswith('unary_union') for f in functions) == 2
    assert any(f.endswith('make_valid') for f in functions)
    assert sum(s.get('projection_discarded', False) for s in result['steps']) == 1
    assert functions[-5:] == [
        'ouem.adapters.voxcity._set_normalized_footprints',
        'ouem.adapters.voxcity._to_voxcity_building_crs / GeoDataFrame.to_crs(4326)',
        'GeoDataFrame.iterfeatures(drop_id=True)', 'GeoDataFrame.to_json(drop_id=True) / json.loads',
        'ouem.adapters.voxcity.canonical_json / json.loads']
    assert frame.geometry.iloc[0].wkb == before
    assert all(c['equal'] for c in result['manifest_comparison'].values())
    json.dumps(result, allow_nan=False)


def test_crs_and_json_transitions_are_compared_without_geometry_changes():
    frame = source_frame()
    saved, record = production_geometry(frame)
    result = diagnostic.replay(frame, TARGET, record, saved)
    assert result['verdict']['classification'] == 'NO_VALID_TO_INVALID_TRANSITION'
    crs = next(s for s in result['steps'] if s['category'] == 'CRS_TRANSFORMATION')
    assert crs['inputs'][0]['crs'] == 'EPSG:6677' and crs['output']['crs'] == 'EPSG:4326'
    assert crs['changes_from_inputs'][0]['hausdorff_distance_m'] < 1e-6
    for stage in result['steps'][-3:]:
        assert stage['changes_from_inputs'][0]['normalized_xy_exact']
    assert result['rounding']['status'] == 'NOT_APPLIED'
    assert result['final_comparison']['exact_geometry_wkb']


def test_rounding_can_introduce_self_intersection_but_is_not_added_to_replay():
    # A narrow notch becomes a self-touch after a synthetic rounding operation.
    valid = Polygon([(0,0),(3,0),(3,3),(1.49,3),(1.49,1),(1.4,1),(1.4,3),(0,3)])
    rounded = Polygon([(round(x), round(y)) for x,y in valid.exterior.coords])
    assert valid.is_valid and not rounded.is_valid
    step = diagnostic.transition('synthetic round(x), NOT a production step', [valid], rounded,
                                 'EPSG:6677','EPSG:6677', category='COORDINATE_ROUNDING', precision='synthetic integer rounding')
    result = diagnostic.verdict([step], faithful=True, issues=[])
    assert result['classification'] == 'COORDINATE_ROUNDING'
    assert step['valid_to_invalid'] and step['output']['self_intersection_location']
    assert diagnostic.verdict([step], faithful=False, issues=['saved mismatch'])['classification'] == 'INCONCLUSIVE'


@pytest.mark.parametrize('category', ['PROJECTION_2D', 'UNION_NORMALIZATION', 'CRS_TRANSFORMATION', 'GEOJSON_SERIALIZATION'])
def test_classification_uses_observed_before_after_and_requires_parity(category):
    good = Polygon([(0,0),(2,0),(2,2),(0,2)])
    bad = Polygon([(0,0),(2,2),(0,2),(2,0)])
    step = diagnostic.transition('synthetic fault injection', [good], bad, 'EPSG:6677', 'EPSG:6677',
                                 category=category, precision='synthetic operation')
    assert diagnostic.verdict([step], faithful=True, issues=[])['classification'] == category
    assert diagnostic.verdict([step], faithful=False, issues=[])['classification'] == 'INCONCLUSIVE'
    assert step['changes_from_inputs'][0]['symmetric_difference']['status'] == 'NOT_CHECKED'


def test_multiple_operations_and_not_equating_invalid_surface_assembly():
    good = Polygon([(0,0),(2,0),(2,2),(0,2)])
    bad = Polygon([(0,0),(2,2),(0,2),(2,0)])
    steps = [diagnostic.transition('synthetic', [good], bad, 6677, 6677, category=c, precision='test')
             for c in ('CRS_TRANSFORMATION', 'GEOJSON_SERIALIZATION')]
    assert diagnostic.verdict(steps, faithful=True, issues=[])['classification'] == 'MULTIPLE_OPERATIONS'
    union = diagnostic.transition('union', [good, good], good, 6677, 6677, category='UNION_NORMALIZATION', precision='test')
    assert not union['valid_to_invalid']  # overlapping operands are not a MultiPolygon validity test


def test_saved_geometry_mismatch_is_inconclusive():
    frame = source_frame()
    saved, record = production_geometry(frame)
    wrong = Polygon([(139,35),(140,35),(140,36)])
    result = diagnostic.replay(frame, TARGET, record, wrong)
    assert result['status'] == result['verdict']['classification'] == 'INCONCLUSIVE'
    assert not result['final_comparison']['exact_geometry_wkb']


@pytest.mark.parametrize('field', ['footprint_valid','source_surface_part_count','projected_union_area'])
def test_manifest_disagreement_is_inconclusive(field):
    frame = source_frame()
    saved, record = production_geometry(frame)
    record['footprint'][field] = None
    result = diagnostic.replay(frame, TARGET, record, saved)
    assert result['verdict']['classification'] == 'INCONCLUSIVE'
    assert not result['manifest_comparison'][field]['equal']


def test_profiler_is_restored_when_production_function_fails():
    _, events, error = diagnostic.capture_footprint(Polygon([(0,0,1),(0,0,2),(0,1,1)]), TARGET)
    assert error and events
    assert sys.getprofile() is None


def test_existing_profiler_is_not_replaced():
    def existing(*args):
        pass
    sys.setprofile(existing)
    try:
        with pytest.raises(ValueError, match='another profiler'):
            diagnostic.capture_footprint(source_frame().geometry.iloc[0], TARGET)
        assert sys.getprofile() is existing
    finally:
        sys.setprofile(None)


def write_json(path, value):
    path.write_bytes(adapter.canonical_json(value))


@pytest.fixture
def run(tmp_path):
    root = tmp_path / 'existing'
    root.mkdir()
    frame = source_frame()
    saved, record = production_geometry(frame)
    report = {'schema': 'ouem-komae-integration/v0.1', 'run_id': 'synthetic', 'artifacts': {}, 'stages': []}
    for number in (1,2):
        folder = root / f'合成 {number}'
        folder.mkdir()
        building = folder / 'selection-input.gpkg'
        geojson = folder / 'serialized-output.json'
        frame.to_file(building, layer='building')
        write_json(runner.adjacent(building), {'schema': 'ouem-standard-building-manifest/v0.1'})
        write_json(geojson, {'type':'FeatureCollection', 'crs':{'properties':{'name':'urn:ogc:def:crs:EPSG::4326'}},
            'features':[{'type':'Feature','properties':{'ouem_id':TARGET},'geometry':mapping(saved)}]})
        write_json(runner.adjacent(geojson), {'schema': adapter.SCHEMA,
            'inputs':{'standard_building':{'path':str(building),'sha256':runner.sha256_file(building)}},
            'output':{'path':str(geojson),'sha256':runner.sha256_file(geojson)},'buildings':[record]})
        report['stages'].append({'name':f'repeat-{number}-a3','command':['python','a3.py',str(building),
                            'unused-terrain','--adapter-output',str(geojson)]})
    for path in root.rglob('*'):
        if path.is_file():
            report['artifacts'][path.relative_to(root).as_posix()] = runner.fingerprint(path)
    write_json(root / 'integration-report.json', report)
    return root


def tree_bytes(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_repeats_and_read_only_no_grids_or_external_processing(run, monkeypatch):
    before = tree_bytes(run)
    def forbidden(*args, **kwargs):
        pytest.fail('attempted processing/write')
    monkeypatch.setattr(adapter, '_run_voxcity_grids', forbidden)
    monkeypatch.setattr(adapter, 'adapt_standard_to_voxcity', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(gpd.GeoDataFrame, 'to_file', forbidden)
    monkeypatch.setattr(runner, 'execute', forbidden)
    result = diagnostic.diagnose_run(run, TARGET)
    assert result['status'] == 'REPRODUCED'
    assert result['comparison']['same_diagnosis'] and result['comparison']['same_verdict']
    assert all(result['input_integrity'].values())
    assert tree_bytes(run) == before


def test_repeat_difference_is_reported(run):
    path = run / '合成 2/serialized-output.json.manifest.json'
    manifest = runner.read_json(path)
    manifest['buildings'][0]['footprint']['footprint_valid'] = False
    write_json(path, manifest)
    report = runner.read_json(run / 'integration-report.json')
    report['artifacts'][path.relative_to(run).as_posix()] = runner.fingerprint(path)
    write_json(run / 'integration-report.json', report)
    result = diagnostic.diagnose_run(run, TARGET)
    assert result['status'] == 'INCONCLUSIVE'
    assert not result['comparison']['same_diagnosis']
    assert not result['comparison']['same_verdict']


def test_changed_hash_blocks_diagnosis(run):
    with (run / '合成 1/serialized-output.json').open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(runner.Blocked, match='hash/size mismatch'):
        diagnostic.diagnose_run(run, TARGET)


def test_json_cli_and_default_id(run, monkeypatch, capsys):
    # Redirect only the repository root for synthetic CLI lookup.
    root = run.parent / 'data/work/integration'
    root.mkdir(parents=True)
    moved = root / run.name
    # Keep artifacts in place: relocate inventory resolution is intentionally tested.
    shutil.copytree(run, moved)
    monkeypatch.setattr(runner, 'REPOSITORY', run.parent)
    assert diagnostic.main([run.name, TARGET, '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'REPRODUCED'
    assert diagnostic.main([run.name, '--json']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'INCONCLUSIVE'


@pytest.mark.parametrize('run_id',['../run','.', '..', 'C:\\run'])
def test_bad_run_id(run_id):
    with pytest.raises(SystemExit) as exc:
        diagnostic.main([run_id])
    assert exc.value.code == 2


def test_windows_launcher(tmp_path):
    source = ROOT / 'scripts/work/diagnose_komae_adapter_geometry_steps.cmd'
    text = source.read_text(encoding='utf-8')
    assert '-B -m ouem.komae_adapter_geometry_steps' in text and '"%~1" "%~2"' in text
    if os.name == 'nt':
        launcher = tmp_path / 'scripts/work' / source.name
        launcher.parent.mkdir(parents=True)
        shutil.copyfile(source, launcher)
        for args in ([], ['one','two','three']):
            result = subprocess.run(['cmd','/d','/c',str(launcher),*args],capture_output=True,timeout=20)
            assert result.returncode == 2
        venv.EnvBuilder(with_pip=False).create(tmp_path / '.venv')
        package = tmp_path / 'ouem'
        package.mkdir()
        (package / '__init__.py').write_text('', encoding='utf-8')
        (package / 'komae_adapter_geometry_steps.py').write_text(
            'import sys,json\nprint(json.dumps(sys.argv[1:]))\nraise SystemExit(7)\n', encoding='utf-8')
        for args in (['run'], ['run',TARGET]):
            result = subprocess.run(['cmd','/d','/c',str(launcher),*args],capture_output=True,timeout=20)
            assert result.returncode == 7 and json.loads(result.stdout) == args


def test_replay_localizes_injected_crs_failure_only_with_exact_saved_match(monkeypatch):
    frame = source_frame()
    original = adapter._to_voxcity_building_crs
    def synthetic_crs_fault(buildings):
        projected = original(buildings)
        x,y = projected.geometry.iloc[0].exterior.coords[0]
        projected.geometry = [Polygon([(x,y),(x+.001,y+.001),(x,y+.001),(x+.001,y)])]
        return projected
    monkeypatch.setattr(adapter, '_to_voxcity_building_crs', synthetic_crs_fault)
    saved, record = production_geometry(frame)
    result = diagnostic.replay(frame, TARGET, record, saved)
    assert result['status'] == 'REPRODUCED'
    assert result['verdict']['classification'] == 'CRS_TRANSFORMATION'
    assert result['verdict']['first_valid_to_invalid']['category'] == 'CRS_TRANSFORMATION'
    assert result['final_comparison']['exact_geometry_wkb']


def test_concurrent_input_change_is_detected(run, monkeypatch):
    original = diagnostic.replay
    def change(*args):
        result = original(*args)
        with (run / 'integration-report.json').open('ab') as stream:
            stream.write(b' ')
        return result
    monkeypatch.setattr(diagnostic, 'replay', change)
    with pytest.raises(runner.Blocked, match='changed'):
        diagnostic.diagnose_run(run, TARGET)


def test_geometry_engine_error_is_inconclusive_with_reason(run, monkeypatch):
    from shapely.errors import GEOSException
    def fail(*args):
        raise GEOSException('synthetic unsupported intermediate geometry')
    monkeypatch.setattr(diagnostic, 'replay', fail)
    result = diagnostic.diagnose_run(run, TARGET)
    assert result['status'] == 'INCONCLUSIVE'
    assert all('GEOSException' in r['diagnosis']['issues'][0] for r in result['repeats'])
    assert all(result['input_integrity'].values())
