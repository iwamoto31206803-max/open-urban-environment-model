"""Actual small SQLite/ISO WKB fixtures; no GDAL, OSGeo4W or Converter CLI."""
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import xml.etree.ElementTree as ET

import pytest
from pyproj import CRS

from ouem.native.building import provenance as p
from ouem.native.building import source_h as h
from ouem.native.building.source_h_geometry import (
    GeometryValidationError, compare_snapshots, decode_geometry, inspect_geopackage,
)

FIXTURE = Path(__file__).parent/'fixtures/plateau_converter/two_buildings.gml'
G = 'http://www.opengis.net/gml'
B = 'http://www.opengis.net/citygml/building/2.0'
NS = {'gml': G, 'bldg': B}


@contextmanager
def db(path):
    connection=sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def source_faces():
    # Independent fixture extraction: no production reader is used to build WKB.
    buildings = {}
    for building in ET.parse(FIXTURE).getroot().findall('.//bldg:Building', NS):
        faces = []
        for branch in building.findall('bldg:boundedBy', NS):
            for polygon in branch.findall('.//gml:Polygon', NS):
                rings = []
                for pos in polygon.findall('.//gml:posList', NS):
                    v = list(map(float, pos.text.split()))
                    rings.append(tuple((v[i+1], v[i], v[i+2]) for i in range(0, len(v), 3)))
                faces.append(tuple(rings))
        buildings[building.get(f'{{{G}}}id')] = tuple(faces)
    return buildings


def polygon_wkb(rings):
    return struct.pack('<BII', 1, 1003, len(rings))+b''.join(
        struct.pack('<I', len(ring))+b''.join(struct.pack('<ddd', *point) for point in ring)
        for ring in rings)


def blob(faces, collection=False):
    body = struct.pack('<BII', 1, 1007 if collection else 1006, len(faces))
    body += b''.join(polygon_wkb(face) for face in faces)
    return b'GP'+bytes([0, 1])+struct.pack('<i', 6697)+body


def write_gpkg(path, collection=False):
    with db(path) as c:
        c.executescript('''
            PRAGMA application_id=1196444487;
            PRAGMA user_version=10300;
            CREATE TABLE gpkg_spatial_ref_sys(srs_name TEXT,srs_id INTEGER PRIMARY KEY,
                organization TEXT,organization_coordsys_id INTEGER,definition TEXT,description TEXT);
            CREATE TABLE gpkg_contents(table_name TEXT PRIMARY KEY,data_type TEXT,identifier TEXT,
                description TEXT,last_change TEXT,min_x DOUBLE,min_y DOUBLE,max_x DOUBLE,max_y DOUBLE,srs_id INTEGER);
            CREATE TABLE gpkg_geometry_columns(table_name TEXT,column_name TEXT,
                geometry_type_name TEXT,srs_id INTEGER,z INTEGER,m INTEGER);
            CREATE TABLE "bldg:Building"(fid INTEGER PRIMARY KEY,id TEXT,geometry BLOB,measuredHeight REAL);
        ''')
        c.execute('INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,?)',
                  ('JGD2011 + height',6697,'EPSG',6697,CRS.from_epsg(6697).to_wkt(),''))
        c.execute('INSERT INTO gpkg_contents VALUES(?,?,?,?,?,?,?,?,?,?)',
                  ('bldg:Building','features','bldg:Building','','2026-10-28T00:00:00Z',138,35,140,38,6697))
        c.execute('INSERT INTO gpkg_geometry_columns VALUES(?,?,?,?,?,?)',
                  ('bldg:Building','geometry','GEOMETRYCOLLECTION' if collection else 'MULTIPOLYGON',6697,1,0))
        for identifier, faces in source_faces().items():
            c.execute('INSERT INTO "bldg:Building"(id,geometry,measuredHeight) VALUES(?,?,?)',
                      (identifier,blob(faces,collection),9.5 if identifier.endswith('tokyo') else 14.75))


def artifact(path, role, layer=None):
    data=path.read_bytes()
    result={'path':path.name,'size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'role':role}
    if layer:
        result['layer']=layer
    return result


@pytest.fixture
def plan(tmp_path):
    shutil.copyfile(FIXTURE,tmp_path/'raw.gml')
    (tmp_path/'cli.exe').write_bytes(b'synthetic CLI identity only; never executed')
    (tmp_path/'source.txt').write_text('synthetic source declaration, not scientific evidence')
    write_gpkg(tmp_path/'converter.gpkg')
    artifacts={'raw':artifact(tmp_path/'raw.gml','raw_citygml'),
        'cli':artifact(tmp_path/'cli.exe','converter_cli'),
        'evidence':artifact(tmp_path/'source.txt','source_evidence'),
        'converter':artifact(tmp_path/'converter.gpkg','converter_gpkg','bldg:Building'),
        'native':{'path':'native-run/native.gpkg','role':'native_gpkg','layer':'bldg:Building'}}
    return {'schema':p.NATIVE_SCHEMA,'profile':p.SOURCE_H_PROFILE,'artifacts':artifacts,
        'source_declaration':{'srs_name':'http://www.opengis.net/def/crs/EPSG/0/6697',
            'horizontal_epsg':6668,'vertical_epsg':6695,'quantity':'gravity_related_height',
            'unit':'metre','axes':['latitude','longitude','H'],'evidence_artifact_id':'evidence'},
        'coordinate_contract':{'input_epsg':6697,'horizontal_epsg':6668,'vertical_epsg':6695,
            'quantity':'gravity_related_height','unit':'metre','storage_axes':['longitude','latitude','H']},
        'geometry_selection':{'requested_lod':2,'split_components':False},
        'converter':{'schema':p.CONVERTER_SCHEMA,'repository':p.REPOSITORY,
            'commit':'ce7766df9788ce391b149c55df16d33082d0bc72','version':'0.1.19',
            'cli_artifact_id':'cli','input_artifact_ids':['raw'],'output_artifact_id':'converter',
            'argv':['cli.exe','raw.gml','--sink','gpkg','--output','converter.gpkg','--epsg','6697','-t','use_lod=lod2'],
            'resolved_options':{'sink':'gpkg','epsg':6697,'use_lod':'lod2','split_components':False},
            'exit_code':0,'execution_status':'COMPLETED'},
        'native':{'input_artifact_id':'converter','output_artifact_id':'native'},
        'operations':[{'input_artifact_ids':['raw'],'output_artifact_id':'converter',
            'horizontal_operation':'latitude_longitude_to_gis_longitude_latitude','vertical_operation':'identity_H',
            'offset_m':0,'geoid_model':None},
            {'input_artifact_ids':['converter'],'output_artifact_id':'native','horizontal_operation':'identity_XY',
             'vertical_operation':'identity_H','offset_m':0,'geoid_model':None}]}


def refresh(plan, root, identifier='converter'):
    ref=plan['artifacts'][identifier]
    path=root/ref['path']
    ref.update(size_bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def mutate_geometry(path, mutate):
    with db(path) as c:
        data=c.execute('SELECT geometry FROM "bldg:Building" WHERE id=?',('synthetic_tokyo',)).fetchone()[0]
        c.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(mutate(data),'synthetic_tokyo'))


def test_preflight_does_not_invent_native_identity(plan,tmp_path):
    preflight=p.validate_source_h_inputs(plan,artifact_root=tmp_path)
    assert preflight.foundation_valid and 'native' not in preflight.checked_artifact_ids
    assert preflight.validation_scope=='source-h-input-preflight/v0.1'
    assert not p.validate_source_h_record(plan,artifact_root=tmp_path).foundation_valid
    assert not (tmp_path/'native-run').exists()


def test_success_exact_structure_ids_xyz_and_final_provenance(plan,tmp_path):
    before={v['path']:(tmp_path/v['path']).read_bytes() for v in plan['artifacts'].values() if v['role']!='native_gpkg'}
    original=copy.deepcopy(plan)
    result=h.ingest_source_h(plan,artifact_root=tmp_path)
    assert result['status']=='COMPLETED' and plan==original
    qa=result['qa']
    assert qa['building_id_preservation']==qa['all_vertex_xyz_preservation']==qa['gpkg_structure']=='PASS'
    assert qa['lod2_correspondence']==qa['source_storage_axis_correspondence']=='PASS'
    assert qa['source_h_eligibility']=='NOT_ESTABLISHED'
    assert qa['human_review']==qa['formal_acceptance']=='NOT_VERIFIED'
    assert qa['summary']['feature_count']==2
    for counts in qa['summary']['buildings'].values():
        assert counts=={'geometry_type':'MultiPolygon','faces':10,'exterior_rings':10,'interior_rings':2,'vertices':60}
    final=json.loads(Path(result['manifest']).read_text())
    assert p.validate_source_h_record(final,artifact_root=tmp_path).foundation_valid
    receipt=json.loads(Path(result['receipt']).read_text())
    assert receipt['manifest_sha256']==hashlib.sha256(Path(result['manifest']).read_bytes()).hexdigest()
    assert receipt['native_sha256']==final['artifacts']['native']['sha256']
    assert all((tmp_path/name).read_bytes()==data for name,data in before.items())
    assert len(list((tmp_path/'native-run').iterdir()))==3


def test_geometry_collection_polygon_children_supported(plan,tmp_path):
    with db(tmp_path/'converter.gpkg') as c:
        c.execute("UPDATE gpkg_geometry_columns SET geometry_type_name='GEOMETRYCOLLECTION'")
        for identifier,faces in source_faces().items():
            c.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(blob(faces,True),identifier))
    refresh(plan,tmp_path)
    result=h.ingest_source_h(plan,artifact_root=tmp_path)
    assert all(v['geometry_type']=='GeometryCollection' for v in result['qa']['summary']['buildings'].values())


@pytest.mark.parametrize('sql',[
    'UPDATE gpkg_contents SET srs_id=4979',
    'UPDATE gpkg_geometry_columns SET srs_id=4979',
    'UPDATE gpkg_geometry_columns SET z=0',
    "UPDATE gpkg_spatial_ref_sys SET definition='undefined'",
    'UPDATE "bldg:Building" SET id=NULL WHERE fid=1',
    'UPDATE "bldg:Building" SET id=\'same\'',
    'UPDATE "bldg:Building" SET geometry=NULL WHERE fid=1',
])
def test_bad_gpkg_rejected_before_output(plan,tmp_path,sql):
    with db(tmp_path/'converter.gpkg') as c:c.execute(sql)
    refresh(plan,tmp_path)
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


@pytest.mark.parametrize('offset,fmt,value',[(4,'i',4979),(9,'I',6),(46,'d',float('nan')),(46,'d',float('inf'))])
def test_blob_srid_z_and_nonfinite_rejected(plan,tmp_path,offset,fmt,value):
    def edit(data):
        data=bytearray(data);struct.pack_into('<'+fmt,data,offset,value);return bytes(data)
    mutate_geometry(tmp_path/'converter.gpkg',edit);refresh(plan,tmp_path)
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


def test_lod2_face_loss_rejected(plan,tmp_path):
    mutate_geometry(tmp_path/'converter.gpkg',lambda _:blob(source_faces()['synthetic_tokyo'][:-1]))
    refresh(plan,tmp_path)
    with pytest.raises(h.SourceHIngestionError,match='LOD2_MISMATCH'):h.ingest_source_h(plan,artifact_root=tmp_path)


def test_hash_mismatch_before_any_output(plan,tmp_path):
    plan['artifacts']['converter']['sha256']='0'*64
    with pytest.raises(h.SourceHIngestionError,match='HASH_MISMATCH'):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


def test_existing_accepted_output_not_overwritten(plan,tmp_path):
    (tmp_path/'native-run').mkdir();old=tmp_path/'native-run/native.gpkg';old.write_bytes(b'accepted bytes')
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert old.read_bytes()==b'accepted bytes'


@pytest.mark.parametrize('step',['copy','qa','publish','manifest'])
def test_failure_removes_only_own_incomplete_outputs(plan,tmp_path,monkeypatch,step):
    if step=='copy':
        def fail_copy(source,output):
            output.write_bytes(b'incomplete');raise OSError('copy failed')
        monkeypatch.setattr(h,'_copy_database',fail_copy)
    elif step=='qa':
        original=h._copy_database
        def alter(source,output):
            original(source,output)
            mutate_geometry(output,lambda _:blob(tuple(reversed(source_faces()['synthetic_tokyo']))))
        monkeypatch.setattr(h,'_copy_database',alter)
    else:
        original=h._publish
        def fail_publish(source,destination):
            if step=='publish' or destination.name.endswith('manifest.json'):raise OSError('publication failed')
            original(source,destination)
        monkeypatch.setattr(h,'_publish',fail_publish)
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()
    assert (tmp_path/'converter.gpkg').exists()


def test_order_and_xyz_change_detected_independently(plan,tmp_path):
    original=inspect_geopackage(tmp_path/'converter.gpkg','bldg:Building')
    for modified in (tuple(reversed(source_faces()['synthetic_tokyo'])),
                     tuple(tuple(tuple((x,y,z+1) for x,y,z in ring) for ring in face) for face in source_faces()['synthetic_tokyo'])):
        path=tmp_path/'changed.gpkg'
        if not path.exists():shutil.copyfile(tmp_path/'converter.gpkg',path)
        mutate_geometry(path,lambda _:blob(modified))
        with pytest.raises(GeometryValidationError,match='XYZ_MISMATCH'):
            compare_snapshots(original,inspect_geopackage(path,'bldg:Building'))


def test_swapped_xy_rejected_by_raw_correspondence(plan,tmp_path):
    faces=tuple(tuple(tuple((y,x,z) for x,y,z in ring) for ring in face) for face in source_faces()['synthetic_tokyo'])
    mutate_geometry(tmp_path/'converter.gpkg',lambda _:blob(faces));refresh(plan,tmp_path)
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)


def test_full_identity_in_plan_rejected_not_reused(plan,tmp_path):
    plan['artifacts']['native'].update(size_bytes=0,sha256='0'*64)
    assert not p.validate_source_h_inputs(plan,artifact_root=tmp_path).foundation_valid


def test_truncated_and_empty_geometry_are_not_accepted():
    for data in (b'',b'GP',b'GP\0\1'+struct.pack('<i',6697)+struct.pack('<BII',1,1006,0)):
        with pytest.raises(GeometryValidationError):decode_geometry(data)


def test_interior_ring_loss_is_lod2_mismatch(plan,tmp_path):
    faces=list(source_faces()['synthetic_tokyo'])
    face=next(i for i,v in enumerate(faces) if len(v)>1)
    faces[face]=(faces[face][0],)
    mutate_geometry(tmp_path/'converter.gpkg',lambda _:blob(faces));refresh(plan,tmp_path)
    with pytest.raises(h.SourceHIngestionError,match='LOD2_MISMATCH'):
        h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


def test_input_changed_during_copy_blocks_and_rolls_back(plan,tmp_path,monkeypatch):
    original=h._copy_database
    def change_input(source,output):
        original(source,output)
        (tmp_path/'source.txt').write_bytes(b'changed evidence')
    monkeypatch.setattr(h,'_copy_database',change_input)
    with pytest.raises(h.SourceHIngestionError,match='HASH_MISMATCH'):
        h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


def test_published_native_is_rehashed_not_just_staged_file(plan,tmp_path,monkeypatch):
    original=h._publish
    def change_native(source,destination):
        original(source,destination)
        if destination.suffix=='.gpkg':
            with db(destination) as c:c.execute('UPDATE "bldg:Building" SET measuredHeight=999')
    monkeypatch.setattr(h,'_publish',change_native)
    with pytest.raises(h.SourceHIngestionError,match='HASH_MISMATCH'):
        h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


@pytest.mark.parametrize('fragment,replacement',[
    (b'EPSG/0/6697',b'EPSG/0/4979'),
    (b'lod2MultiSurface',b'lod2Solid'),
    (b'gml:id="synthetic_niigata"',b'gml:id="synthetic_tokyo"'),
])
def test_unsupported_or_conflicting_raw_is_not_ignored(plan,tmp_path,fragment,replacement):
    path=tmp_path/'raw.gml';path.write_bytes(path.read_bytes().replace(fragment,replacement));refresh(plan,tmp_path,'raw')
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert not (tmp_path/'native-run').exists()


def test_forged_review_never_establishes_eligibility(plan,tmp_path):
    plan['eligibility_review']={'decision':'ELIGIBLE'}
    plan['acceptance']={'status':'ACCEPTED'}
    result=h.ingest_source_h(plan,artifact_root=tmp_path)
    final=json.loads(Path(result['manifest']).read_text())
    assert final['eligibility_review']==final['acceptance']=={'status':'NOT_VERIFIED'}
    assert result['qa']['source_h_eligibility']=='NOT_ESTABLISHED'


def test_legacy_profile_not_auto_ingested(plan,tmp_path):
    plan['profile']=p.LEGACY_PROFILE
    with pytest.raises(h.SourceHIngestionError,match='LEGACY_NOT_REGISTERED'):
        h.ingest_source_h(plan,artifact_root=tmp_path)


def test_protected_manifest_and_source_bytes_unchanged(plan,tmp_path):
    target=tmp_path/'native-run';target.mkdir()
    for name in ('native.gpkg','native.gpkg.manifest.json','native.gpkg.receipt.json'):
        (target/name).write_bytes(b'accepted historical '+name.encode())
    before={path.name:path.read_bytes() for path in target.iterdir()}
    source=(tmp_path/'converter.gpkg').read_bytes()
    with pytest.raises(h.SourceHIngestionError):h.ingest_source_h(plan,artifact_root=tmp_path)
    assert {path.name:path.read_bytes() for path in target.iterdir()}==before
    assert (tmp_path/'converter.gpkg').read_bytes()==source
