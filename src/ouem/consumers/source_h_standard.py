"""Read-only candidate source-H Standard consumer. Never executes an engine/writer."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import stat

from pyproj import Transformer

from ouem.native.building.provenance import SOURCE_H_PROFILE, identify_profile, validate_source_h_record
from ouem.native.building.source_h_geometry import require, inspect_geopackage, compare_snapshots
from ouem.native.building.source_h_lod2 import read_lod2, compare_lod2
from ouem.study_area import load_study_area
from ._source_h_geometry import read_standard, verify_geometry, XY_TOLERANCE_M

SCHEMA = 'ouem-standard-building-manifest/v0.2'
RECEIPT = 'ouem-standard-building-receipt/v0.2'
VERTICAL = {'horizontal_crs':'EPSG:6677','vertical_quantity':'gravity_related_height',
    'vertical_crs':'EPSG:6695','vertical_unit':'metre','vertical_operation':'identity_H',
    'horizontal_operation':'EPSG:6668 -> EPSG:6677','source_horizontal_crs':'EPSG:6668',
    'source_compound_crs':'EPSG:6697'}
LIMITS = ['Technical point-in-time validation only; no eligibility, datum accuracy or acceptance approval.',
    'Hashes and coordinate correspondence do not authenticate original execution claims, source declarations or reviewers.',
    'Bounded candidate ISO WKB Z / inline Raw LoD2 scope; not a complete CityGML or solid-topology validator.',
    'Pre/post hashes, metadata and resolved-path checks are best-effort TOCTOU detection, not an atomic snapshot or lock.',
    'Later Adapter must revalidate at use or bind immutable verified inputs; this report is not an authorization token.',
    'No Terrain compatibility, coverage, grid fusion, voxelization or solar validation; Phase 5 A1-A4 remain OPEN.']


def exact(actual, expected, field):
    require(type(actual) is type(expected) and actual == expected, field, 'unexpected value/type', 'DECLARATION_MISMATCH')


def obj(value, keys, field, optional=()):
    require(type(value) is dict and keys <= value.keys() and value.keys() <= keys | set(optional), field, 'missing/unknown object fields')
    return value


def text(value, field):
    require(type(value) is str and value.strip(), field, 'nonblank text required')


def number(value, field):
    require(type(value) in (int,float) and math.isfinite(value), field, 'finite number required')


def digest_text(value, field):
    require(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value), field, 'SHA-256 required')


def strict_json(data):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'JSON', 'duplicate key')
            result[key] = value
        return result
    def numeric(value):
        result = float(value)
        require(math.isfinite(result), 'JSON', 'nonfinite value')
        return result
    return json.loads(data.decode('utf-8'),object_pairs_hook=unique,parse_float=numeric,parse_constant=numeric)


def same_json(a, b, field):
    require(json.dumps(a,sort_keys=True,allow_nan=False) == json.dumps(b,sort_keys=True,allow_nan=False),field,'record mismatch')


class Watch:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        require(self.root.is_dir(), 'artifact_root', 'directory required')
        self.identities = {}

    def resolve(self, locator):
        text(locator, 'locator')
        relative = Path(locator)
        win = PureWindowsPath(locator)
        require(not relative.is_absolute() and not win.drive and not win.root and not win.is_absolute()
                and '..' not in relative.parts and '..' not in win.parts and '\x00' not in locator,
                'locator', 'relative confined path required', 'PATH_INVALID')
        resolved = (self.root/relative).resolve(strict=True)
        require(resolved.is_relative_to(self.root), 'locator', 'resolved path escapes root', 'PATH_INVALID')
        return resolved

    @staticmethod
    def stamp(info):
        return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)

    def scan(self, locator, *, json_data=False):
        path = self.resolve(locator)
        require(not any(Path(str(path)+s).exists() for s in ('-wal','-shm','-journal')), locator, 'live sidecar not frozen input')
        require(stat.S_ISREG(path.stat().st_mode), locator, 'regular file required')
        digest = hashlib.sha256()
        chunks = []
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode), locator, 'regular file required')
            require(not json_data or before.st_size <= 16*1024*1024, locator, 'JSON exceeds16MiB budget')
            remaining, count = before.st_size+1, 0
            while remaining:
                chunk=stream.read(min(1024*1024,remaining))
                if not chunk:break
                digest.update(chunk)
                if json_data:chunks.append(chunk)
                remaining-=len(chunk)
                count+=len(chunk)
            after = os.fstat(stream.fileno())
        require(count==before.st_size and self.stamp(before)==self.stamp(after)==self.stamp(path.stat())
                and self.resolve(locator)==path, locator, 'changed during read', 'INPUT_CHANGED')
        return {'path':locator,'resolved_path':path.relative_to(self.root).as_posix(),
                'size_bytes':after.st_size,'sha256':digest.hexdigest(),'stamp':self.stamp(after)}, b''.join(chunks)

    def capture(self, key, locator, sha=None, size=None, *, json_data=False):
        identity,data = self.scan(locator,json_data=json_data)
        if key in self.identities:
            exact(identity,self.identities[key],key)
        else:
            self.identities[key] = identity
        if sha is not None:
            digest_text(sha,key+'.sha256')
            require(identity['sha256']==sha,key,'SHA-256 mismatch','HASH_MISMATCH')
        if size is not None:
            require(type(size) is int and size >= 0,key,'nonnegative integer size required')
            require(identity['size_bytes']==size,key,'size mismatch','HASH_MISMATCH')
        return strict_json(data) if json_data else self.resolve(locator)

    def unchanged(self):
        for key, before in self.identities.items():
            after,_ = self.scan(before['path'])
            require(after==before,key,'input changed during validation','INPUT_CHANGED')


def entry_locator(value, root):
    require(isinstance(value,(str,Path)), 'argument.path', 'path required')
    path = Path(value)
    if path.is_absolute():
        path = path.relative_to(root)  # Watch still checks unresolved symlinks
    return path.as_posix()


def manifest_format(m, expected):
    keys = {'schema','status','execution_status','processed_at','profile','native_input','native_manifest','native_receipt',
        'source_chain','standard_output','study_area','selection','selected_ids','excluded_ids','input_features',
        'output_features','metadata_mapping','selected_lod_by_id','coordinate_operation','validation',
        'source_h_eligibility','human_review','formal_acceptance','implementation'} | VERTICAL.keys()
    obj(m,set(keys),'manifest',('extensions',))
    if 'extensions' in m:require(type(m['extensions']) is dict,'extensions','object required')
    exact(m['schema'],SCHEMA,'schema')
    exact(m['profile'],expected,'profile')
    identify_profile(m['profile'])
    for key,value in VERTICAL.items():exact(m[key],value,key)
    for key,value in {'status':'EXPERIMENTAL','execution_status':'COMPLETED','source_h_eligibility':'NOT_ESTABLISHED',
                      'human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED'}.items():exact(m[key],value,key)
    text(m['processed_at'],'processed_at')
    require(datetime.fromisoformat(m['processed_at'].replace('Z','+00:00')).tzinfo is not None,'processed_at','timezone required')
    for name in ('native_manifest','native_receipt'):
        obj(m[name],{'path','sha256'},name);text(m[name]['path'],name);digest_text(m[name]['sha256'],name)
    obj(m['native_input'],{'path','sha256','layer'},'native_input')
    obj(m['standard_output'],{'path','sha256','size_bytes','layer'},'standard_output')
    for name in ('native_input','standard_output'):
        text(m[name]['path'],name);text(m[name]['layer'],name);digest_text(m[name]['sha256'],name)
    require(type(m['standard_output']['size_bytes']) is int and m['standard_output']['size_bytes']>0,'standard_output.size','positive integer required')
    area=obj(m['study_area'],{'id','epsg','extent','config_sha256'},'study_area')
    text(area['id'],'study_area.id');exact(area['epsg'],6677,'study_area.epsg');digest_text(area['config_sha256'],'study_area.config_sha256')
    require(type(area['extent']) is list and len(area['extent'])==4,'study_area.extent','four coordinates required')
    for v in area['extent']:number(v,'study_area.extent')
    x0,y0,x1,y1=area['extent'];require(x0<x1 and y0<y1,'study_area.extent','invalid rectangle')
    exact(m['selection'],'2D intersection with closed study-area rectangle; complete geometry retained; no clipping','selection')
    for name in ('selected_ids','excluded_ids'):
        values=m[name]
        require(type(values) is list and all(type(v) is str and v.strip() for v in values)
                and len(values)==len(set(values)),name,'unique nonblank ID list required')
    for name in ('input_features','output_features'):
        require(type(m[name]) is int and m[name]>0,name,'positive integer required')
    same_json(m['metadata_mapping'],{'source_id':'Native id','source_lod':'existing recognized field or null; no inference',
        'measured_height':'measuredHeight/measured_height or null','source_dataset':'PLATEAU CityGML',
        'ouem_id':'unchanged oub- UUIDv5 URL namespace v0.1 rule'},'metadata_mapping')
    require(type(m['selected_lod_by_id']) is dict,'selected_lod_by_id','object required')
    for lod in m['selected_lod_by_id'].values():exact(lod,2,'selected_lod_by_id')
    op=obj(m['coordinate_operation'],{'always_xy','meaning','input_storage_axes','output_storage_axes','arguments',
        'definition','description','accuracy_m','allow_ballpark','only_best'},'coordinate_operation')
    for key,value in {'always_xy':True,'allow_ballpark':False,'only_best':True,
        'meaning':'input GIS longitude/latitude -> easting/northing','input_storage_axes':['longitude','latitude','H'],
        'output_storage_axes':['easting','northing','H'],'arguments':'XY only; original H never passed to PROJ'}.items():exact(op[key],value,'coordinate_operation.'+key)
    text(op['description'],'coordinate_operation.description');number(op['accuracy_m'],'coordinate_operation.accuracy')
    # Declaration check only. Actual coordinates use the independent Proj reader.
    reference=Transformer.from_crs(6668,6677,always_xy=True,allow_ballpark=False,only_best=True)
    exact(op['definition'],reference.definition,'coordinate_operation.definition')
    exact(float(op['accuracy_m']),reference.accuracy,'coordinate_operation.accuracy')
    impl=obj(m['implementation'],{'id','python','pyproj','proj','module_sha256'},'implementation')
    exact(impl['id'],'source-h-standardizer-step3/v0.1','implementation.id')
    for key in ('python','pyproj','proj'):text(impl[key],'implementation.'+key)
    hashes=obj(impl['module_sha256'],{'source_h.py','source_h_geometry.py'},'module_sha256')
    for value in hashes.values():digest_text(value,'module_sha256')


def source_chain(watch, m):
    record=watch.capture('native_manifest',m['native_manifest']['path'],m['native_manifest']['sha256'],json_data=True)
    require(type(record) is dict,'native_manifest','object required')
    same_json(m['source_chain'],record,'source_chain')
    exact(record['profile'],m['profile'],'native.profile')
    for name in ('eligibility_review','acceptance'):
        same_json(record.get(name),{'status':'NOT_VERIFIED'},'native.'+name)
    validation=obj(record['validation'],{'execution_status','processed_at','foundation','ingestion'},'native.validation')
    exact(validation['execution_status'],'COMPLETED','native.execution_status')
    text(validation['processed_at'],'native.processed_at')
    require(datetime.fromisoformat(validation['processed_at'].replace('Z','+00:00')).tzinfo is not None,
            'native.processed_at','timezone required')
    for key,value in {'source_h_eligibility':'NOT_ESTABLISHED','human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED'}.items():
        exact(record['validation']['ingestion'][key],value,'native.ingestion.'+key)
    for key,value in {'format_status':'PASS','file_hash_status':'PASS','foundation_valid':True,
        'eligibility':'NOT_ESTABLISHED','human_review_status':'NOT_VERIFIED',
        'formal_acceptance_status':'NOT_VERIFIED','converter_qualification_status':'NOT_VERIFIED',
        'coordinate_geometry_status':'NOT_RUN'}.items():
        exact(record['validation']['foundation'][key],value,'native.foundation.'+key)
    format_report=validate_source_h_record(record,verify_files=False,artifact_root=watch.root)
    require(format_report.format_status=='PASS','native.format',json.dumps(format_report.to_dict()))
    artifacts=record['artifacts']
    require(type(artifacts) is dict,'native.artifacts','object required')
    for key,ref in artifacts.items():
        require(type(ref) is dict,'artifact','object required')
        watch.capture('chain.'+key,ref['path'],ref['sha256'],ref['size_bytes'])
    report=validate_source_h_record(record,artifact_root=watch.root)
    require(report.foundation_valid,'native.provenance',json.dumps(report.to_dict()))
    same_json(validation['foundation'],report.to_dict(),'native.foundation')
    native_id=record['native']['output_artifact_id'];native_ref=artifacts[native_id]
    same_json(m['native_input'],{k:native_ref[k] for k in ('path','sha256','layer')},'native_input')
    native=watch.resolve(native_ref['path'])
    require(watch.resolve(m['native_manifest']['path'])==native.with_suffix('.gpkg.manifest.json'),'native_manifest','not adjacent')
    require(watch.resolve(m['native_receipt']['path'])==native.with_suffix('.gpkg.receipt.json'),'native_receipt','not adjacent')
    receipt=watch.capture('native_receipt',m['native_receipt']['path'],m['native_receipt']['sha256'],json_data=True)
    same_json(receipt,{'schema':'ouem-plateau-native-receipt/v0.2','profile':m['profile'],'status':'COMPLETED',
        'eligibility':'NOT_ESTABLISHED','native_sha256':native_ref['sha256'],'manifest_sha256':m['native_manifest']['sha256']},'native_receipt')
    snapshot=inspect_geopackage(native,native_ref['layer'])
    converter=artifacts[record['native']['input_artifact_id']]
    actual_qa=compare_snapshots(inspect_geopackage(watch.resolve(converter['path']),converter['layer']),snapshot)
    raw,excluded=read_lod2(watch.resolve(a['path']) for a in artifacts.values() if a['role']=='raw_citygml')
    actual_qa.update(compare_lod2(snapshot,raw))
    actual_qa.update(gpkg_structure='PASS',source_h_eligibility='NOT_ESTABLISHED',human_review='NOT_VERIFIED',
                     formal_acceptance='NOT_VERIFIED',excluded_no_lod2_ids=excluded)
    same_json(validation['ingestion'],actual_qa,'native.ingestion')
    return snapshot,native


def _validate(watch, m, manifest_locator, config_locator):
    output=m['standard_output']
    standard=watch.capture('standard',output['path'],output['sha256'],output['size_bytes'])
    require(watch.resolve(manifest_locator)==standard.with_suffix('.gpkg.manifest.json'),'manifest','not adjacent to Standard')
    receipt_locator=standard.with_suffix('.gpkg.receipt.json').relative_to(watch.root).as_posix()
    receipt=watch.capture('standard_receipt',receipt_locator,json_data=True)
    same_json(receipt,{'schema':RECEIPT,'profile':m['profile'],'status':'COMPLETED','eligibility':'NOT_ESTABLISHED',
        'standard_sha256':output['sha256'],'manifest_sha256':watch.identities['standard_manifest']['sha256']},'standard_receipt')
    native,native_path=source_chain(watch,m)
    require(config_locator is not None,'study_area_config','explicit confined locator required; manifest has hash but no path','CONFIG_LOCATOR_REQUIRED')
    config=watch.capture('study_area_config',config_locator,m['study_area']['config_sha256'])
    area=load_study_area(config)
    same_json({'id':area.id,'epsg':area.epsg,'extent':list(area.extent)},
              {k:m['study_area'][k] for k in ('id','epsg','extent')},'study_area.config')
    actual=read_standard(standard,output['layer'])
    qa=verify_geometry(native,native_path,actual,m['study_area']['extent'])
    require(set(m['selected_ids'])==qa['selected'] and set(m['excluded_ids'])==qa['excluded'],'selected/excluded_ids','ID membership mismatch')
    exact(m['input_features'],len(native.features),'input_features');exact(m['output_features'],len(actual),'output_features')
    require(m['selected_lod_by_id'].keys()==actual.keys(),'selected_lod_by_id','ID membership mismatch')
    persisted=obj(m['validation'],{'all_vertex_H_exact','structure_order_ids_attributes','independent_XY','max_xy_error_m',
        'xy_tolerance_m','h_tolerance_m','buildings'},'validation')
    for key in ('all_vertex_H_exact','structure_order_ids_attributes','independent_XY'):exact(persisted[key],'PASS','validation.'+key)
    exact(persisted['h_tolerance_m'],0,'validation.h_tolerance_m')
    number(persisted['xy_tolerance_m'],'validation.xy_tolerance_m');exact(float(persisted['xy_tolerance_m']),XY_TOLERANCE_M,'validation.xy_tolerance_m')
    number(persisted['max_xy_error_m'],'validation.max_xy_error_m')
    require(0<=persisted['max_xy_error_m']<=XY_TOLERANCE_M,'validation.max_xy_error_m','out of budget')
    same_json(persisted['buildings'],qa['buildings'],'validation.counts')
    return {'feature_count':len(actual),'native_feature_count':len(native.features),'vertex_count':qa['vertices'],
        'selected_ids':sorted(qa['selected']),'excluded_ids':sorted(qa['excluded']),
        'xy_h_qa':{'H_binary64_exact':'PASS','ordered_geometry':'PASS','XY':'PASS',
            'xy_tolerance_m':XY_TOLERANCE_M,'max_xy_error_m':qa['max_xy_error_m'],'h_tolerance_m':0},'buildings':qa['buildings']}


def validate_source_h_standard(standard_manifest, artifact_root, expected_profile, *, study_area_config=None):
    """Return a structured report; never write, standardize, launch an engine or approve.

    Candidate manifests have no config locator: pass it explicitly inside root.
    A missing locator fails closed rather than scanning or trusting its hash alone.
    """
    result={'technical_validation':'FAIL','verified_profile':None,'verified_schema':None,'artifacts':{},
        'feature_count':None,'vertex_count':None,'xy_h_qa':{'status':'NOT_RUN'},'issues':[],
        'validation_scope':'source-h-standard-consumer/v0.1','limitations':list(LIMITS),
        'phase5_gates':{'A1':'OPEN','A2':'OPEN','A3':'OPEN','A4':'OPEN'},
        'source_h_eligibility':'NOT_ESTABLISHED','human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED'}
    watch=None
    try:
        exact(expected_profile,SOURCE_H_PROFILE,'expected_profile');identify_profile(expected_profile)
        watch=Watch(artifact_root)
        locator=entry_locator(standard_manifest,watch.root)
        m=watch.capture('standard_manifest',locator,json_data=True)
        manifest_format(m,expected_profile)
        result.update(verified_profile=m['profile'],verified_schema=m['schema'])
        config=entry_locator(study_area_config,watch.root) if study_area_config is not None else None
        result.update(_validate(watch,m,locator,config))
        watch.unchanged()
        result['input_immutability_checks']='PASS'
        result['technical_validation']='PASS'
    except Exception as exc:
        result['issues'].append({'code':getattr(exc,'code','VALIDATION_FAILED'),
            'field':getattr(exc,'field','consumer'),'reason':str(exc)})
    finally:
        if watch:result['artifacts']=watch.identities
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('standard-manifest','artifact-root','expected-profile','study-area-config'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    result=validate_source_h_standard(args.standard_manifest,args.artifact_root,args.expected_profile,
        study_area_config=args.study_area_config)
    print(json.dumps(result,indent=2))
    return 0 if result['technical_validation']=='PASS' else 2


if __name__=='__main__':
    raise SystemExit(main())
