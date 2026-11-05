"""Candidate B experimental VoxCity grid preflight. No voxel generation."""
import argparse
from importlib.metadata import distribution, version
from itertools import combinations
import json
import math
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import geopandas as gpd
import numpy as np
from pyproj import Transformer
import rasterio
from scipy.spatial import ConvexHull, cKDTree
from shapely.geometry import box

from ouem import candidate_b_t4a as t4a
from ouem.adapters import voxcity as adapter
from ouem.terrain_candidate_b_preflight import AOI, digest, require

PROFILE = "ouem-candidate-b-t4b1-grid-preflight/v0.1"
T4A_SHA = "7fdc8839f785b54467dd6b67db5090caa34d9286a36a798cfae0d1ec0a5005d9"
PIN = "fa212656305328a9a657973bae26f352bfe813bc"
MESH = 1.


def selection(path, expected):
    t4a.verify(path,T4A_SHA)
    report = json.loads(path.read_bytes())
    require(report["profile"]==t4a.PROFILE and report["status"]=="COMPLETED"
            and report["vertical"]=="CONDITIONAL" and report["terrain_integration_ready"] is False
            and report["aoi"]["bounds"]==list(AOI),"unexpected T4-A report")
    rows = {r["source_id"]:r for r in report["buildings"]}
    require(len(rows)==len(report["buildings"]) and {k:(r["ouem_id"],r["source_lod"]) for k,r in rows.items()}==expected,
            "T4-A ID set differs from Standard")
    selected, excluded = {}, []
    for sid,row in sorted(rows.items()):
        if row["screen"]=="NO_SCREENING_FLAGS" and not row["flags"] and row["footprint"]["complete"] and row["footprint"]["outside_m2"]==0:
            selected[sid] = row
        else:
            require("FOOTPRINT_EXTENDS_OUTSIDE_AOI" in row["flags"],"unexpected T4-A exclusion")
            excluded.append({k:row[k] for k in ("source_id","ouem_id","source_lod","flags")})
    require(len(selected)==40 and len(excluded)==23,"T4-A selection count differs")
    return selected,excluded


def sample_dem(path, centres, rectangle, raster_dem):
    """Bound the engine's UTM nearest-neighbour lookup before it can extrapolate."""
    lons,lats = (np.asarray(centres[k]) for k in ("lons","lats"))
    x,y = Transformer.from_crs(4326,6677,always_xy=True).transform(lons,lats,errcheck=True)
    require(lons.shape==lats.shape==tuple(centres["grid_size"]) and np.isfinite(x).all() and np.isfinite(y).all(),
            "invalid VoxCity centre positions")
    xmin,ymin,xmax,ymax = AOI
    require(((x>=xmin)&(x<xmax)&(y>=ymin)&(y<ymax)).all(),"VoxCity centre outside the T3 AOI")
    require((np.diff(y,axis=0)>0).all() and (np.diff(x,axis=1)>0).all(),"unexpected VoxCity axis orientation")
    with rasterio.open(path) as ds:
        raster = ds.read(1,masked=True)
        require(not np.ma.getmaskarray(raster).any() and np.isfinite(raster.data).all() and (raster.data>=-1000).all(),
                "T3 contains invalid or engine-rewritten DEM values")
        row,col = np.indices(ds.shape)
        source_x,source_y = rasterio.transform.xy(ds.transform,row.ravel(),col.ravel())
    zone = int((float(lons.mean())+180)//6)+1
    utm = (32600 if lats.mean()>=0 else 32700)+zone
    sx,sy = Transformer.from_crs(6677,utm,always_xy=True).transform(source_x,source_y,errcheck=True)
    tx,ty = Transformer.from_crs(4326,utm,always_xy=True).transform(lons.ravel(),lats.ravel(),errcheck=True)
    points, targets = np.column_stack((sx,sy)),np.column_stack((tx,ty))
    tree = cKDTree(points)
    distance, index = tree.query(targets)
    planes = ConvexHull(points).equations
    require((targets@planes[:,:2].T+planes[:,2]<=1e-8).all(),
            "VoxCity nearest lookup would extrapolate beyond source centres")
    dem = raster_dem(str(path),MESH,rectangle,dem_interpolation=False)
    require(dem.shape==lons.shape and np.array_equal(dem,raster.data.ravel()[index].reshape(lons.shape)),
            "VoxCity DEM disagrees with checked UTM nearest samples")
    sample = np.stack(np.unravel_index(index,raster.shape),axis=-1).reshape(lons.shape+(2,))
    return dem,np.stack((x,y),axis=-1),sample,dict(utm_epsg=utm,max_nearest_distance_m=float(distance.max()),
                         min_aoi_edge_distance_m=float(min((x-xmin).min(),(xmax-x).min(),(y-ymin).min(),(ymax-y).min())))


def grid_buildings(buildings, rectangle, raster_buildings, dem, z_values):
    def raster(frame):
        height,segments,ids,filtered = raster_buildings(frame,MESH,rectangle,overlapping_footprint=True)
        require(ids.shape==dem.shape and height.shape==dem.shape and segments.shape==dem.shape
                and np.isin(ids,[0,*frame.id]).all(),"unexpected engine grid or owner IDs")
        return height,segments,ids.astype("int32"),filtered

    isolated = {}
    for i in buildings.index:
        _,_,ids,_ = raster(buildings.loc[[i]])
        isolated[int(buildings.at[i,"id"])] = ids!=0
    claims = np.sum(list(isolated.values()),axis=0)
    history = []
    previous = None
    converged = False
    for _ in range(8):
        height,segments,ids,filtered = raster(buildings)
        segments_count = np.fromiter((len(items) for items in segments.flat),dtype="int16").reshape(ids.shape)
        remapped = {row.ouem_id:int(row.id) for row in filtered.itertuples()}
        rows = []
        for row in buildings.itertuples():
            candidate = isolated[int(row.id)]
            samples = dem[ids==row.id]
            mapped = remapped.get(row.ouem_id)
            flags = []
            if mapped!=row.id:
                flags.append("FILTERED_OR_REMAPPED_ID")
            if not samples.size:
                flags.append("NO_OWNED_ENGINE_CELL")
                flags.append("NO_ISOLATED_PRECISE_CELL" if not candidate.any() else "LOST_OWNERSHIP_OR_REMAP")
            top = max(z_values[row.ouem_id])
            ground = None if not samples.size else math.fsum(samples)/len(samples)
            relative = None if ground is None else top-ground
            if relative is not None and relative<=0:
                flags.append("NONPOSITIVE_RELATIVE_HEIGHT")
            rows.append(dict(source_id=row.source_id,ouem_id=row.ouem_id,source_lod=int(row.source_lod),
                             id=int(row.id),engine_filtered_id=mapped,
                             isolated_cells=int(candidate.sum()),owned_cells=int(samples.size),
                             competing_candidate_cells=int(np.count_nonzero(candidate&(claims>1))),
                             owner_outside_isolated=int(np.count_nonzero((ids==row.id)&~candidate)),
                             z_top_abs=top,g_eff_abs=ground,height=relative,min_height=0.,
                             ground_min_abs=None if ground is None else float(samples.min()),
                             ground_max_abs=None if ground is None else float(samples.max()),flags=flags))
        history.append(dict(owners=int(np.unique(ids[ids>0]).size),owned_cells=int((ids>0).sum()),
                            changed_cells=None if previous is None else int((ids!=previous).sum())))
        if previous is not None and np.array_equal(ids,previous):
            converged = True
            break
        by_id = {r["id"]:r["height"] for r in rows if r["height"] is not None and r["height"]>0}
        buildings["height"] = [by_id.get(i,h) for i,h in zip(buildings.id,buildings.height)]
        previous = ids
    return ids,height,claims,rows,dict(iterations=history,converged=converged,
             overlapping_candidate_cells=int((claims>1).sum()),multi_segment_cells=int((segments_count>1).sum()),
             competitions=[dict(index=[int(i),int(j)], candidates=[key for key,mask in isolated.items() if mask[i,j]],
                                owner=int(ids[i,j]), segment_count=int(segments_count[i,j]),
                                raster_height=float(height[i,j]))
                           for i,j in np.argwhere(claims>1)])


def run(building_run,consumer_receipt,terrain_run,t4a_report,out):
    out.mkdir()
    report = dict(profile=PROFILE,status="BLOCKED",vertical="CONDITIONAL",terrain_integration_ready=False,t4b2_candidate=False)
    try:
        checked,expected,*_ = t4a.load_inputs(building_run,consumer_receipt,terrain_run)
        selected,excluded = selection(t4a_report,expected)
        checked["t4a_report"] = (t4a_report,T4A_SHA)
        for key,ref in json.loads(t4a_report.read_bytes())["inputs"].items():
            require(ref["sha256"]==checked[key][1],f"T4-A input binding differs: {key}")
        report.update(excluded=excluded,selected_ids=sorted(selected),
                      inputs={k:{"path":str(p),"sha256":sha} for k,(p,sha) in checked.items()})
        direct = json.loads(distribution("voxcity").read_text("direct_url.json"))
        require(version("voxcity")=="1.7.0" and direct.get("vcs_info",{}).get("commit_id")==PIN,
                "VoxCity pin mismatch")
        from voxcity.geoprocessor.raster import (
            create_building_height_grid_from_gdf_polygon,create_dem_grid_from_geotiff_polygon,
        )
        from voxcity.geoprocessor.raster.core import compute_cell_center_coords

        frame = gpd.read_file(checked["building_gpkg"][0],layer="building")
        require(frame.crs.to_epsg()==6677 and frame.source_id.is_unique
                and {row.source_id:(row.ouem_id,row.source_lod) for row in frame.itertuples()}==expected,
                "actual Standard CRS/IDs/LoDs differ")
        frame = frame[frame.source_id.isin(selected)].sort_values("ouem_id").reset_index(drop=True)
        z = {row.ouem_id:adapter._z_values(row.geometry) for row in frame.itertuples()}
        footprints = {row.ouem_id:adapter.build_normalized_footprint(row.geometry,row.ouem_id)
                      for row in frame.itertuples()}
        aoi = box(*AOI)
        require(all(aoi.covers(footprint) for footprint,_ in footprints.values()),
                "selected normalized footprint outside the AOI")
        overlaps = []
        for a,b in combinations(footprints,2):
            area = footprints[a][0].intersection(footprints[b][0]).area
            if area>0:
                overlaps.append(dict(ouem_ids=[a,b],area_m2=area))
        buildings = adapter._set_normalized_footprints(frame,footprints)
        buildings["id"] = buildings.ouem_id.map(adapter.numeric_id_mapping(buildings.ouem_id))
        buildings["height"],buildings["min_height"] = 1.,0.
        buildings,repairs = adapter._repair_post_crs(adapter._to_voxcity_building_crs(buildings),footprints)
        transform = Transformer.from_crs(6677,4326,always_xy=True)
        x0,y0,x1,y1 = AOI
        rectangle = [transform.transform(x,y,errcheck=True) for x,y in ((x0,y0),(x0,y1),(x1,y1),(x1,y0))]
        centres = compute_cell_center_coords(rectangle,MESH)
        report.update(voxcity=dict(version="1.7.0",commit=PIN),mesh_m=MESH,rectangle_lonlat=rectangle,
                      projected_aoi=AOI,orientation="axis 0 north from SW; axis 1 east from SW",
                      engine_grid={k:np.asarray(v).tolist() for k,v in centres.items() if k not in ("lons","lats")},
                      dem_interpolation=False,overlapping_footprint=True,post_crs_repairs=repairs,
                      footprint_overlaps=overlaps,environment=dict(python=platform.python_version(),os=platform.platform()),
                      implementation_sha256=digest(Path(__file__)))
        dem,xy,indices,coverage = sample_dem(checked["terrain"][0],centres,rectangle,create_dem_grid_from_geotiff_polygon)
        ids,height,claims,records,grid = grid_buildings(buildings,rectangle,create_building_height_grid_from_gdf_polygon,dem,z)
        for conflict in grid["competitions"]:
            conflict["centre_xy"] = xy[tuple(conflict["index"])].tolist()
        for r in records:
            baseline = selected[r["source_id"]]
            r.update(t4a_native_ground_mean=baseline["ground_m"]["mean"],footprint=footprints[r["ouem_id"]][1])
        candidate = grid["converged"] and all(not r["flags"] and not r["owner_outside_isolated"] for r in records)
        with TemporaryDirectory(prefix=".stage-",dir=out) as directory:
            stage = Path(directory)
            artifacts = stage/"grids"
            artifacts.mkdir()
            for name,array in dict(dem=dem,building_ids=ids,building_height=height,
                                   isolated_claim_count=claims,centres_xy=xy,t3_row_col=indices).items():
                np.save(artifacts/(name+".npy"),array,allow_pickle=False)
            for path,sha in checked.values():
                t4a.verify(path,sha)
            result = report | dict(status="COMPLETED",t4b2_candidate=candidate,grid=grid,dem_coverage=coverage,
                buildings=records,outputs={f"grids/{p.name}":digest(p) for p in sorted(artifacts.iterdir())})
            t4a.write(stage/"report.json",result)
            artifacts.rename(out/"grids")
            (stage/"report.json").rename(out/"report.json")
        return result
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        t4a.write(out/"failure.json",report)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("building-run","consumer-receipt","terrain-run","t4a-report","output-dir"):
        parser.add_argument("--"+name,type=Path,required=True)
    args = parser.parse_args()
    report = run(args.building_run,args.consumer_receipt,args.terrain_run,args.t4a_report,args.output_dir)
    print(report["status"],report.get("error",report.get("grid")))
    return int(report["status"]!="COMPLETED")


if __name__=="__main__":
    raise SystemExit(main())
