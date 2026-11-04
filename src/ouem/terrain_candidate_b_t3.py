"""Isolated Candidate B WARD_FIRST Terrain preparation, outside Standard Terrain."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from scipy.spatial.distance import cdist

from ouem.terrain_candidate_b_diagnostics import AFFINE, HASHES, centre, policy
from ouem.terrain_candidate_b_preflight import AOI, digest, raster_cells, require

PROFILE = "ouem-experimental-candidate-b-terrain/v0.1"
TILES = {i: key for i, key in enumerate(HASHES, 1)}
HEIGHT_NODATA = -32767.0


def select(grids):
    """Select with explicit tile provenance; refuse ambiguity even under fallback."""
    tama, ward = (np.isfinite(grids[start:start+2]) for start in (0,2))
    require(not np.any(tama.sum(axis=0)>1) and not np.any(ward.sum(axis=0)>1),
            "same-source valid tile overlap")
    ids = np.zeros(grids.shape[1:], dtype="uint8")
    for tile_id, values in enumerate(grids, 1):
        ids[np.isfinite(values)] = tile_id
    require(ids.all(), "uncovered cell")
    values = np.take_along_axis(grids, (ids-1)[None], axis=0)[0]
    return values, ids


def write_raster(path, array, nodata, label):
    with rasterio.open(path, "w", driver="GTiff", width=200, height=200, count=1, crs="EPSG:6677",
                       transform=AFFINE, dtype=array.dtype, nodata=nodata, compress="deflate") as dst:
        dst.write(array, 1)
        dst.update_tags(AREA_OR_POINT="Area", ouem_profile=PROFILE, role=label)


def audit(folder, grids, ids):
    arrays = []
    for filename,dtype,nodata,role in (("terrain.tif","float32",HEIGHT_NODATA,"terrain"),
                                      ("source_tile.tif","uint8",0,"source_tile")):
        with rasterio.open(folder/filename) as ds:
            require(ds.driver=="GTiff" and ds.count==1 and ds.shape==(200,200) and ds.dtypes==(dtype,)
                    and ds.crs and ds.crs.to_epsg()==6677 and ds.transform==AFFINE and ds.nodata==nodata
                    and ds.scales==(1.,) and ds.offsets==(0.,)
                    and ds.tags().get("ouem_profile")==PROFILE and ds.tags().get("role")==role
                    and ds.tags().get("AREA_OR_POINT")=="Area", f"reopened metadata differs: {filename}")
            data = ds.read(1, masked=True)
            require(not np.ma.getmaskarray(data).any() and np.isfinite(data.data).all(),
                    f"invalid output cells: {filename}")
            arrays.append(data.data)
    heights, actual_ids = arrays
    require(np.array_equal(ids,actual_ids),"reopened tile IDs differ")
    # Check the actual output against original tile values and masks by provenance ID.
    ward_valid = np.isfinite(grids[2:]).any(axis=0)
    require(np.array_equal(actual_ids>=3,ward_valid),"reopened priority differs from input masks")
    for code in TILES:
        mask = actual_ids==code
        source = grids[code-1][mask]
        require(np.isfinite(source).all() and np.array_equal(heights[mask].view("uint32"),source.view("uint32")),
                f"reopened Float32 bits or source mask differ for tile ID {code}")
    return heights, actual_ids


def diagnostics(grids, heights, ids):
    tama, ward = (np.where(np.isfinite(a),a,b).astype("float64") for a,b in (grids[:2],grids[2:]))
    tm, wm = (np.where(np.isfinite(a),3423,3433) for a in (grids[0],grids[2]))
    result, edges = policy(ward,tama,wm,tm,"WARD")
    require(result["chosen"]=={"WARD":16103,"TAMA":23897} and result["switch_edges"]==284,
            "T1 source or switch counts differ")
    for direction,n,mae in (("east",200,.043905019760131836),("south",84,.030797617776053294)):
        stats = result["directions"][direction]["cross_source"]
        require(stats["n"]==n and abs(stats["mae"]-mae)<1e-12, f"T1 {direction} switch metrics differ")
    require(abs(abs(result["largest_switch"]["jump_m"])-.17200088500976562)<1e-12,
            "T1 maximum switch jump differs")
    # Verify the T1 jumps on the values reopened from disk, rather than only the scenario.
    switches = [edge for edge in edges if edge["source_switch"]]
    ends = np.array([[e[k] for k in ("x0","y0","x1","y1")] for e in switches])
    cols0,rows0 = ((ends[:,0]-AOI[0])*2).astype(int),((AOI[3]-ends[:,1])*2).astype(int)
    cols1,rows1 = ((ends[:,2]-AOI[0])*2).astype(int),((AOI[3]-ends[:,3])*2).astype(int)
    chosen = ids>=3
    require(np.all(chosen[rows0,cols0]!=chosen[rows1,cols1])
            and sum(np.count_nonzero(np.diff(chosen,axis=i)) for i in (0,1))==len(switches),
            "reopened switch edges differ")
    jumps = heights[rows1,cols1].astype("float64")-heights[rows0,cols0].astype("float64")
    require(np.array_equal(jumps,[e["jump_m"] for e in switches]),"reopened switch jumps differ")
    delta = ward-tama
    require(int(np.isfinite(delta).sum())==4336,"T1 overlap count differs")
    mask = np.abs(delta)>.50
    r,c = np.where(mask)
    require(len(r)==47 and (ids[mask]>=3).all(),"T1 outlier cells or priority differ")
    low = tuple(map(int,np.unravel_index(np.nanargmin(delta),delta.shape)))
    xy = [centre(int(row),int(col)) for row,col in zip(r,c)]
    return dict(t1_ward_first=result, outliers=dict(cells=len(r),threshold_m=.5,
                selected_min_m=float(heights[mask].min()),selected_max_m=float(heights[mask].max()),
                worst=dict(xy=centre(*low),ward_minus_tama_m=float(delta[low]),
                           selected_m=float(heights[low]),source_tile=int(ids[low])),
                endpoint_cells=int(np.count_nonzero(cdist(xy,np.vstack((ends[:,:2],ends[:,2:]))).min(axis=1)==0)),
                min_switch_midpoint_distance_m=float(cdist(xy,(ends[:,:2]+ends[:,2:])/2).min()),
                selected_cells=[dict(xy=point,selected_m=float(heights[row,col]),tile_id=int(ids[row,col]),
                                     ward_minus_tama_m=float(delta[row,col]))
                                for point,row,col in zip(xy,r,c)]))


def save_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write("\n")


def run(inputs, out):
    out.mkdir()
    try:
        sources, arrays = {}, []
        for tile_id,key in TILES.items():
            path = inputs/(key+".tif")
            expected = HASHES[key]
            require(digest(path)==expected, f"input SHA-256 mismatch: {key}")
            meta, values, _ = raster_cells(path,AOI,catalogue_declares_ix=key.startswith("23ku/"))
            require(meta["sha256"]==expected and meta["dtype"]=="float32",f"input identity or dtype differs: {key}")
            sources[str(tile_id)] = {"file":key+".tif","release":"2024" if key.startswith("23ku/") else "2023"} | meta
            arrays.append(values.astype("float32"))
        grids = np.stack(arrays)
        heights, ids = select(grids)
        require(np.isfinite(heights).all() and not np.any(heights==HEIGHT_NODATA),
                "nonfinite or reserved output NoData value")
        with TemporaryDirectory(prefix=".stage-",dir=out) as name:
            stage = Path(name)
            product = stage/"artifacts"
            product.mkdir()
            write_raster(product/"terrain.tif",heights,HEIGHT_NODATA,"terrain")
            write_raster(product/"source_tile.tif",ids,0,"source_tile")
            measured, mapped = audit(product,grids,ids)
            results = diagnostics(grids,measured,mapped)
            results.update(valid_cells=int(measured.size),tile_counts={str(i):int((mapped==i).sum()) for i in TILES},
                           original_float32_bits="MATCH",reopen_audit="PASS")
            save_json(product/"validation.json",results)
            manifest = dict(profile=PROFILE,status="COMPLETED",scope="EXPERIMENTAL / NOT_FORMALLY_ACCEPTED",
                            terrain_integration_ready=False,policy="WARD_FIRST", grid=dict(epsg=6677,bounds=AOI,
                            shape=[200,200],affine=list(AFFINE)[:6],height_nodata=HEIGHT_NODATA,tile_nodata=0),
                            vertical="T.P. inferred for ward; DEM datum realization and epoch unverified; identity height",
                            horizontal="Conditional ward CRS interpretation as in T1; aligned centres, no reprojection",
                            inputs=sources, input_run=str(inputs), implementation_sha256=digest(Path(__file__)),
                            outputs={f"artifacts/{p.name}":digest(p) for p in sorted(product.iterdir())},
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            environment=dict(python=platform.python_version(),rasterio=rasterio.__version__))
            pending = stage/"manifest.json"
            save_json(pending,manifest)
            for key,expected in HASHES.items():
                require(digest(inputs/(key+".tif"))==expected, f"input changed before publication: {key}")
            product.rename(out/"artifacts")
            pending.rename(out/"manifest.json")
        return manifest
    except Exception as exc:
        (out/"manifest.json").unlink(missing_ok=True)
        failure = dict(profile=PROFILE,status="BLOCKED",error=f"{type(exc).__name__}: {exc}",
                       terrain_integration_ready=False)
        save_json(out/"failure.json",failure)
        return failure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-run",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args = parser.parse_args()
    report = run(args.input_run,args.output_dir)
    print(report["status"],report.get("error",""))
    return int(report["status"]!="COMPLETED")


if __name__ == "__main__":
    raise SystemExit(main())
