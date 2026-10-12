"""Read-only saved-geometry provenance diagnosis; never repairs or reruns stages."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import re
import sys

from ouem import komae_integration as runner
from ouem.komae_adapter_diagnostics import json_safe
from ouem.standardize.building import ID_RULE, SOURCE_DATASET, deterministic_ouem_id

DEFAULT_ID = 'oub-21a29be1-9794-593f-b22c-e3639a7d9d45'
STAGES = ('native', 'a1_standard', 'contained_standard', 'adapter')


class Inconclusive(ValueError):
    """Missing/ambiguous lineage, distinct from altered or unsafe evidence."""


def require(condition, message):
    if not condition:
        raise Inconclusive(message)


class Evidence:
    """Resolve recorded paths, validate saved hashes, and track every opened file."""

    def __init__(self, root):
        self.root = Path(root).absolute()
        self.before = {}
        self.report = self.document(self.protect(self.root / 'integration-report.json'))
        require(self.report.get('schema') == 'ouem-komae-integration/v0.1',
                'unsupported integration report schema')

    def protect(self, path, record=None):
        path = Path(path).absolute()
        for ancestor in (path, *path.parents):
            runner.check_links(ancestor)
        if path.suffix.lower() == '.gpkg' and any(
                os.path.lexists(str(path) + suffix) for suffix in ('-wal', '-shm', '-journal')):
            raise runner.Blocked(f'active/recovery GeoPackage sidecars: {path}; close writers, preserve evidence')
        actual = runner.fingerprint(path)
        if record is not None and (actual['sha256'] != record['sha256'] or
                                   ('bytes' in record and actual['bytes'] != record['bytes'])):
            raise runner.Blocked(f'saved hash/size mismatch: {path}')
        previous = self.before.setdefault(str(path), actual)
        if previous != actual:
            raise runner.Blocked(f'input changed during diagnosis: {path}')
        return path

    def artifact(self, recorded):
        matches = [(key, info) for key, info in self.report['artifacts'].items()
                   if recorded in (info.get('path'), info.get('resolved_path'))]
        require(len(matches) == 1, f'artifact inventory does not uniquely identify {recorded}')
        key, info = matches[0]
        relative = Path(key)
        if (relative.is_absolute() or PureWindowsPath(key).drive or '..' in relative.parts
                or '\\' in key or not (self.root / relative).resolve().is_relative_to(self.root.resolve())):
            raise runner.Blocked(f'unsafe artifact inventory path: {key}')
        return self.protect(self.root / relative, info)

    def input(self, name):
        record = self.report['inputs'][name]
        # External Native is never located by a guessed filename or proximity.
        # Relocated runs still require the original recorded Native path.
        return self.protect(Path(record['path']), record)

    def manifest(self, artifact):
        # Adjacency is the repository manifest convention, not a guessed output name.
        matches = [info for key, info in self.report['artifacts'].items()
                   if self.root / key == runner.adjacent(artifact)]
        require(len(matches) == 1, f'missing inventoried adjacent manifest: {artifact}')
        return self.document(self.artifact(matches[0]['path']))

    @staticmethod
    def document(path):
        return runner.read_json(path)

    def finish(self):
        integrity = runner.verify_inputs(self.before)
        # Recheck path/link and sidecar safety as well as bytes after GDAL reads.
        for path in self.before:
            self.protect(path)
        if not all(integrity.values()):
            raise runner.Blocked('an input changed while reading; diagnosis is not trustworthy')
        return integrity


def reproject_xy(geometry, source, target):
    """Horizontal-only diagnostic projection. Preserve Z; never infer a vertical datum."""
    from pyproj import CRS, Transformer
    from shapely import transform
    transformer = Transformer.from_crs(CRS.from_user_input(source).to_2d(),
                                       CRS.from_user_input(target).to_2d(), always_xy=True)

    def xy(coordinates):
        result = coordinates.copy()
        result[:, 0], result[:, 1] = transformer.transform(
            coordinates[:, 0], coordinates[:, 1], errcheck=True)
        return result
    return transform(geometry, xy, include_z=geometry.has_z)


def counts(geometry):
    if geometry.geom_type == 'Polygon':
        rings = [geometry.exterior, *geometry.interiors]
        return {'polygons': 1, 'rings': len(rings), 'vertices': sum(len(r.coords) for r in rings)}
    if hasattr(geometry, 'geoms'):
        children = [counts(g) for g in geometry.geoms]
        return {key: sum(c[key] for c in children) for key in ('polygons', 'rings', 'vertices')}
    return {'polygons': 0, 'rings': 0, 'vertices': len(geometry.coords)}


def validity(geometry):
    from shapely.validation import explain_validity
    reason = explain_validity(geometry)
    location = None
    match = re.search(r'\[([^\]]+)\]$', reason)
    if 'self-intersection' in reason.lower() and match:
        try:
            location = [float(v) for v in match[1].split()]
        except ValueError:
            pass
    return {'is_valid': bool(geometry.is_valid), 'validity_reason': reason,
            'self_intersection_location': location}


def observe(geometry, crs):
    from pyproj import CRS
    require(geometry is not None, 'missing geometry')
    require(crs is not None, 'missing declared CRS; no CRS is inferred')
    parsed = CRS.from_user_input(crs)
    projected = reproject_xy(geometry, parsed, 'EPSG:6677')
    return json_safe({'geometry_type': geometry.geom_type, 'crs': parsed.to_string(),
                     **validity(geometry), 'is_empty': bool(geometry.is_empty),
                     'has_z': bool(geometry.has_z), 'bounds': list(geometry.bounds),
                     'area_coordinate_units_squared': geometry.area, 'counts': counts(geometry),
                     'wkb_sha256': hashlib.sha256(geometry.wkb).hexdigest(),
                     'projected': {'crs': 'EPSG:6677', 'area_m2': projected.area,
                                   'bounds': list(projected.bounds), **validity(projected)},
                     'interpretation': 'GEOS XY validity ignores Z. Raw 3D surface-assembly area is not a dissolved footprint area.'})


def compare(left, right):
    from shapely import force_2d
    a = force_2d(reproject_xy(left[0], left[1], 'EPSG:6677'))
    b = force_2d(reproject_xy(right[0], right[1], 'EPSG:6677'))
    result = {'crs': 'EPSG:6677', 'area_delta_m2': b.area - a.area,
              'same_representation': a.geom_type == b.geom_type,
              'normalized_xy_exact': a.normalize().equals_exact(b.normalize(), 0),
              'symmetric_difference': {'status': 'NOT_CHECKED', 'reason': 'requires valid, nonempty polygons; no repair permitted'}}
    if not a.is_empty and not b.is_empty:
        result['hausdorff_distance_m'] = a.hausdorff_distance(b)
    if (a.is_valid and b.is_valid and not a.is_empty and not b.is_empty
            and a.geom_type in ('Polygon', 'MultiPolygon') and b.geom_type in ('Polygon', 'MultiPolygon')):
        result['symmetric_difference'] = {'status': 'CHECKED', 'area_m2': a.symmetric_difference(b).area}
    return json_safe(result)


def read_feature(path, layer, field, identifier, *, native=False):
    import geopandas as gpd
    require(isinstance(layer, str) and bool(layer), f'manifest lacks layer for {path}')
    frame = gpd.read_file(path, layer=layer)
    fields = [column for column in frame.columns if column.casefold() == field.casefold()] if native else [field]
    require(len(fields) == 1 and fields[0] in frame, f'missing/ambiguous {field} field: {path}')
    values = frame[fields[0]]
    if native:
        values = values.map(lambda value: str(value).strip() if value is not None else None)
    selected = frame.loc[values == identifier]
    require(len(selected) == 1, f'{field}={identifier!r} has {len(selected)} matches in {path}; no row/spatial fallback')
    row = selected.iloc[0]
    return row, (row.geometry, frame.crs)


def command(report, number, stage):
    found = [s for s in report['stages'] if s.get('name') == f'repeat-{number}-{stage}']
    require(len(found) == 1, f'missing/ambiguous repeat-{number}-{stage} command')
    value = found[0]['command']
    require(isinstance(value, list) and all(isinstance(v, str) for v in value), 'unsupported command record')
    return value


def option(command, name):
    require(command.count(name) == 1 and command.index(name) + 1 < len(command), f'missing/ambiguous {name}')
    return command[command.index(name) + 1]


def diagnose_repeat(evidence, number, identifier):
    from pyproj import CRS
    from shapely.geometry import shape
    result = {'repeat': number, 'stages': {}, 'lineage': {}, 'comparisons': {}, 'issues': []}
    geometries = {}

    def save(stage, path, geometry):
        geometries[stage] = geometry
        result['stages'][stage] = {'path': str(path), **observe(*geometry)}

    try:
        a1 = command(evidence.report, number, 'a1')
        a3 = command(evidence.report, number, 'a3')
        require(len(a1) > 3 and a1[1:3] == ['-m', 'ouem.standardize.building'], 'unsupported A1 command')
        require(len(a3) > 3, 'unsupported A3 command')
        full = evidence.artifact(option(a1, '--output'))
        subset = evidence.artifact(a3[2])
        adapter = evidence.artifact(option(a3, '--adapter-output'))
        full_manifest = evidence.manifest(full)
        subset_manifest = evidence.manifest(subset)
        adapter_manifest = evidence.manifest(adapter)
        require(full_manifest.get('schema') == subset_manifest.get('schema') == 'ouem-standard-building-manifest/v0.1',
                'unsupported Standard manifest schema')
        require(adapter_manifest.get('schema') == 'ouem-standard-to-voxcity-building-adapter/v0.1',
                'unsupported Adapter manifest schema')
        layer = full_manifest['validation']['output_layer']
        full_row, full_geometry = read_feature(full, layer, 'ouem_id', identifier)
        save('a1_standard', full, full_geometry)
        subset_row, subset_geometry = read_feature(subset, layer, 'ouem_id', identifier)
        save('contained_standard', subset, subset_geometry)
        document = evidence.document(adapter)
        features = [f for f in document['features'] if f.get('properties', {}).get('ouem_id') == identifier]
        require(len(features) == 1, 'missing/duplicate target OUEM ID in Adapter')
        adapter_crs = document.get('crs', {}).get('properties', {}).get('name')
        save('adapter', adapter, (shape(features[0]['geometry']), adapter_crs))

        parent = subset_manifest['parent']
        require(evidence.artifact(parent['building']['path']) == full, 'subset parent is not recorded A1 output')
        evidence.protect(full, parent['building'])
        require(evidence.artifact(parent['manifest']['path']) == runner.adjacent(full), 'subset parent manifest differs')
        evidence.protect(runner.adjacent(full), parent['manifest'])
        require(evidence.artifact(full_manifest['standard_output']) == full and
                evidence.artifact(subset_manifest['standard_output']) == subset, 'Standard output lineage mismatch')
        require(identifier in subset_manifest['selection']['selected_ids'], 'target not in recorded subset selection')
        require(full_row['source_id'] == subset_row['source_id'] and
                full_row['source_dataset'] == subset_row['source_dataset'] == SOURCE_DATASET,
                'full/subset source metadata mismatch')
        require(CRS.from_user_input(full_geometry[1]) == CRS.from_user_input(subset_geometry[1]) and
                full_geometry[0].normalize().wkb == subset_geometry[0].normalize().wkb,
                'subset changed the selected A1 geometry/CRS')
        result['lineage']['subset_preserves_a1_geometry_and_source'] = True
        adapter_input = adapter_manifest['inputs']['standard_building']
        require(evidence.artifact(adapter_input['path']) == subset, 'Adapter input is not the recorded subset')
        evidence.protect(subset, adapter_input)
        require(evidence.artifact(adapter_manifest['output']['path']) == adapter, 'Adapter output lineage mismatch')
        evidence.protect(adapter, adapter_manifest['output'])
        records = [b for b in adapter_manifest['buildings'] if b['ouem_id'] == identifier]
        require(len(records) == 1, 'missing/ambiguous target in Adapter manifest')
        result['recorded_footprint_diagnostics'] = records[0].get('footprint')
        result['recorded_footprint_note'] = 'Saved manifest observations only; normalized geometry is not reconstructed or repaired.'

        require(full_manifest.get('metadata_mapping', {}).get('source_id') == 'Native Building id' and
                full_manifest.get('ouem_id_rule') == ID_RULE and full_manifest.get('source_dataset') == SOURCE_DATASET,
                'missing/unsupported source_id mapping or deterministic OUEM ID rule')
        source_id = full_row['source_id']
        require(isinstance(source_id, str) and bool(source_id.strip()) and deterministic_ouem_id(source_id) == identifier,
                'source_id does not reproduce target OUEM ID')
        native_record = evidence.report['inputs']['native_building']
        require(full_manifest['native_input'] in (native_record['path'], native_record.get('resolved_path')) and
                a1[3] in (native_record['path'], native_record.get('resolved_path')), 'Native input path lineage mismatch')
        native = evidence.input('native_building')
        native_manifest_path = evidence.input('native_building_manifest')
        require(native_manifest_path == runner.adjacent(native), 'Native manifest is not adjacent to recorded Native')
        native_manifest = evidence.document(native_manifest_path)
        require(native_manifest.get('schema') == 'ouem-plateau-native-ingest/v0.1', 'unsupported Native manifest schema')
        require(native_manifest['native_output'] in (native_record['path'], native_record.get('resolved_path')),
                'Native manifest output differs from recorded input')
        native_layer = native_manifest['parameters']['output_layer']
        require(native_layer == full_manifest['validation']['input_layer'], 'Native/A1 layer lineage mismatch')
        _, native_geometry = read_feature(native, native_layer, 'id', source_id, native=True)
        save('native', native, native_geometry)
        result['lineage'].update(source_id=source_id, ouem_id=identifier, native_id_field='id (case-insensitive)',
                                 deterministic_id_verified=True, native_layer=native_layer)
    except (KeyError, IndexError, ValueError, TypeError, OSError) as exc:
        # Hash/link safety failures are Blocked (RuntimeError) and propagate.
        result['issues'].append(f'{type(exc).__name__}: {exc}')

    for left, right in zip(STAGES, STAGES[1:]):
        if left in geometries and right in geometries:
            try:
                result['comparisons'][f'{left}_to_{right}'] = compare(geometries[left], geometries[right])
            except Exception as exc:
                result['comparisons'][f'{left}_to_{right}'] = {'status': 'NOT_CHECKED', 'reason': str(exc)}
    if 'contained_standard' in geometries and 'adapter' in geometries:
        try:
            standard, source = geometries['contained_standard']
            adapter_geometry, target = geometries['adapter']
            probe = reproject_xy(standard, source, target)
            from shapely import force_2d
            result['crs_probe'] = {**validity(probe), 'source_crs': str(source), 'target_crs': str(target),
                'xy_exactly_matches_adapter': force_2d(probe).normalize().equals_exact(force_2d(adapter_geometry).normalize(), 0),
                'limitation': 'XY-only projection of raw Standard; no footprint normalization or rounding. Not a reconstruction of Adapter generation.'}
            result['crs_probe']['projection_reproduces_invalid_adapter'] = bool(
                standard.is_valid and not probe.is_valid and not adapter_geometry.is_valid
                and result['crs_probe']['xy_exactly_matches_adapter'])
        except Exception as exc:
            result['crs_probe'] = {'status': 'NOT_CHECKED', 'reason': str(exc)}

    complete = not result['issues'] and all(stage in result['stages'] for stage in STAGES)
    invalid = [stage for stage in STAGES if stage in result['stages'] and not result['stages'][stage]['is_valid']]
    result['first_invalid_saved_stage'] = invalid[0] if complete and invalid else ('NONE' if complete else 'INCONCLUSIVE')
    result['observed_invalid_stages'] = invalid
    result['classification'] = ('INCONCLUSIVE' if not complete else {
        'native': 'NATIVE_ALREADY_INVALID', 'a1_standard': 'NATIVE_TO_STANDARD',
        'contained_standard': 'A1_TO_CONTAINED', 'adapter': 'STANDARD_TO_ADAPTER', 'NONE': 'ALL_SAVED_GEOMETRIES_VALID'
    }[result['first_invalid_saved_stage']])
    result['causal_mechanism'] = {'status': 'INCONCLUSIVE' if invalid or not complete else 'NOT_APPLICABLE',
        'reasons': ['Saved-stage validity locates an observed interval, not proof of the same self-intersection propagating.',
                    '3D surface assemblies and dissolved 2D footprints differ; GEOS validity ignores Z.',
                    'Normalized pre-reprojection geometry and pre/post-rounding coordinate snapshots are not available; CRS/rounding causality is not established.']}
    return result


def diagnose_run(root, identifier=DEFAULT_ID):
    import pyproj
    import shapely
    evidence = Evidence(root)
    results = [diagnose_repeat(evidence, number, identifier) for number in (1, 2)]
    integrity = evidence.finish()
    def comparable(result):
        return {key: value for key, value in result.items() if key != 'repeat' and key != 'stages'} | {
            'stages': {stage: {k: v for k, v in details.items() if k != 'path'}
                       for stage, details in result['stages'].items()}}
    comparison = {'same_diagnosis': comparable(results[0]) == comparable(results[1]),
                  'same_classification': results[0]['classification'] == results[1]['classification'],
                  'same_stage_geometry': {stage: results[0]['stages'][stage]['wkb_sha256'] == results[1]['stages'][stage]['wkb_sha256']
                                         for stage in STAGES if all(stage in r['stages'] for r in results)}}
    return json_safe({'schema': 'ouem-geometry-provenance-diagnostic/v0.1',
        'scope': 'READ_ONLY_DIAGNOSTIC_NOT_ACCEPTANCE', 'run_id': evidence.report.get('run_id'), 'ouem_id': identifier,
        'diagnostic_environment': {'python': platform.python_version(), 'platform': sys.platform,
            'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
            'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str},
        'status': 'INCONCLUSIVE' if any(r['classification'] == 'INCONCLUSIVE' for r in results) else 'DIAGNOSED',
        'repeats': results, 'comparison': comparison, 'inputs': evidence.before, 'input_integrity': integrity,
        'limitations': ['No repair, footprint union, coordinate rounding, generation, or acceptance is performed.',
                        'All coordinate transformations are horizontal-only in memory; original Z is retained, not datum-converted.',
                        'Only the targeted building and its discovered lineage are inspected; this is not a full run validation.']})


def display(report):
    print(f"Run: {report['run_id']} | OUEM ID: {report['ouem_id']} | {report['status']}")
    for result in report['repeats']:
        print(f"\nRepeat {result['repeat']}: {result['classification']}; first invalid saved stage: {result['first_invalid_saved_stage']}")
        for stage in STAGES:
            detail = result['stages'].get(stage)
            if detail:
                print(f"  {stage}: {detail['geometry_type']} {detail['crs']} valid={detail['is_valid']} Z={detail['has_z']} "
                      f"area6677={detail['projected']['area_m2']} m2 | {detail['validity_reason']}\n    {detail['path']}")
        print('  Lineage: ' + json.dumps(result['lineage'], ensure_ascii=True))
        for issue in result['issues']:
            print('  Missing/conflicting evidence: ' + issue)
        print('  Shape differences: ' + json.dumps(result['comparisons'], ensure_ascii=True))
        print('  CRS probe: ' + json.dumps(result.get('crs_probe'), ensure_ascii=True))
        print('  Recorded footprint (not recomputed): ' + json.dumps(result.get('recorded_footprint_diagnostics'), ensure_ascii=True))
        print('  Causal mechanism: ' + json.dumps(result['causal_mechanism'], ensure_ascii=True))
    print('\nRepeat comparison: ' + json.dumps(report['comparison'], ensure_ascii=True))
    print('SHA-256 before/after: PASS. Read-only diagnosis; no rerun, repair, or formal acceptance. Full metrics: --json.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id', help='existing run ID, not a path')
    parser.add_argument('ouem_id', nargs='?', default=DEFAULT_ID)
    parser.add_argument('--json', action='store_true', help='JSON to stdout; no file is created')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.run_id) or args.run_id in ('.', '..'):
        parser.error('run ID must be a single directory name')
    try:
        report = diagnose_run(runner.REPOSITORY / 'data/work/integration' / args.run_id, args.ouem_id)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
        else:
            display(report)
        if report['status'] == 'INCONCLUSIVE':
            return 2
        return 1 if any(r['observed_invalid_stages'] for r in report['repeats']) else 0
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        print(json.dumps({'status': 'BLOCKED', 'error': error}, ensure_ascii=True) if args.json else f'BLOCKED: {error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
