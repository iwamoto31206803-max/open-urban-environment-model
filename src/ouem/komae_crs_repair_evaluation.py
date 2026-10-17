"""Memory-only CRS repair experiments. No production changes, writers or acceptance."""
from __future__ import annotations

import argparse
import copy
from decimal import Decimal, localcontext
import hashlib
import inspect
import json
import math
import re
import sys

from ouem.adapters import voxcity as adapter
from ouem import komae_adapter_geometry_steps as steps
from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem.komae_adapter_diagnostics import json_safe

# Experimental settings, NOT quality thresholds or production defaults.
CANDIDATES = {'A_make_valid': ('A', None), 'B_remove_1um': ('B', 1e-6),
              'B_remove_0.1mm': ('B', 1e-4), 'C_round_10dp': ('C', 10), 'C_round_12dp': ('C', 12),
              'D_segmentize_1m': ('D', 1.0)}


def digest(value):
    return hashlib.sha256(adapter.canonical_json(value)).hexdigest()


def rings(geometry):
    """Keep polygon/ring and vertex indices; closure is excluded from vertex pairs."""
    result = []
    def visit(g, path):
        if g.geom_type == 'Polygon':
            for i, ring in enumerate([g.exterior, *g.interiors]):
                result.append((f'{path}/ring-{i}', list(ring.coords)))
        elif hasattr(g, 'geoms'):
            for i, part in enumerate(g.geoms):
                visit(part, f'{path}/part-{i}')
    visit(geometry, 'geometry')
    return result


def geometry_summary(geometry, crs):
    from shapely import get_precision
    result = provenance.observe(geometry, crs)
    result['component_types'] = [g.geom_type for g in geometry.geoms] if hasattr(geometry, 'geoms') else [geometry.geom_type]
    result['precision_grid_coordinate_units'] = float(get_precision(geometry))
    return result


def displacement(reference, geographic):
    """Use the valid original 6677 footprint, never repair a metric operand."""
    import numpy as np
    from shapely import get_coordinates
    back = provenance.reproject_xy(geographic, 4326, 6677)
    delta = back.area - reference.area
    result = {'area_difference_m2': delta,
              'area_difference_percent': delta / reference.area * 100 if reference.area > 0 else None,
              'roundtrip_validity': provenance.validity(back), 'symmetric_difference_m2': None,
              'hausdorff_m': None, 'status': 'NOT_CHECKED', 'reason': None}
    if not np.isfinite(get_coordinates(back)).all() or back.is_empty:
        result['reason'] = 'empty/nonfinite metric operand'
        return json_safe(result)
    result['hausdorff_m'] = reference.hausdorff_distance(back)
    if reference.is_valid and back.is_valid and back.geom_type in ('Polygon', 'MultiPolygon'):
        try:
            result['symmetric_difference_m2'] = reference.symmetric_difference(back).area
            result['status'] = 'COMPUTED'
        except Exception as exc:
            result['reason'] = f'{type(exc).__name__}: {exc}'
    else:
        result['reason'] = 'invalid/nonpolygonal metric operand; no implicit repair'
    return json_safe(result)


def orientation(a, b, c):
    """High precision on stored binary64 values, NOT an exact CRS transform."""
    float_det = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    with localcontext() as context:
        context.prec = 200
        ax, ay, bx, by, cx, cy = map(Decimal.from_float, map(float, (*a[:2], *b[:2], *c[:2])))
        det = (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)
    return {'float_determinant': float_det, 'stored_binary64_decimal_determinant': str(det),
            'sign': int(det > 0) - int(det < 0)}


def edge_evidence(geometry, crs):
    import numpy as np
    from scipy.spatial import cKDTree
    from shapely.geometry import LineString, Point, mapping
    from shapely import STRtree
    source_rings = rings(geometry)
    projected_rings = dict(rings(provenance.reproject_xy(geometry, crs, 6677)))
    edges, edge_info, vertices, labels = [], [], [], []
    for name, coords in source_rings:
        metric = projected_rings[name]
        for i, (a, b) in enumerate(zip(coords, coords[1:])):
            edges.append(LineString([a[:2], b[:2]]))
            length = math.dist(metric[i][:2], metric[i+1][:2])
            edge_info.append({'ring': name, 'edge': i, 'a': list(a[:2]), 'b': list(b[:2]), 'length_m': length})
        for i, coordinate in enumerate(metric[:-1]):
            vertices.append(coordinate[:2])
            labels.append({'ring': name, 'vertex': i})
    close = []
    if vertices:
        for i, j in sorted(cKDTree(vertices).query_pairs(1e-4)):
            distance = math.dist(vertices[i], vertices[j])
            close.append({'first': labels[i], 'second': labels[j], 'distance_m': distance,
                          'duplicate_xy': distance == 0})
    intersections = []
    tree = STRtree(edges)
    for i, line in enumerate(edges):
        for j_value in tree.query(line, predicate='intersects'):
            j = int(j_value)
            if j <= i:
                continue
            left, right = edge_info[i], edge_info[j]
            shared = set(map(tuple, (left['a'], left['b']))) & set(map(tuple, (right['a'], right['b'])))
            ring_size = sum(e['ring'] == left['ring'] for e in edge_info)
            adjacent = left['ring'] == right['ring'] and abs(left['edge']-right['edge']) in (1, ring_size-1)
            intersection = line.intersection(edges[j])
            if adjacent and intersection.geom_type == 'Point' and any(intersection.equals(Point(p)) for p in shared):
                continue  # ordinary ring adjacency, not an anomalous intersection
            a, b, c, d = left['a'], left['b'], right['a'], right['b']
            intersections.append({'first_edge': left, 'second_edge': right,
                'intersection': mapping(intersection), 'proper_crossing': line.crosses(edges[j]),
                'orientations': [orientation(a,b,c), orientation(a,b,d), orientation(c,d,a), orientation(c,d,b)]})
    coordinates = [xy for _, values in source_rings for p in values for xy in p[:2]]
    return json_safe({'crs': str(crs), 'rings': [{'ring': name, 'vertices_with_closure': len(c)} for name,c in source_rings],
        'edges': edge_info, 'minimum_edge_m': min((e['length_m'] for e in edge_info), default=None),
        'short_edges_at_most_0.1mm': [e for e in edge_info if e['length_m'] <= 1e-4],
        'close_vertex_pairs_at_most_0.1mm': close, 'anomalous_edge_intersections': intersections,
        'max_binary64_ulp_coordinate_units': max((abs(float(np.spacing(x))) for x in coordinates), default=None),
        'precision_note': 'GEOS uses stored double-precision straight segments. Decimal signs describe those coordinates only; they are not a high-precision PROJ result.'})


def numerical_diagnosis(reference, geographic):
    from shapely.geometry import LineString, Point
    before, after = edge_evidence(reference, 6677), edge_evidence(geographic, 4326)
    edges = {(e['ring'], e['edge']): e for e in before['edges']}
    for pair in after['anomalous_edge_intersections']:
        left, right = [edges.get((pair[k]['ring'], pair[k]['edge'])) for k in ('first_edge','second_edge')]
        if left and right:
            a,b,c,d = left['a'], left['b'], right['a'], right['b']
            pair['source_edges'] = [left, right]
            pair['source_orientations'] = [orientation(a,b,c), orientation(a,b,d), orientation(c,d,a), orientation(c,d,b)]
            pair['source_endpoint_to_other_edge_distances_m'] = [
                LineString([a,b]).distance(Point(c)), LineString([a,b]).distance(Point(d)),
                LineString([c,d]).distance(Point(a)), LineString([c,d]).distance(Point(b))]
            offsets = []
            for edge in (left,right):
                endpoints = provenance.reproject_xy(LineString([edge['a'],edge['b']]),6677,4326)
                geographic_chord_midpoint = endpoints.interpolate(.5,normalized=True)
                back = provenance.reproject_xy(geographic_chord_midpoint,4326,6677)
                source_midpoint = LineString([edge['a'],edge['b']]).interpolate(.5,normalized=True)
                offsets.append(source_midpoint.distance(back))
            pair['midpoint_chord_offset_m'] = offsets
    return {'source': geometry_summary(reference, 6677), 'transformed': geometry_summary(geographic, 4326),
            'before_edges': before, 'after_edges': after, 'roundtrip': displacement(reference, geographic),
            'explicit_rounding_in_baseline': False,
            'cause': {'status': 'INCONCLUSIVE',
                      'observed_valid_to_invalid': reference.is_valid and not geographic.is_valid,
                      'reason': 'Endpoint reprojection connects transformed vertices by straight chords. Nonlinearity, near-degenerate edges and binary64 rounding may interact; edge/ULP/orientation evidence does not isolate their contributions. No Native 3D causal attribution.'}}


def transform_one(geometry):
    import geopandas as gpd
    frame = gpd.GeoDataFrame(geometry=[geometry], crs=6677)
    return adapter._to_voxcity_building_crs(frame).geometry.iloc[0]


def candidate_geometry(reference, baseline, kind, parameter):
    """Conditional experiments only. Valid baseline buildings remain byte-identical."""
    import numpy as np
    import shapely
    if baseline.is_valid:
        return baseline, 'UNCHANGED_VALID_BASELINE'
    if kind == 'A':
        return shapely.make_valid(baseline), 'make_valid after CRS; retain ALL returned components'
    if kind == 'B':
        minimum = min((math.dist(a[:2],b[:2]) for _,c in rings(reference) for a,b in zip(c,c[1:])), default=math.inf)
        if minimum > parameter:
            return baseline, 'NOT_APPLIED: no consecutive edge at/below experimental tolerance'
        cleaned = shapely.remove_repeated_points(reference, tolerance=parameter)
        provenance.require(cleaned.is_valid and not cleaned.is_empty and cleaned.geom_type in ('Polygon','MultiPolygon'),
                           'pre-transform vertex removal produced invalid/empty/nonpolygonal geometry')
        return transform_one(cleaned), 'conditional remove_repeated_points before CRS; no simplification/repair fallback'
    if kind == 'C':
        return shapely.transform(baseline, lambda coordinates: np.round(coordinates, decimals=parameter)), 'pointwise decimal rounding after CRS; no topology repair'
    if kind == 'D':
        dense = shapely.segmentize(reference, max_segment_length=parameter)
        provenance.require(dense.is_valid and not dense.is_empty, 'densification produced invalid/empty geometry')
        return transform_one(dense), 'conditional source edge densification before CRS; approximates projected curves, no vertex removal'
    raise ValueError(f'unknown candidate kind: {kind}')


def assess(reference, baseline, candidate):
    import numpy as np
    from shapely import get_coordinates
    summary = geometry_summary(candidate, 4326)
    metrics = displacement(reference, candidate)
    contract = (candidate.is_valid and not candidate.is_empty and not candidate.has_z and
                candidate.geom_type in ('Polygon','MultiPolygon') and candidate.area > 0 and
                np.isfinite(get_coordinates(candidate)).all())
    original_counts, final_counts = provenance.counts(reference), provenance.counts(candidate)
    changes = [key for key in ('polygons','rings') if original_counts[key] != final_counts[key]]
    if reference.geom_type != candidate.geom_type:
        changes.append('geometry_type')
    available = metrics['status'] == 'COMPUTED' and all(isinstance(metrics.get(k), (float,int)) and math.isfinite(metrics[k])
                  for k in ('area_difference_m2','area_difference_percent','symmetric_difference_m2','hausdorff_m'))
    if not available:
        metrics['status'] = 'NOT_CHECKED'
        metrics['reason'] = metrics['reason'] or 'nonfinite or unavailable metric; no ranking is possible'
    return {'geometry': summary, 'metrics': metrics, 'structural_changes': changes,
            'reference_counts': original_counts, 'vertex_count_delta': final_counts['vertices']-original_counts['vertices'],
            'changed_from_baseline': candidate.wkb != baseline.wkb,
            'geometry_contract_compatible': bool(contract),
            'screening': 'REJECTED' if not contract else 'NOT_CHECKED' if not available else
                         'STRUCTURAL_REVIEW_REQUIRED' if changes else 'REVIEW_REQUIRED',
            'reason': 'Incompatible geometry' if not contract else 'Metrics incomplete' if not available else
                      'No approved deformation tolerance or grid/voxel validation; small area change alone is insufficient.'}


def summarize_candidate(records, features, original):
    properties_preserved = [f['properties'] for f in features] == [f['properties'] for f in original]
    # Canonical bytes also avoid NaN equality ambiguities in audit-only attributes.
    properties_preserved = properties_preserved or digest([f['properties'] for f in features]) == digest([f['properties'] for f in original])
    changes = [r['ouem_id'] for r in records if r.get('changed_from_baseline')]
    rejected = [r['ouem_id'] for r in records if r['screening'] == 'REJECTED']
    available = all(r.get('metrics', {}).get('status') == 'COMPUTED' for r in records)
    aggregate = None
    if available:
        aggregate = {'sum_absolute_area_difference_m2': sum(abs(r['metrics']['area_difference_m2']) for r in records),
            'sum_symmetric_difference_m2': sum(r['metrics']['symmetric_difference_m2'] for r in records),
            'maximum_hausdorff_m': max((r['metrics']['hausdorff_m'] for r in records), default=0),
            'maximum_absolute_area_difference_percent': max((abs(r['metrics']['area_difference_percent']) for r in records), default=0)}
    return {'buildings': records, 'count': len(records), 'changed_ids': changes, 'rejected_ids': rejected,
            'structural_change_ids': [r['ouem_id'] for r in records if r.get('structural_changes')],
            'incomplete_metric_ids': [r['ouem_id'] for r in records if r.get('metrics', {}).get('status') != 'COMPUTED'],
            'ids_and_attributes_preserved': properties_preserved,
            'candidate_features_sha256': None if any('error' in r for r in records) else digest(features),
            'content_hash_scope': 'ordered in-memory features; unavailable if an operation failed', 'aggregate': aggregate,
            'quality_gate': 'NOT_RUN: no grids, voxels, DEM coverage or vertical/roof revalidation'}


def evaluate_frame(frame, document, manifest, identifier):
    """Replay all saved inputs, then evaluate each conditional policy for every building."""
    from shapely.geometry import shape, mapping
    issues = []
    expected = sorted(adapter.numeric_id_mapping(frame.ouem_id.tolist()))  # validate IDs; never write/remap them
    saved = document['features']
    ids = [f['properties']['ouem_id'] for f in saved]
    provenance.require(ids == expected, 'saved feature IDs/order do not match Standard IDs')
    provenance.require(identifier in ids, 'target OUEM ID is missing')
    provenance.require(frame.crs is not None and frame.crs.to_epsg() == 6677, 'Standard must declare EPSG:6677')
    records = manifest['buildings']
    provenance.require(len(records) == len(ids) and len({r['ouem_id'] for r in records}) == len(ids) and
                       {r['ouem_id'] for r in records} == set(ids), 'manifest building IDs differ')
    by_id = {r['ouem_id']:r for r in records}
    footprints = {row.ouem_id:adapter.build_normalized_footprint(row.geometry,row.ouem_id) for row in frame.itertuples()}
    normalized = adapter._set_normalized_footprints(frame[['ouem_id','geometry']].copy(), footprints)
    projected = adapter._to_voxcity_building_crs(normalized)
    # The actual GeoPandas JSON path; never the production file writer.
    serialized = json.loads(projected.to_json(drop_id=True))
    baseline = {f['properties']['ouem_id']:shape(f['geometry']) for f in serialized['features']}
    parity = {}
    for index, feature in enumerate(saved, 1):
        key = feature['properties']['ouem_id']
        props = feature['properties']
        stats = footprints[key][1]
        parity[key] = {'saved_geometry_equal': baseline[key].wkb == shape(feature['geometry']).wkb,
                      'manifest_fields': {k: {'recorded': by_id[key].get('footprint',{}).get(k), 'replayed':v,
                          'equal': by_id[key].get('footprint',{}).get(k) == v} for k,v in stats.items()}}
        if not parity[key]['saved_geometry_equal'] or not all(v['equal'] for v in parity[key]['manifest_fields'].values()):
            issues.append(f'{key}: baseline geometry/manifest parity failed')
        if not (props.get('id') == props.get('voxcity_id') == index and
                isinstance(props.get('height'), (int,float)) and math.isfinite(props['height']) and
                props['height'] > 0 and props.get('min_height') == 0):
            issues.append(f'{key}: saved ID/height attributes incompatible with Adapter contract; no renumbering or correction')
    target_replay = steps.replay(frame, identifier, by_id[identifier], shape(saved[ids.index(identifier)]['geometry']))
    if target_replay['status'] != 'REPRODUCED':
        issues.append('PR #41 target replay is not reproduced')
    results = {}
    for name, (kind, parameter) in CANDIDATES.items():
        output_features, observations = copy.deepcopy(saved), []
        for feature in output_features:
            key = feature['properties']['ouem_id']
            try:
                candidate, operation = candidate_geometry(footprints[key][0], baseline[key], kind, parameter)
                # Test the candidate after the same canonical JSON numeric roundtrip.
                candidate = shape(json.loads(adapter.canonical_json(mapping(candidate))))
                record = assess(footprints[key][0], baseline[key], candidate)
                feature['geometry'] = mapping(candidate)
                observations.append({'ouem_id':key, 'operation':operation, **record})
            except Exception as exc:
                observations.append({'ouem_id':key, 'screening':'REJECTED', 'error':f'{type(exc).__name__}: {exc}',
                                     'result':'No candidate geometry produced; building is not dropped.'})
        results[name] = {'kind':kind, 'parameter':parameter, **summarize_candidate(observations,output_features,saved)}
    return json_safe({'baseline_status':'REPRODUCED' if not issues else 'INCONCLUSIVE', 'issues':issues,
        'count':len(ids), 'complete_92_building_scope':len(ids)==92, 'baseline_parity':parity,
        'baseline_measurements':{key:{'geometry':geometry_summary(baseline[key],4326),
            'roundtrip':displacement(footprints[key][0],baseline[key])} for key in ids},
        'baseline_invalid_ids':[key for key in ids if not baseline[key].is_valid],
        'target_replay':{'status':target_replay['status'], 'verdict':target_replay['verdict'], 'issues':target_replay['issues']},
        'target_numerics':numerical_diagnosis(footprints[identifier][0],baseline[identifier]), 'candidates':results})


def recommendation(repeats):
    result = {'status':'INCONCLUSIVE', 'non_dominated_candidates':[], 'rejected_candidates':[],
              'reason':'No approved shape-change tolerances or voxel/coverage/vertical results; no automatic safest-candidate claim.'}
    if len(repeats) != 2 or any(r.get('baseline_status') != 'REPRODUCED' or not r.get('complete_92_building_scope') for r in repeats):
        result['reason'] = 'Both faithful 92-building repeats are required; incomplete/mismatching baseline evidence.'
        return result
    scores = {}
    for name in CANDIDATES:
        a,b = [r['candidates'][name] for r in repeats]
        if (a['candidate_features_sha256'] is None or a != b or
            any(r['rejected_ids'] or r['incomplete_metric_ids'] or not r['ids_and_attributes_preserved'] for r in (a,b))):
            result['rejected_candidates'].append(name)
        elif not a['structural_change_ids'] and not b['structural_change_ids']:
            scores[name] = tuple(max(a['aggregate'][key],b['aggregate'][key]) for key in
                                ('sum_absolute_area_difference_m2','sum_symmetric_difference_m2','maximum_hausdorff_m'))
    result['non_dominated_candidates'] = [name for name,score in scores.items() if not any(
        all(x <= y for x,y in zip(other,score)) and any(x < y for x,y in zip(other,score))
        for key,other in scores.items() if key != name)]
    result['ranking_note'] = 'Pareto shortlist among repeatable, structurally unchanged, measurable candidates only; not a safety ranking or authorization.'
    return result


def diagnose_run(root, identifier=provenance.DEFAULT_ID):
    import geopandas as gpd
    import shapely
    import pyproj
    evidence = provenance.Evidence(root)
    source = evidence.protect(inspect.getsourcefile(adapter))
    repeats = []
    for number in (1,2):
        try:
            command = provenance.command(evidence.report,number,'a3')
            building = evidence.artifact(command[2])
            output = evidence.artifact(provenance.option(command,'--adapter-output'))
            bm, manifest = evidence.manifest(building), evidence.manifest(output)
            provenance.require(bm.get('schema') == 'ouem-standard-building-manifest/v0.1' and
                               manifest.get('schema') == adapter.SCHEMA, 'unsupported manifest schema')
            for record,path in ((manifest['inputs']['standard_building'],building),(manifest['output'],output)):
                provenance.require(evidence.artifact(record['path']) == path, 'manifest path lineage differs')
                evidence.protect(path,record)
            provenance.require(manifest.get('voxcity') == {'version':adapter.VOXCITY_VERSION,'commit':adapter.VOXCITY_COMMIT},
                               'saved manifest VoxCity pin missing/different; installed commit is not asserted')
            document = evidence.document(output)
            provenance.require(document.get('crs',{}).get('properties',{}).get('name') == 'urn:ogc:def:crs:EPSG::4326',
                               'saved Adapter CRS is not EPSG:4326')
            result = evaluate_frame(gpd.read_file(building,layer='building'),document,manifest,identifier)
            repeats.append({'repeat':number,**result})
        except runner.Blocked:
            raise
        except Exception as exc:
            repeats.append({'repeat':number,'baseline_status':'INCONCLUSIVE','issues':[f'{type(exc).__name__}: {exc}']})
    integrity = evidence.finish()
    comparison = {}
    if all('candidates' in r for r in repeats):
        for name in CANDIDATES:
            a,b = [r['candidates'][name] for r in repeats]
            comparison[name] = {'same_candidate_content':a['candidate_features_sha256'] is not None and
                                a['candidate_features_sha256']==b['candidate_features_sha256'],
                                'same_measurements':a==b}
    rec = recommendation(repeats)
    return json_safe({'schema':'ouem-crs-repair-experiment/v0.1','scope':'MEMORY_ONLY_NOT_ACCEPTANCE',
        'run_id':evidence.report.get('run_id'),'ouem_id':identifier,'repeats':repeats,'comparison':comparison,
        'recommendation':rec,'inputs':evidence.before,'input_integrity':integrity,
        'environment':{'python':sys.version,'platform':sys.platform,'geopandas':gpd.__version__,
            'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,
            'proj':pyproj.proj_version_str,'adapter_source_sha256':evidence.before[str(source)]['sha256']},
        'not_checked':['Actual company-PC cause unless this CLI is run there','Native 3D validity repair',
            'DEM coverage of changed footprints','Building ID grid retention','Vertical/roof/overlap criteria',
            'Voxel content/reproducibility','QGIS visual inspection','Formal acceptance'],
        'status':'EVALUATED' if all(r['baseline_status']=='REPRODUCED' and r.get('complete_92_building_scope') for r in repeats)
                  and all(c['same_candidate_content'] and c['same_measurements'] for c in comparison.values()) else 'INCONCLUSIVE'})


def display(report):
    print(f"Run: {report['run_id']} | target: {report['ouem_id']} | {report['status']}")
    for repeat in report['repeats']:
        print(f"\nRepeat {repeat['repeat']}: baseline={repeat['baseline_status']}; count={repeat.get('count', 'unknown')}")
        for issue in repeat['issues']:
            print('  INCONCLUSIVE: ' + issue)
        if 'candidates' not in repeat:
            continue
        numeric = repeat['target_numerics']
        print('  Target CRS transition: ' + str(numeric['cause']['observed_valid_to_invalid']))
        print('  Intersecting edge pairs: ' + str(len(numeric['after_edges']['anomalous_edge_intersections'])))
        print('  Roundtrip: ' + json.dumps(numeric['roundtrip']))
        for name,result in repeat['candidates'].items():
            target = next(r for r in result['buildings'] if r['ouem_id']==report['ouem_id'])
            geometry = target.get('geometry',{})
            print(f"  {name}: {target['screening']}; changed={len(result['changed_ids'])}/{result['count']}; "
                  f"rejected={len(result['rejected_ids'])}; attributes preserved={result['ids_and_attributes_preserved']}")
            print(f"    target geometry: {geometry.get('geometry_type')}, valid={geometry.get('is_valid')}, "
                  f"counts={geometry.get('counts')}, structural changes={target.get('structural_changes')}")
            print('    target metrics: ' + json.dumps(target.get('metrics',target.get('error'))))
            print('    all-building aggregate: ' + json.dumps(result['aggregate']))
    print('\nRepeat comparison: ' + json.dumps(report['comparison']))
    print('Recommendation: ' + json.dumps(report['recommendation']))
    print('Input SHA-256 unchanged. No artifacts written, no E2E or acceptance. Full edge/geometry evidence: --json.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('ouem_id',nargs='?',default=provenance.DEFAULT_ID)
    parser.add_argument('--json',action='store_true',help='full JSON on stdout; no output files')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',args.run_id) or args.run_id in ('.','..'):
        parser.error('run ID must be one directory name')
    try:
        report = diagnose_run(runner.REPOSITORY/'data/work/integration'/args.run_id,args.ouem_id)
        print(json.dumps(report,indent=2,ensure_ascii=True,allow_nan=False)) if args.json else display(report)
        return 0 if report['status']=='EVALUATED' else 2
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        print(json.dumps({'status':'BLOCKED','error':error},ensure_ascii=True) if args.json else f'BLOCKED: {error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
