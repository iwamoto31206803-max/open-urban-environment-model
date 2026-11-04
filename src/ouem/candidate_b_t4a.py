"""Candidate B T4-A read-only Building/Terrain diagnostics. No VoxCity imports."""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import rasterio
from shapely import intersects_xy
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from ouem.consumers._source_h_geometry import decode
from ouem.native.building.source_h_geometry import open_readonly, polygons
from ouem.terrain_candidate_b_diagnostics import AFFINE
from ouem.terrain_candidate_b_preflight import AOI, digest, require

PROFILE = "ouem-candidate-b-t4a/v0.1"
BUILDING = "ouem-standard-building/plateau-mixed-lod-source-h/v0.1"
TERRAIN = "ouem-experimental-candidate-b-terrain/v0.1"
PINS = {
    "building_manifest": "9789d443e0286ad0c5da57156d7ba10ed19adafba5e42cec068e9deeead0f789",
    "consumer_receipt": "1f9de8a7bdd7c92fd455f7c3897f45d8280dff05da90634f2aa677a86298e415",
    "terrain_manifest": "66c0c835a2a448140dbce905cf2be3af3942b809ce72788bb0e4c81be953b1ab",
}


def verify(path, expected):
    require(digest(path)==expected,f"SHA-256 mismatch: {path.name}")


def vertical_state(building, terrain):
    source = building.get("input", {})
    epsg = building.get("vertical_epsg")
    if any(code not in (None,6695) for code in (epsg,source.get("vertical_epsg"))):
        return "MISMATCH"
    if epsg is None or source.get("vertical_epsg") is None or terrain in (None,"unresolved","UNRESOLVED"):
        return "UNRESOLVED"
    if terrain != "T.P. inferred for ward; DEM datum realization and epoch unverified; identity height":
        return "MISMATCH"
    if (building.get("vertical_operation"),source.get("quantity"),source.get("unit")) != (
            "identity_H","gravity_related_height","metre"):
        return "UNRESOLVED"
    return "CONDITIONAL"


def raster(path, dtype, nodata, role):
    with rasterio.open(path) as ds:
        require(ds.driver=="GTiff" and ds.count==1 and ds.dtypes==(dtype,) and ds.shape==(200,200)
                and ds.crs and ds.crs.to_epsg()==6677 and ds.transform==AFFINE and ds.nodata==nodata
                and ds.scales==(1.,) and ds.offsets==(0.,) and ds.tags().get("ouem_profile")==TERRAIN
                and ds.tags().get("role")==role, f"unexpected T3 raster metadata: {path.name}")
        return ds.read(1,masked=True)


def load_inputs(building_run, consumer_receipt, terrain_run):
    manifest_paths = dict(building_manifest=building_run/"manifest.json",consumer_receipt=consumer_receipt,
                          terrain_manifest=terrain_run/"manifest.json")
    checked = {key:(path,PINS[key]) for key,path in manifest_paths.items()}
    for path,expected in checked.values():
        verify(path,expected)
    building, receipt, terrain = (json.loads(path.read_bytes()) for path in manifest_paths.values())
    require(building["schema"]=="ouem-mixed-lod-standard-manifest/v0.1" and building["profile"]==BUILDING
            and building["execution_status"]=="COMPLETED" and building["formal_acceptance"]=="NOT_VERIFIED"
            and building["output"]["layer"]=="building" and building["aoi"]["epsg"]==6677
            and building["aoi"]["bounds"]==list(AOI) and building["crs"]["output_horizontal_epsg"]==6677
            and building["crs"]["output_axes"]==["X","Y","H"],"unexpected Building manifest")
    require(receipt["schema"]=="ouem-mixed-lod-consumer-receipt/v0.1" and receipt["profile"]==BUILDING
            and receipt["execution_status"]=="COMPLETED" and receipt["consumer_validation"]=="PASS"
            and receipt["crs"]==building["crs"] and receipt["aoi"]==building["aoi"]
            and receipt["artifacts"]["standard_manifest"]["sha256"]==PINS["building_manifest"]
            and receipt["artifacts"]["standard_gpkg"]["sha256"]==building["output"]["sha256"],
            "Consumer receipt does not bind the Building inputs")
    require(terrain["profile"]==TERRAIN and terrain["status"]=="COMPLETED"
            and terrain["policy"]=="WARD_FIRST" and terrain["terrain_integration_ready"] is False
            and terrain["grid"]==dict(epsg=6677,bounds=list(AOI),shape=[200,200],
                                     affine=list(AFFINE)[:6],height_nodata=-32767.,tile_nodata=0),
            "unexpected experimental Terrain manifest")
    vertical = vertical_state(building["crs"],terrain.get("vertical"))
    require(vertical=="CONDITIONAL",f"vertical declaration: {vertical}")
    require({key:entry["file"] for key,entry in terrain["inputs"].items()}==
            {"1":"tama/09LD3423.tif","2":"tama/09LD3433.tif","3":"23ku/09LD3423.tif","4":"23ku/09LD3433.tif"},
            "unexpected T3 source tile mapping")
    checked["building_gpkg"] = (building_run/"standard.gpkg",building["output"]["sha256"])
    for key,file in (("terrain","terrain.tif"),("source_tile","source_tile.tif"),("terrain_validation","validation.json")):
        locator = "artifacts/"+file
        checked[key] = (terrain_run/locator,terrain["outputs"][locator])
    for path,expected in checked.values():
        verify(path,expected)
    ground = raster(checked["terrain"][0],"float32",-32767.,"terrain")
    source = raster(checked["source_tile"][0],"uint8",0,"source_tile")
    require(not np.ma.getmaskarray(ground).any() and np.isfinite(ground.data).all()
            and not np.ma.getmaskarray(source).any() and np.isin(source.data,[1,2,3,4]).all()
            and int((source.data>=3).sum())==16103,"incomplete T3 grid or unexpected provenance")
    expected = {r["source_id"]:(r["ouem_id"],r["source_lod"]) for r in building["buildings"]}
    require(len(expected)==len(building["buildings"]) and sorted(expected)==receipt["validation"]["matched_ids"],
            "Building manifest/Consumer ID sets differ")
    return checked,expected,ground,source.data,vertical


def read_buildings(path, expected):
    rows = {}
    with open_readonly(path) as db:
        require(db.execute("SELECT * FROM gpkg_geometry_columns").fetchall()
                == [("building","geometry","MULTIPOLYGON",6677,1,0)],"unexpected Building geometry declaration")
        for sid,oid,lod,blob in db.execute("SELECT source_id,ouem_id,source_lod,geometry FROM building"):
            require(sid not in rows and sid in expected and expected[sid]==(oid,lod)
                    and type(lod) is int and lod in (1,2),"Building ID/LoD mismatch")
            tree = decode(blob)
            require(tree[0]=="MultiPolygon",f"{sid}: unexpected BLOB type")
            rows[sid] = (oid,lod,polygons(tree))
    require(rows.keys()==expected.keys() and len({r[0] for r in rows.values()})==len(rows)
            and Counter(r[1] for r in rows.values())=={1:31,2:32},"Building ID or LoD counts differ")
    return rows


def stats(values):
    if not len(values):
        return None
    return dict(min=float(np.min(values)),max=float(np.max(values)),mean=float(np.mean(values)),
                std=float(np.std(values)),range=float(np.ptp(values)))


def lower_envelope(projected, x, y):
    """Sample the lowest eligible planar shell surface, as a geometric proxy only."""
    low = np.full(x.shape,np.inf)
    skipped = 0
    for shape,face in projected:
        hit = intersects_xy(shape,x,y)
        if not hit.any():
            continue
        vertices = np.array([p for ring in face for p in ring])
        origin = vertices[0,:2]
        matrix = np.column_stack((vertices[:,:2]-origin,np.ones(len(vertices))))
        fit,_,rank,_ = np.linalg.lstsq(matrix,vertices[:,2],rcond=None)
        # Numerical plane-fit criterion, not a vertical-compatibility tolerance.
        if rank!=3 or np.max(np.abs(matrix@fit-vertices[:,2]))>1e-6:
            skipped += 1
            continue
        height = fit[0]*(x[hit]-origin[0])+fit[1]*(y[hit]-origin[1])+fit[2]
        low[hit] = np.minimum(low[hit],height)
    return low,skipped


def diagnose(sid, oid, lod, faces, ground, source, x, y, aoi):
    z = stats([p[2] for face in faces for ring in face for p in ring])
    valid_faces, invalid, zero = [],0,0
    for face in faces:
        shape = Polygon([p[:2] for p in face[0]],[[p[:2] for p in ring] for ring in face[1:]])
        if shape.area<=0:
            zero += 1
        elif not shape.is_valid:
            invalid += 1
        else:
            valid_faces.append((shape,face))
    flags = []
    if invalid:
        flags.append("INVALID_POSITIVE_AREA_PROJECTION")
    footprint = unary_union([p[0] for p in valid_faces])
    area = footprint.area
    inside = footprint.intersection(aoi).area
    outside = footprint.difference(aoi).area
    if not area:
        flags.append("NO_POSITIVE_AREA_FOOTPRINT")
    if outside>0:
        flags.append("FOOTPRINT_EXTENDS_OUTSIDE_AOI")
    covered = intersects_xy(footprint,x,y)
    valid = covered & ~np.ma.getmaskarray(ground) & np.isfinite(ground.data)
    values = ground.data[valid].astype(float)
    if not len(values):
        flags.append("NO_VALID_GROUND_CENTRES")
    if int(covered.sum())>len(values):
        flags.append("MISSING_GROUND_CENTRES")
    headroom = stats(z["max"]-values)
    if headroom and headroom["min"]<=0:
        flags.append("TOP_NOT_ABOVE_ALL_SAMPLED_GROUND")
    lower,skipped = lower_envelope(valid_faces,x[valid],y[valid])
    usable = np.isfinite(lower)
    gaps = lower[usable]-values[usable]
    if len(gaps) and len(gaps)==len(values) and (gaps>0).all():
        flags.append("LOWER_SHELL_PROXY_ABOVE_ALL_SAMPLED_GROUND")
    return dict(source_id=sid,ouem_id=oid,source_lod=lod,z_abs=z,
                projected_faces=dict(positive=len(valid_faces)+invalid,invalid_positive=invalid,zero=zero),
                footprint=dict(area_m2=area,inside_m2=inside,outside_m2=outside,
                               inside_fraction=inside/area if area else None,
                               outside_fraction=outside/area if area else None,complete=not invalid and area>0),
                terrain_centres=int(covered.sum()),valid_terrain_centres=len(values),ground_m=stats(values),
                terrain_sources=dict(tama=int(np.count_nonzero(valid&(source<=2))),
                                     ward=int(np.count_nonzero(valid&(source>=3)))),
                z_top_minus_ground_m=headroom,z_min_minus_ground_m=stats(z["min"]-values),
                lower_shell_proxy=dict(cells=int(usable.sum()),skipped_faces=skipped,minus_ground_m=stats(gaps),
                                       positive=int((gaps>0).sum()),negative=int((gaps<0).sum())),
                flags=flags,screen="REVIEW" if flags else "NO_SCREENING_FLAGS")


def write(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write("\n")


def run(building_run, consumer_receipt, terrain_run, out):
    out.mkdir()
    report = dict(profile=PROFILE,status="BLOCKED",terrain_integration_ready=False)
    try:
        checked,expected,ground,source,vertical = load_inputs(building_run,consumer_receipt,terrain_run)
        rows = read_buildings(checked["building_gpkg"][0],expected)
        y,x = np.meshgrid(AOI[3]-.25-.5*np.arange(200),AOI[0]+.25+.5*np.arange(200),indexing="ij")
        aoi = box(*AOI)
        records = [diagnose(sid,*rows[sid],ground,source,x,y,aoi) for sid in sorted(rows)]
        for path,expected_hash in checked.values():
            verify(path,expected_hash)
        report.update(status="COMPLETED",vertical=vertical, aoi=dict(epsg=6677,bounds=AOI,cell_size_m=.5),
                      method="Closed XY footprint covers native T3 cell centre; no VoxCity ID raster or G_eff_abs.",
                      inputs={key:{"path":str(path),"sha256":sha} for key,(path,sha) in checked.items()},
                      by_lod={str(lod):summarize([r for r in records if r["source_lod"]==lod]) for lod in (1,2)},
                      buildings=records)
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    pending = out/"report.pending.json"
    write(pending,report)
    pending.rename(out/"report.json")
    return report


def summarize(records):
    return dict(buildings=len(records),no_screening_flags=sum(r["screen"]=="NO_SCREENING_FLAGS" for r in records),
                flags=dict(sorted(Counter(flag for r in records for flag in r["flags"]).items())),
                terrain_centres_per_building=stats([r["valid_terrain_centres"] for r in records]),
                ground_std_m=stats([r["ground_m"]["std"] for r in records if r["ground_m"]]),
                mixed_source_buildings=sum(all(r["terrain_sources"].values()) for r in records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("building-run","consumer-receipt","terrain-run","output-dir"):
        parser.add_argument("--"+key,type=Path,required=True)
    args = parser.parse_args()
    report = run(args.building_run,args.consumer_receipt,args.terrain_run,args.output_dir)
    print(report["status"],report.get("by_lod",report.get("error")))
    return int(report["status"]!="COMPLETED")


if __name__=="__main__":
    raise SystemExit(main())
