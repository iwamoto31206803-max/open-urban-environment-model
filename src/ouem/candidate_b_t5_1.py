"""Read-only Candidate B processing-domain and DEM coverage preflight."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import platform

import geopandas as gpd
import numpy as np
from shapely.geometry import box

from ouem import candidate_b_t4a as t4a
from ouem import candidate_b_t4b1 as b1
from ouem.terrain_candidate_b_preflight import AOI, digest, raster_cells, require
from ouem.terrain_candidate_b_t3 import TILES, HASHES


def domains(bounds):
    """Use the evaluation grid origin, then reserve one nominal mesh at each edge."""
    snapped = [
        origin + rounding(value-origin)
        for value, origin, rounding in zip(bounds, AOI, (math.floor, math.floor, math.ceil, math.ceil))
    ]
    return {"aligned_minimum": snapped,
            "one_mesh_margin": [value+offset for value, offset in zip(snapped, (-1,-1,1,1))]}


def extension(bounds):
    return {key:max(0., (value-limit)*sign)
            for key,value,limit,sign in zip(("west","south","east","north"),bounds,AOI,(-1,-1,1,1))}


def coverage(values, footprints, bounds):
    valid = np.isfinite(values)
    tama, ward = (group.sum(axis=0) for group in (valid[:2],valid[2:]))
    ids = np.zeros(tama.shape, dtype="uint8")
    bits = ids.copy()
    for code, mask in enumerate(valid, 1):
        ids[mask] = code
        bits[mask] |= 1 << (code-1)
    y,x = np.where(ids == 0)
    missing_bounds = None if not x.size else [
        bounds[0]+x.min()*.5, bounds[3]-(y.max()+1)*.5,
        bounds[0]+(x.max()+1)*.5, bounds[3]-y.min()*.5,
    ]
    chosen = np.take_along_axis(values, (np.maximum(ids,1)-1)[None], axis=0)[0]
    chosen[ids == 0] = np.nan
    return dict(tama=int((tama>0).sum()),ward=int((ward>0).sum()),
                both=int(((tama>0)&(ward>0)).sum()),neither=int(x.size),
                missing_cell_edge_bounds=missing_bounds,
                missing_within_tile_extent=int(((ids==0)&footprints.any(axis=0)).sum()),
                same_source_overlap=int(((tama>1)|(ward>1)).sum()),
                chosen_by_tile={key:int((ids==code).sum()) for code,key in TILES.items()}), ids, chosen, bits


def run(building_run, consumer_receipt, terrain_run, t4a_report, input_run, out):
    out.mkdir()
    report = dict(profile="ouem-candidate-b-t5-1/v0.1", status="BLOCKED",
                  terrain_integration_ready=False, t5_2_candidate=False,
                  evaluation_aoi=dict(epsg=6677,bounds=AOI))
    try:
        checked, expected, ground, source, vertical = t4a.load_inputs(building_run, consumer_receipt, terrain_run)
        selected, excluded = b1.selection(t4a_report, expected)
        checked["t4a_report"] = (t4a_report,b1.T4A_SHA)
        frame = gpd.read_file(checked["building_gpkg"][0], layer="building")
        require(frame.crs.to_epsg()==6677 and frame.source_id.is_unique
                and {r.source_id:(r.ouem_id,r.source_lod) for r in frame.itertuples()}==expected,
                "Standard CRS or identity differs")
        aoi = box(*AOI)
        records = []
        for row in frame.sort_values("ouem_id").itertuples():
            footprint, _ = b1.adapter.build_normalized_footprint(row.geometry,row.ouem_id)
            crosses = not aoi.covers(footprint)
            require(aoi.intersects(footprint) and crosses==(row.source_id not in selected),
                    f"T4-A extent classification differs: {row.source_id}")
            raw = row.geometry.bounds
            records.append(dict(source_id=row.source_id,ouem_id=row.ouem_id,source_lod=int(row.source_lod),
                                raw_xy_bounds=raw,footprint_bounds=footprint.bounds,crosses=crosses,
                                footprint_extension_m=extension(footprint.bounds),raw_extension_m=extension(raw)))
        all_bounds = [AOI]+[r[key] for r in records for key in ("raw_xy_bounds","footprint_bounds")]
        minimum = [reduce(values) for reduce,values in zip((min,min,max,max),zip(*all_bounds))]
        report.update(buildings=records, excluded_from_t4_only=excluded,
                      lod_counts=dict(Counter(r["source_lod"] for r in records)),
                      minimum_bounds=minimum, vertical=vertical, candidates={})
        for label,bounds in domains(minimum).items():
            metadata, values, footprints = {}, [], []
            for key,sha in HASHES.items():
                path = input_run/(key+".tif")
                t4a.verify(path,sha)
                meta, data, mask = raster_cells(path,bounds,catalogue_declares_ix=key.startswith("23ku/"))
                require(meta["sha256"]==sha and meta["dtype"]=="float32",f"tile changed: {key}")
                checked[key] = (path,sha)
                metadata[key] = meta
                values.append(data.astype("float32"))
                footprints.append(mask)
            result, ids, heights, bits = coverage(np.stack(values),np.stack(footprints),bounds)
            r,c = round((bounds[3]-AOI[3])*2),round((AOI[0]-bounds[0])*2)
            h,w = ground.shape
            overlap = np.s_[r:r+h,c:c+w]
            require(np.array_equal(ids[overlap],source)
                    and np.array_equal(heights[overlap].view("uint32"),ground.data.view("uint32")),
                    "existing T3 values or tile IDs differ")
            path = out/(label+"_tile_validity.npy")
            np.save(path,bits,allow_pickle=False)
            width,height = bounds[2]-bounds[0],bounds[3]-bounds[1]
            report["candidates"][label] = result | dict(
                bounds=bounds,width_m=width,height_m=height,terrain_shape=list(ids.shape),
                nominal_voxcity_shape=[height,width],tiles=metadata,
                t3_overlap=dict(cells=h*w,float32_bits="MATCH",tile_ids="MATCH"),
                validity_artifact=dict(file=path.name,sha256=digest(path)))
        for path,sha in checked.values():
            t4a.verify(path,sha)
        recommended = report["candidates"]["one_mesh_margin"]
        ready = not (recommended["neither"] or recommended["same_source_overlap"])
        report.update(status="COMPLETED" if ready else "BLOCKED",t5_2_candidate=ready,
                      reason=None if ready else "preferred domain has missing or ambiguous original DEM cells",
                      inputs={k:dict(path=str(p),sha256=sha) for k,(p,sha) in checked.items()},
                      implementation_sha256=digest(Path(__file__)),python=platform.python_version())
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    pending = out/"report.pending.json"
    t4a.write(pending,report)
    pending.rename(out/"report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("building-run","consumer-receipt","terrain-run","t4a-report","input-run","output-dir"):
        parser.add_argument("--"+name,type=Path,required=True)
    args = parser.parse_args()
    report = run(args.building_run,args.consumer_receipt,args.terrain_run,args.t4a_report,args.input_run,args.output_dir)
    print(report["status"],report.get("error",report.get("reason")))
    return int(report["status"]!="COMPLETED")


if __name__ == "__main__":
    raise SystemExit(main())
