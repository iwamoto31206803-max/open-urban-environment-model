"""Synthetic PoC selection and two-repeat runner tests, without local Komae data."""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.affinity import translate
from shapely.geometry import Polygon

from ouem import komae_contained as contained
from ouem import komae_integration as runner
from ouem.study_area import load_study_area
from test_komae_integration import setup, frame, write_json


def full_frame():
    inside = frame()
    crossing = frame()
    crossing['ouem_id'] = ['outside-poc']
    crossing['source_id'] = ['outside-poc']
    crossing.geometry = crossing.geometry.map(lambda g: translate(g, xoff=23))
    return gpd.GeoDataFrame(pd.concat([inside, crossing], ignore_index=True), crs=6677)


@pytest.fixture
def poc(setup, monkeypatch):
    monkeypatch.setattr(contained, 'SELECTED', 1)
    monkeypatch.setattr(contained, 'EXCLUDED', 1)
    setup.args.contained_poc = True
    setup.args.expected_native_buildings = 2
    reference = Path(setup.args.reference_standard_building)
    reference.unlink()
    full_frame().to_file(reference, layer='building', driver='GPKG')
    def execute(command, log, **kwargs):
        result = setup.execute(command, log, **kwargs)
        if 'ouem.standardize.building' in command:
            output = Path(command[command.index('--output') + 1])
            output.unlink()
            full_frame().to_file(output, layer='building', driver='GPKG')
            manifest = runner.read_json(runner.adjacent(output))
            manifest['validation'].update(input_features=2, output_features=2, z_geometries=2)
            write_json(runner.adjacent(output), manifest)
        return result
    monkeypatch.setattr(runner, 'execute', execute)
    setup.poc_execute = execute
    return setup


def test_poc_two_repeats_preserve_full_a1_and_accepted_inputs(poc):
    before = {p: p.read_bytes() for p in poc.inputs.iterdir()}
    assert runner.run(poc.args) == 0
    report = runner.read_json(poc.report)
    assert report['quality'] == report['reproducibility'] == 'PASS'
    assert report['poc_selection']['selected_ids'] == ['oub-synthetic']
    assert report['poc_selection']['excluded_ids'] == ['outside-poc']
    assert report['poc_coverage']['status'] == 'PASS'
    assert report['comparisons']['full_a1_building']
    assert report['comparisons']['poc_selection_sha256']
    assert len([s for s in report['stages'] if s['name'].endswith(('-a1', '-a2', '-a3'))]) == 6
    for number in (1, 2):
        folder = poc.report.parent / f'repeat-{number}'
        assert len(gpd.read_file(folder / 'building.gpkg')) == 2
        assert len(gpd.read_file(folder / 'building-contained.gpkg')) == 1
        subset_manifest = runner.read_json(runner.adjacent(folder / 'building-contained.gpkg'))
        assert subset_manifest['status'] == 'POC_DERIVED_NOT_ACCEPTED'
        assert subset_manifest['parent']['building']['sha256'] == runner.sha256_file(folder / 'building.gpkg')
        assert f'repeat-{number}/arrays.json' in report['artifacts']
    assert all(p.read_bytes() == original for p, original in before.items())
    assert all(report['input_integrity'].values())


def test_expected_92_19_selection_on_synthetic_geometries(setup):
    source = full_frame()
    items = []
    for number in range(111):
        item = source.iloc[[0 if number < 92 else 1]].copy()
        item['ouem_id'] = [f'synthetic-{number:03}']
        items.append(item)
    full = gpd.GeoDataFrame(pd.concat(items, ignore_index=True), crs=6677)
    subset, evidence = contained.select(full, load_study_area(setup.args.study_area))
    contained.validate_selection(evidence)
    assert len(subset) == 92 and evidence['excluded_count'] == 19
    assert set(evidence['selected_ids']).isdisjoint(evidence['excluded_ids'])
    assert all(g.equals_exact(source.geometry.iloc[0], 0) for g in subset.geometry)
    assert all(g.has_z for g in subset.geometry)


def test_covers_includes_boundary_but_does_not_clip(setup):
    area = load_study_area(setup.args.study_area)
    source = frame()
    source.geometry = [Polygon([(-23600,-40800,20),(-23595,-40800,20),
                                (-23595,-40795,20),(-23600,-40795,20)])]
    subset, evidence = contained.select(source, area)
    assert evidence['selected_count'] == 1
    assert subset.geometry.iloc[0].equals_exact(source.geometry.iloc[0], 0)


def test_wrong_selection_count_blocks_before_gis_and_retains_evidence(poc):
    # The production-sized expectation is not waived merely to make this fixture pass.
    contained.SELECTED = 92
    poc.args.expected_buildings = 92
    assert runner.run(poc.args) == 2  # reference count is also a prerequisite
    assert runner.read_json(poc.report)['status'] == 'BLOCKED'
    assert not poc.commands


def test_selection_classification_mismatch_is_recorded(poc):
    reference = Path(poc.args.reference_standard_building)
    source = full_frame()
    source.geometry = source.geometry.map(lambda g: translate(g, xoff=-10))
    reference.unlink()
    source.to_file(reference, layer='building', driver='GPKG')
    assert runner.run(poc.args) == 2
    report = runner.read_json(poc.report)
    assert report['poc_selection']['selected_count'] == 2
    assert report['status'] == 'BLOCKED'
    assert not poc.commands


def test_dem_envelope_outside_blocks_before_any_stage(poc):
    reference = Path(poc.args.reference_standard_building)
    source = full_frame()
    source.loc[0, 'geometry'] = translate(source.geometry.iloc[0], xoff=-15)
    reference.unlink()
    source.to_file(reference, layer='building', driver='GPKG')
    raw_hash = runner.sha256_file(poc.raw)
    assert runner.run(poc.args) == 2
    report = runner.read_json(poc.report)
    assert report['poc_coverage']['status'] == 'BLOCKED'
    assert 'rectangle' in report['poc_coverage']['reason']
    assert not poc.commands
    assert runner.sha256_file(poc.raw) == raw_hash
    assert (poc.report.parent / 'poc-reference.gpkg').exists()


def test_full_a1_reproducibility_is_still_checked(poc, monkeypatch):
    def execute(command, log, **kwargs):
        result = poc.poc_execute(command, log, **kwargs)
        if 'ouem.standardize.building' in command and 'repeat-2' in str(log):
            output = Path(command[command.index('--output') + 1])
            source = gpd.read_file(output)
            index = source.index[source.ouem_id == 'outside-poc'][0]
            source.loc[index, 'geometry'] = translate(source.loc[index, 'geometry'], zoff=1)
            output.unlink()
            source.to_file(output, layer='building', driver='GPKG')
        return result
    monkeypatch.setattr(runner, 'execute', execute)
    assert runner.run(poc.args) == 1
    report = runner.read_json(poc.report)
    assert report['quality'] == 'PASS'
    assert report['reproducibility'] == 'FAIL'
    assert not report['comparisons']['full_a1_building']
    assert report['comparisons']['building']


def test_subset_write_refuses_existing_file(setup):
    target = setup.repo / 'subset.gpkg'
    target.write_bytes(b'protected')
    with pytest.raises(contained.PocBlocked, match='overwrite'):
        contained.write_subset(frame(), target, setup.args.reference_standard_building, {}, guard=lambda: None)
    assert target.read_bytes() == b'protected'


def test_poc_existing_run_is_not_reused(poc):
    poc.report.parent.mkdir(parents=True)
    with pytest.raises(runner.Blocked, match='exists'):
        runner.run(poc.args)
    assert not poc.commands


def test_matches_existing_diagnostic_classification(setup):
    import importlib.util
    from test_komae_integration import REAL_ROOT
    from ouem.adapters.voxcity import build_normalized_footprint, _set_normalized_footprints
    spec = importlib.util.spec_from_file_location('coverage_diagnostic', REAL_ROOT / 'scripts/work/diagnose_komae_dem_coverage.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = full_frame()
    area = load_study_area(setup.args.study_area)
    shapes = {r.ouem_id: build_normalized_footprint(r.geometry, r.ouem_id) for r in source.itertuples()}
    diagnostic = module.classify_study_intersections(_set_normalized_footprints(source, shapes), area.extent)
    _, evidence = contained.select(source, area)
    assert evidence['selected_ids'] == diagnostic['ouem_ids_by_class']['fully_within']
    assert evidence['excluded_ids'] == diagnostic['ouem_ids_by_class']['boundary_crossing']


def test_nodata_blocks_without_interpolation(poc):
    import rasterio
    from ouem.native.terrain import accept_native_terrain
    with rasterio.open(poc.raw, 'r+') as raster:
        values = raster.read(1)
        values[22, 17] = -9999
        raster.write(values, 1)
    Path(poc.args.native_terrain).unlink()
    accept_native_terrain(poc.raw, poc.args.native_terrain, provider='synthetic', source_dataset='synthetic',
        vertical_reference_status='source-declared', vertical_reference='T.P.', vertical_reference_source='fixture')
    before = runner.sha256_file(poc.raw)
    assert runner.run(poc.args) == 2
    report = runner.read_json(poc.report)
    assert report['poc_coverage']['status'] == 'BLOCKED'
    assert 'NoData' in report['poc_coverage']['reason']
    assert not poc.commands
    assert runner.sha256_file(poc.raw) == before


def test_quality_failure_remains_separate_from_repeat_equality(poc, monkeypatch):
    def execute(command, log, **kwargs):
        result = poc.poc_execute(command, log, **kwargs)
        if '--array-evidence' in command:
            path = Path(command[command.index('--report') + 1])
            evidence = runner.read_json(path)
            evidence['max_absolute_roof_error_m'] = 99.0
            write_json(path, evidence)
        return result
    monkeypatch.setattr(runner, 'execute', execute)
    assert runner.run(poc.args) == 1
    report = runner.read_json(poc.report)
    assert report['quality'] == 'FAIL'
    assert report['reproducibility'] == 'PASS'


def test_input_change_fails_and_preserves_run(poc, monkeypatch):
    def execute(command, log, **kwargs):
        result = poc.poc_execute(command, log, **kwargs)
        if 'ouem.standardize.building' in command:
            with Path(poc.args.native_building).open('ab') as stream:
                stream.write(b'simulated external writer')
        return result
    monkeypatch.setattr(runner, 'execute', execute)
    assert runner.run(poc.args) != 0
    report = runner.read_json(poc.report)
    assert report['status'] == 'FAILED'
    assert not report['input_integrity']['native_building']
    assert (poc.report.parent / 'logs/repeat-1-a1.log').exists()


def test_windows_launcher_requires_run_id_before_processing():
    import os
    import subprocess
    from test_komae_integration import REAL_ROOT
    launcher = REAL_ROOT / 'scripts/work/run_komae_contained_poc.cmd'
    text = launcher.read_text(encoding='utf-8')
    assert '--contained-poc' in text and '--expected-buildings 92' in text
    assert 'exit /b %ERRORLEVEL%' in text
    if os.name == 'nt':
        result = subprocess.run(['cmd', '/d', '/c', str(launcher)], capture_output=True, timeout=10)
        assert result.returncode == 2
        assert b'Usage:' in result.stdout
