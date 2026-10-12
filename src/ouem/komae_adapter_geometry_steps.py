"""Observe existing Adapter geometry operations in memory, without regenerating artifacts."""
from __future__ import annotations

import argparse
import inspect
import json
import re
import sys

from ouem.adapters import voxcity as adapter
from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem.komae_adapter_diagnostics import json_safe


def capture_footprint(geometry, identifier):
    """Observe actual Python call/return events; never wrap/replace Adapter or GEOS functions.

    Geometry objects are immutable. Only references and copies of input lists are
    captured while the existing function runs; metrics are calculated afterwards.
    No global monkeypatch or production instrumentation is installed.
    """
    import shapely
    from shapely.ops import unary_union
    provenance.require(sys.getprofile() is None, 'another profiler is active; cannot safely observe calls')
    functions = [(shapely.force_2d, 'geometry'), (shapely.make_valid, 'geometry'),
                 (shapely.normalize, 'geometry'), (unary_union, 'geoms')]
    watched = {inspect.unwrap(f).__code__: (f.__module__ + '.' + f.__name__, parameter)
               for f, parameter in functions}
    pending, events = {}, []

    def profiler(frame, event, value):
        if frame.f_code not in watched:
            return
        name, parameter = watched[frame.f_code]
        if event == 'call':
            argument = frame.f_locals[parameter]
            inputs = [argument] if isinstance(argument, shapely.Geometry) else list(argument)
            pending[id(frame)] = (name, inputs)
        elif event == 'return' and id(frame) in pending:
            name, inputs = pending.pop(id(frame))
            events.append({'function': name, 'inputs': inputs, 'output': value})

    output, error = None, None
    try:
        sys.setprofile(profiler)
        output = adapter.build_normalized_footprint(geometry, identifier)
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        sys.setprofile(None)
    return output, events, error


def transition(function, before, after, source_crs, target_crs, *, category, precision):
    """Describe actual operands individually, never treating a surface list as a footprint."""
    from shapely import get_precision
    result = {'function': function, 'category': category, 'precision': precision,
              'inputs': [provenance.observe(g, source_crs) for g in before],
              'output': provenance.observe(after, target_crs),
              'precision_grid_coordinate_units': {'inputs': [float(get_precision(g)) for g in before],
                                                   'output': float(get_precision(after))}}
    result['valid_to_invalid'] = bool(before and all(g.is_valid for g in before) and not after.is_valid)
    result['representation_change'] = any(g.has_z != after.has_z or g.geom_type != after.geom_type for g in before)
    # Union is many-to-one: retain individual operand evidence, not a fabricated
    # invalid MultiPolygon of overlapping input surfaces.
    result['changes_from_inputs'] = [provenance.compare((g, source_crs), (after, target_crs)) for g in before]
    return result


def verdict(steps, *, faithful, issues):
    candidates = [{'step': i + 1, 'function': step['function'], 'category': step['category']}
                  for i, step in enumerate(steps) if step['valid_to_invalid']]
    if not faithful or issues:
        classification = 'INCONCLUSIVE'
    elif not candidates:
        classification = 'NO_VALID_TO_INVALID_TRANSITION' if steps[-1]['output']['is_valid'] else 'INCONCLUSIVE'
    elif len({c['category'] for c in candidates}) > 1:
        classification = 'MULTIPLE_OPERATIONS'
    else:
        classification = candidates[0]['category']
    return {'classification': classification, 'first_valid_to_invalid': candidates[0] if candidates else None,
            'transitions': candidates,
            'scope': 'Observed current-runtime replay, gated by exact saved-geometry and manifest parity; not proof of historical runtime equivalence.'}


def replay(frame, identifier, record, saved_geometry):
    """Replay the target's geometry path only; DEM, grids and VoxCity never run."""
    from shapely.geometry import shape
    issues, steps = [], []
    mapping = adapter.numeric_id_mapping(frame.ouem_id.tolist())
    target = frame.loc[frame.ouem_id == identifier, ['ouem_id', 'geometry']].copy()
    provenance.require(len(target) == 1, 'target must identify exactly one Standard building')
    provenance.require(frame.crs is not None and frame.crs.to_epsg() == 6677, 'Standard CRS must be EPSG:6677')
    source = target.geometry.iloc[0]
    output, events, error = capture_footprint(source, identifier)
    for event in events:
        if event['output'] is None:
            issues.append(f"{event['function']} did not return geometry")
            continue
        name = event['function']
        category = 'PROJECTION_2D' if name.endswith('force_2d') else 'UNION_NORMALIZATION'
        steps.append(transition(name, event['inputs'], event['output'], frame.crs, frame.crs,
                                category=category, precision='No new precision/rounding argument; original Adapter defaults.'))
        if name.endswith('force_2d'):
            g = event['output']
            import math
            steps[-1]['projection_discarded'] = bool(g.is_empty or not math.isfinite(g.area) or g.area <= 0)
    if error:
        return {'status': 'INCONCLUSIVE', 'issues': [*issues, error], 'steps': steps,
                'verdict': verdict(steps, faithful=False, issues=[error])}
    footprint, diagnostics = output
    # Independent unobserved call verifies that instrumentation did not alter output.
    baseline, baseline_diagnostics = adapter.build_normalized_footprint(source, identifier)
    instrumentation_equal = footprint.wkb == baseline.wkb and diagnostics == baseline_diagnostics
    observed_projection_count = sum(e['function'].endswith('force_2d') for e in events)
    capture_complete = (observed_projection_count == diagnostics['source_surface_part_count'] and
                        sum(e['function'].endswith('unary_union') for e in events) == 2 and
                        any(e['function'].endswith('normalize') for e in events))
    if not capture_complete:
        issues.append('incomplete/unsupported footprint operation capture')
    if not instrumentation_equal:
        issues.append('instrumented/uninstrumented footprint differs')

    recorded = record.get('footprint', {})
    manifest_comparison = {key: {'recorded': recorded.get(key), 'replayed': value,
                                 'equal': key in recorded and recorded[key] == value}
                           for key, value in diagnostics.items()}
    manifest_equal = all(value['equal'] for value in manifest_comparison.values())
    if not manifest_equal:
        issues.append('saved footprint diagnostics differ or are missing (exact comparison, including area)')

    assigned = adapter._set_normalized_footprints(target, {identifier: output})
    steps.append(transition('ouem.adapters.voxcity._set_normalized_footprints', [footprint], assigned.geometry.iloc[0],
                            frame.crs, assigned.crs, category='FOOTPRINT_ASSIGNMENT', precision='No rounding.'))
    assigned['voxcity_id'] = assigned.ouem_id.map(mapping)
    assigned['id'] = assigned.voxcity_id
    assigned['min_height'] = 0.0
    # Saved grid-derived scalar, not a recalculated height. It cannot change geometry.
    assigned['height'] = record['height']
    transformed = adapter._to_voxcity_building_crs(assigned)
    steps.append(transition('ouem.adapters.voxcity._to_voxcity_building_crs / GeoDataFrame.to_crs(4326)',
                            [assigned.geometry.iloc[0]], transformed.geometry.iloc[0], assigned.crs, transformed.crs,
                            category='CRS_TRANSFORMATION', precision='GeoPandas/PROJ double precision; no explicit rounding.'))
    feature = next(transformed.iterfeatures(drop_id=True))
    feature_geometry = shape(feature['geometry'])
    steps.append(transition('GeoDataFrame.iterfeatures(drop_id=True)', [transformed.geometry.iloc[0]], feature_geometry,
                            transformed.crs, transformed.crs, category='GEOJSON_FEATURE', precision='No precision argument.'))
    collection = json.loads(transformed.to_json(drop_id=True))
    json_geometry = shape(collection['features'][0]['geometry'])
    steps.append(transition('GeoDataFrame.to_json(drop_id=True) / json.loads', [feature_geometry], json_geometry,
                            transformed.crs, transformed.crs, category='GEOJSON_SERIALIZATION',
                            precision='Default Python JSON numeric encoding; no explicit rounding.'))
    collection['name'] = 'voxcity_buildings'
    collection['crs'] = {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:EPSG::4326'}}
    feature = collection['features'][0]
    feature['properties'].update({key: value for key, value in record.items() if key != 'footprint'})
    feature['properties'].update(adapter.interface_id_properties(identifier, mapping))
    final_document = json.loads(adapter.canonical_json(collection))
    final = shape(final_document['features'][0]['geometry'])
    steps.append(transition('ouem.adapters.voxcity.canonical_json / json.loads', [json_geometry], final,
                            transformed.crs, transformed.crs, category='GEOJSON_SERIALIZATION',
                            precision='sort_keys/separators/UTF-8 only; no explicit rounding.'))
    exact = final.wkb == saved_geometry.wkb
    final_comparison = {'exact_geometry_wkb': exact,
                        'normalized_exact': final.normalize().equals_exact(saved_geometry.normalize(), 0),
                        'changes': provenance.compare((final, transformed.crs), (saved_geometry, transformed.crs))}
    if not exact:
        issues.append('replayed final geometry does not exactly match saved Adapter; no causal conclusion')
    faithful = instrumentation_equal and capture_complete and manifest_equal and exact
    result = verdict(steps, faithful=faithful, issues=issues)
    return json_safe({'status': 'REPRODUCED' if faithful else 'INCONCLUSIVE', 'issues': issues,
        'source': provenance.observe(source, frame.crs), 'steps': steps, 'verdict': result,
        'instrumentation_equal': instrumentation_equal, 'capture_complete': capture_complete,
        'manifest_comparison': manifest_comparison, 'final_comparison': final_comparison,
        'rounding': {'status': 'NOT_APPLIED', 'reason': 'No explicit coordinate rounding in inspected production geometry path.'},
        'not_run': ['DEM processing', 'VoxCity grids/voxels', 'A1/A2/A3 E2E', 'any file writer'],
        'representation_note': 'Native/Standard 3D surface XY validity is not normalized 2D footprint validity. Discarded faces and existing conditional make_valid calls are observed, not new repairs.'})


def diagnose_run(root, identifier=provenance.DEFAULT_ID):
    import geopandas as gpd
    import pyproj
    import shapely
    from shapely.geometry import shape
    evidence = provenance.Evidence(root)
    source_path = evidence.protect(inspect.getsourcefile(adapter))
    repeats = []
    for number in (1, 2):
        try:
            command = provenance.command(evidence.report, number, 'a3')
            building = evidence.artifact(command[2])
            geojson = evidence.artifact(provenance.option(command, '--adapter-output'))
            bm, manifest = evidence.manifest(building), evidence.manifest(geojson)
            provenance.require(bm.get('schema') == 'ouem-standard-building-manifest/v0.1' and
                               manifest.get('schema') == adapter.SCHEMA, 'unsupported manifest schema')
            recorded_input = manifest['inputs']['standard_building']
            provenance.require(evidence.artifact(recorded_input['path']) == building, 'Adapter input lineage mismatch')
            evidence.protect(building, recorded_input)
            provenance.require(evidence.artifact(manifest['output']['path']) == geojson, 'Adapter output lineage mismatch')
            evidence.protect(geojson, manifest['output'])
            document = evidence.document(geojson)
            provenance.require(document.get('crs', {}).get('properties', {}).get('name') == 'urn:ogc:def:crs:EPSG::4326',
                               'saved Adapter CRS is not the production EPSG:4326 declaration')
            features = [f for f in document['features'] if f['properties']['ouem_id'] == identifier]
            records = [r for r in manifest['buildings'] if r['ouem_id'] == identifier]
            provenance.require(len(features) == len(records) == 1, 'target missing/ambiguous in Adapter or manifest')
            frame = gpd.read_file(building, layer='building')  # exact _run_voxcity_grids input layer
            result = replay(frame, identifier, records[0], shape(features[0]['geometry']))
            repeats.append({'repeat': number, 'building': str(building), 'adapter': str(geojson), 'diagnosis': result})
        except runner.Blocked:
            raise  # Integrity/path safety failures must not become a trusted replay.
        except Exception as exc:
            repeats.append({'repeat': number, 'diagnosis': {'status': 'INCONCLUSIVE',
                            'issues': [f'{type(exc).__name__}: {exc}'], 'verdict': {'classification': 'INCONCLUSIVE'}}})
    integrity = evidence.finish()
    a, b = [r['diagnosis'] for r in repeats]
    return {'schema': 'ouem-adapter-geometry-steps/v0.1', 'scope': 'READ_ONLY_DIAGNOSTIC_NOT_ACCEPTANCE',
            'run_id': evidence.report.get('run_id'), 'ouem_id': identifier, 'repeats': repeats,
            'status': 'REPRODUCED' if all(r['diagnosis']['status'] == 'REPRODUCED' for r in repeats) else 'INCONCLUSIVE',
            'comparison': {'same_diagnosis': a == b, 'same_verdict': a['verdict'] == b['verdict']},
            'inputs': evidence.before, 'input_integrity': integrity,
            'environment': {'python': sys.version, 'platform': sys.platform, 'geopandas': gpd.__version__,
                'shapely': shapely.__version__, 'geos': shapely.geos_version_string, 'pyproj': pyproj.__version__,
                'proj': pyproj.proj_version_str, 'adapter_source_sha256': evidence.before[str(source_path)]['sha256']},
            'limitations': ['Only geometry is replayed, not grid-derived scalars or whole-feature/whole-file generation.',
                           'Current-runtime parity does not establish the original runtime versions or formal acceptance.']}


def display(report):
    print(f"Run: {report['run_id']} | {report['ouem_id']} | {report['status']}")
    for repeat in report['repeats']:
        result = repeat['diagnosis']
        print(f"\nRepeat {repeat['repeat']}: {result['status']} | {result['verdict']['classification']}")
        for issue in result['issues']:
            print('  INCONCLUSIVE: ' + issue)
        for i, step in enumerate(result.get('steps', []), 1):
            out = step['output']
            print(f"  {i}. {step['function']}: valid={out['is_valid']}, {out['geometry_type']}, "
                  f"{out['crs']}, area={out['projected']['area_m2']} m2; {out['validity_reason']}"
                  + (' [VALID -> INVALID]' if step['valid_to_invalid'] else '')
                  + (' [discarded projection]' if step.get('projection_discarded') else ''))
        print('  First transition: ' + json.dumps(result['verdict'].get('first_valid_to_invalid')))
        print('  Final saved geometry comparison: ' + json.dumps(result.get('final_comparison')))
        print('  Footprint manifest: ' + json.dumps(result.get('manifest_comparison')))
    print('\nRepeat comparison: ' + json.dumps(report['comparison']))
    print('SHA-256 before/after: PASS. No artifacts written; no E2E rerun or acceptance. Full metrics: --json.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('ouem_id', nargs='?', default=provenance.DEFAULT_ID)
    parser.add_argument('--json', action='store_true', help='full JSON to stdout; no files created')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.run_id) or args.run_id in ('.', '..'):
        parser.error('run ID must be a single directory name')
    try:
        report = diagnose_run(runner.REPOSITORY / 'data/work/integration' / args.run_id, args.ouem_id)
        if args.json:
            print(json.dumps(json_safe(report), indent=2, ensure_ascii=True, allow_nan=False))
        else:
            display(report)
        if report['status'] == 'INCONCLUSIVE' or any(r['diagnosis']['verdict']['classification'] == 'INCONCLUSIVE' for r in report['repeats']):
            return 2
        return 1 if any(r['diagnosis']['verdict']['transitions'] for r in report['repeats']) else 0
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        print(json.dumps({'status': 'BLOCKED', 'error': error}, ensure_ascii=True) if args.json else f'BLOCKED: {error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
