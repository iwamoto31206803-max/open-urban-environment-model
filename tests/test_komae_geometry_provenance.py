"""Synthetic saved provenance, including raw invalid shapes; no local Komae data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import venv

import geopandas as gpd
import pytest
from shapely.geometry import MultiPolygon, Polygon, mapping

from ouem import komae_geometry_provenance as diagnostic
from ouem import komae_integration as runner
from ouem.standardize.building import ID_RULE, SOURCE_DATASET, deterministic_ouem_id

SOURCE_ID = 'synthetic-元-building'
TARGET = deterministic_ouem_id(SOURCE_ID)
REPOSITORY = Path(__file__).resolve().parents[1]


def write_json(path, document):
    path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')


def polygon(invalid=False):
    points = [(0, 0), (12, 12), (0, 12), (12, 0)] if invalid else [(0, 0), (12, 0), (12, 12), (0, 12)]
    return Polygon([(x - 24000, y - 48000, 20) for x, y in points])


def make_run(tmp_path, invalid_at=None, *, native_surface=False):
    """Use deliberately noncanonical filenames; discovery must follow records."""
    root = tmp_path / 'run'
    root.mkdir()
    native = tmp_path / '受入 Native.gpkg'
    native_geometry = diagnostic.reproject_xy(polygon(invalid_at == 'native'), 'EPSG:6677', 'EPSG:4979')
    if native_surface:
        native_geometry = MultiPolygon([native_geometry, native_geometry])
    gpd.GeoDataFrame({'ID': [SOURCE_ID]}, geometry=[native_geometry], crs='EPSG:4979').to_file(native, layer='source_surfaces')
    write_json(runner.adjacent(native), {'schema': 'ouem-plateau-native-ingest/v0.1', 'native_output': str(native),
        'parameters': {'output_layer': 'source_surfaces'}})
    report = {'schema': 'ouem-komae-integration/v0.1', 'run_id': 'synthetic', 'stages': [], 'artifacts': {},
              'inputs': {'native_building': runner.fingerprint(native),
                         'native_building_manifest': runner.fingerprint(runner.adjacent(native))}}
    for repeat in (1, 2):
        directory = root / f'試験 {repeat}'
        directory.mkdir()
        full, subset, adapter = [directory / name for name in ('complete.gpkg', 'selection.gpkg', 'engine.json')]
        geometry = polygon(invalid_at in ('native', 'a1_standard'))
        if native_surface:
            geometry = MultiPolygon([geometry, geometry])
        frame = gpd.GeoDataFrame({'ouem_id': [TARGET], 'source_id': [SOURCE_ID], 'source_dataset': [SOURCE_DATASET]},
                                geometry=[geometry], crs='EPSG:6677')
        frame.to_file(full, layer='standard_surfaces')
        write_json(runner.adjacent(full), {'schema': 'ouem-standard-building-manifest/v0.1',
            'native_input': str(native), 'standard_output': str(full), 'source_dataset': SOURCE_DATASET,
            'metadata_mapping': {'source_id': 'Native Building id'}, 'ouem_id_rule': ID_RULE,
            'validation': {'input_layer': 'source_surfaces', 'output_layer': 'standard_surfaces'}})
        frame.to_file(subset, layer='standard_surfaces')
        write_json(runner.adjacent(subset), {'schema': 'ouem-standard-building-manifest/v0.1',
            'standard_output': str(subset), 'selection': {'selected_ids': [TARGET]},
            'parent': {'building': runner.fingerprint(full), 'manifest': runner.fingerprint(runner.adjacent(full))}})
        from shapely import force_2d
        engine_geometry = force_2d(diagnostic.reproject_xy(polygon(invalid_at is not None), 'EPSG:6677', 'EPSG:4326'))
        write_json(adapter, {'type': 'FeatureCollection', 'crs': {'properties': {'name': 'urn:ogc:def:crs:EPSG::4326'}},
            'features': [{'type': 'Feature', 'properties': {'ouem_id': TARGET, 'id': 1, 'voxcity_id': 1},
                          'geometry': mapping(engine_geometry)}]})
        write_json(runner.adjacent(adapter), {'schema': 'ouem-standard-to-voxcity-building-adapter/v0.1',
            'inputs': {'standard_building': {'path': str(subset), 'sha256': runner.sha256_file(subset)}},
            'output': {'path': str(adapter), 'sha256': runner.sha256_file(adapter)},
            'buildings': [{'ouem_id': TARGET, 'footprint': {'footprint_valid': True}}]})
        report['stages'] += [
            {'name': f'repeat-{repeat}-a1', 'command': ['python', '-m', 'ouem.standardize.building', str(native), '--output', str(full)]},
            {'name': f'repeat-{repeat}-a3', 'command': ['python', 'recorded_a3.py', str(subset), 'unused-terrain', '--adapter-output', str(adapter)]}]
    for path in root.rglob('*'):
        if path.is_file():
            report['artifacts'][path.relative_to(root).as_posix()] = runner.fingerprint(path)
    write_json(root / 'integration-report.json', report)
    return root


def tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def reindex(root):
    """Only fixture construction may rewrite evidence; never used by diagnosis."""
    report = runner.read_json(root / 'integration-report.json')
    for key in report['artifacts']:
        report['artifacts'][key] = runner.fingerprint(root / key)
    write_json(root / 'integration-report.json', report)


@pytest.mark.parametrize('invalid_at,classification', [
    (None, 'ALL_SAVED_GEOMETRIES_VALID'), ('native', 'NATIVE_ALREADY_INVALID'),
    ('a1_standard', 'NATIVE_TO_STANDARD'), ('adapter', 'STANDARD_TO_ADAPTER')])
def test_first_invalid_stage_and_read_only(tmp_path, monkeypatch, invalid_at, classification):
    root = make_run(tmp_path, invalid_at)
    before = tree_bytes(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail('diagnostic attempted processing/repair')
    import shapely
    import shapely.validation
    from shapely.geometry.base import BaseGeometry
    monkeypatch.setattr(runner, 'execute', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(shapely, 'make_valid', forbidden)
    monkeypatch.setattr(shapely.validation, 'make_valid', forbidden)
    monkeypatch.setattr(BaseGeometry, 'buffer', forbidden)
    result = diagnostic.diagnose_run(root, TARGET)
    assert result['status'] == 'DIAGNOSED'
    assert all(r['classification'] == classification for r in result['repeats'])
    assert all(r['first_invalid_saved_stage'] == (invalid_at or 'NONE') for r in result['repeats'])
    assert result['comparison']['same_diagnosis']
    assert all(result['comparison']['same_stage_geometry'].values())
    assert all(result['input_integrity'].values())
    assert tree_bytes(tmp_path) == before
    json.dumps(result, allow_nan=False)
    if invalid_at:
        stage = result['repeats'][0]['stages'][invalid_at]
        assert stage['self_intersection_location']
        assert result['repeats'][0]['causal_mechanism']['status'] == 'INCONCLUSIVE'


def test_crs_provenance_metrics_and_z_preservation(tmp_path):
    root = make_run(tmp_path)
    repeat = diagnostic.diagnose_run(root, TARGET)['repeats'][0]
    assert repeat['lineage']['source_id'] == SOURCE_ID
    assert repeat['lineage']['deterministic_id_verified']
    stages = repeat['stages']
    assert stages['native']['crs'] == 'EPSG:4979'
    assert stages['a1_standard']['crs'] == 'EPSG:6677'
    assert stages['adapter']['crs'] == 'EPSG:4326'
    for stage in stages.values():
        assert stage['projected']['area_m2'] == pytest.approx(144, abs=1e-5)
        assert stage['counts'] == {'polygons': 1, 'rings': 1, 'vertices': 5}
    assert repeat['comparisons']['native_to_a1_standard']['hausdorff_distance_m'] < 1e-6
    assert repeat['comparisons']['contained_standard_to_adapter']['symmetric_difference']['area_m2'] < 1e-5
    source = polygon()
    projected = diagnostic.reproject_xy(source, 'EPSG:6677', 'EPSG:4979')
    assert [p[2] for p in source.exterior.coords] == [p[2] for p in projected.exterior.coords]


@pytest.mark.parametrize('missing', ['metadata_mapping', 'ouem_id_rule', 'native_input'])
def test_missing_provenance_is_inconclusive_with_partial_observations(tmp_path, missing):
    root = make_run(tmp_path, 'adapter')
    for path in root.glob('*/complete.gpkg.manifest.json'):
        document = runner.read_json(path)
        document.pop(missing)
        write_json(path, document)
        child = path.parent / 'selection.gpkg.manifest.json'
        manifest = runner.read_json(child)
        manifest['parent']['manifest'] = runner.fingerprint(path)
        write_json(child, manifest)
    reindex(root)
    result = diagnostic.diagnose_run(root, TARGET)
    assert result['status'] == 'INCONCLUSIVE'
    for repeat in result['repeats']:
        assert repeat['first_invalid_saved_stage'] == 'INCONCLUSIVE'
        assert repeat['observed_invalid_stages'] == ['adapter']
        assert repeat['issues']


def test_missing_target_never_uses_row_or_spatial_fallback(tmp_path):
    root = make_run(tmp_path)
    result = diagnostic.diagnose_run(root, deterministic_ouem_id('unknown'))
    assert result['status'] == 'INCONCLUSIVE'
    assert '0 matches' in result['repeats'][0]['issues'][0]


def test_surface_assembly_validity_is_not_a_causal_claim(tmp_path):
    root = make_run(tmp_path, native_surface=True)
    repeat = diagnostic.diagnose_run(root, TARGET)['repeats'][0]
    assert repeat['stages']['native']['geometry_type'] == 'MultiPolygon'
    assert not repeat['stages']['native']['is_valid']
    assert repeat['stages']['adapter']['is_valid']
    assert repeat['causal_mechanism']['status'] == 'INCONCLUSIVE'
    assert not repeat['comparisons']['contained_standard_to_adapter']['same_representation']
    assert repeat['comparisons']['contained_standard_to_adapter']['symmetric_difference']['status'] == 'NOT_CHECKED'


def test_repeats_can_differ(tmp_path):
    root = make_run(tmp_path)
    path = root / '試験 2/engine.json'
    document = runner.read_json(path)
    document['features'][0]['geometry'] = mapping(diagnostic.reproject_xy(polygon(True), 'EPSG:6677', 'EPSG:4326'))
    write_json(path, document)
    manifest = runner.read_json(runner.adjacent(path))
    manifest['output']['sha256'] = runner.sha256_file(path)
    write_json(runner.adjacent(path), manifest)
    reindex(root)
    result = diagnostic.diagnose_run(root, TARGET)
    assert not result['comparison']['same_diagnosis']
    assert not result['comparison']['same_classification']
    assert not result['comparison']['same_stage_geometry']['adapter']


@pytest.mark.parametrize('target', ['native', 'artifact'])
def test_saved_hash_mismatch_is_blocked(tmp_path, target):
    root = make_run(tmp_path)
    path = tmp_path / '受入 Native.gpkg' if target == 'native' else root / '試験 1/engine.json'
    with path.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(runner.Blocked, match='hash/size mismatch'):
        diagnostic.diagnose_run(root, TARGET)


def test_concurrent_changes_are_blocked(tmp_path, monkeypatch):
    root = make_run(tmp_path)
    original = diagnostic.diagnose_repeat
    def change(evidence, number, identifier):
        result = original(evidence, number, identifier)
        if number == 2:
            with (root / 'integration-report.json').open('ab') as stream:
                stream.write(b' ')
        return result
    monkeypatch.setattr(diagnostic, 'diagnose_repeat', change)
    with pytest.raises(runner.Blocked, match='changed'):
        diagnostic.diagnose_run(root, TARGET)


def test_active_geopackage_sidecars_block_without_deletion(tmp_path):
    root = make_run(tmp_path)
    sidecar = Path(str(tmp_path / '受入 Native.gpkg') + '-wal')
    sidecar.write_bytes(b'evidence')
    with pytest.raises(runner.Blocked, match='sidecars'):
        diagnostic.diagnose_run(root, TARGET)
    assert sidecar.read_bytes() == b'evidence'


def test_json_cli_and_default_target_no_files(tmp_path, monkeypatch, capsys):
    base = tmp_path / 'data/work/integration'
    base.mkdir(parents=True)
    root = make_run(base, 'adapter')
    monkeypatch.setattr(runner, 'REPOSITORY', tmp_path)
    before = tree_bytes(tmp_path)
    assert diagnostic.main([root.name, TARGET, '--json']) == 1
    assert json.loads(capsys.readouterr().out)['repeats'][0]['classification'] == 'STANDARD_TO_ADAPTER'
    assert diagnostic.main([root.name, '--json']) == 2
    assert json.loads(capsys.readouterr().out)['ouem_id'] == diagnostic.DEFAULT_ID
    assert tree_bytes(tmp_path) == before


@pytest.mark.parametrize('run_id', ['../run', '.', '..', 'C:\\run', '/tmp/run'])
def test_cli_rejects_path_as_run_id(run_id):
    with pytest.raises(SystemExit) as exc:
        diagnostic.main([run_id])
    assert exc.value.code == 2


def test_windows_launcher_arguments_and_exit_code(tmp_path):
    source = REPOSITORY / 'scripts/work/diagnose_komae_geometry_provenance.cmd'
    content = source.read_text(encoding='utf-8')
    assert '-B -m ouem.komae_geometry_provenance' in content
    assert '"%~1" "%~2"' in content and 'exit /b %ERRORLEVEL%' in content
    if os.name == 'nt':
        # Isolated launcher harness: actually exercise cmd.exe and optional argv,
        # without executing diagnostics against repository/local data.
        launcher = tmp_path / 'scripts/work' / source.name
        launcher.parent.mkdir(parents=True)
        shutil.copyfile(source, launcher)
        for args, expected in [([], b'Usage:'), (['one', 'two', 'three'], b'ERROR:')]:
            process = subprocess.run(['cmd', '/d', '/c', str(launcher), *args], capture_output=True, timeout=20)
            assert process.returncode == 2 and expected in process.stdout
        venv.EnvBuilder(with_pip=False).create(tmp_path / '.venv')
        package = tmp_path / 'ouem'
        package.mkdir()
        (package / '__init__.py').write_text('', encoding='utf-8')
        (package / 'komae_geometry_provenance.py').write_text(
            'import sys, json\nprint(json.dumps(sys.argv[1:]))\nraise SystemExit(7)\n', encoding='utf-8')
        for args in [['run'], ['run', TARGET]]:
            process = subprocess.run(['cmd', '/d', '/c', str(launcher), *args], capture_output=True, timeout=20)
            assert process.returncode == 7
            assert json.loads(process.stdout) == args


def test_duplicate_native_id_is_inconclusive(tmp_path):
    root = make_run(tmp_path)
    native = tmp_path / '受入 Native.gpkg'
    frame = gpd.read_file(native, layer='source_surfaces')
    # Append duplicate in fixture setup, then accurately record its new input hash.
    frame.to_file(native, layer='source_surfaces', mode='a')
    report = runner.read_json(root / 'integration-report.json')
    report['inputs']['native_building'] = runner.fingerprint(native)
    write_json(root / 'integration-report.json', report)
    before = tree_bytes(tmp_path)
    result = diagnostic.diagnose_run(root, TARGET)
    assert result['status'] == 'INCONCLUSIVE'
    assert '2 matches' in result['repeats'][0]['issues'][0]
    assert tree_bytes(tmp_path) == before


def test_missing_native_is_inconclusive_not_a_guess(tmp_path):
    root = make_run(tmp_path)
    (tmp_path / '受入 Native.gpkg').rename(tmp_path / 'nearby-but-not-recorded.gpkg')
    result = diagnostic.diagnose_run(root, TARGET)
    assert result['status'] == 'INCONCLUSIVE'
    assert result['repeats'][0]['stages']['adapter']
    assert 'FileNotFoundError' in result['repeats'][0]['issues'][0]


@pytest.mark.parametrize('unsafe', ['../outside.json', 'C:/outside.json', 'folder\\outside.json'])
def test_unsafe_inventory_path_is_blocked(tmp_path, unsafe):
    root = make_run(tmp_path)
    report = runner.read_json(root / 'integration-report.json')
    record = report['artifacts'].pop('試験 1/engine.json')
    report['artifacts'][unsafe] = record
    write_json(root / 'integration-report.json', report)
    with pytest.raises(runner.Blocked, match='unsafe artifact'):
        diagnostic.diagnose_run(root, TARGET)


def test_hardlinked_artifact_is_blocked(tmp_path):
    root = make_run(tmp_path)
    os.link(root / '試験 1/engine.json', tmp_path / 'linked.json')
    with pytest.raises(runner.Blocked, match='hardlinked'):
        diagnostic.diagnose_run(root, TARGET)


def test_comparison_never_repairs_invalid_geometry():
    result = diagnostic.compare((polygon(True), 'EPSG:6677'), (polygon(), 'EPSG:6677'))
    assert result['symmetric_difference']['status'] == 'NOT_CHECKED'
    assert 'hausdorff_distance_m' in result
