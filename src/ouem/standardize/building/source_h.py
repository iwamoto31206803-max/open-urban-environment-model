"""Explicit experimental source-H dispatch; legacy Standardizer is untouched."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import tempfile
from datetime import datetime, timezone

import pyproj
from pyproj import Transformer

from ouem.native.building.provenance import SOURCE_H_PROFILE, load_source_h_record, identify_profile
from ouem.native.building.source_h_geometry import inspect_geopackage, compare_snapshots, require
from ouem.native.building.source_h_lod2 import read_lod2, compare_lod2
from ouem.study_area import load_study_area
from .source_h_geometry import map_xy, intersects, read_attributes, write_standard, audit_standard

SCHEMA = 'ouem-standard-building-manifest/v0.2'
RECEIPT_SCHEMA = 'ouem-standard-building-receipt/v0.2'
VERTICAL = {'horizontal_crs':'EPSG:6677','vertical_quantity':'gravity_related_height',
    'vertical_crs':'EPSG:6695','vertical_unit':'metre','vertical_operation':'identity_H',
    'horizontal_operation':'EPSG:6668 -> EPSG:6677','source_horizontal_crs':'EPSG:6668',
    'source_compound_crs':'EPSG:6697'}


class SourceHStandardError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(json.dumps(report, ensure_ascii=False))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def strict_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'JSON', 'duplicate key')
            result[key] = value
        return result
    def number(text):
        value = float(text)
        require(math.isfinite(value), 'JSON', 'nonfinite value')
        return value
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_float=number,parse_constant=number)


def confined(root, locator):
    locator = Path(locator)
    require(not locator.is_absolute() and not locator.drive and '..' not in locator.parts,
            'path', 'relative artifact-root path required')
    path = (root/locator).resolve()
    require(path.is_relative_to(root), 'path', 'path escapes artifact root')
    return path


def validate_native(manifest_path, root):
    report = load_source_h_record(manifest_path, artifact_root=root)
    require(report.foundation_valid, 'Native.provenance', json.dumps(report.to_dict()))
    record = strict_json(manifest_path)
    identify_profile(record['profile'])
    ref = record['artifacts'][record['native']['output_artifact_id']]
    native = confined(root, ref['path'])
    require(manifest_path == native.with_suffix('.gpkg.manifest.json'), 'Native.manifest', 'adjacent manifest required')
    receipt_path = native.with_suffix('.gpkg.receipt.json')
    receipt = strict_json(receipt_path)
    require(receipt == {'schema':'ouem-plateau-native-receipt/v0.2','profile':SOURCE_H_PROFILE,
            'native_sha256':digest(native),'manifest_sha256':digest(manifest_path),
            'eligibility':'NOT_ESTABLISHED','status':'COMPLETED'}, 'Native.receipt', 'receipt/hash mismatch')
    validation = record.get('validation', {})
    require(validation.get('execution_status') == 'COMPLETED', 'Native', 'not completed')
    # Reperform actual geometry checks; do not trust persisted PASS declarations.
    snapshot = inspect_geopackage(native, ref['layer'])
    converter_ref = record['artifacts'][record['native']['input_artifact_id']]
    compare_snapshots(inspect_geopackage(confined(root,converter_ref['path']),converter_ref['layer']),snapshot)
    raw, _ = read_lod2(confined(root,a['path']) for a in record['artifacts'].values() if a['role']=='raw_citygml')
    compare_lod2(snapshot,raw)
    return record, native, receipt_path, snapshot


def _publish(source, destination):
    os.link(source, destination)  # same filesystem, no overwrite; closed handles


def standardize_source_h(*, profile, native_manifest, artifact_root, output, study_area_config):
    """Exact profile dispatch, real-file chain checks, horizontal-only conversion.

    Input/output locators are relative to artifact_root. Output parent must be a
    NEW child directory with an existing parent. No legacy fallback or eligibility.
    """
    published, claimed, output_path = [], False, None
    try:
        identify_profile(profile)  # never infer a profile from EPSG
        root = Path(artifact_root).resolve(strict=True)
        manifest_path = confined(root,native_manifest)
        before_manifest = digest(manifest_path)
        record,native,receipt_path,snapshot = validate_native(manifest_path,root)
        before_receipt = digest(receipt_path)
        output_path = confined(root,output)
        require(output_path.suffix.lower()=='.gpkg' and output_path.parent != root, 'output', 'new child GeoPackage required')
        area_path = Path(study_area_config).resolve(strict=True)
        area_sha = digest(area_path)
        area = load_study_area(area_path)
        require(area.epsg==6677 and all(map(math.isfinite,area.extent)), 'study_area', 'finite EPSG:6677 extent required')
        attributes = read_attributes(native,snapshot.layer)
        transformer = Transformer.from_crs(6668,6677,always_xy=True,allow_ballpark=False,only_best=True)
        def xy(lon,lat):
            return transformer.transform(lon,lat,errcheck=True)
        transformed = {key:map_xy(tree,xy) for key,tree in snapshot.features.items()}
        selected = {key:tree for key,tree in transformed.items() if intersects(tree,area.extent)}
        require(selected, 'selection', 'no buildings intersect study area')
        output_path.parent.mkdir()  # exclusive claim, no ancestor creation
        claimed = True
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
        with tempfile.TemporaryDirectory(prefix='.unverified-',dir=output_path.parent) as tmp:
            tmp=Path(tmp)
            staged = tmp/'standard.gpkg'
            write_standard(staged,selected,attributes,timestamp)
            qa = audit_standard(staged,snapshot.features,selected,attributes)
            def recheck_inputs():
                validate_native(manifest_path,root)
                require(digest(manifest_path)==before_manifest and digest(receipt_path)==before_receipt,
                        'inputs', 'Native records changed during conversion')
                require(digest(area_path)==area_sha,'study_area','config changed during conversion')
            recheck_inputs()
            _publish(staged,output_path)
            published.append(output_path)
            final_qa = audit_standard(output_path,snapshot.features,selected,attributes)
            require(qa==final_qa,'QA','final output differs')
            standard_sha = digest(output_path)
            final = {'schema':SCHEMA,'status':'EXPERIMENTAL','execution_status':'COMPLETED',
                'processed_at':timestamp,'profile':profile,**VERTICAL,
                'native_input':{'path':record['artifacts'][record['native']['output_artifact_id']]['path'],
                    'sha256':digest(native),'layer':snapshot.layer},
                'native_manifest':{'path':str(Path(native_manifest).as_posix()),'sha256':before_manifest},
                'native_receipt':{'path':receipt_path.relative_to(root).as_posix(),'sha256':before_receipt},
                'source_chain':record,  # immutable snapshot; original records are never updated
                'standard_output':{'path':output_path.relative_to(root).as_posix(),'sha256':standard_sha,
                    'size_bytes':output_path.stat().st_size,'layer':'building'},
                'study_area':{'id':area.id,'epsg':6677,'extent':list(area.extent),'config_sha256':area_sha},
                'selection':'2D intersection with closed study-area rectangle; complete geometry retained; no clipping',
                'selected_ids':list(selected),'excluded_ids':[key for key in transformed if key not in selected],
                'input_features':len(snapshot.features),'output_features':len(selected),
                'metadata_mapping':{'source_id':'Native id','source_lod':'existing recognized field or null; no inference',
                    'measured_height':'measuredHeight/measured_height or null','source_dataset':'PLATEAU CityGML',
                    'ouem_id':'unchanged oub- UUIDv5 URL namespace v0.1 rule'},
                'selected_lod_by_id':{key:2 for key in selected},
                'coordinate_operation':{'always_xy':True,'meaning':'input GIS longitude/latitude -> easting/northing',
                    'input_storage_axes':['longitude','latitude','H'],'output_storage_axes':['easting','northing','H'],
                    'arguments':'XY only; original H never passed to PROJ','definition':transformer.definition,
                    'description':transformer.description,'accuracy_m':transformer.accuracy,
                    'allow_ballpark':False,'only_best':True},
                'validation':final_qa,'source_h_eligibility':'NOT_ESTABLISHED',
                'human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED',
                'implementation':{'id':'source-h-standardizer-step3/v0.1','python':platform.python_version(),
                    'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str,
                    'module_sha256':{p.name:digest(p) for p in (Path(__file__),Path(__file__).with_name('source_h_geometry.py'))}}}
            manifest = output_path.with_suffix('.gpkg.manifest.json')
            receipt = output_path.with_suffix('.gpkg.receipt.json')
            staged_manifest = tmp/'manifest.json'
            staged_manifest.write_text(json.dumps(final,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            receipt_value = {'schema':RECEIPT_SCHEMA,'profile':profile,'status':'COMPLETED',
                'standard_sha256':standard_sha,'manifest_sha256':digest(staged_manifest),
                'eligibility':'NOT_ESTABLISHED'}
            staged_receipt = tmp/'receipt.json'
            staged_receipt.write_text(json.dumps(receipt_value,indent=2)+'\n',encoding='utf-8')
            _publish(staged_receipt,receipt)
            published.append(receipt)
            recheck_inputs()
            require(digest(output_path)==standard_sha,'output','output changed before completion')
            _publish(staged_manifest,manifest)  # completion marker LAST
            published.append(manifest)
        return {'status':'COMPLETED','output':str(output_path),'manifest':str(manifest),'receipt':str(receipt),'qa':final_qa}
    except Exception as exc:
        cleanup_errors=[]
        for path in reversed(published):
            try:path.unlink()
            except OSError as error:cleanup_errors.append(str(error))
        if claimed:
            try:output_path.parent.rmdir()
            except OSError as error:cleanup_errors.append(str(error))
        raise SourceHStandardError({'status':'FAILED','field':getattr(exc,'field','standardize'),
            'code':getattr(exc,'code','STANDARDIZATION_FAILED'),'reason':str(exc),
            'cleanup_errors':cleanup_errors,'eligibility':'NOT_ESTABLISHED'}) from exc


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('profile','native-manifest','artifact-root','output','study-area'):
        parser.add_argument('--'+arg,required=True)
    args=parser.parse_args()
    try:
        result=standardize_source_h(profile=args.profile,native_manifest=args.native_manifest,
            artifact_root=args.artifact_root,output=args.output,study_area_config=args.study_area)
    except SourceHStandardError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
