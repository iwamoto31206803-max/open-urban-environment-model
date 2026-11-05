"""Candidate B expanded WARD_FIRST and gated experimental VoxCity integration."""
import argparse
from collections import Counter
from importlib.metadata import distribution, version
import json
from pathlib import Path
import platform

import geopandas as gpd
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.transform import from_origin
from scipy.spatial import cKDTree
from shapely.geometry import box

from ouem import candidate_b_t4a as t4a
from ouem import candidate_b_t4b1 as b1
from ouem import candidate_b_t4b2 as b2
from ouem.terrain_candidate_b_preflight import AOI, digest, raster_cells, require
from ouem.terrain_candidate_b_t3 import HASHES, HEIGHT_NODATA, TILES, select

DOMAIN = (-22588,-39938,-22461,-39811)
T5_1_SHA = "2b832f2c3a146812e3e77a4363e80058b33996c6b80e62eb9f141cbd540832b9"
T4B2_SHA = "5105b192961e771cf24336ab2dc36ed84c1b3d14e2d591d140968634f67978b9"


def terrain(input_run, out, checked, ground, source):
    """Apply the T3 selector to aligned native pixels and verify reopened outputs."""
    grids = []
    for key, sha in HASHES.items():
        path = input_run/(key+".tif")
        t4a.verify(path, sha)
        meta, values, _ = raster_cells(path, DOMAIN, catalogue_declares_ix=key.startswith("23ku/"))
        require(meta["sha256"] == sha and meta["dtype"] == "float32", f"tile changed: {key}")
        grids.append(values.astype("float32"))
        checked[key] = (path, sha)
    heights, ids = select(np.stack(grids))
    require(not np.any(heights == HEIGHT_NODATA), "valid height collides with output NoData")
    r,c = round((DOMAIN[3]-AOI[3])*2),round((AOI[0]-DOMAIN[0])*2)
    h,w = ground.shape
    subset = np.s_[r:r+h,c:c+w]
    affine = from_origin(DOMAIN[0], DOMAIN[3], .5, .5)
    for name, array, nodata in (("terrain",heights,HEIGHT_NODATA),("source_tile",ids,0)):
        path = out/(name+".tif")
        with rasterio.open(path,"w",driver="GTiff",count=1,width=array.shape[1],height=array.shape[0],
                           dtype=array.dtype,crs="EPSG:6677",transform=affine,nodata=nodata,compress="deflate") as ds:
            ds.write(array,1)
            ds.update_tags(AREA_OR_POINT="Area",ouem_profile="candidate-b-expanded-experimental",role=name)
        with rasterio.open(path) as ds:
            read = ds.read(1,masked=True)
            require(ds.crs.to_epsg()==6677 and ds.transform==affine and ds.nodata==nodata
                    and read.dtype==array.dtype and not np.ma.getmaskarray(read).any()
                    and read.data.tobytes()==array.tobytes(), f"reopened {name} differs")
    require(heights[subset].tobytes()==ground.data.tobytes() and np.array_equal(ids[subset],source),
            "T3 Float32 or source tile mismatch")
    return dict(shape=list(heights.shape),affine=list(affine)[:6],t3_matching_cells=h*w,
                tile_counts={key:int((ids==code).sum()) for code,key in TILES.items()})


def evaluation_mask(xy):
    x,y = np.moveaxis(xy,-1,0)
    return (x>=AOI[0]) & (x<AOI[2]) & (y>=AOI[1]) & (y<AOI[3])


def grid_gate(grid, rows):
    if not grid["converged"] or any(r["owner_outside_isolated"] for r in rows):
        return "FAIL"
    if any(r["flags"] or not r["owned_cells"] for r in rows):
        return "REVIEW_REQUIRED"
    return "PASS"


def grid_phase(frame, path):
    from voxcity.geoprocessor.raster import (
        create_building_height_grid_from_gdf_polygon, create_dem_grid_from_geotiff_polygon,
    )
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords

    z = {r.ouem_id:b1.adapter._z_values(r.geometry) for r in frame.itertuples()}
    footprints = {r.ouem_id:b1.adapter.build_normalized_footprint(r.geometry,r.ouem_id) for r in frame.itertuples()}
    domain = box(*DOMAIN)
    require(all(domain.covers(fp) for fp,_ in footprints.values())
            and all(domain.covers(box(*geometry.bounds)) for geometry in frame.geometry),
            "building extent outside domain")
    buildings = b1.adapter._set_normalized_footprints(frame,footprints)
    buildings["id"] = buildings.ouem_id.map(b1.adapter.numeric_id_mapping(buildings.ouem_id))
    buildings["height"], buildings["min_height"] = 1.,0.
    buildings, repairs = b1.adapter._repair_post_crs(b1.adapter._to_voxcity_building_crs(buildings),footprints)
    transform = Transformer.from_crs(6677,4326,always_xy=True)
    x0,y0,x1,y1 = DOMAIN
    rectangle = [transform.transform(x,y,errcheck=True) for x,y in ((x0,y0),(x0,y1),(x1,y1),(x1,y0))]
    centres = compute_cell_center_coords(rectangle,b1.MESH)
    dem,xy,source,coverage = b1.sample_dem(path,centres,rectangle,create_dem_grid_from_geotiff_polygon,bounds=DOMAIN)
    raster = create_building_height_grid_from_gdf_polygon
    ids,height,claims,rows,grid = b1.grid_buildings(buildings,rectangle,raster,dem,z)
    arrays = dict(dem=dem,centres_xy=xy,terrain_row_col=source,building_ids=ids,
                  building_height=height,isolated_claim_count=claims,evaluation_mask=evaluation_mask(xy))
    result = dict(grid=grid,buildings=rows,rectangle_lonlat=rectangle,dem_coverage=coverage,
                  engine_grid={k:np.asarray(v).tolist() for k,v in centres.items() if k not in ("lons","lats")},
                  orientation="axis 0 north from SW; axis 1 east from SW",post_crs_repairs=repairs)
    if grid_gate(grid,rows)!="PASS":
        return result,arrays,None
    final_height,segments,final_ids,_ = raster(buildings,b1.MESH,rectangle,overlapping_footprint=True)
    require(np.array_equal(final_ids,ids) and np.array_equal(final_height,height),
            "final rerasterization changed grid")
    counts = np.fromiter((len(cell) for cell in segments.flat), dtype=int).reshape(ids.shape)
    require(np.array_equal(counts>0, ids>0) and np.array_equal(counts>1,claims>1),
            "segment coverage disagrees with ownership or competition")
    for conflict in grid["competitions"]:
        index = tuple(conflict["index"])
        conflict["centre_xy"] = xy[index].tolist()
        isolated = []
        for key in conflict["candidates"]:
            _,single,single_ids,_ = raster(buildings[buildings.id==key],b1.MESH,rectangle,overlapping_footprint=True)
            require(single_ids[index]==key,"isolated claim differs")
            isolated.extend(dict(id=key,bounds=list(pair)) for pair in single[index])
        require(Counter(tuple(r["bounds"]) for r in isolated)==Counter(map(tuple,segments[index])),
                "isolated and grouped segments differ")
        conflict["isolated_segments"] = isolated
    return result,arrays,segments


def compare_t4(old_rows, rows, old_xy, old_ids, arrays):
    new_by_source = {r["source_id"]:r for r in rows}
    distance, index = cKDTree(arrays["centres_xy"].reshape(-1,2)).query(old_xy.reshape(-1,2))
    paired_ids = arrays["building_ids"].ravel()[index].reshape(old_ids.shape)
    result = []
    for old in old_rows:
        new = new_by_source[old["source_id"]]
        require(old["ouem_id"]==new["ouem_id"] and old["z_top_abs"]==new["z_top_abs"],
                "T4 identity or absolute top differs")
        mask = old_ids==old["id"]
        result.append(dict(source_id=old["source_id"],t4_id=old["id"],t5_id=new["id"],
                           old_cells=int(mask.sum()),same_source_nearest_cells=int((paired_ids[mask]==new["id"]).sum()),
                           ground_delta_m=None if new["g_eff_abs"] is None else new["g_eff_abs"]-old["g_eff_abs"],
                           height_delta_m=None if new["height"] is None else new["height"]-old["height"]))
    return dict(max_nearest_centre_distance_m=float(distance.max()),buildings=result),index


def voxel_phase(arrays, rows, grid, segments, old_voxels, old_ids, old_rows, nearest, old_z):
    from voxcity.generator.voxelizer import NUMBA_AVAILABLE, Voxelizer

    dem,ids,height = (arrays[k] for k in ("dem","building_ids","building_height"))
    voxels = Voxelizer(b1.MESH,"Standard").generate_combined(
        height.copy(),segments.copy(),ids.copy(),np.ones(ids.shape,dtype=int),dem.copy(),
        np.zeros(ids.shape),print_class_info=False)
    effective, diagnostic = b2.audit_voxels(voxels,dem,ids,segments,rows,grid["competitions"])
    by_index = {tuple(c["index"]):c for c in grid["competitions"]}
    for item in diagnostic["conflicts"]:
        original = by_index[tuple(item["index"])]
        item.update(isolated_segments=original["isolated_segments"],centre_xy=original["centre_xy"])
    evaluation = arrays["evaluation_mask"]
    output = dict(voxels=voxels,effective_dem_abs=effective,
                  evaluation_voxels=voxels[evaluation],evaluation_centres_xy=arrays["centres_xy"][evaluation],
                  evaluation_indices=np.argwhere(evaluation))
    counts = []
    for row in rows:
        mask = (ids==row["id"]) & evaluation
        counts.append(dict(source_id=row["source_id"],owner_cells=int(mask.sum()),
                           owner_columns_with_building=int(np.any(voxels[mask]==-3,axis=1).sum())))
    new_columns = np.any(voxels== -3,axis=2)
    new_top = voxels.shape[2]-1-np.argmax((voxels==-3)[...,::-1],axis=2)
    old_top = old_voxels.shape[2]-1-np.argmax((old_voxels==-3)[...,::-1],axis=2)
    old_competition = (48,83)
    new_clean = (arrays["isolated_claim_count"]==1) & new_columns
    roof_deltas = []
    for old in old_rows:
        new = next(row for row in rows if row["source_id"]==old["source_id"])
        old_mask = old_ids==old["id"]
        old_mask[old_competition] = False
        target = nearest[old_mask.ravel()]
        match = (ids.ravel()[target]==new["id"]) & new_clean.ravel()[target]
        deltas = diagnostic["z_reference_abs_m"]+new_top.ravel()[target[match]]-old_z-old_top[old_mask][match]
        roof_deltas.append(dict(source_id=old["source_id"],matched_unambiguous_columns=int(match.sum()),
                                absolute_roof_delta_m=None if not deltas.size else b2.stats(deltas)))
    diagnostic.update(evaluation_columns=int(evaluation.sum()),evaluation_buildings=counts,
                      t4_geographic_roof_comparison=roof_deltas,numba=NUMBA_AVAILABLE)
    return output,diagnostic


def run(building_run, consumer_receipt, terrain_run, input_run, preflight, old_grid, old_voxel, out):
    out.mkdir()
    report = dict(profile="ouem-candidate-b-t5-23/v0.1",gate1="FAIL",gate2="NOT_RUN",
                  terrain_integration_ready=False,formal_acceptance="NOT_VERIFIED",domain=DOMAIN,evaluation_aoi=AOI)
    phase = "gate1"
    try:
        checked,expected,ground,source,vertical = t4a.load_inputs(building_run,consumer_receipt,terrain_run)
        for label,path,sha in (("t5_1",preflight,T5_1_SHA),("t4_grid",old_grid/"report.json",b2.B1_SHA),
                               ("t4_voxel",old_voxel/"report.json",T4B2_SHA)):
            t4a.verify(path,sha)
            checked[label]=(path,sha)
        plan,t4_grid,t4_voxel = (json.loads(checked[k][0].read_bytes()) for k in ("t5_1","t4_grid","t4_voxel"))
        require(plan["t5_2_candidate"] is True and plan["candidates"]["one_mesh_margin"]["bounds"]==list(DOMAIN),
                "unexpected T5-1 domain")
        for key,(_,sha) in checked.items():
            if key in plan["inputs"]:
                require(plan["inputs"][key]["sha256"]==sha,f"T5-1 input binding differs: {key}")
        previous = {}
        for key,folder,name,sha in (
                ("xy",old_grid,"grids/centres_xy.npy",t4_grid["outputs"]["grids/centres_xy.npy"]),
                ("ids",old_grid,"grids/building_ids.npy",t4_grid["outputs"]["grids/building_ids.npy"]),
                ("voxels",old_voxel,"voxels.npy",t4_voxel["outputs"]["voxels.npy"])):
            path=folder/name
            t4a.verify(path,sha)
            checked["t4_"+key]=(path,sha)
            previous[key]=np.load(path,allow_pickle=False)
        direct = json.loads(distribution("voxcity").read_text("direct_url.json"))
        require(version("voxcity")=="1.7.0" and direct["vcs_info"]["commit_id"]==b1.PIN,"VoxCity pin mismatch")
        report.update(vertical=vertical,vertical_evidence=t4_voxel["vertical_reference"],
                      engine=dict(version="1.7.0",commit=b1.PIN),python=platform.python_version(),
                      host=platform.node(),os=platform.platform(),implementation_sha256=digest(Path(__file__)))
        stage1=out/"t5-2"
        stage1.mkdir()
        report["terrain"]=terrain(input_run,stage1,checked,ground,source)
        require(report["terrain"]["shape"]==[254,254] and report["terrain"]["tile_counts"]==
                plan["candidates"]["one_mesh_margin"]["chosen_by_tile"],"terrain differs from T5-1")
        frame=gpd.read_file(checked["building_gpkg"][0],layer="building").sort_values("ouem_id").reset_index(drop=True)
        require(frame.crs.to_epsg()==6677 and frame.source_id.is_unique and
                {r.source_id:(r.ouem_id,r.source_lod) for r in frame.itertuples()}==expected,"Standard CRS or IDs differ")
        result,arrays,segments=grid_phase(frame,stage1/"terrain.tif")
        rows=result["buildings"]
        require(len(rows)==63 and Counter(r["source_lod"] for r in rows)=={1:31,2:32},"target composition differs")
        result["t4_comparison"], nearest = compare_t4(t4_grid["buildings"],rows,previous["xy"],previous["ids"],arrays)
        crossing = {r["source_id"] for r in plan["buildings"] if r["crosses"]}
        for row in rows:
            row["crosses_evaluation_aoi"] = row["source_id"] in crossing
            row["evaluation_owner_cells"] = int(
                ((arrays["building_ids"]==row["id"]) & arrays["evaluation_mask"]).sum())
        report["grid"]=result
        for key,array in arrays.items():
            np.save(stage1/(key+".npy"),array,allow_pickle=False)
        for path,sha in checked.values():
            t4a.verify(path,sha)
        report["gate1"]=grid_gate(result["grid"],rows)
        report["inputs"]={k:dict(path=str(p),sha256=sha) for k,(p,sha) in checked.items()}
        if report["gate1"]=="PASS":
            phase="gate2"
            stage2=out/"t5-3"
            stage2.mkdir()
            output,diagnostic=voxel_phase(arrays,rows,result["grid"],segments,previous["voxels"],
                                          previous["ids"],t4_grid["buildings"],nearest,
                                          t4_voxel["diagnostics"]["z_reference_abs_m"])
            for key,array in output.items():
                np.save(stage2/(key+".npy"),array,allow_pickle=False)
            t4a.write(stage2/"segments.json",segments.tolist())
            for path,sha in checked.values():
                t4a.verify(path,sha)
            report.update(gate2="PASS",voxels=diagnostic,voxel_shape=list(output["voxels"].shape))
    except Exception as exc:
        report[phase]="FAIL"
        report["error"]=f"{type(exc).__name__}: {exc}"
    report["outputs"]={p.relative_to(out).as_posix():digest(p) for p in sorted(out.rglob("*")) if p.is_file()}
    pending=out/"report.pending.json"
    t4a.write(pending,report)
    pending.rename(out/"report.json")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("building-run","consumer-receipt","terrain-run","input-run","preflight","old-grid","old-voxel","output-dir"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    report=run(args.building_run,args.consumer_receipt,args.terrain_run,args.input_run,args.preflight,
               args.old_grid,args.old_voxel,args.output_dir)
    print(report["gate1"],report["gate2"],report.get("error",""))
    return int(report["gate2"]!="PASS")


if __name__=="__main__":
    raise SystemExit(main())
