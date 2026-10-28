"""Synthetic real-file chains; no Converter, GIS runtime, engine or acceptance."""
import hashlib
import json
from pathlib import Path
import sqlite3
import struct

import pytest

from test_source_h_ingestion import plan, db, refresh, blob, source_faces
from test_source_h_standard import native, area, run
from ouem.native.building.source_h import ingest_source_h
from ouem.standardize.building import source_h as standardizer
from ouem.consumers import source_h_standard as c
from ouem.consumers import _source_h_geometry as g


@pytest.fixture
def standard(native,area,tmp_path):
    return run(tmp_path,area)


def validate(tmp_path,area,**kwargs):
    args=dict(standard_manifest='standard-run/standard.gpkg.manifest.json',artifact_root=tmp_path,
        expected_profile=c.SOURCE_H_PROFILE,study_area_config=area)
    args.update(kwargs)
    return c.validate_source_h_standard(**args)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(standard):
    return json.loads(Path(standard['manifest']).read_text())


def save(standard,m,*,refresh_output=False):
    if refresh_output:
        m['standard_output'].update(sha256=sha(standard['output']),size_bytes=Path(standard['output']).stat().st_size)
    Path(standard['manifest']).write_text(json.dumps(m),encoding='utf-8')
    receipt=json.loads(Path(standard['receipt']).read_text())
    receipt.update(manifest_sha256=sha(standard['manifest']),standard_sha256=m['standard_output']['sha256'])
    Path(standard['receipt']).write_text(json.dumps(receipt),encoding='utf-8')


def fail(report):
    assert report['technical_validation']=='FAIL' and report['issues']
    assert report['source_h_eligibility']=='NOT_ESTABLISHED'
    assert report['human_review']==report['formal_acceptance']=='NOT_VERIFIED'


def test_success_full_revalidation_and_readonly(standard,tmp_path,area,monkeypatch):
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in tmp_path.rglob('*') if p.is_file()}
    def forbidden(*args,**kwargs):raise AssertionError('writer/engine/process called')
    monkeypatch.setattr(standardizer,'standardize_source_h',forbidden)
    monkeypatch.setattr(standardizer,'write_standard',forbidden)
    import subprocess,builtins
    monkeypatch.setattr(subprocess,'run',forbidden)
    real_import=builtins.__import__
    def import_guard(name,*args,**kwargs):
        assert not name.startswith('voxcity')
        return real_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',import_guard)
    real_connect=sqlite3.connect
    def readonly_connect(path,*args,**kwargs):
        assert '?mode=ro&immutable=1' in str(path) and kwargs.get('uri') is True
        return real_connect(path,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',readonly_connect)
    report=validate(tmp_path,area)
    assert report['technical_validation']=='PASS',report
    assert report['feature_count']==2 and report['vertex_count']==120
    assert report['xy_h_qa']['H_binary64_exact']=='PASS' and report['xy_h_qa']['max_xy_error_m']<=1e-7
    assert report['verified_profile']==c.SOURCE_H_PROFILE and report['verified_schema']==c.SCHEMA
    assert report['artifacts']['standard']['sha256']==sha(standard['output'])
    assert all(v['interior_rings']==2 for v in report['buildings'].values())
    assert before.keys()=={p for p in tmp_path.rglob('*') if p.is_file()}
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==value for p,value in before.items())


@pytest.mark.parametrize('field,value',[
    ('profile','ouem-native-building/plateau-source-h/v9'),('schema','ouem-standard-building-manifest/v0.1'),
    ('status','ACCEPTED'),('execution_status','FAILED'),('source_h_eligibility','ELIGIBLE'),
    ('human_review','VERIFIED'),('formal_acceptance','ACCEPTED'),('vertical_crs','EPSG:4979'),
    ('vertical_quantity','ellipsoidal_height'),('vertical_operation','geoid_shift'),
    ('input_features',True),('output_features','2'),('selected_ids',['synthetic_tokyo','synthetic_tokyo']),
    ('excluded_ids',['synthetic_tokyo']),('selected_lod_by_id',{'synthetic_tokyo':1}),
    ('native_input',None),('source_chain',{}),
])
def test_manifest_conflicts(standard,tmp_path,area,field,value):
    m=load(standard);m[field]=value;save(standard,m)
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('profile',[None,'unknown','ouem-native-building/plateau-legacy-4979-claimed-tp/v0.1'])
def test_expected_profile_exact_no_fallback(standard,tmp_path,area,profile):
    fail(validate(tmp_path,area,expected_profile=profile))


@pytest.mark.parametrize('artifact',['standard','native','converter','raw','cli','evidence','native_receipt','standard_receipt','config'])
def test_missing_or_tampered_bytes(standard,native,tmp_path,area,artifact):
    paths={'standard':Path(standard['output']),'native':Path(native['output']),'converter':tmp_path/'converter.gpkg',
        'raw':tmp_path/'raw.gml','cli':tmp_path/'cli.exe','evidence':tmp_path/'source.txt',
        'native_receipt':Path(native['receipt']),'standard_receipt':Path(standard['receipt']),'config':area}
    with paths[artifact].open('ab') as stream:stream.write(b'tampered')
    fail(validate(tmp_path,area))


def test_receipt_missing_and_wrong_schema(standard,tmp_path,area):
    path=Path(standard['receipt']);receipt=path.read_bytes();path.unlink()
    fail(validate(tmp_path,area))
    value=json.loads(receipt);value['schema']='ouem-standard-building-receipt/v9';path.write_text(json.dumps(value))
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('field,path',[
    ('native_manifest','../escape.json'),('native_receipt','C:/outside.json'),
    ('native_manifest','..\\escape.json'),('standard_output','/etc/passwd'),
])
def test_confined_locators(standard,tmp_path,area,field,path):
    m=load(standard);m[field]['path']=path;save(standard,m)
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('sql',[
    'PRAGMA application_id=0',
    'UPDATE gpkg_contents SET srs_id=4979',
    'UPDATE gpkg_geometry_columns SET z=0',
    "UPDATE gpkg_geometry_columns SET geometry_type_name='POLYGON'",
    "UPDATE gpkg_spatial_ref_sys SET definition='undefined' WHERE srs_id=6677",
    "UPDATE gpkg_spatial_ref_sys SET definition_12_063='undefined' WHERE srs_id=6677",
    "DELETE FROM gpkg_extensions",
    "UPDATE building SET source_lod='1'",
    "UPDATE building SET measured_height=111",
    "UPDATE building SET source_dataset='other'",
    "UPDATE building SET ouem_id='wrong' WHERE fid=1",
    "DELETE FROM building WHERE fid=1",
])
def test_rehashed_gpkg_corruption_independently_detected(standard,tmp_path,area,sql):
    with db(Path(standard['output'])) as conn:conn.execute(sql)
    save(standard,load(standard),refresh_output=True)
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('mutation',['srid','2d','nan','inf','H','XY','order','empty','null','mixed'])
def test_rehashed_geometry_corruption(standard,tmp_path,area,mutation):
    with db(Path(standard['output'])) as conn:
        data=conn.execute('SELECT geometry FROM building WHERE fid=1').fetchone()[0]
        if mutation=='null':changed=None
        else:
            changed=bytearray(data)
            if mutation=='srid':struct.pack_into('<i',changed,4,6697)
            elif mutation=='2d':struct.pack_into('<I',changed,9,6)
            elif mutation=='mixed':struct.pack_into('<I',changed,18,1002)
            elif mutation=='empty':struct.pack_into('<I',changed,13,0)
            elif mutation=='order':
                a,b=bytes(changed[30:54]),bytes(changed[54:78]);changed[30:54]=b;changed[54:78]=a
            elif mutation=='XY':
                x,y=struct.unpack_from('<dd',changed,30);struct.pack_into('<dd',changed,30,y,x)
            else:struct.pack_into('<d',changed,46,{'nan':float('nan'),'inf':float('inf'),'H':999.}[mutation])
            changed=bytes(changed)
        if mutation=='null':
            # Rebuild only the synthetic feature table to remove SQL constraints.
            conn.execute('ALTER TABLE building RENAME TO old_building')
            conn.execute('CREATE TABLE building AS SELECT * FROM old_building')
            conn.execute('DROP TABLE old_building')
        conn.execute('UPDATE building SET geometry=? WHERE fid=1',(changed,))
    save(standard,load(standard),refresh_output=True)
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('column,value',[('source_id',None),('source_id','same'),('ouem_id',None),('ouem_id','same')])
def test_null_duplicate_identifiers(standard,tmp_path,area,column,value):
    with db(Path(standard['output'])) as conn:
        conn.execute('ALTER TABLE building RENAME TO old_building')
        conn.execute('CREATE TABLE building AS SELECT * FROM old_building')
        conn.execute('DROP TABLE old_building')
        conn.execute(f'UPDATE building SET {column}=?',(value,))
    save(standard,load(standard),refresh_output=True)
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('addition',[',"profile":"duplicate"',',"unexpected":NaN',',"unexpected":Infinity'])
def test_strict_json(standard,tmp_path,area,addition):
    path=Path(standard['manifest']);data=path.read_text().rstrip();path.write_text(data[:-1]+addition+'}')
    fail(validate(tmp_path,area))


def test_aoi_and_config_rebound_tamper(standard,tmp_path,area):
    # Rebind hashes so this reaches actual membership, not only a hash check.
    area.write_text('study_area:\n  id: false\ncrs:\n  epsg: 6677\nextent:\n  xmin: 0\n  ymin: 0\n  xmax: 1\n  ymax: 1\n')
    m=load(standard);m['study_area'].update(id='false',extent=[0.,0.,1.,1.],config_sha256=sha(area));save(standard,m)
    fail(validate(tmp_path,area))


def test_config_locator_is_required(standard,tmp_path,area):
    report=validate(tmp_path,area,study_area_config=None)
    fail(report)
    assert report['issues'][0]['code']=='CONFIG_LOCATOR_REQUIRED'


def test_change_after_geometry_read_fails_closed(standard,tmp_path,area,monkeypatch):
    original=c.read_standard
    def mutate(*args):
        result=original(*args)
        with (tmp_path/'raw.gml').open('ab') as stream:stream.write(b'changed during validation')
        return result
    monkeypatch.setattr(c,'read_standard',mutate)
    report=validate(tmp_path,area);fail(report)
    assert report['issues'][0]['code']=='INPUT_CHANGED'


def test_only_persisted_pass_is_not_enough(standard,tmp_path,area):
    m=load(standard);m['validation']['buildings']['synthetic_tokyo']['vertices']=1;save(standard,m)
    fail(validate(tmp_path,area))


def test_nested_collection_success(plan,tmp_path,area):
    with db(tmp_path/'converter.gpkg') as conn:
        conn.execute("UPDATE gpkg_geometry_columns SET geometry_type_name='GEOMETRYCOLLECTION'")
        for key,faces in source_faces().items():
            nested=b'GP\x00\x01'+struct.pack('<i',6697)+struct.pack('<BII',1,1007,1)+blob(faces)[8:]
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(nested,key))
    refresh(plan,tmp_path);ingest_source_h(plan,artifact_root=tmp_path);run(tmp_path,area)
    report=validate(tmp_path,area)
    assert report['technical_validation']=='PASS',report
    assert all(b['geometry_type']=='GeometryCollection' for b in report['buildings'].values())


def test_polygon_success_with_hole(plan,tmp_path,area):
    from xml.etree import ElementTree as ET
    from test_source_h_ingestion import polygon_wkb
    xml=ET.parse(tmp_path/'raw.gml');b='http://www.opengis.net/citygml/building/2.0'
    for building in xml.findall(f'.//{{{b}}}Building'):
        for branch in building.findall(f'{{{b}}}boundedBy')[1:]:building.remove(branch)
    xml.write(tmp_path/'raw.gml',encoding='utf-8',xml_declaration=True)
    with db(tmp_path/'converter.gpkg') as conn:
        conn.execute("UPDATE gpkg_geometry_columns SET geometry_type_name='POLYGON'")
        for key,faces in source_faces().items():
            value=b'GP\x00\x01'+struct.pack('<i',6697)+polygon_wkb(faces[0])
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(value,key))
    refresh(plan,tmp_path,'raw');refresh(plan,tmp_path)
    ingest_source_h(plan,artifact_root=tmp_path);run(tmp_path,area)
    report=validate(tmp_path,area)
    assert report['technical_validation']=='PASS',report
    assert all(b['geometry_type']=='Polygon' and b['interior_rings']==1 for b in report['buildings'].values())


@pytest.mark.parametrize('flip_zero_sign',[False,True])
def test_H_signed_zero_binary64(plan,tmp_path,area,flip_zero_sign):
    from xml.etree import ElementTree as ET
    xml=ET.parse(tmp_path/'raw.gml')
    for node in xml.findall('.//{http://www.opengis.net/gml}posList'):
        values=node.text.split();values[2::3]=['-0.0']*len(values[2::3]);node.text=' '.join(values)
    xml.write(tmp_path/'raw.gml',encoding='utf-8',xml_declaration=True)
    with db(tmp_path/'converter.gpkg') as conn:
        for key,faces in source_faces().items():
            changed=tuple(tuple(tuple((x,y,-0.0) for x,y,z in ring) for ring in face) for face in faces)
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(blob(changed),key))
    refresh(plan,tmp_path,'raw');refresh(plan,tmp_path)
    ingest_source_h(plan,artifact_root=tmp_path);standard=run(tmp_path,area)
    if flip_zero_sign:
        with db(Path(standard['output'])) as conn:
            data=bytearray(conn.execute('SELECT geometry FROM building WHERE fid=1').fetchone()[0])
            struct.pack_into('<d',data,46,0.0)
            conn.execute('UPDATE building SET geometry=? WHERE fid=1',(bytes(data),))
        save(standard,load(standard),refresh_output=True)
    report=validate(tmp_path,area)
    if flip_zero_sign:fail(report)
    else:assert report['technical_validation']=='PASS',report


def test_filtered_aoi_membership_and_exclusions(native,tmp_path,area):
    from pyproj import Proj
    x,y=Proj('EPSG:6677')(139.57,35.63)
    area.write_text(f'study_area:\n  id: one\ncrs:\n  epsg: 6677\nextent:\n  xmin: {x-.1}\n  ymin: {y-.1}\n  xmax: {x+.1}\n  ymax: {y+.1}\n')
    run(tmp_path,area)
    report=validate(tmp_path,area)
    assert report['technical_validation']=='PASS',report
    assert report['selected_ids']==['synthetic_tokyo'] and report['excluded_ids']==['synthetic_niigata']


def test_same_bytes_file_replacement_detected(standard,tmp_path,area,monkeypatch):
    import os
    original=c.read_standard
    def mutate(*args):
        result=original(*args)
        target=tmp_path/'cli.exe';stamp=target.stat();replacement=tmp_path/'replacement.exe'
        replacement.write_bytes(target.read_bytes());os.utime(replacement,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        os.replace(replacement,target)
        return result
    monkeypatch.setattr(c,'read_standard',mutate)
    report=validate(tmp_path,area);fail(report)
    assert report['issues'][0]['code']=='INPUT_CHANGED'


def test_closed_ring_cyclic_reordering_is_not_normalized(standard,tmp_path,area):
    with db(Path(standard['output'])) as conn:
        data=bytearray(conn.execute('SELECT geometry FROM building WHERE fid=1').fetchone()[0])
        length=struct.unpack_from('<I',data,26)[0]
        values=[bytes(data[30+24*i:30+24*(i+1)]) for i in range(length-1)]
        rotated=values[1:]+values[:1];rotated.append(rotated[0])
        data[30:30+24*length]=b''.join(rotated)
        conn.execute('UPDATE building SET geometry=? WHERE fid=1',(bytes(data),))
    save(standard,load(standard),refresh_output=True)
    fail(validate(tmp_path,area))


def test_explicit_lod_and_nullable_height_success(plan,tmp_path,area):
    with db(tmp_path/'converter.gpkg') as conn:
        conn.execute('ALTER TABLE "bldg:Building" ADD COLUMN source_lod INTEGER')
        conn.execute('UPDATE "bldg:Building" SET source_lod=2,measuredHeight=NULL')
    refresh(plan,tmp_path);ingest_source_h(plan,artifact_root=tmp_path);run(tmp_path,area)
    report=validate(tmp_path,area)
    assert report['technical_validation']=='PASS',report


def test_chain_artifact_traversal_even_with_rebound_records(standard,native,tmp_path,area):
    nm=json.loads(Path(native['manifest']).read_text())
    nm['artifacts']['raw']['path']='../raw.gml'
    Path(native['manifest']).write_text(json.dumps(nm))
    nr=json.loads(Path(native['receipt']).read_text());nr['manifest_sha256']=sha(native['manifest'])
    Path(native['receipt']).write_text(json.dumps(nr))
    m=load(standard);m.update(source_chain=nm)
    m['native_manifest']['sha256']=sha(native['manifest']);m['native_receipt']['sha256']=sha(native['receipt'])
    save(standard,m)
    report=validate(tmp_path,area);fail(report)
    assert report['issues'][0]['code']=='PATH_INVALID'


def test_layer_mismatch(standard,tmp_path,area):
    m=load(standard);m['standard_output']['layer']='unrecorded';save(standard,m)
    fail(validate(tmp_path,area))


def test_rehashed_native_geometry_correspondence_rechecked(standard,native,tmp_path,area):
    with db(Path(native['output'])) as conn:
        data=bytearray(conn.execute('SELECT geometry FROM "bldg:Building" WHERE fid=1').fetchone()[0])
        struct.pack_into('<d',data,46,123.)
        conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE fid=1',(bytes(data),))
    nm=json.loads(Path(native['manifest']).read_text());nm['artifacts']['native']['sha256']=sha(native['output'])
    Path(native['manifest']).write_text(json.dumps(nm))
    nr=json.loads(Path(native['receipt']).read_text());nr.update(native_sha256=sha(native['output']),manifest_sha256=sha(native['manifest']))
    Path(native['receipt']).write_text(json.dumps(nr))
    m=load(standard);m['source_chain']=nm;m['native_input']['sha256']=sha(native['output'])
    m['native_manifest']['sha256']=sha(native['manifest']);m['native_receipt']['sha256']=sha(native['receipt']);save(standard,m)
    fail(validate(tmp_path,area))


@pytest.mark.parametrize('locator',['/rooted.gpkg','\\rooted.gpkg','C:relative.gpkg','C:/absolute.gpkg'])
def test_rooted_and_drive_locators_rejected_before_resolution(tmp_path,locator):
    from ouem.native.building.source_h_geometry import GeometryValidationError
    with pytest.raises(GeometryValidationError) as error:c.Watch(tmp_path).resolve(locator)
    assert error.value.code=='PATH_INVALID'


@pytest.mark.parametrize('target',['ingestion','foundation','processed_at'])
def test_native_persisted_validation_must_match_actual(standard,native,tmp_path,area,target):
    nm=json.loads(Path(native['manifest']).read_text())
    if target=='ingestion':nm['validation']['ingestion']['gpkg_structure']='FAILED'
    elif target=='foundation':nm['validation']['foundation']['issues']=[{'reason':'contradictory issue'}]
    else:nm['validation']['processed_at']=None
    Path(native['manifest']).write_text(json.dumps(nm))
    nr=json.loads(Path(native['receipt']).read_text());nr['manifest_sha256']=sha(native['manifest'])
    Path(native['receipt']).write_text(json.dumps(nr))
    m=load(standard);m['source_chain']=nm;m['native_manifest']['sha256']=sha(native['manifest'])
    m['native_receipt']['sha256']=sha(native['receipt']);save(standard,m)
    fail(validate(tmp_path,area))
