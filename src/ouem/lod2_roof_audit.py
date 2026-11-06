"""STEP 4-0 read-only roof eligibility audit; no Derived or engine generation."""
from collections import Counter, defaultdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import rasterio
from shapely.geometry import Polygon
from shapely.ops import unary_union

from ouem.consumers import mixed_lod as consumer
from ouem.consumers import _mixed_lod_raw as city
from ouem.consumers._source_h_geometry import decode
from ouem.consumers.source_h_standard import Watch
from ouem.native.building.source_h_geometry import open_readonly, polygons, require
from ouem import synthetic_height_distribution as synthetic

PROFILE = "ouem-readonly-real-lod2-roof-audit/v0.1"
T5_SHA = "1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f"
SEMANTICS = {"RoofSurface", "WallSurface", "GroundSurface", "ClosureSurface",
             "OuterCeilingSurface", "OuterFloorSurface", "CeilingSurface", "FloorSurface", "InteriorWallSurface"}


def key(face):
    """Exact XYZ-bit ring identity, invariant to start/winding/hole order."""
    return next(iter(consumer.face_keys((face,))))


def semantic_faces(node, dimensions):
    """Only explicit direct boundedBy semantics on LoD2 inline polygons qualify."""
    parents = {child:parent for parent in node.iter() for child in parent}
    result = []
    for polygon in node.iter(city.G+"Polygon"):
        ancestors, current = [], polygon
        while current in parents:
            current = parents[current]
            ancestors.append(current)
        if not any(a.tag==city.B+"lod2MultiSurface" for a in ancestors):
            continue
        surfaces = [a for a in ancestors if a.tag in {city.B+s for s in SEMANTICS}]
        semantic, surface_id = "UNDETERMINED", None
        if len(surfaces)==1:
            surface=surfaces[0]
            boundary=parents.get(surface)
            if boundary is not None and boundary.tag==city.B+"boundedBy" and parents.get(boundary) is node:
                semantic=surface.tag.removeprefix(city.B)
                surface_id=surface.get(city.G+"id")
        result.append(dict(polygon_id=polygon.get(city.G+"id"),semantic=semantic,
                           semantic_surface_id=surface_id,rings=city.face(polygon,dimensions)))
    return result


def read_semantics(path, targets):
    """Stream verified extracted member without changing it or creating a cache."""
    result, stack, dimensions, active = {}, [], {}, False
    with Path(path).open("rb") as stream:
        require(Path(path).stat().st_size<=256*1024*1024,"Raw.XML","member exceeds audit budget")
        tail=b""
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            checked=(tail+chunk).upper()
            require(b"<!DOCTYPE" not in checked and b"<!ENTITY" not in checked and b"\x00" not in checked,
                    "Raw.XML","DTD/entities/non-ASCII-compatible XML unsupported")
            tail=checked[-16:]
        stream.seek(0)
        for event,node in ET.iterparse(stream,events=("start","end")):
            if event=="start":
                dimension=node.get("srsDimension",stack[-1] if stack else None)
                stack.append(dimension)
                if node.tag==city.B+"Building":
                    active=node.get(city.G+"id") in targets
                if active:
                    dimensions[node]=dimension
            else:
                if node.tag==city.B+"Building":
                    sid=node.get(city.G+"id")
                    if active:
                        require(sid not in result,"Raw.semantics","duplicate Building")
                        result[sid]=semantic_faces(node,dimensions)
                    active=False
                    dimensions={}
                    node.clear()
                elif node.tag==city.CORE+"cityObjectMember":
                    node.clear()
                stack.pop()
    require(result.keys()==targets,"Raw.semantics","missing selected buildings")
    return result


def correspondence(raw_faces, native_faces):
    """No ordinal-only assertions: require unique geometry AND unique source ID."""
    raw_keys, native_keys = defaultdict(list), defaultdict(list)
    ids=Counter(f["polygon_id"] for f in raw_faces)
    for i,face in enumerate(raw_faces): raw_keys[key(face["rings"])].append(i)
    for i,face in enumerate(native_faces): native_keys[key(face)].append(i)
    result=[]
    for i,face in enumerate(native_faces):
        candidates=raw_keys.get(key(face),[])
        unique=(len(candidates)==1 and len(native_keys[key(face)])==1
                and raw_faces[candidates[0]]["polygon_id"] is not None
                and ids[raw_faces[candidates[0]]["polygon_id"]]==1)
        source=raw_faces[candidates[0]] if unique else None
        result.append(dict(standard_face_index=i,native_face_index=i,
            mapping="VERIFIED" if unique else "AMBIGUOUS_OR_MISSING",
            raw_candidate_indices=candidates,polygon_id=source["polygon_id"] if source else None,
            semantic=source["semantic"] if source else "UNDETERMINED",
            semantic_surface_id=source["semantic_surface_id"] if source else None))
    return result


def geometry_qa(rings):
    """Diagnostics only; SVD does not flatten, repair or classify a roof."""
    points=np.array([p for ring in rings for p in ring],dtype=float)
    require(points.ndim==2 and points.shape[1]==3 and np.isfinite(points).all(),"face","nonfinite XYZ")
    require(all(len(r)>=4 and tuple(r[0])==tuple(r[-1]) for r in rings),"face","ring not closed")
    centred=points-points[0]
    _,singular,vectors=np.linalg.svd(centred,full_matrices=False)
    normal=vectors[-1]
    polygon=Polygon([p[:2] for p in rings[0]],[[p[:2] for p in r] for r in rings[1:]])
    try:
        support=synthetic._face(synthetic.Face("audit-only",tuple(rings)))
        compatible=support is not None
        reason=None if compatible else "vertical face is not roof support"
    except ValueError as exc:
        compatible,reason=False,str(exc)
    return dict(finite=True,closed=True,vertices=len(points),interior_rings=len(rings)-1,
        projected_area_m2=float(polygon.area),projected_valid=bool(polygon.is_valid),
        max_plane_residual_m=float(np.max(abs(centred@normal))),
        degenerate=bool(len(singular)<2 or singular[1]<=1e-8),
        abs_normal_z=float(abs(normal[2])),near_vertical=bool(abs(normal[2])<=1e-3),
        z_range=[float(points[:,2].min()),float(points[:,2].max())],
        step3a_planar_polygon_compatible=compatible,step3a_rejection=reason)


def projected_polygon(rings):
    return Polygon([p[:2] for p in rings[0]],[[p[:2] for p in r] for r in rings[1:]])


def building_audit(sid,attrs,raw_faces,native_faces,standard_faces):
    """Standard face order/XYZ must already pass independent Consumer audit."""
    matches=correspondence(raw_faces,native_faces)
    require(len(matches)==len(standard_faces),sid,"Native/Standard face count differs")
    faces=[]
    for row,face in zip(matches,standard_faces,strict=True):
        qa=geometry_qa(face)
        faces.append(row | dict(qa=qa,geometric_candidate_only=(row["semantic"]=="UNDETERMINED"
                     and qa["projected_valid"] and qa["projected_area_m2"]>0 and not qa["near_vertical"])))
    roof=[r for r in faces if r["semantic"]=="RoofSurface"]
    grounds=[projected_polygon(standard_faces[r["standard_face_index"]]) for r in faces
             if r["semantic"]=="GroundSurface"]
    valid_ground=bool(grounds) and all(p.is_valid and p.area>0 for p in grounds)
    footprint=unary_union(grounds) if valid_ground else None
    valid_roofs=[projected_polygon(standard_faces[r["standard_face_index"]]) for r in roof
                 if r["qa"]["projected_valid"] and r["qa"]["projected_area_m2"]>0]
    roof_union=unary_union(valid_roofs) if valid_roofs else None
    duplicate_faces=sum(n-1 for n in consumer.face_keys(standard_faces).values() if n>1)
    reasons=[]
    complete=consumer.face_keys(tuple(r["rings"] for r in raw_faces))==consumer.face_keys(native_faces)
    if not complete: reasons.append("RAW_FACE_SET_NOT_FULLY_ACCOUNTED")
    if any(r["mapping"]!="VERIFIED" for r in faces): reasons.append("NONUNIQUE_RAW_NATIVE_STANDARD_FACE_MAPPING")
    if not roof: reasons.append("NO_VERIFIED_EXPLICIT_ROOF")
    if any(not r["qa"]["step3a_planar_polygon_compatible"] for r in roof): reasons.append("ROOF_REJECTED_BY_UNCHANGED_STEP3A")
    if not valid_ground or footprint.geom_type!="Polygon": reasons.append("INDEPENDENT_FOOTPRINT_NOT_ESTABLISHED")
    blocked=bool(reasons)
    if not blocked:
        reasons.extend(["GROUND_SURFACE_PROJECTION_IS_ONLY_A_FOOTPRINT_CANDIDATE",
                        "BUILDING_DEM_COMMON_VERTICAL_REALIZATION_EPOCH_NOT_VERIFIED"])
    all_z=[p[2] for f in standard_faces for ring in f for p in ring]
    measured=attrs[8]
    ground_z=[p[2] for r in faces if r["semantic"]=="GroundSurface"
              for ring in standard_faces[r["standard_face_index"]] for p in ring]
    roof_z=[p[2] for r in roof for ring in standard_faces[r["standard_face_index"]] for p in ring]
    row=dict(source_id=sid,ouem_id=attrs[1],source_member=attrs[5],source_lod=attrs[3],
        raw_semantic_counts=dict(Counter(r["semantic"] for r in raw_faces)),
        mapping_counts=dict(Counter(r["mapping"] for r in faces)),faces=faces,
        roof_faces=len(roof),duplicate_faces=duplicate_faces,
        classification="BLOCKED" if blocked else "CONDITIONAL",reasons=reasons,
        vertical=dict(absolute_z_range=[min(all_z),max(all_z)],measured_height=measured,
                      ground_surface_z_range=[min(ground_z),max(ground_z)] if ground_z else None,
                      roof_surface_z_range=[min(roof_z),max(roof_z)] if roof_z else None,
                      geometry_z_span=max(all_z)-min(all_z),
                      span_minus_measured=None if measured is None else max(all_z)-min(all_z)-measured,
                      HAG_validity="NOT_VERIFIED"),
        footprint_candidate=dict(status="CONDITIONAL" if valid_ground else "NOT_VERIFIED",
            method="union of independently semantic GroundSurface XY projections; not an adopted footprint",
            geometry_type=None if footprint is None else footprint.geom_type,
            area_m2=None if footprint is None else float(footprint.area),
            exterior_vertices=None if footprint is None or footprint.geom_type!="Polygon" else len(footprint.exterior.coords)-1,
            roof_area_m2=None if roof_union is None else float(roof_union.area),
            roof_projection_sum_minus_union_m2=None if roof_union is None else
                float(sum(p.area for p in valid_roofs)-roof_union.area),
            uncovered_m2=None if footprint is None or roof_union is None else float(footprint.difference(roof_union).area),
            overhang_m2=None if footprint is None or roof_union is None else float(roof_union.difference(footprint).area),
            roof_holes=0 if roof_union is None else sum(len(p.interiors) for p in
                ([roof_union] if roof_union.geom_type=="Polygon" else roof_union.geoms))))
    return row,footprint,roof_union


def select_samples(rows):
    """First lexical matching ID per category; prefer distinct IDs, no fabricated examples."""
    def roofs(r): return [f for f in r["faces"] if f["semantic"]=="RoofSurface"]
    categories={
        "simple_flat":lambda r:r["roof_faces"]==1 and all(f["qa"]["z_range"][1]-f["qa"]["z_range"][0]<1e-8 for f in roofs(r)),
        "sloped":lambda r:any(f["qa"]["z_range"][1]-f["qa"]["z_range"][0]>.01 and not f["qa"]["near_vertical"] for f in roofs(r)),
        "multiple_roof_faces":lambda r:r["roof_faces"]>1,
        "hole_or_complex_outline":lambda r:r["footprint_candidate"]["roof_holes"]>0 or
            (r["footprint_candidate"]["exterior_vertices"] or 0)>4,
        "missing_duplicate_or_ambiguous":lambda r:r["duplicate_faces"]>0 or r["classification"]=="BLOCKED"}
    result,used={},set()
    for category,predicate in categories.items():
        candidates=sorted(r["source_id"] for r in rows if predicate(r))
        chosen=next((sid for sid in candidates if sid not in used),candidates[0] if candidates else None)
        result[category]=dict(status="FOUND" if chosen else "NOT_FOUND",source_id=chosen,candidates=candidates)
        if chosen: used.add(chosen)
    return result


def _capture(watch,name,path,sha=None):
    path=Path(path).resolve(strict=True)
    watch.capture(name,path.relative_to(watch.root).as_posix(),sha)
    return path


def verify_population(rows,attrs):
    require(len(rows)==len(attrs) and len({r["source_id"] for r in rows})==len(rows)
            and len({r["ouem_id"] for r in rows})==len(rows)
            and len({r["id"] for r in rows})==len(rows)
            and all(type(r["id"]) is int and r["id"]>0 for r in rows)
            and {r["source_id"]:(r["ouem_id"],r["source_lod"]) for r in rows}
            =={sid:(a[1],a[3]) for sid,a in attrs.items()},"T5","population or ID bijection differs from Standard")


def audit(t5_path,*,t5_sha=T5_SHA,artifact_root=Path("C:/dev")):
    watch=Watch(artifact_root)
    t5_path=_capture(watch,"T5_report",t5_path,t5_sha)
    t5=consumer.load(t5_path)
    paths_t5={k:_capture(watch,"T5_input_"+k,r["path"],r["sha256"]) for k,r in t5["inputs"].items()}
    bounds=t5["evaluation_aoi"]
    standard,native,bridge,selector,paths,member=consumer.graph(watch,paths_t5["building_manifest"],
        t5["inputs"]["building_manifest"]["sha256"],bounds)
    raw=city.read_zip(paths["raw_zip"],member["member"],member)
    projection=consumer.zone_ix()
    xy=lambda x,y:projection(x,y,errcheck=True)
    selected,all_rows=consumer.raw_selection(raw,selector,paths["selector_geometry"],member["member"],bounds,xy)
    snapshots=consumer.converter_passes(raw,bridge,paths)  # read-only saved converter outputs; no subprocess
    consumer.verify_decisions(all_rows,selected,raw,native,bridge,selector)
    native_geometry,attrs=consumer.gpkg_rows(paths,selected,snapshots,bridge,selector["source"]["release"],raw)
    chain=consumer.audit_standard(paths["standard"],native_geometry,attrs,standard,bounds,xy)
    verify_population(t5["grid"]["buildings"],attrs)
    receipt=consumer.load(paths_t5["consumer_receipt"])
    require(paths_t5["building_gpkg"]==paths["standard"] and receipt["consumer_validation"]=="PASS"
            and receipt["validation"]["matched_ids"]==sorted(attrs),"T5","receipt/Standard population binding differs")
    targets={sid for sid,a in attrs.items() if a[3]==2}
    semantic=read_semantics(paths["extracted_member"],targets)
    with open_readonly(paths["standard"]) as db:
        standard_geometry={sid:polygons(decode(blob)) for sid,blob in db.execute("SELECT source_id,geometry FROM building")}
        standard_fields=[r[1] for r in db.execute("PRAGMA table_info(building)")]
        standard_tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    with open_readonly(paths["native_gpkg"]) as db:
        native_fields=[r[1] for r in db.execute('PRAGMA table_info("bldg:Building")')]
    rows,footprints,roof_projections=[],{},{}
    terrain=t5_path.parent/"t5-2/terrain.tif"
    _capture(watch,"T5_expanded_terrain",terrain,t5["outputs"]["t5-2/terrain.tif"])
    with rasterio.open(terrain) as dem:
        require(dem.crs.to_epsg()==6677 and dem.count==1,"DEM","unexpected grid")
        for sid in sorted(targets):
            row,footprint,roof_projection=building_audit(sid,attrs[sid],semantic[sid],polygons(native_geometry[sid]),standard_geometry[sid])
            if roof_projection is not None: roof_projections[sid]=roof_projection
            if footprint is not None:
                footprints[sid]=footprint
                point=footprint.representative_point()
                value=next(dem.sample([(point.x,point.y)],masked=True))[0]
                valid=not np.ma.is_masked(value) and np.isfinite(value)
                row["vertical"].update(dem_sample_method="nearest pixel at GroundSurface candidate representative point; diagnostic only",
                    dem_sample_xy=[point.x,point.y],dem_z=float(value) if valid else None,
                    geometry_min_minus_dem=None if not valid else row["vertical"]["absolute_z_range"][0]-float(value),
                    geometry_top_minus_dem=None if not valid else row["vertical"]["absolute_z_range"][1]-float(value))
            rows.append(row)
    def overlaps(geometries):
        result=[]
        for i,sid in enumerate(sorted(geometries)):
            for other in sorted(geometries)[i+1:]:
                area=geometries[sid].intersection(geometries[other]).area
                if area>1e-8: result.append(dict(source_ids=[sid,other],area_m2=float(area)))
        return result
    acquisition=paths["raw_zip"].with_name("acquisition-manifest.json")
    _capture(watch,"acquisition_record",acquisition)
    acquisition_record=consumer.load(acquisition)
    require(acquisition_record["status"]=="COMPLETED"
            and acquisition_record["archive"]["sha256"]==standard["raw_source"]["zip_sha256"]
            and acquisition_record["raw_zip"]==str(paths["raw_zip"]),"acquisition","record/ZIP identity differs")
    with ZipFile(paths["raw_zip"]) as archive:
        readme=archive.read("README.md")
        resources=archive.read("metadata/udx_13219_2025_resource_op.csv")
    watch.unchanged()
    return dict(profile=PROFILE,status="AUDIT_COMPLETED",technical_audit="PASS",real_data_audit="EXECUTED",
        step4a_transition="BLOCKED_PENDING_INPUT_CONDITIONS",terrain_integration_ready=False,
        scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED",inputs=watch.identities,
        raw_source=standard["raw_source"],crs=standard["crs"],operation=standard["operation"],chain_qa=chain,
        population=dict(total=len(attrs),by_lod=dict(Counter(str(a[3]) for a in attrs.values())),lod2=len(targets)),
        semantic_counts=dict(sum((Counter(f["semantic"] for f in semantic[sid]) for sid in targets),Counter())),
        native_storage=dict(fields=native_fields,raw_face_locators="Native manifest decisions.raw_polygons; not per-face GPKG attributes"),
        standard_storage=dict(fields=standard_fields,tables=standard_tables,
            semantics="not embedded per face; reconstructed external crosswalk requires unique Raw/Native XYZ and ordered Standard correspondence"),
        vertical=dict(building=standard["crs"],terrain_manifest=consumer.load(paths_t5["terrain_manifest"])["vertical"],
                      T5_evidence=t5["vertical_evidence"],HAG_validity="NOT_VERIFIED"),
        classifications=dict(Counter(r["classification"] for r in rows)),sample_selection=select_samples(rows),
        buildings=rows,building_ground_projection_overlaps=overlaps(footprints),
        building_roof_projection_overlaps=overlaps(roof_projections),overlap_reporting_threshold_m2=1e-8,
        licensing=dict(acquisition_source=acquisition_record["source"],zip_readme_sha256=hashlib.sha256(readme).hexdigest(),
                       zip_readme_text=readme.decode("utf-8-sig"),
                       resource_member="metadata/udx_13219_2025_resource_op.csv",
                       readme_resource_link="metadata/udx_13219_2025_resource.csv (NOT_FOUND; actual member has _op suffix)",
                       resource_sha256=hashlib.sha256(resources).hexdigest(),resource_text=resources.decode("utf-8-sig"),
                       current_terms_review="NOT_PERFORMED; stored acquisition and ZIP declarations only"),
        input_immutability="PASS_SHA_AND_STAT_BEFORE_AFTER",environment=dict(python=platform.python_version(),
            **{k:version(k) for k in ("numpy","shapely","pyproj","rasterio")}),
        implementation={Path(f).name:consumer.digest(f) for f in (__file__,consumer.__file__,city.__file__,synthetic.__file__)})


def run(t5_path,output,*,t5_sha=T5_SHA,artifact_root=Path("C:/dev")):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    try:
        result=audit(t5_path,t5_sha=t5_sha,artifact_root=artifact_root)
        write(output/"report.json",result)
        write(output/"manifest.json",dict(profile=PROFILE,status="AUDIT_COMPLETED",
            report_sha256=consumer.digest(output/"report.json"),terrain_integration_ready=False,
            scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED"))
        return result
    except Exception as exc:
        result=dict(profile=PROFILE,status="BLOCKED",real_data_audit="NOT_COMPLETED",step4a_transition="BLOCKED",
                    error=f"{type(exc).__name__}: {exc}",terrain_integration_ready=False,
                    scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED")
        write(output/"failure.json",result)
        return result


def write(path,value):
    temporary=path.with_suffix(path.suffix+".tmp")
    with temporary.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write("\n")
    require(consumer.canonical(json.loads(temporary.read_bytes()))==consumer.canonical(value),"output","reread differs")
    require(not path.exists(),"output","existing file")
    temporary.rename(path)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t5-report",type=Path,required=True)
    parser.add_argument("--t5-sha256",default=T5_SHA)
    parser.add_argument("--artifact-root",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    report=run(args.t5_report,args.output_dir,t5_sha=args.t5_sha256,artifact_root=args.artifact_root)
    print(report["status"],report.get("error",report.get("classifications")))
    return int(report["status"]!="AUDIT_COMPLETED")


if __name__=="__main__":
    raise SystemExit(main())
