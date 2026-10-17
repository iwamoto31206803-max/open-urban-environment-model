"""Synthetic QGIS export checks; no company-PC Komae artifacts are used."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import venv

import geopandas as gpd
import pytest
from shapely.geometry import Polygon, shape

from ouem import komae_crs_repair_evaluation as evaluation
from ouem import komae_repair_qgis_export as exporter
from ouem import komae_integration as runner
from tests.test_komae_crs_repair_evaluation import TARGET, build_run, tree_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_candidate_a_gpkg_parts_metrics_repeat_and_non_destructive(tmp_path):
    root = build_run(tmp_path)
    before = tree_bytes(root)
    report = exporter.export_run(root, tmp_path/'diagnostics', TARGET)
    path = Path(report['gpkg'])
    assert path.is_file() and not path.is_relative_to(root)
    assert report['status'] == 'EXPORTED_FOR_INSPECTION_NOT_ACCEPTANCE'
    assert report['part_count'] == 3  # synthetic notch, real run must report its actual count
    assert all(report['repeat_comparison'].values())
    assert all(report['source_sha256_unchanged_after'].values())
    assert tree_bytes(root) == before
    assert runner.sha256_file(path) == report['gpkg_sha256']
    assert (path.parent/'inspection.json').is_file()
    for layer, count in [('adapter_before', 1), ('candidate_a', 1),
                         ('candidate_a_parts', 3), ('self_intersection', 1)]:
        frame = gpd.read_file(path, layer=layer)
        assert len(frame) == count and frame.crs.to_epsg() == 4326
        assert all(json.loads(props)['audit_attribute']['text'] == '属性を保持'
                   for props in frame.properties_json)
        assert frame.ouem_id.tolist() == [TARGET] * count
        assert frame.id.tolist() == [1] * count
    saved = shape(runner.read_json(root/'試験 1/engine-export.json')['features'][0]['geometry'])
    reference = evaluation.provenance.reproject_xy(saved, 4326, 6677)
    expected, _ = evaluation.candidate_geometry(reference, saved, 'A', None)
    from ouem.adapters import voxcity as adapter
    from shapely.geometry import mapping
    expected = shape(json.loads(adapter.canonical_json(mapping(expected))))
    actual = gpd.read_file(path, layer='candidate_a').geometry.iloc[0]
    assert actual.wkb == expected.wkb
    parts = gpd.read_file(path, layer='candidate_a_parts')
    assert parts.part_index.tolist() == [1, 2, 3]
    assert [g.wkb for g in parts.geometry] == [g.wkb for g in expected.geoms]
    assert sum(parts.area_m2) == pytest.approx(
        evaluation.provenance.reproject_xy(expected, 4326, 6677).area, rel=1e-10)
    assert sum(parts.area_share_percent) == pytest.approx(100)
    assert all(parts.vertex_count > 0)
    assert all(parts.is_valid)
    assert report['repeats'][0]['candidate_a_sha256'] == report['repeats'][1]['candidate_a_sha256']


def test_two_polygon_extraction_and_nonpolygonal_rejection():
    bowtie = Polygon([(0, 0), (2, 2), (0, 2), (2, 0)])
    candidate, _ = evaluation.candidate_geometry(None, bowtie, 'A', None)
    parts = exporter._checked_parts(candidate, TARGET)
    assert candidate.geom_type == 'MultiPolygon' and len(parts) == 2
    # PR #42 retains lines as well as polygons. The export must not hide them.
    spike = Polygon([(0, 0), (2, 0), (2, 2), (1, 2), (1, 3), (1, 2), (0, 2)])
    candidate, _ = evaluation.candidate_geometry(None, spike, 'A', None)
    with pytest.raises(ValueError, match='Polygon/MultiPolygon'):
        exporter._checked_parts(candidate, TARGET)


def test_full_92_building_replay_and_fresh_diagnostic_directory(tmp_path):
    root = build_run(tmp_path, count=92)
    before = tree_bytes(root)
    destination = tmp_path/'diagnostics'
    first = exporter.export_run(root, destination, TARGET)
    second = exporter.export_run(root, destination, TARGET)
    assert first['gpkg'] != second['gpkg']
    assert first['repeats'] == second['repeats']
    assert first['parts'] == second['parts']
    for layer in ('adapter_before', 'candidate_a', 'candidate_a_parts', 'self_intersection'):
        left = gpd.read_file(first['gpkg'], layer=layer)
        right = gpd.read_file(second['gpkg'], layer=layer)
        assert left.geometry.to_wkb().tolist() == right.geometry.to_wkb().tolist()
        assert left.properties_json.tolist() == right.properties_json.tolist()
    assert len(list(destination.iterdir())) == 2
    assert tree_bytes(root) == before


def test_repeat_mismatch_blocks_before_creating_output(tmp_path):
    root = build_run(tmp_path)
    path = root/'試験 2/engine-export.json'
    from ouem.adapters import voxcity as adapter
    document = runner.read_json(path)
    document['features'][0]['properties']['audit_attribute']['text'] = 'different repeat'
    path.write_bytes(adapter.canonical_json(document))
    manifest_path = runner.adjacent(path)
    manifest = runner.read_json(manifest_path)
    manifest['output']['sha256'] = runner.sha256_file(path)
    manifest_path.write_bytes(adapter.canonical_json(manifest))
    report_path = root/'integration-report.json'
    report = runner.read_json(report_path)
    for changed in (path, manifest_path):
        report['artifacts'][changed.relative_to(root).as_posix()] = runner.fingerprint(changed)
    report_path.write_bytes(adapter.canonical_json(report))
    destination = tmp_path/'diagnostics'
    with pytest.raises(ValueError, match='Repeat 1/2'):
        exporter.export_run(root, destination, TARGET)
    assert not destination.exists()


def test_input_hash_mismatch_blocks_before_creating_output(tmp_path):
    root = build_run(tmp_path)
    with (root/'試験 1/engine-export.json').open('ab') as stream:
        stream.write(b' ')
    destination = tmp_path/'diagnostics'
    with pytest.raises(runner.Blocked, match='hash/size mismatch'):
        exporter.export_run(root, destination, TARGET)
    assert not destination.exists()


def test_concurrent_input_change_after_gpkg_blocks_and_retains_diagnostic(tmp_path, monkeypatch):
    root = build_run(tmp_path)
    destination = tmp_path/'diagnostics'
    original = exporter._write_gpkg
    def change(*args):
        result = original(*args)
        with (root/'integration-report.json').open('ab') as stream:
            stream.write(b' ')
        return result
    monkeypatch.setattr(exporter, '_write_gpkg', change)
    with pytest.raises(runner.Blocked, match='hash/size mismatch|changed'):
        exporter.export_run(root, destination, TARGET)
    folders = list(destination.iterdir())
    assert len(folders) == 1 and (folders[0]/'candidate-a-inspection.gpkg').exists()
    assert not (folders[0]/'inspection.json').exists()


def test_linked_output_base_rejected_without_touching_target(tmp_path):
    source = tmp_path/'existing-output'
    source.mkdir()
    destination = tmp_path/'linked-output'
    try:
        destination.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        if os.name == 'nt' and getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows symlink creation privilege unavailable')
        raise
    root = build_run(tmp_path)
    with pytest.raises(runner.Blocked, match='linked output'):
        exporter.export_run(root, destination, TARGET)
    assert list(source.iterdir()) == []


def test_windows_launcher_arguments_and_exit_status(tmp_path):
    source = REPOSITORY/'scripts/work/export_komae_adapter_repair_qgis.cmd'
    text = source.read_text(encoding='utf-8')
    assert '-B -m ouem.komae_repair_qgis_export' in text
    assert '"%~1" "%~2"' in text
    if os.name == 'nt':
        launcher = tmp_path/'scripts/work'/source.name
        launcher.parent.mkdir(parents=True)
        shutil.copyfile(source, launcher)
        for args in ([], ['one', 'two', 'three']):
            result = subprocess.run(['cmd', '/d', '/c', str(launcher), *args], capture_output=True, timeout=20)
            assert result.returncode == 2
        venv.EnvBuilder(with_pip=False).create(tmp_path/'.venv')
        package = tmp_path/'ouem'
        package.mkdir()
        (package/'__init__.py').write_text('', encoding='utf-8')
        (package/'komae_repair_qgis_export.py').write_text(
            'import json,sys\nprint(json.dumps(sys.argv[1:]))\nraise SystemExit(7)\n', encoding='utf-8')
        for args in (['run'], ['run', TARGET]):
            result = subprocess.run(['cmd', '/d', '/c', str(launcher), *args], capture_output=True, timeout=20)
            assert result.returncode == 7 and json.loads(result.stdout) == args


def test_cli_prints_path_and_areas(tmp_path, monkeypatch, capsys):
    base = tmp_path/'data/work/integration'
    base.mkdir(parents=True)
    root = build_run(base)
    monkeypatch.setattr(runner, 'REPOSITORY', tmp_path)
    assert exporter.main([root.name, TARGET]) == 0
    output = capsys.readouterr().out
    assert 'QGIS GeoPackage:' in output and 'part 1:' in output and 'part 2:' in output
    assert 'Repeat 1/2 and source SHA-256: MATCH' in output
    for bad in ('../run', '.', '..', 'C:\\run'):
        with pytest.raises(SystemExit):
            exporter.main([bad])
