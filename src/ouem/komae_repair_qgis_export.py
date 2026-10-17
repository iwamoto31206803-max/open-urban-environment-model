"""Export PR #42 Candidate A for QGIS inspection; never alter E2E evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

from ouem.adapters import voxcity as adapter
from ouem import komae_crs_repair_evaluation as evaluation
from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner


def _hash_geometry(geometry):
    return hashlib.sha256(geometry.wkb).hexdigest()


def _checked_parts(geometry, identifier):
    """Retain every Candidate A component; never silently discard lines."""
    provenance.require(geometry.is_valid and not geometry.is_empty and not geometry.has_z and
                       geometry.geom_type in ('Polygon', 'MultiPolygon'),
                       f'{identifier}: Candidate A is not a valid 2D Polygon/MultiPolygon')
    parts = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    provenance.require(all(part.is_valid and not part.is_empty and part.area > 0 for part in parts),
                       f'{identifier}: Candidate A has an empty/invalid component')
    return parts


def _one_repeat(evidence, number, identifier, evaluated):
    import geopandas as gpd
    from shapely.geometry import mapping, shape
    command = provenance.command(evidence.report, number, 'a3')
    building = evidence.artifact(command[2])
    output = evidence.artifact(provenance.option(command, '--adapter-output'))
    building_manifest, manifest = evidence.manifest(building), evidence.manifest(output)
    provenance.require(building_manifest.get('schema') == 'ouem-standard-building-manifest/v0.1' and
                       manifest.get('schema') == adapter.SCHEMA, 'unexpected source manifest schema')
    for record, path in ((manifest['inputs']['standard_building'], building), (manifest['output'], output)):
        provenance.require(evidence.artifact(record['path']) == path, 'manifest lineage mismatch')
        evidence.protect(path, record)
    document = evidence.document(output)
    provenance.require(document.get('crs', {}).get('properties', {}).get('name') ==
                       'urn:ogc:def:crs:EPSG::4326', 'saved Adapter CRS differs from EPSG:4326')
    features = [f for f in document['features'] if f['properties']['ouem_id'] == identifier]
    provenance.require(len(features) == 1, 'target feature is not unique in saved Adapter')
    properties = features[0]['properties']
    original = shape(features[0]['geometry'])
    frame = gpd.read_file(building, layer='building')
    provenance.require(frame.crs is not None and frame.crs.to_epsg() == 6677,
                       'saved Standard CRS differs from EPSG:6677')
    matches = frame.loc[frame.ouem_id == identifier]
    provenance.require(len(matches) == 1, 'target feature is not unique in saved Standard')
    reference, _ = adapter.build_normalized_footprint(matches.geometry.iloc[0], identifier)
    entry = next((r for r in evaluated['candidates']['A_make_valid']['buildings']
                  if r['ouem_id'] == identifier), None)
    provenance.require(evaluated['baseline_status'] == 'REPRODUCED' and entry is not None and
                       'error' not in entry and
                       evaluated['baseline_parity'][identifier]['saved_geometry_equal'] and
                       all(v['equal'] for v in evaluated['baseline_parity'][identifier]['manifest_fields'].values()),
                       'PR #42 baseline replay/manifest parity failed')
    provenance.require(not original.is_valid, 'target saved Adapter geometry is already valid')
    kind, parameter = evaluation.CANDIDATES['A_make_valid']
    repaired, operation = evaluation.candidate_geometry(reference, original, kind, parameter)
    # Same JSON numeric roundtrip as PR #42 evaluate_frame, before comparison/export.
    repaired = shape(json.loads(adapter.canonical_json(mapping(repaired))))
    provenance.require(_hash_geometry(repaired) == entry['geometry']['wkb_sha256'] and
                       repaired.geom_type == entry['geometry']['geometry_type'] and
                       repaired.is_valid == entry['geometry']['is_valid'],
                       'Candidate A differs from PR #42 evaluation for this repeat')
    provenance.require(entry['screening'] != 'REJECTED', 'PR #42 Candidate A rejected the target')
    parts = _checked_parts(repaired, identifier)
    provenance.require(evaluated['candidates']['A_make_valid']['ids_and_attributes_preserved'],
                       'PR #42 candidate did not preserve attributes')
    return {'repeat': number, 'original': original, 'repaired': repaired, 'parts': parts,
            'properties': properties, 'operation': operation, 'source_building': str(building),
            'source_adapter': str(output), 'candidate_a_sha256': _hash_geometry(repaired),
            'pr42_candidate_features_sha256': evaluated['candidates']['A_make_valid']['candidate_features_sha256']}


def _verify_all_sources(evidence, evaluated):
    """Recheck every PR #42 input, including all 92-building run evidence."""
    for path, record in evaluated['inputs'].items():
        evidence.protect(path, record)
    return evidence.finish()


def _inspect(one, identifier):
    from shapely.geometry import Point
    original, repaired, parts = one['original'], one['repaired'], one['parts']
    location = provenance.validity(original)['self_intersection_location']
    point = Point(location[:2]) if location and len(location) >= 2 and all(math.isfinite(v) for v in location[:2]) else None
    metric_parts = [provenance.reproject_xy(part, 4326, 6677) for part in parts]
    areas = [part.area for part in metric_parts]
    total = sum(areas)
    provenance.require(math.isfinite(total) and total > 0, 'Candidate A metric area is unavailable')
    metric_point = provenance.reproject_xy(point, 4326, 6677) if point else None
    rows = [{'part_index': index, 'ouem_id': identifier,
             'is_valid': bool(part.is_valid), 'geometry_type': part.geom_type,
             'area_m2': area, 'area_share_percent': area / total * 100,
             'vertex_count': provenance.counts(part)['vertices'],
             'distance_to_intersection_m': metric_part.distance(metric_point) if metric_point else None,
             'wkb_sha256': _hash_geometry(part)}
            for index, (part, metric_part, area) in enumerate(zip(parts, metric_parts, areas), 1)]
    return rows, point


def _guard_output(base, directory, identity):
    for path in (base, *base.parents, directory):
        runner.check_links(path)
    info = directory.stat()
    if not directory.is_dir() or (info.st_dev, info.st_ino) != identity or directory.resolve() != directory:
        raise runner.Blocked('diagnostic directory identity changed')
    for child in directory.iterdir():
        runner.check_links(child)


def _new_directory(base, source_root, run_id):
    base, source_root = Path(base).absolute(), Path(source_root).absolute()
    if '..' in base.parts or base == source_root or base.is_relative_to(source_root) or source_root.is_relative_to(base):
        raise runner.Blocked('diagnostic output must be separate from the integration run')
    for path in (base, *base.parents):
        runner.check_links(path)
        if path.exists() and not path.is_dir():
            raise runner.Blocked(f'output ancestor is not a directory: {path}')
    base.mkdir(parents=True, exist_ok=True)
    runner.check_links(base)
    directory = base / f'{run_id}-{uuid.uuid4().hex}'
    directory.mkdir(exist_ok=False)
    info = directory.stat()
    return directory, (info.st_dev, info.st_ino)


def _row(properties, geometry, **extras):
    # The canonical JSON column retains *all* original attributes, including
    # nested values; QGIS also gets the main ID/height fields as scalar columns.
    result = {key: properties.get(key) for key in ('ouem_id', 'id', 'voxcity_id', 'height', 'min_height')}
    result['properties_json'] = adapter.canonical_json(properties).decode('utf-8').rstrip('\n')
    return {**result, **extras, 'geometry': geometry}


def _write_gpkg(directory, identity, one, part_rows, point):
    import geopandas as gpd
    path = directory / 'candidate-a-inspection.gpkg'
    properties = one['properties']
    original, repaired = one['original'], one['repaired']
    layers = [
        ('adapter_before', [_row(properties, original,
                                 is_valid=bool(original.is_valid), validity_reason=provenance.validity(original)['validity_reason'])]),
        ('candidate_a', [_row(properties, repaired, is_valid=bool(repaired.is_valid),
                              candidate='A_make_valid')]),
        ('candidate_a_parts', [_row(properties, part, **{key: value for key, value in row.items() if key != 'ouem_id'})
                               for part, row in zip(one['parts'], part_rows)]),
    ]
    if point is not None:
        layers.append(('self_intersection', [_row(properties, point,
                                                   location_source='GEOS validity reason; approximate')]))
    expected = []
    for index, (name, records) in enumerate(layers):
        _guard_output(directory.parent, directory, identity)
        if index == 0:
            provenance.require(not os.path.lexists(path), 'diagnostic GeoPackage already exists')
        else:
            current = path.stat()
            provenance.require((current.st_dev, current.st_ino) == gpkg_identity,
                               'diagnostic GeoPackage identity changed')
        frame = gpd.GeoDataFrame(records, geometry='geometry', crs=4326)
        frame.to_file(path, layer=name, driver='GPKG', mode='w' if index == 0 else 'a')
        current = path.stat()
        if index == 0:
            gpkg_identity = (current.st_dev, current.st_ino)
        provenance.require((current.st_dev, current.st_ino) == gpkg_identity,
                           'diagnostic GeoPackage identity changed during writing')
        loaded = gpd.read_file(path, layer=name)
        provenance.require(loaded.crs is not None and loaded.crs.to_epsg() == 4326 and
                           len(loaded) == len(records), f'{name}: GeoPackage readback count/CRS mismatch')
        for saved, source in zip(loaded.itertuples(index=False), records):
            provenance.require(saved.geometry.wkb == source['geometry'].wkb and
                               json.loads(saved.properties_json) == properties and
                               saved.ouem_id == properties['ouem_id'] and
                               saved.id == properties['id'] and saved.voxcity_id == properties['voxcity_id'],
                               f'{name}: GeoPackage readback geometry/attributes differ')
            if name == 'candidate_a_parts':
                provenance.require(saved.part_index == source['part_index'] and
                                   saved.area_m2 == source['area_m2'] and
                                   saved.area_share_percent == source['area_share_percent'] and
                                   saved.vertex_count == source['vertex_count'],
                                   'GeoPackage part metrics differ on readback')
        expected.append({'layer': name, 'features': len(records),
                         'geometry_sha256': [_hash_geometry(r['geometry']) for r in records]})
    return path, expected


def export_run(root, output_base, identifier=provenance.DEFAULT_ID):
    """Verify both saved repeats and PR #42 first; only then make a new output."""
    import geopandas as gpd
    import shapely
    import pyproj
    root = Path(root).absolute()
    evaluated = evaluation.diagnose_run(root, identifier)
    provenance.require(len(evaluated['repeats']) == 2 and
                       all(r['baseline_status'] == 'REPRODUCED' for r in evaluated['repeats']),
                       'PR #42 did not reproduce both saved baselines')
    evidence = provenance.Evidence(root)
    repeats = [_one_repeat(evidence, number, identifier, evaluated['repeats'][number-1]) for number in (1, 2)]
    left, right = repeats
    provenance.require(left['original'].wkb == right['original'].wkb and
                       left['repaired'].wkb == right['repaired'].wkb and
                       adapter.canonical_json(left['properties']) == adapter.canonical_json(right['properties']) and
                       left['pr42_candidate_features_sha256'] == right['pr42_candidate_features_sha256'],
                       'Repeat 1/2 Adapter, Candidate A, attributes or PR #42 content differ')
    rows, point = _inspect(left, identifier)
    provenance.require(_verify_all_sources(evidence, evaluated) and all(evaluated['input_integrity'].values()),
                       'source SHA-256 verification failed before export')
    directory, identity = _new_directory(output_base, root, root.name)
    try:
        gpkg, layers = _write_gpkg(directory, identity, left, rows, point)
        integrity = _verify_all_sources(evidence, evaluated)
        provenance.require(all(integrity.values()), 'source SHA-256 verification failed after export')
        _guard_output(directory.parent, directory, identity)
        report = {'schema': 'ouem-candidate-a-qgis-inspection/v0.1',
                  'status': 'EXPORTED_FOR_INSPECTION_NOT_ACCEPTANCE',
                  'run_id': evidence.report['run_id'], 'ouem_id': identifier,
                  'candidate': 'A_make_valid', 'operation': left['operation'],
                  'gpkg': str(gpkg), 'gpkg_sha256': runner.sha256_file(gpkg), 'layers': layers,
                  'part_count': len(rows), 'parts': rows,
                  'self_intersection_location_epsg4326': list(point.coords[0]) if point else None,
                  'repeat_comparison': {'same_adapter_geometry': True, 'same_candidate_a_geometry': True,
                                        'same_attributes': True, 'same_pr42_candidate_content': True},
                  'repeats': [{key: value for key, value in repeat.items() if key not in
                               ('original', 'repaired', 'parts', 'properties')} for repeat in repeats],
                  'source_fingerprints_before': evidence.before,
                  'source_sha256_unchanged_after': integrity,
                  'environment': {'python': sys.version, 'platform': sys.platform,
                                  'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                                  'geopandas': gpd.__version__, 'pyproj': pyproj.__version__},
                  'not_checked': ['QGIS visual inspection', 'historical PR #42 JSON, if not supplied',
                                  'E2E quality/voxels after repair', 'formal acceptance']}
        audit = directory / 'inspection.json'
        with audit.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
        _guard_output(directory.parent, directory, identity)
        provenance.require(all(_verify_all_sources(evidence, evaluated).values()),
                           'source SHA-256 verification failed at completion')
        return report
    except BaseException:
        # Keep any partial diagnostic output for investigation; never touch E2E files.
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('ouem_id', nargs='?', default=provenance.DEFAULT_ID)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.run_id) or args.run_id in ('.', '..'):
        parser.error('run ID must be one directory name')
    try:
        report = export_run(runner.REPOSITORY / 'data/work/integration' / args.run_id,
                            runner.REPOSITORY / 'data/work/diagnostics/adapter-repair', args.ouem_id)
        print(f"QGIS GeoPackage: {report['gpkg']}")
        print(f"Candidate A: {report['part_count']} Polygon part(s); EPSG:6677 areas:")
        for row in report['parts']:
            print(f"  part {row['part_index']}: {row['area_m2']:.9f} m² ({row['area_share_percent']:.9f}%)")
        print(f"Audit: {Path(report['gpkg']).with_name('inspection.json')}")
        print('Repeat 1/2 and source SHA-256: MATCH. Diagnostic output only; acceptance pending.')
        return 0
    except Exception as exc:
        print(f'BLOCKED: {type(exc).__name__}: {exc}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
