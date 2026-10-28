"""Explicit opt-in integration check with existing PR #87 artifacts, not a CI test.

No Converter execution/download, OSGeo4W or generated WKB. A real-file plan is
required; never silently substitute the synthetic unit-test plan or skip.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import struct
import sys

import shapely

from ouem.gdal_citygml_feasibility import signature, source_reference
from ouem.native.building.provenance import validate_source_h_record
from ouem.native.building.source_h import ingest_source_h
from ouem.native.building.source_h_geometry import compare_snapshots, inspect_geopackage
from ouem.native.building.source_h_lod2 import compare_lod2, read_lod2

CLI_SHA = '0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b'
CONVERTER_SHA = '00af24b34f750ef71ead24b02cf7ff395c0ac125e51449888c3a84ab309d0fce'


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def independent_geometry(path):
    """GEOS readback independent of Step 2's hand-written ISO WKB decoder."""
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)) as conn:
        rows = conn.execute('SELECT id,geometry,measuredHeight FROM "bldg:Building"').fetchall()
    result = {}
    for identifier, blob, height in rows:
        offset = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 7]
        check(struct.unpack('<i' if blob[3] & 1 else '>i', blob[4:8])[0] == 6697, 'BLOB SRID')
        geom = shapely.from_wkb(blob[offset:])
        check(geom.geom_type == 'MultiPolygon' and geom.has_z and not geom.is_empty, 'MultiPolygon Z required')
        faces = [tuple(tuple(tuple(p) for p in ring.coords) for ring in [poly.exterior, *poly.interiors])
                 for poly in geom.geoms]
        check(identifier not in result, 'duplicate ID')
        result[identifier] = {'faces': faces, 'measuredHeight': height, 'blob_sha256': hashlib.sha256(blob).hexdigest()}
    return result


def run(plan, root):
    artifacts = plan['artifacts']
    paths = {key: root / ref['path'] for key, ref in artifacts.items() if ref['role'] != 'native_gpkg'}
    before = {key: sha(path) for key, path in paths.items()}
    converter_id = plan['native']['input_artifact_id']
    cli_id = plan['converter']['cli_artifact_id']
    check(before[cli_id] == CLI_SHA, 'not the PR #87 verified CLI')
    check(before[converter_id] == CONVERTER_SHA, 'not the PR #87 original 6697 output')
    check(plan['converter']['commit'] == 'ce7766df9788ce391b149c55df16d33082d0bc72', 'Converter commit')
    raw_ids = [key for key, ref in artifacts.items() if ref['role'] == 'raw_citygml']
    check(len(raw_ids) == 1, 'this integration runner is only for the two-building fixture')
    source = paths[converter_id]
    snapshot = inspect_geopackage(source, artifacts[converter_id]['layer'])
    raw, excluded = read_lod2([paths[raw_ids[0]]])
    raw_qa = compare_lod2(snapshot, raw)
    oracle = source_reference(paths[raw_ids[0]])  # independent fixture-only XML extraction
    source_geos = independent_geometry(source)
    check(set(source_geos) == set(oracle), 'independent Raw ID mismatch')
    for identifier, actual in source_geos.items():
        check(signature(actual['faces']) == signature(oracle[identifier][2]), 'independent Raw XYZ/ring mismatch')
    result = ingest_source_h(plan, artifact_root=root)
    native = Path(result['output'])
    final = json.loads(Path(result['manifest']).read_text(encoding='utf-8'))
    receipt = json.loads(Path(result['receipt']).read_text(encoding='utf-8'))
    native_snapshot = inspect_geopackage(native, artifacts[converter_id]['layer'])
    exact = compare_snapshots(snapshot, native_snapshot)
    check(independent_geometry(native) == source_geos, 'independent ordered XYZ/attributes/BLOB mismatch')
    final_report = validate_source_h_record(final, artifact_root=root)
    check(final_report.foundation_valid, 'final provenance mismatch')
    native_id = plan['native']['output_artifact_id']
    check(sha(native) == final['artifacts'][native_id]['sha256'] == receipt['native_sha256'], 'Native hash mismatch')
    check(sha(Path(result['manifest'])) == receipt['manifest_sha256'], 'manifest receipt mismatch')
    check(before == {key: sha(path) for key, path in paths.items()}, 'input modified')
    return {'status': 'PASS', 'scope': 'actual Converter output of synthetic CityGML; not real Komae data',
            'python': sys.version, 'platform': platform.platform(), 'sqlite': sqlite3.sqlite_version,
            'shapely': shapely.__version__, 'input_sha256': before, 'input_unchanged': True,
            'source_summary': snapshot.summary(), 'raw_qa': raw_qa, 'excluded_ids': excluded,
            'native_result': result, 'final_provenance': final_report.to_dict(), 'exact_comparison': exact,
            'independent_geos_and_raw_comparison': 'PASS',
            'output_sha256': {key: sha(Path(result[key])) for key in ('output', 'manifest', 'receipt')},
            'source_h_eligibility': 'NOT_ESTABLISHED', 'human_review': 'NOT_VERIFIED',
            'formal_acceptance': 'NOT_VERIFIED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--artifact-root', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    # Reserve a NEW report before ingestion. Failure is recorded, never a skip/PASS.
    with args.report.open('x', encoding='utf-8') as stream:
        try:
            report = run(json.loads(args.plan.read_text(encoding='utf-8')), args.artifact_root.resolve(strict=True))
        except Exception as exc:
            json.dump({'status': 'FAILED', 'reason': str(exc)}, stream, indent=2)
            raise
        report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'report': str(args.report)}, indent=2))


if __name__ == '__main__':
    main()
