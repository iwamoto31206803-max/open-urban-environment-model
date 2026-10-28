"""Opt-in, bounded Komae 2025 source-H experiment; no engine or acceptance."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping

from ouem.native.building.provenance import SOURCE_H_PROFILE, NATIVE_SCHEMA, CONVERTER_SCHEMA, REPOSITORY
from ouem.native.building.source_h import ingest_source_h
from ouem.native.building.source_h_geometry import require
from ouem.standardize.building.source_h import digest, standardize_source_h
from ouem.standardize.building.source_h_geometry import points, as_shape
from ouem.consumers.source_h_standard import validate_source_h_standard
from ouem.consumers._source_h_geometry import read_standard

CLI_SHA = '0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b'
MEMBERS = ('53393456_bldg_6697_op.gml', '53393466_bldg_6697_op.gml')


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def distribution(values):
    values = np.asarray(values, dtype=float)
    require(values.size and np.isfinite(values).all(), 'statistics', 'finite samples required')
    return dict(zip(('min', 'p05', 'median', 'p95', 'max'), map(float, np.percentile(values, [0, 5, 50, 95, 100]))))


def compare_terrain(standard, terrain):
    """Diagnostic all-touched XY surface cells, not an adapter ground estimate."""
    meta = json.loads(terrain.with_suffix('.tif.manifest.json').read_text(encoding='utf-8'))
    require(meta['standard']['sha256'] == digest(terrain), 'Terrain.hash', 'manifest mismatch')
    require(meta['vertical_reference']['status'] in ('source-declared', 'verified')
            and meta['vertical_reference']['name'] == 'T.P. (Tokyo Peil / Tokyo Bay mean sea level)',
            'Terrain.vertical', 'explicit compatible source declaration required')
    rows, heights = [], []
    with rasterio.open(terrain) as dem:
        require(dem.crs.to_epsg() == 6677 and dem.count == 1, 'Terrain', 'EPSG:6677 single band required')
        grid = dem.read(1, masked=True)
        for identifier, (tree, lod, measured) in read_standard(standard, 'building').items():
            xyz = points(tree)
            h = [p[2] for p in xyz]
            heights.extend(h)
            footprint = as_shape(tree)
            mask = geometry_mask([mapping(footprint)], grid.shape, dem.transform, invert=True, all_touched=True)
            ground = grid[mask].compressed()
            require(ground.size and np.isfinite(ground).all(), identifier, 'no finite DEM overlap')
            bounds = footprint.bounds
            complete = (bounds[0] >= dem.bounds.left and bounds[1] >= dem.bounds.bottom
                        and bounds[2] <= dem.bounds.right and bounds[3] <= dem.bounds.top)
            require(not np.ma.getmaskarray(grid)[mask].any(), identifier, 'NoData in DEM overlap')
            row = dict(source_id=identifier, vertices=len(h), h_min=min(h), h_max=max(h),
                       geometry_height=max(h)-min(h), measured_height=measured,
                       dem_cells=int(ground.size), dem=distribution(ground), complete_coverage=complete,
                       top_minus_dem_mean=max(h)-float(ground.mean()),
                       bottom_minus_dem_mean=min(h)-float(ground.mean()))
            row['flags'] = (['PARTIAL_DEM_COVERAGE'] if not complete else [])
            if max(h) <= float(ground.min()): row['flags'].append('TOP_BELOW_DEM')
            if abs(row['bottom_minus_dem_mean']) > 3: row['flags'].append('BOTTOM_OFFSET_OVER_3M')
            rows.append(row)
        return dict(method='All-touched XY surface intersections within existing DEM; no repair/resampling/Z adjustment. Boundary buildings retain full geometry; incomplete DEM coverage flagged.',
                    thresholds='3m bottom offset is an exploratory review flag, not an acceptance tolerance.',
                    vertical_semantics='Source-declared EPSG:6695 H versus source-declared Tokyo T.P.; numerical comparison does not verify datum realization or survey accuracy.',
                    terrain_sha256=digest(terrain), terrain_manifest_sha256=digest(terrain.with_suffix('.tif.manifest.json')),
                    building_h=distribution(heights), dem=distribution(grid.compressed()),
                    top_minus_dem_mean=distribution([r['top_minus_dem_mean'] for r in rows]),
                    buildings=rows)


def run(args):
    root = args.artifact_root.resolve(strict=True)
    run_dir = args.run_dir.resolve()
    require(run_dir.is_relative_to(root), 'run_dir', 'must be inside artifact root')
    require(digest(args.converter) == CLI_SHA, 'Converter', 'fixed binary SHA mismatch')
    run_dir.mkdir()  # new run only; no overwrite/resume
    report = dict(status='RUNNING', python=sys.version, platform=platform.platform(),
                  started_at=datetime.now(timezone.utc).isoformat(), source_h_eligibility='NOT_ESTABLISHED',
                  formal_acceptance='NOT_VERIFIED', phase5_gates='UNCHANGED')
    report['implementation_sha256'] = {str(p): digest(p) for p in (
        Path(__file__), Path(__file__).parent/'native/building/source_h_lod2.py')}
    protected = [args.zip, args.converter, args.terrain, args.terrain.with_suffix('.tif.manifest.json'), args.study_area]
    before = {str(p): digest(p) for p in protected}
    try:
        extracted = run_dir/'extracted'
        extracted.mkdir()
        raw = []
        archive_members = []
        with zipfile.ZipFile(args.zip) as archive:
            for name in archive.namelist():
                if not name.endswith('/') and (Path(name).name in MEMBERS or name.startswith('codelists/')):
                    target = (extracted/name).resolve()
                    require(target.is_relative_to(extracted), 'ZIP', 'unsafe member path')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(name) as source, target.open('xb') as dest:
                        while chunk := source.read(1024*1024): dest.write(chunk)
                    if Path(name).name in MEMBERS:
                        raw.append(target)
                        archive_members.append(dict(member=name, sha256=digest(target)))
        raw.sort()
        require(len(raw) == 2 and {p.name for p in raw} == set(MEMBERS), 'ZIP', 'exact target members required')
        output = run_dir/'converter.gpkg'
        argv = [str(args.converter.resolve()), *map(str, raw), '--sink', 'gpkg', '--output', str(output), '--epsg', '6697', '-t', 'use_lod=lod2']
        with (run_dir/'converter.stdout.log').open('xb') as out, (run_dir/'converter.stderr.log').open('xb') as err:
            process = subprocess.run(argv, stdout=out, stderr=err, check=False)
        execution = dict(argv=argv, exit_code=process.returncode, started_at=report['started_at'], ended_at=datetime.now(timezone.utc).isoformat())
        write(run_dir/'converter-run.json', execution)
        require(process.returncode == 0, 'Converter', 'execution failed; see logs')
        evidence = run_dir/'source-evidence.json'
        write(evidence, dict(zip_sha256=before[str(args.zip)], members=archive_members,
                            declaration='Raw CityGML explicit EPSG:6697: latitude, longitude, gravity-related H (EPSG:6695), metres; no independent survey verification.'))
        def artifact(path, role, layer=None):
            value = dict(path=path.resolve().relative_to(root).as_posix(), role=role, size_bytes=path.stat().st_size, sha256=digest(path))
            if layer: value['layer'] = layer
            return value
        artifacts = {f'raw{i}': artifact(p, 'raw_citygml') for i, p in enumerate(raw)}
        raw_ids = list(artifacts)
        artifacts.update(cli=artifact(args.converter, 'converter_cli'), evidence=artifact(evidence, 'source_evidence'),
                         converter=artifact(output, 'converter_gpkg', 'bldg:Building'),
                         native=dict(path=(run_dir/'native/native.gpkg').relative_to(root).as_posix(), role='native_gpkg', layer='bldg:Building'))
        plan = dict(schema=NATIVE_SCHEMA, profile=SOURCE_H_PROFILE, artifacts=artifacts,
                    source_declaration=dict(srs_name='http://www.opengis.net/def/crs/EPSG/0/6697', horizontal_epsg=6668, vertical_epsg=6695, quantity='gravity_related_height', unit='metre', axes=['latitude','longitude','H'], evidence_artifact_id='evidence'),
                    coordinate_contract=dict(input_epsg=6697, horizontal_epsg=6668, vertical_epsg=6695, quantity='gravity_related_height', unit='metre', storage_axes=['longitude','latitude','H']),
                    geometry_selection=dict(requested_lod=2, split_components=False),
                    converter=dict(schema=CONVERTER_SCHEMA, repository=REPOSITORY, commit='ce7766df9788ce391b149c55df16d33082d0bc72', version='0.1.19', cli_artifact_id='cli', input_artifact_ids=raw_ids, output_artifact_id='converter', argv=argv, resolved_options=dict(sink='gpkg', epsg=6697, use_lod='lod2', split_components=False), exit_code=0, execution_status='COMPLETED'),
                    native=dict(input_artifact_id='converter', output_artifact_id='native'),
                    operations=[dict(input_artifact_ids=raw_ids, output_artifact_id='converter', horizontal_operation='latitude_longitude_to_gis_longitude_latitude', vertical_operation='identity_H', offset_m=0, geoid_model=None),
                                dict(input_artifact_ids=['converter'], output_artifact_id='native', horizontal_operation='identity_XY', vertical_operation='identity_H', offset_m=0, geoid_model=None)])
        write(run_dir/'plan.json', plan)
        report['native'] = ingest_source_h(plan, artifact_root=root)
        native_manifest = Path(report['native']['manifest']).relative_to(root)
        report['standard'] = standardize_source_h(profile=SOURCE_H_PROFILE, native_manifest=native_manifest,
            artifact_root=root, output=(run_dir/'standard/standard.gpkg').relative_to(root), study_area_config=args.study_area.resolve())
        report['consumer'] = validate_source_h_standard(report['standard']['manifest'], root, SOURCE_H_PROFILE, study_area_config=args.study_area.resolve())
        require(report['consumer']['technical_validation'] == 'PASS', 'Consumer', str(report['consumer']['issues']))
        report['terrain_comparison'] = compare_terrain(Path(report['standard']['output']), args.terrain)
        report['status'] = 'COMPLETED'
    except Exception as exc:
        report.update(status='FAILED', error=str(exc))
        raise
    finally:
        report['input_unchanged'] = before == {str(p): digest(p) for p in protected}
        if not report['input_unchanged']: report['status'] = 'FAILED'
        report['input_sha256'] = before
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        write(run_dir/'report.json', report)
        with (run_dir/'RESULTS.md').open('x', encoding='utf-8') as stream:
            consumer = report.get('consumer', {})
            stream.write(f"# Real Komae source-H experiment\n\nStatus: {report['status']}\n\n"
                         f"Standard buildings: {consumer.get('feature_count', 'NOT_COMPLETED')}; "
                         f"vertices: {consumer.get('vertex_count', 'NOT_COMPLETED')}.\n\n"
                         "See report.json for Native/Standard manifests, exact H checks and per-building Terrain diagnostics. "
                         "Source-H eligibility is NOT_ESTABLISHED; formal acceptance is NOT_VERIFIED; Phase 5 gates unchanged.\n")
    require(report['status'] == 'COMPLETED', 'run', 'input integrity failure')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact-root', 'run-dir', 'zip', 'converter', 'terrain', 'study-area'):
        parser.add_argument('--'+name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
