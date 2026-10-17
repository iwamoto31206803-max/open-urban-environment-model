"""Synthetic CRS failures and memory-only repair experiments, never local Komae data."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import venv

import geopandas as gpd
import pytest
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon, mapping, shape
from shapely import force_2d

from ouem import komae_crs_repair_evaluation as evaluation
from ouem import komae_integration as runner
from ouem.adapters import voxcity as adapter

TARGET = 'oub-000'
REPOSITORY = Path(__file__).resolve().parents[1]


def notch():
    # A micron-wide clearance to a nonadjacent edge. Nonlinear endpoint
    # reprojection really changes straight-segment topology; no mocked PROJ.
    return Polygon([(x-24000,y-48000,20) for x,y in
                    [(0,0),(4,0),(5,10-1e-6),(6,0),(10,0),(10,10),(0,10)]])


def frame(count=3):
    geometries = [notch()]
    for i in range(1,count):
        x,y = -24000+i*20,-48000
        geometries.append(Polygon([(x,y,20),(x+10,y,20),(x+10,y+10,20),(x,y+10,20)]))
    return gpd.GeoDataFrame({'ouem_id':[f'oub-{i:03}' for i in range(count)]},geometry=geometries,crs=6677)


def saved_documents(source):
    footprints = {row.ouem_id:adapter.build_normalized_footprint(row.geometry,row.ouem_id) for row in source.itertuples()}
    assigned = adapter._set_normalized_footprints(source,footprints)
    projected = adapter._to_voxcity_building_crs(assigned)
    features,records = [],[]
    for i,row in enumerate(projected.itertuples(),1):
        properties = {'ouem_id':row.ouem_id,'id':i,'voxcity_id':i,'height':10.,'min_height':0.,
                      'audit_attribute':{'text':'属性を保持','items':[1,None,False]}}
        features.append({'type':'Feature','properties':properties,'geometry':mapping(row.geometry)})
        records.append({'ouem_id':row.ouem_id,'height':10.,'footprint':footprints[row.ouem_id][1]})
    document = {'type':'FeatureCollection','crs':{'properties':{'name':'urn:ogc:def:crs:EPSG::4326'}},'features':features}
    return json.loads(adapter.canonical_json(document)), {'buildings':records}


def build_run(tmp_path,count=3):
    root = tmp_path / 'existing'
    root.mkdir()
    report = {'schema':'ouem-komae-integration/v0.1','run_id':'synthetic','stages':[],'artifacts':{}}
    for number in (1,2):
        directory = root / f'試験 {number}'
        directory.mkdir()
        building,output = directory/'input-selection.gpkg',directory/'engine-export.json'
        frame(count).to_file(building,layer='building')
        document,manifest = saved_documents(gpd.read_file(building,layer='building'))
        output.write_bytes(adapter.canonical_json(document))
        runner.adjacent(building).write_bytes(adapter.canonical_json({'schema':'ouem-standard-building-manifest/v0.1'}))
        manifest.update(schema=adapter.SCHEMA,voxcity={'version':adapter.VOXCITY_VERSION,'commit':adapter.VOXCITY_COMMIT},
            inputs={'standard_building':{'path':str(building),'sha256':runner.sha256_file(building)}},
            output={'path':str(output),'sha256':runner.sha256_file(output)})
        runner.adjacent(output).write_bytes(adapter.canonical_json(manifest))
        report['stages'].append({'name':f'repeat-{number}-a3','command':['python','a3.py',str(building),
                                'unused-dem','--adapter-output',str(output)]})
    for path in root.rglob('*'):
        if path.is_file():
            report['artifacts'][path.relative_to(root).as_posix()] = runner.fingerprint(path)
    (root/'integration-report.json').write_bytes(adapter.canonical_json(report))
    return root


def tree_bytes(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_actual_crs_invalidity_edges_and_stored_coordinate_orientation():
    reference = force_2d(notch())
    transformed = evaluation.transform_one(reference)
    assert reference.is_valid and not transformed.is_valid
    result = evaluation.numerical_diagnosis(reference,transformed)
    assert result['cause']['observed_valid_to_invalid']
    assert result['cause']['status']=='INCONCLUSIVE'  # mechanism is not established by reproduction alone
    assert not result['before_edges']['anomalous_edge_intersections']
    pairs = result['after_edges']['anomalous_edge_intersections']
    assert pairs and any(pair['proper_crossing'] for pair in pairs)
    assert all(pair['source_edges'] and pair['source_orientations'] for pair in pairs)
    assert any(min(pair['source_endpoint_to_other_edge_distances_m']) < 1e-4 for pair in pairs)
    assert any(max(pair['midpoint_chord_offset_m']) > 1e-6 for pair in pairs)
    assert any([v['sign'] for v in p['orientations']] != [v['sign'] for v in p['source_orientations']] for p in pairs)
    assert result['after_edges']['max_binary64_ulp_coordinate_units'] > 0
    assert result['explicit_rounding_in_baseline'] is False
    json.dumps(result,allow_nan=False)


def test_short_edges_duplicates_near_vertices_and_ring_indices():
    geometry = Polygon([(0,0),(1,0),(1,0),(1,1),(0,1),(0,1-1e-6)])
    result = evaluation.edge_evidence(geometry,6677)
    assert any(e['length_m']==0 for e in result['short_edges_at_most_0.1mm'])
    assert any(p['duplicate_xy'] for p in result['close_vertex_pairs_at_most_0.1mm'])
    assert result['rings'][0]['vertices_with_closure']==7


@pytest.mark.parametrize('name', list(evaluation.CANDIDATES))
def test_candidates_report_validity_type_metrics_and_no_mutation(name):
    reference = force_2d(notch())
    baseline = evaluation.transform_one(reference)
    before = reference.wkb,baseline.wkb
    kind,parameter = evaluation.CANDIDATES[name]
    candidate,operation = evaluation.candidate_geometry(reference,baseline,kind,parameter)
    result = evaluation.assess(reference,baseline,candidate)
    assert (reference.wkb,baseline.wkb)==before
    assert result['geometry']['is_valid']==candidate.is_valid
    assert result['geometry']['geometry_type']==candidate.geom_type
    assert result['metrics']['hausdorff_m'] is not None
    assert operation
    if not candidate.is_valid:
        assert result['screening']=='REJECTED'
    if kind=='A':
        assert candidate.is_valid and candidate.geom_type=='MultiPolygon'
        assert result['screening']=='STRUCTURAL_REVIEW_REQUIRED'
        assert 'polygons' in result['structural_changes']
    if kind=='D':
        assert candidate.is_valid and candidate.geom_type=='Polygon'
        assert not result['structural_changes'] and result['vertex_count_delta']>0
    if kind=='B':
        assert candidate.wkb==baseline.wkb and operation.startswith('NOT_APPLIED')


@pytest.mark.parametrize('kind,parameter', list(evaluation.CANDIDATES.values()))
def test_every_policy_leaves_valid_baseline_exactly_unchanged(kind,parameter):
    reference = force_2d(frame(2).geometry.iloc[1])
    baseline = evaluation.transform_one(reference)
    candidate,operation = evaluation.candidate_geometry(reference,baseline,kind,parameter)
    assert candidate.wkb==baseline.wkb and operation=='UNCHANGED_VALID_BASELINE'


def test_a_keeps_geometrycollection_components_and_rejects_it():
    # A polygon with a retraced spike makes make_valid return a polygon + line.
    bad = Polygon([(0,0),(2,0),(2,2),(1,2),(1,3),(1,2),(0,2)])
    candidate,_ = evaluation.candidate_geometry(Polygon([(0,0),(2,0),(2,2),(0,2)]),bad,'A',None)
    assert candidate.geom_type=='GeometryCollection'
    result = evaluation.assess(Polygon([(-24000,-48000),(-23990,-48000),(-23990,-47990)]),bad,candidate)
    assert result['screening']=='REJECTED'
    assert 'LineString' in result['geometry']['component_types']


def test_b_is_conditional_and_can_remove_tiny_consecutive_edge():
    reference = Polygon([(-24000,-48000),(-24000+1e-8,-48000),(-23990,-48000),(-23990,-47990),(-24000,-47990)])
    bad = Polygon([(139,35),(140,36),(139,36),(140,35)])
    output,operation = evaluation.candidate_geometry(reference,bad,'B',1e-6)
    assert output.is_valid
    assert len(output.exterior.coords)<len(reference.exterior.coords)
    assert operation.startswith('conditional')


def test_metric_values_are_in_metres_and_empty_or_invalid_candidates_rejected():
    reference = Polygon([(-24000,-48000),(-23990,-48000),(-23990,-47990),(-24000,-47990)])
    shifted = Polygon([(x+.1,y) for x,y in reference.exterior.coords])
    geographic = evaluation.transform_one(shifted)
    metrics = evaluation.displacement(reference,geographic)
    assert metrics['status']=='COMPUTED'
    assert metrics['area_difference_m2']==pytest.approx(0,abs=1e-6)
    assert metrics['symmetric_difference_m2']==pytest.approx(2,abs=1e-6)
    assert metrics['hausdorff_m']==pytest.approx(.1,abs=1e-6)
    for bad in (Polygon(),LineString([(139,35),(139.01,35.01)])):
        result = evaluation.assess(reference,geographic,bad)
        assert result['screening']=='REJECTED'


def test_rounding_can_introduce_self_intersection_and_is_rejected():
    good = Polygon([(139,35),(139.003,35),(139.003,35.003),(139.00149,35.003),
                    (139.00149,35.001),(139.0014,35.001),(139.0014,35.003),(139,35.003)])
    import shapely
    import numpy as np
    bad = shapely.transform(good,lambda coords:np.round(coords,3))
    assert good.is_valid and not bad.is_valid
    reference = evaluation.provenance.reproject_xy(good,4326,6677)
    assert evaluation.assess(reference,good,bad)['screening']=='REJECTED'


def test_all_building_properties_and_ids_preserved_in_memory():
    source = frame()
    document,manifest = saved_documents(source)
    before = adapter.canonical_json(document),source.geometry.to_wkb().tolist()
    result = evaluation.evaluate_frame(source,document,manifest,TARGET)
    assert result['baseline_status']=='REPRODUCED'
    assert result['baseline_invalid_ids']==[TARGET]
    assert result['target_replay']['verdict']['classification']=='CRS_TRANSFORMATION'
    for candidate in result['candidates'].values():
        assert candidate['ids_and_attributes_preserved'] and candidate['count']==3
        assert set(candidate['changed_ids']) <= {TARGET}
        assert len(candidate['buildings'])==3
    assert before==(adapter.canonical_json(document),source.geometry.to_wkb().tolist())


def test_mismatching_manifest_and_geometry_prevent_faithful_baseline():
    source = frame()
    document,manifest = saved_documents(source)
    manifest['buildings'][0]['footprint']['projected_union_area'] += 1
    document['features'][1]['geometry'] = copy.deepcopy(document['features'][2]['geometry'])
    result = evaluation.evaluate_frame(source,document,manifest,TARGET)
    assert result['baseline_status']=='INCONCLUSIVE'
    assert len(result['issues'])>=2


def test_ids_are_not_silently_renumbered():
    source = frame()
    document,manifest = saved_documents(source)
    document['features'][0]['properties']['id']=99
    result = evaluation.evaluate_frame(source,document,manifest,TARGET)
    assert result['baseline_status']=='INCONCLUSIVE'
    assert document['features'][0]['properties']['id']==99
    assert all(c['ids_and_attributes_preserved'] for c in result['candidates'].values())


def test_full_92_both_repeats_hashes_and_non_destruction(tmp_path,monkeypatch):
    root = build_run(tmp_path,92)
    before = tree_bytes(tmp_path)
    def forbidden(*args,**kwargs):
        pytest.fail('attempted generation/write/external processing')
    monkeypatch.setattr(adapter,'_run_voxcity_grids',forbidden)
    monkeypatch.setattr(adapter,'adapt_standard_to_voxcity',forbidden)
    monkeypatch.setattr(gpd.GeoDataFrame,'to_file',forbidden)
    monkeypatch.setattr(runner,'execute',forbidden)
    monkeypatch.setattr(subprocess,'run',forbidden)
    result = evaluation.diagnose_run(root,TARGET)
    assert result['status']=='EVALUATED'
    assert all(r['count']==92 and r['complete_92_building_scope'] for r in result['repeats'])
    assert all(c['same_candidate_content'] and c['same_measurements'] for c in result['comparison'].values())
    assert all(result['input_integrity'].values())
    assert result['recommendation']['status']=='INCONCLUSIVE'
    assert 'D_segmentize_1m' in result['recommendation']['non_dominated_candidates']
    assert tree_bytes(tmp_path)==before
    json.dumps(result,allow_nan=False)


def test_small_run_is_not_claimed_as_92_building_evaluation(tmp_path):
    result = evaluation.diagnose_run(build_run(tmp_path),TARGET)
    assert result['status']=='INCONCLUSIVE'
    assert '92-building' in result['recommendation']['reason']
    assert result['repeats'][0]['baseline_status']=='REPRODUCED'


def test_hash_mismatch_and_sidecars_block(tmp_path):
    root = build_run(tmp_path)
    path = root/'試験 1/input-selection.gpkg'
    sidecar = Path(str(path)+'-wal')
    sidecar.write_bytes(b'evidence')
    with pytest.raises(runner.Blocked,match='sidecars'):
        evaluation.diagnose_run(root,TARGET)
    assert sidecar.read_bytes()==b'evidence'
    sidecar.unlink()  # synthetic setup only
    with (root/'試験 1/engine-export.json').open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(runner.Blocked,match='hash/size mismatch'):
        evaluation.diagnose_run(root,TARGET)


def test_concurrent_modification_is_detected(tmp_path,monkeypatch):
    root = build_run(tmp_path)
    original = evaluation.evaluate_frame
    def change(*args):
        result = original(*args)
        with (root/'integration-report.json').open('ab') as stream:
            stream.write(b' ')
        return result
    monkeypatch.setattr(evaluation,'evaluate_frame',change)
    with pytest.raises(runner.Blocked,match='changed'):
        evaluation.diagnose_run(root,TARGET)


def test_unavailable_candidate_has_no_fake_output_hash(monkeypatch):
    source = frame()
    document,manifest = saved_documents(source)
    original = evaluation.candidate_geometry
    def fail(reference,baseline,kind,parameter):
        if kind=='A' and not baseline.is_valid:
            raise ValueError('synthetic failed operation')
        return original(reference,baseline,kind,parameter)
    monkeypatch.setattr(evaluation,'candidate_geometry',fail)
    result = evaluation.evaluate_frame(source,document,manifest,TARGET)['candidates']['A_make_valid']
    assert result['candidate_features_sha256'] is None
    assert result['rejected_ids']==[TARGET]
    assert result['count']==3


def test_json_cli_and_run_id_validation(tmp_path,monkeypatch,capsys):
    base = tmp_path/'data/work/integration'
    base.mkdir(parents=True)
    root = build_run(base)
    monkeypatch.setattr(runner,'REPOSITORY',tmp_path)
    before = tree_bytes(tmp_path)
    assert evaluation.main([root.name,TARGET,'--json'])==2  # deliberately incomplete PoC fixture
    result = json.loads(capsys.readouterr().out)
    assert result['repeats'][0]['baseline_status']=='REPRODUCED'
    assert tree_bytes(tmp_path)==before
    for value in ('../run','.','..','C:\\run'):
        with pytest.raises(SystemExit):
            evaluation.main([value])


def test_windows_launcher_arguments_and_exit_status(tmp_path):
    source = REPOSITORY/'scripts/work/evaluate_komae_adapter_crs_repairs.cmd'
    text = source.read_text(encoding='utf-8')
    assert '-B -m ouem.komae_crs_repair_evaluation' in text
    assert '"%~1" "%~2"' in text
    if os.name=='nt':
        launcher = tmp_path/'scripts/work'/source.name
        launcher.parent.mkdir(parents=True)
        shutil.copyfile(source,launcher)
        for args in ([],['one','two','three']):
            result = subprocess.run(['cmd','/d','/c',str(launcher),*args],capture_output=True,timeout=20)
            assert result.returncode==2
        venv.EnvBuilder(with_pip=False).create(tmp_path/'.venv')
        package = tmp_path/'ouem'
        package.mkdir()
        (package/'__init__.py').write_text('',encoding='utf-8')
        (package/'komae_crs_repair_evaluation.py').write_text(
            'import json,sys\nprint(json.dumps(sys.argv[1:]))\nraise SystemExit(7)\n',encoding='utf-8')
        for args in (['run'],['run',TARGET]):
            result = subprocess.run(['cmd','/d','/c',str(launcher),*args],capture_output=True,timeout=20)
            assert result.returncode==7 and json.loads(result.stdout)==args


def test_repeat_attribute_difference_is_not_reproducible(tmp_path):
    root = build_run(tmp_path)
    path = root/'試験 2/engine-export.json'
    document = runner.read_json(path)
    document['features'][0]['properties']['audit_attribute']['text']='different synthetic repeat'
    path.write_bytes(adapter.canonical_json(document))
    manifest_path = runner.adjacent(path)
    manifest = runner.read_json(manifest_path)
    manifest['output']['sha256']=runner.sha256_file(path)
    manifest_path.write_bytes(adapter.canonical_json(manifest))
    report_path = root/'integration-report.json'
    report = runner.read_json(report_path)
    for changed in (path,manifest_path):
        report['artifacts'][changed.relative_to(root).as_posix()]=runner.fingerprint(changed)
    report_path.write_bytes(adapter.canonical_json(report))
    result = evaluation.diagnose_run(root,TARGET)
    assert all(r['baseline_status']=='REPRODUCED' for r in result['repeats'])
    assert all(not c['same_candidate_content'] for c in result['comparison'].values())
    assert result['recommendation']['status']=='INCONCLUSIVE'


def test_attribute_mutation_cannot_pass_preservation_check():
    original=[{'type':'Feature','properties':{'ouem_id':'one','id':1},'geometry':None}]
    changed=copy.deepcopy(original)
    changed[0]['properties']['id']=2
    result=evaluation.summarize_candidate([{'ouem_id':'one','screening':'NOT_CHECKED'}],changed,original)
    assert not result['ids_and_attributes_preserved']


def test_pretransform_cleanup_that_collapses_shape_is_rejected():
    from shapely.errors import GEOSException
    reference=Polygon([(0,0),(1e-8,0),(1e-8,1e-8),(0,1e-8)])
    bad=Polygon([(139,35),(140,36),(139,36),(140,35)])
    # GEOS versions may reject the collapsed ring themselves or return a shape
    # that the experiment's validity guard rejects. Neither may be accepted.
    with pytest.raises((ValueError,GEOSException)):
        evaluation.candidate_geometry(reference,bad,'B',1e-4)
