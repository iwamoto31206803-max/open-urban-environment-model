"""Synthetic actual GPKG/Raw chain; no GDAL or Converter executable required."""
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import struct

import pytest
from pyproj import Proj

from test_source_h_ingestion import plan, db, refresh, mutate_geometry, blob, source_faces
from ouem.native.building.source_h import ingest_source_h
from ouem.native.building.provenance import SOURCE_H_PROFILE
from ouem.standardize.building import source_h as s
from ouem.standardize.building import source_h_geometry as g
from ouem.standardize.building import deterministic_ouem_id


@pytest.fixture
def native(plan,tmp_path):
    return ingest_source_h(plan,artifact_root=tmp_path)


@pytest.fixture
def area(tmp_path):
    p=tmp_path/'area.yaml'
    p.write_text('study_area:\n  id: synthetic-both\ncrs:\n  epsg: 6677\nextent:\n  xmin: -1000000\n  ymin: -1000000\n  xmax: 1000000\n  ymax: 1000000\n')
    return p


def run(tmp_path,area,**kwargs):
    values=dict(profile=SOURCE_H_PROFILE,native_manifest='native-run/native.gpkg.manifest.json',
        artifact_root=tmp_path,output='standard-run/standard.gpkg',study_area_config=area)
    values.update(kwargs)
    return s.standardize_source_h(**values)


def test_full_xy_h_ids_holes_nullable_metadata_and_hashes(native,tmp_path,area):
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result=run(tmp_path,area)
    qa=result['qa']
    assert qa['all_vertex_H_exact']=='PASS' and qa['h_tolerance_m']==0
    assert qa['independent_XY']=='PASS' and qa['max_xy_error_m']<=1e-7
    for c in qa['buildings'].values():
        assert c==dict(geometry_type='MultiPolygon',faces=10,exterior_rings=10,interior_rings=2,vertices=60)
    manifest=json.loads(Path(result['manifest']).read_text())
    receipt=json.loads(Path(result['receipt']).read_text())
    assert manifest['schema']==s.SCHEMA
    assert manifest['horizontal_crs']=='EPSG:6677' and manifest['vertical_crs']=='EPSG:6695'
    assert manifest['vertical_operation']=='identity_H'
    assert manifest['source_h_eligibility']=='NOT_ESTABLISHED'
    assert manifest['human_review']==manifest['formal_acceptance']=='NOT_VERIFIED'
    assert manifest['standard_output']['sha256']==s.digest(result['output'])==receipt['standard_sha256']
    assert receipt['manifest_sha256']==s.digest(result['manifest'])
    assert manifest['selected_lod_by_id']=={'synthetic_tokyo':2,'synthetic_niigata':2}
    with closing(sqlite3.connect(result['output'])) as conn:
        rows=conn.execute('SELECT source_id,ouem_id,source_lod,measured_height FROM building').fetchall()
    assert set((r[0],r[1],r[2]) for r in rows)=={(key,deterministic_ouem_id(key),None) for key in source_faces()}
    assert all(p.read_bytes()==value for p,value in before.items())


def test_transform_receives_only_xy(native,tmp_path,area,monkeypatch):
    original=s.Transformer.from_crs
    calls=[]
    class Spy:
        def __init__(self):self.actual=original(6668,6677,always_xy=True,allow_ballpark=False,only_best=True)
        def transform(self,*args,**kwargs):
            assert len(args)==2
            calls.append(args)
            return self.actual.transform(*args,**kwargs)
        def __getattr__(self,name):return getattr(self.actual,name)
    def factory(a,b,**kwargs):
        assert (a,b)==(6668,6677) and kwargs==dict(always_xy=True,allow_ballpark=False,only_best=True)
        return Spy()
    monkeypatch.setattr(s.Transformer,'from_crs',factory)
    run(tmp_path,area)
    assert len(calls)==120


@pytest.mark.parametrize('profile',[None,'unknown','ouem-native-building/plateau-source-h/v9','ouem-native-building/plateau-legacy-4979-claimed-tp/v0.1'])
def test_exact_dispatch_no_legacy_fallback(native,tmp_path,area,profile):
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area,profile=profile)
    assert not (tmp_path/'standard-run').exists()


@pytest.mark.parametrize('target',['native','converter','raw','receipt','manifest'])
def test_hash_and_record_mutations_fail_closed(native,tmp_path,area,target):
    paths={'native':tmp_path/'native-run/native.gpkg','converter':tmp_path/'converter.gpkg','raw':tmp_path/'raw.gml',
        'receipt':Path(native['receipt']),'manifest':Path(native['manifest'])}
    with paths[target].open('ab') as f:f.write(b'changed')
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)
    assert not (tmp_path/'standard-run').exists()


@pytest.mark.parametrize('step',['write','postwrite','publish','manifest'])
def test_incomplete_output_rolls_back_only_own_run(native,tmp_path,area,monkeypatch,step):
    if step=='write':
        def fail(path,*args):path.write_bytes(b'incomplete');raise OSError('write failure')
        monkeypatch.setattr(s,'write_standard',fail)
    elif step=='postwrite':
        def fail(*args):raise ValueError('reopen QA failed')
        monkeypatch.setattr(s,'audit_standard',fail)
    else:
        original=s._publish
        def fail(src,dst):
            if step=='publish' or dst.name.endswith('manifest.json'):raise OSError('publish failure')
            original(src,dst)
        monkeypatch.setattr(s,'_publish',fail)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)
    assert not (tmp_path/'standard-run').exists()
    assert Path(native['output']).exists()


def test_existing_accepted_files_protected(native,tmp_path,area):
    folder=tmp_path/'standard-run';folder.mkdir()
    for name in ('standard.gpkg','standard.gpkg.manifest.json','standard.gpkg.receipt.json'):
        (folder/name).write_bytes(b'accepted historical '+name.encode())
    before={p:p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)
    assert all(p.read_bytes()==value for p,value in before.items())


def test_partial_aoi_selects_whole_building(native,tmp_path,area):
    lon,lat,_=g.points(('MultiPolygon',tuple(('Polygon',f) for f in source_faces()['synthetic_tokyo'])))[0]
    x,y=Proj('EPSG:6677')(lon,lat)
    area.write_text(f'study_area:\n  id: tiny\ncrs:\n  epsg: 6677\nextent:\n  xmin: {x-0.1}\n  ymin: {y-0.1}\n  xmax: {x+0.1}\n  ymax: {y+0.1}\n')
    result=run(tmp_path,area)
    assert set(result['qa']['buildings'])=={'synthetic_tokyo'}
    assert result['qa']['buildings']['synthetic_tokyo']['vertices']==60


def test_geometry_collection_preserves_nested_type(plan,tmp_path,area):
    with db(tmp_path/'converter.gpkg') as conn:
        conn.execute("UPDATE gpkg_geometry_columns SET geometry_type_name='GEOMETRYCOLLECTION'")
        for key,faces in source_faces().items():
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(blob(faces,True),key))
    refresh(plan,tmp_path)
    ingest_source_h(plan,artifact_root=tmp_path)
    result=run(tmp_path,area)
    assert all(v['geometry_type']=='GeometryCollection' for v in result['qa']['buildings'].values())


@pytest.mark.parametrize('field,value',[('srs_id',4979),('srs_id',6677),('z',0)])
def test_native_crs_or_z_conflict_even_after_rehash(native,tmp_path,area,field,value):
    with db(Path(native['output'])) as conn:conn.execute(f'UPDATE gpkg_geometry_columns SET {field}=?',(value,))
    rehash_native(native,tmp_path)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)


def rehash_native(native,root):
    manifest=Path(native['manifest']);r=json.loads(manifest.read_text());ref=r['artifacts']['native']
    ref.update(sha256=s.digest(native['output']),size_bytes=Path(native['output']).stat().st_size)
    manifest.write_text(json.dumps(r))
    receipt=Path(native['receipt']);v=json.loads(receipt.read_text());v.update(native_sha256=s.digest(native['output']),manifest_sha256=s.digest(manifest));receipt.write_text(json.dumps(v))


@pytest.mark.parametrize('value',[float('nan'),float('inf')])
def test_nonfinite_native_refused(native,tmp_path,area,value):
    def change(data):
        data=bytearray(data);struct.pack_into('<d',data,46,value);return bytes(data)
    mutate_geometry(Path(native['output']),change);rehash_native(native,tmp_path)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)


def test_wrong_axis_operation_independent_oracle_rejects(native,tmp_path,area,monkeypatch):
    original=s.map_xy
    def wrong(tree,transform):return original(tree,lambda lon,lat:(lon,lat))
    monkeypatch.setattr(s,'map_xy',wrong)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)


def test_h_or_vertex_order_corruption_detected(native,tmp_path,area,monkeypatch):
    original=s.write_standard
    def corrupt(path,features,attrs,timestamp):
        original(path,features,attrs,timestamp)
        with db(path) as conn:
            data=conn.execute('SELECT geometry FROM building WHERE fid=1').fetchone()[0]
            data=bytearray(data);struct.pack_into('<d',data,46,999.)
            conn.execute('UPDATE building SET geometry=? WHERE fid=1',(bytes(data),))
    monkeypatch.setattr(s,'write_standard',corrupt)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)
    assert not (tmp_path/'standard-run').exists()


def test_nullable_lod_is_not_inferred_and_conflicts_fail(native,tmp_path,area):
    with db(Path(native['output'])) as conn:
        conn.execute('ALTER TABLE "bldg:Building" ADD COLUMN source_lod TEXT')
        conn.execute('UPDATE "bldg:Building" SET source_lod=\'1\'')
    rehash_native(native,tmp_path)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)


def test_output_path_escape_and_no_selected_data(native,tmp_path,area):
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area,output='../escaped.gpkg')
    area.write_text('study_area:\n  id: empty\ncrs:\n  epsg: 6677\nextent:\n  xmin: 0\n  ymin: 0\n  xmax: 1\n  ymax: 1\n')
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)


def test_native_changed_during_write_rolls_back(native,tmp_path,area,monkeypatch):
    original=s.write_standard
    def change(*args):
        original(*args)
        with Path(native['receipt']).open('ab') as f:f.write(b'changed')
    monkeypatch.setattr(s,'write_standard',change)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)
    assert not (tmp_path/'standard-run').exists()


def test_source_axis_declaration_conflict_rejected(native,tmp_path,area):
    manifest=Path(native['manifest']);r=json.loads(manifest.read_text())
    r['coordinate_contract']['storage_axes']=['latitude','longitude','H']
    manifest.write_text(json.dumps(r));receipt=Path(native['receipt']);v=json.loads(receipt.read_text())
    v['manifest_sha256']=s.digest(manifest);receipt.write_text(json.dumps(v))
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)


def test_signed_zero_H_bits_preserved(plan,tmp_path,area):
    # Raw, Converter and Native must correspond; author negative zero in all
    # source Z positions first, then let real ingestion validate the chain.
    raw=tmp_path/'raw.gml'
    from xml.etree import ElementTree as ET
    xml=ET.parse(raw)
    for node in xml.findall('.//{http://www.opengis.net/gml}posList'):
        values=node.text.split()
        values[2::3]=['-0.0']*len(values[2::3]);node.text=' '.join(values)
    xml.write(raw,encoding='utf-8',xml_declaration=True)
    with db(tmp_path/'converter.gpkg') as conn:
        for identifier,faces in source_faces().items():
            changed=tuple(tuple(tuple((x,y,-0.0) for x,y,z in ring) for ring in face) for face in faces)
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',(blob(changed),identifier))
    refresh(plan,tmp_path,'raw');refresh(plan,tmp_path)
    ingest_source_h(plan,artifact_root=tmp_path)
    assert run(tmp_path,area)['qa']['all_vertex_H_exact']=='PASS'


def test_final_output_mutation_prevents_completion(native,tmp_path,area,monkeypatch):
    original=s._publish
    def alter(src,dst):
        original(src,dst)
        if dst.suffix=='.gpkg':
            with db(dst) as conn:conn.execute("UPDATE building SET source_id='changed' WHERE fid=1")
    monkeypatch.setattr(s,'_publish',alter)
    with pytest.raises(s.SourceHStandardError):run(tmp_path,area)
    assert not (tmp_path/'standard-run').exists()


def test_numeric_lod_copied_nullable_height_preserved(plan,tmp_path,area):
    with db(tmp_path/'converter.gpkg') as conn:
        conn.execute('ALTER TABLE "bldg:Building" ADD COLUMN source_lod INTEGER')
        conn.execute('UPDATE "bldg:Building" SET source_lod=2,measuredHeight=NULL')
    refresh(plan,tmp_path);ingest_source_h(plan,artifact_root=tmp_path)
    result=run(tmp_path,area)
    with closing(sqlite3.connect(result['output'])) as conn:
        assert conn.execute('SELECT source_lod,measured_height FROM building').fetchall()==[('2',None),('2',None)]


def test_preexisting_authored_horizontal_controls(native,tmp_path,area):
    result=run(tmp_path,area)
    from shapely import from_wkb
    expected=json.loads((Path(__file__).parent/'fixtures/plateau_converter/expected.json').read_text())
    source=source_faces()
    with closing(sqlite3.connect(result['output'])) as conn:
        output={key:g.from_shape(from_wkb(data[8:])) for key,data in conn.execute('SELECT source_id,geometry FROM building')}
    for building in expected['buildings']:
        key=building['id']
        originals=g.points(('MultiPolygon',tuple(('Polygon',f) for f in source[key])))
        actual=g.points(output[key])
        controls={tuple(c['expected_gpkg_lon_lat']):c['expected_6677_easting_northing'] for c in building['horizontal_control_points']}
        for a,b in zip(originals,actual):
            # Authored expectation uses computed 35.630100000000006, while XML
            # serializes 35.6301. Match only within 1e-12 degree, then check XY
            # against the unchanged pre-existing numerical reference.
            key_xy=min(controls,key=lambda xy:max(abs(xy[i]-a[i]) for i in (0,1)))
            assert max(abs(key_xy[i]-a[i]) for i in (0,1))<=1e-12
            assert max(abs(b[i]-controls[key_xy][i]) for i in (0,1))<=g.XY_TOLERANCE_M
            assert a[2]==b[2]
