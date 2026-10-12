"""Read-only explanation of the unchanged integration adapter_content predicate."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re

from ouem import komae_integration as runner


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def diagnose_adapter(path, expected_ids):
    """Explain each clause without changing ordering, coercing values or repairing geometry.

    The production predicate is deliberately left unchanged and called as an
    independent parity check. Exceptions from it are reported as ERROR, not PASS.
    """
    from shapely.geometry import shape
    from shapely.validation import explain_validity
    document = runner.read_json(path)
    features = document['features']
    properties = [f['properties'] for f in features]
    ids = [p['ouem_id'] for p in properties]
    checks = {}
    def record(name, passed, **details):
        checks[name] = {'status': 'PASS' if passed else 'FAIL', **details}

    actual_crs = document.get('crs', {}).get('properties', {}).get('name')
    expected_crs = 'urn:ogc:def:crs:EPSG::4326'
    record('crs', actual_crs == expected_crs, expected=expected_crs, actual=actual_crs)
    remaining = ids.copy()
    missing = []
    for identifier in expected_ids:
        if identifier in remaining:
            remaining.remove(identifier)
        else:
            missing.append(identifier)
    mismatches = [{'position': index + 1,
                   'expected': expected_ids[index] if index < len(expected_ids) else None,
                   'actual': ids[index] if index < len(ids) else None}
                  for index in range(max(len(ids), len(expected_ids)))
                  if index >= len(ids) or index >= len(expected_ids) or ids[index] != expected_ids[index]]
    record('ouem_ids', ids == expected_ids, expected=expected_ids, actual=ids,
           missing=missing, extra=remaining, order_only=bool(mismatches and not missing and not remaining),
           position_mismatches=mismatches)
    sequence, heights, geometries = [], [], []
    observed_sequence, observed_heights, observed_geometry = [], [], []
    for index, (feature, props) in enumerate(zip(features, properties), 1):
        identity = {'position': index, 'ouem_id': props['ouem_id']}
        try:
            passed = props['id'] == props['voxcity_id'] == index
            detail = {'expected': index, 'id': props['id'], 'voxcity_id': props['voxcity_id']}
        except Exception as exc:
            passed, detail = False, {'error': f'{type(exc).__name__}: {exc}'}
        observed_sequence.append({**identity, **detail, "passed": bool(passed)})
        if not passed:
            sequence.append({**identity, **detail})
        try:
            passed = math.isfinite(props['height']) and props['height'] > 0 and props['min_height'] == 0
            detail = {'height': props['height'], 'min_height': props['min_height'],
                      'finite_height': math.isfinite(props['height']),
                      'positive_height': props['height'] > 0, 'zero_min_height': props['min_height'] == 0}
        except Exception as exc:
            passed, detail = False, {'height': props.get('height'), 'min_height': props.get('min_height'),
                                     'error': f'{type(exc).__name__}: {exc}'}
        observed_heights.append({**identity, **detail, "passed": bool(passed)})
        if not passed:
            heights.append({**identity, **detail})
        try:
            geometry = shape(feature['geometry'])
            passed = geometry.is_valid and not geometry.is_empty and not geometry.has_z and geometry.area > 0
            detail = {'valid': geometry.is_valid, 'empty': geometry.is_empty, 'has_z': geometry.has_z,
                      'area': geometry.area, 'type': geometry.geom_type,
                      'reasons': [name for name, failed in (
                          ('invalid', not geometry.is_valid), ('empty', geometry.is_empty),
                          ('has_z', geometry.has_z), ('area_not_positive', not geometry.area > 0)) if failed],
                      'validity_reason': explain_validity(geometry)}
        except Exception as exc:
            passed, detail = False, {'reasons': ['unreadable_geometry'], 'error': f'{type(exc).__name__}: {exc}'}
        observed_geometry.append({**identity, **detail, "passed": bool(passed)})
        if not passed:
            geometries.append({**identity, **detail})
    record('sequential_ids', not sequence, expected='id == voxcity_id == 1-based feature position', failures=sequence, observations=observed_sequence)
    record('heights', not heights, expected='finite height > 0 and min_height == 0', failures=heights, observations=observed_heights)
    record('geometry', not geometries, expected='valid, nonempty, no Z, area > 0', failures=geometries, observations=observed_geometry)
    aggregate = all(check['status'] == 'PASS' for check in checks.values())
    try:
        original = runner.adapter_quality(path, expected_ids)
        oracle = {'status': 'PASS' if original else 'FAIL', 'value': original}
        parity = 'PASS' if aggregate == original else 'FAIL'
    except Exception as exc:
        oracle = {'status': 'ERROR', 'error': f'{type(exc).__name__}: {exc}'}
        parity = 'NOT_CHECKED'
    return json_safe({'status': oracle['status'] if parity != 'FAIL' else 'ERROR',
                      'aggregate': aggregate, 'checks': checks, 'existing_predicate': oracle,
                      'predicate_parity': parity})


def diagnose_run(root):
    root = Path(root).absolute()
    for ancestor in (*root.parents, root):
        runner.check_links(ancestor)
    report_path = root / 'integration-report.json'
    runner.check_links(report_path)
    before = {'report': runner.fingerprint(report_path)}
    report = runner.read_json(report_path)
    if report.get('schema') != 'ouem-komae-integration/v0.1':
        raise runner.Blocked('unsupported integration report schema')
    artifacts = report['artifacts']

    def locate(recorded):
        # Resolve through the report inventory, never through guessed filenames or
        # execution of a stored command. Relative inventory keys also permit a
        # byte-identical relocated copy of a run, including Windows path records.
        matches = [(key, info) for key, info in artifacts.items()
                   if recorded in (info.get('path'), info.get('resolved_path'))]
        if len(matches) != 1:
            raise runner.Blocked(f'artifact inventory does not uniquely identify: {recorded}')
        key, info = matches[0]
        relative = Path(key)
        if relative.is_absolute() or '..' in relative.parts or '\\' in key:
            raise runner.Blocked('unsafe artifact inventory path')
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()):
            raise runner.Blocked('artifact leaves the run directory')
        for ancestor in (path, *path.parents):
            runner.check_links(ancestor)
        if path.suffix.lower() == '.gpkg' and any(os.path.lexists(str(path) + s) for s in ('-wal', '-shm', '-journal')):
            raise runner.Blocked('GeoPackage has active/recovery sidecars; close writers and review it, do not delete evidence')
        actual = runner.fingerprint(path)
        if actual['sha256'] != info['sha256'] or actual['bytes'] != info['bytes']:
            raise runner.Blocked(f'artifact differs from the recorded hash/size: {key}')
        before[key] = actual
        return path

    # This diagnostic targets the contained PoC. Its reference is itself an
    # inventoried run artifact; no accepted datasets outside the run are opened.
    reference_record = report['inputs']['poc_reference']
    reference = locate(reference_record['path'])
    if before[reference.relative_to(root).as_posix()]['sha256'] != reference_record['sha256']:
        raise runner.Blocked('PoC reference input and artifact hashes disagree')
    expected = runner.building_semantics(reference)['ids']
    if expected != report['poc_selection']['selected_ids']:
        raise runner.Blocked('PoC reference IDs differ from the recorded selection')
    results = []
    for number in (1, 2):
        stages = [s for s in report['stages'] if s['name'] == f'repeat-{number}-a3']
        repeats = [r for r in report['repeats'] if r['repeat'] == number]
        if len(stages) != 1 or len(repeats) != 1:
            raise runner.Blocked(f'missing or ambiguous A3 stage/repeat {number}')
        command = stages[0]['command']
        if not isinstance(command, list) or len(command) < 5 or command.count('--adapter-output') != 1:
            raise runner.Blocked('unsupported recorded A3 command structure')
        building = locate(command[2])  # positional Standard Building in the existing A3 CLI
        adapter = locate(command[command.index('--adapter-output') + 1])
        standard_ids = runner.building_semantics(building)['ids']
        diagnosis = diagnose_adapter(adapter, expected)
        recorded = repeats[0]['quality']['adapter_content']
        if type(recorded) is not bool:
            raise runner.Blocked('recorded adapter_content is not a boolean')
        results.append({'repeat': number, 'adapter': str(adapter), 'standard_building': str(building),
                        'standard_ids_match_reference': standard_ids == expected,
                        'standard_ids': standard_ids, 'recorded_adapter_content': recorded,
                        'recorded_parity': diagnosis['existing_predicate'].get('value') == recorded,
                        'diagnosis': diagnosis})
    integrity = runner.verify_inputs(before)
    if not all(integrity.values()):
        raise runner.Blocked('a diagnostic input changed during reading; results are not trustworthy')
    left, right = [r['diagnosis'] for r in results]
    comparable = {name: left['checks'][name] == right['checks'][name] for name in left['checks']}
    consistent = all(r['standard_ids_match_reference'] and r['recorded_parity']
                     and r['diagnosis']['predicate_parity'] == 'PASS' for r in results)
    return {'schema': 'ouem-adapter-content-diagnostic/v0.1', 'run_id': report.get('run_id'),
            'scope': 'READ_ONLY_DIAGNOSTIC_NOT_ACCEPTANCE', 'evidence_consistent': consistent,
            'repeats': results, 'comparison': {'same_diagnosis': left == right, 'conditions_equal': comparable},
            'inputs': before, 'input_integrity': integrity,
            'limitation': 'Identifies failing predicates, not the cause in adapter generation; no repair or acceptance.'}


def display(report):
    print(f"Run: {report['run_id']} | read-only adapter diagnostics")
    print(f"Evidence and recorded predicate consistency: {'PASS' if report['evidence_consistent'] else 'FAIL'}")
    for result in report['repeats']:
        diagnosis = result['diagnosis']
        print(f"\nRepeat {result['repeat']}: {diagnosis['status']} "
              f"(recorded adapter_content={result['recorded_adapter_content']}, "
              f"predicate parity={diagnosis['predicate_parity']}, recorded parity={result['recorded_parity']})")
        print(f"  Adapter: {result['adapter']}\n  Standard: {result['standard_building']}")
        print(f"  Standard IDs match PoC reference: {result['standard_ids_match_reference']}")
        for name, check in diagnosis['checks'].items():
            print(f"  {name}: {check['status']}")
            if check['status'] != 'PASS' or name == 'crs':
                print(json.dumps({k: v for k, v in check.items() if k != "observations"},
                                 indent=2, ensure_ascii=True, allow_nan=False))
            else:
                expected = check.get('expected')
                print(f"    expected={expected if not isinstance(expected, list) else str(len(expected)) + ' reference IDs in order'}; observed: all match")
        if diagnosis['existing_predicate']['status'] == 'ERROR':
            print(json.dumps(diagnosis['existing_predicate'], ensure_ascii=True))
    print('\nRepeat comparison: ' + json.dumps(report['comparison'], ensure_ascii=True))
    print('Input hashes unchanged: PASS. No stages rerun; no artifacts updated; no formal acceptance.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id', help='existing contained PoC run ID, not a path')
    parser.add_argument('--json', action='store_true', help='JSON on stdout instead of the readable report; no output file is created')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.run_id) or args.run_id in ('.', '..'):
        parser.error('run ID must be a single directory name using letters, numbers, dot, underscore or hyphen')
    try:
        report = diagnose_run(runner.REPOSITORY / 'data/work/integration' / args.run_id)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
        else:
            display(report)
        if not report['evidence_consistent']:
            return 2
        return 0 if all(r['diagnosis']['status'] == 'PASS' for r in report['repeats']) else 1
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(json.dumps({"status": "BLOCKED", "error": error}, ensure_ascii=True) if args.json else f"BLOCKED: {error}")
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
