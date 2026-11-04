"""Candidate B T1 read-only replay. Output maps describe differences and masks."""
import argparse
import csv
import json
from pathlib import Path
import struct

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt, maximum_filter

from ouem.terrain_candidate_b_preflight import AOI, digest, raster_cells, require

HASHES = {
    "tama/09LD3423": "8b92f4ce3cb72f6084858df629b0cc676cd7cd45e6973942f0a9cf0c793b34ca",
    "tama/09LD3433": "491defd8c37fb52241d73ae4bd2142c605056133b51a320a750aeddfb9018d92",
    "23ku/09LD3423": "62b98534376827a0906b6703522764356e20eb5c2d8ef53ac36b1ea3e3e6b8b8",
    "23ku/09LD3433": "66190876d0baab6aa25fb518a6e4827d45b78286a2e3fa385e0fe9b61f7eb18c",
}
STEP = .5
AFFINE = from_origin(AOI[0], AOI[3], STEP, STEP)


def distribution(values):
    values = np.asarray(values, dtype="float64")
    values = values[np.isfinite(values)]
    if not values.size:
        return {"n": 0}
    levels = (1, 5, 25, 50, 75, 95, 99)
    quantiles = np.percentile(values, levels, method="linear")
    absolute = np.abs(values)
    return dict(n=int(values.size), min=float(values.min()), max=float(values.max()),
                mean=float(values.mean()), mae=float(absolute.mean()), rmse=float(np.sqrt(np.mean(values**2))),
                quantiles={f"p{q:02}":float(value) for q,value in zip(levels,quantiles)},
                abs_exceeds_m={str(t):int((absolute>t).sum()) for t in (.05,.10,.20,.50)})


def raw_geotags(path):
    """Read ModelPixelScale and ModelTiepoint from the first classic TIFF IFD."""
    with path.open("rb") as f:
        marker = f.read(2)
        require(marker in (b"II",b"MM"), "invalid TIFF byte order")
        order = "<" if marker == b"II" else ">"
        version, offset = struct.unpack(order+"HI",f.read(6))
        require(version == 42, "expected classic TIFF")
        f.seek(offset)
        count, = struct.unpack(order+"H",f.read(2))
        tags = {}
        for _ in range(count):
            code, kind, n, pos = struct.unpack(order+"HHII",f.read(12))
            if code not in (33550,33922):
                continue
            require(kind == 12 and n == (3 if code == 33550 else 6), "unexpected GeoTIFF tag shape")
            next_entry = f.tell()
            f.seek(pos)
            tags[code] = struct.unpack(order+"d"*n,f.read(8*n))
            f.seek(next_entry)
    require(set(tags) == {33550,33922}, "missing GeoTIFF tiepoint or pixel scale")
    return dict(pixel_scale=tags[33550], tiepoint=tags[33922])


def centre(row, col):
    return AFFINE.c + AFFINE.a*(col+.5), AFFINE.f + AFFINE.e*(row+.5)


def overlap_diagnostics(tama, ward):
    a,b = np.isfinite(tama),np.isfinite(ward)
    shared = a & b
    delta = np.where(shared,ward-tama,np.nan)
    # Distances to an observed invalid centre, not to a padded AOI edge.
    distances = [distance_transform_edt(mask)*STEP for mask in (a,b)]
    distance = np.minimum(*distances)
    mesh_north = np.indices(delta.shape)[0] < int((AOI[3]+39900)/STEP)
    segments = {}
    for key, mask in (("north_09LD3423",mesh_north),("south_09LD3433",~mesh_north)):
        segments[key] = distribution(delta[mask])
    bands = {}
    for lo,hi in ((0,1),(1,2),(2,5),(5,np.inf)):
        bands[f"{lo}-{hi}m"] = distribution(delta[(distance>lo)&(distance<=hi)])
    extremes = []
    for func in (np.nanargmin,np.nanargmax):
        row,col = map(int,np.unravel_index(func(delta),delta.shape))
        sl = np.s_[max(row-1,0):row+2,max(col-1,0):col+2]
        extremes.append(dict(row=row,col=col,xy=centre(row,col),ward_minus_tama=float(delta[row,col]),
                             tama=float(tama[row,col]),ward=float(ward[row,col]),
                             distance_to_invalid_m=[float(d[row,col]) for d in distances],
                             validity_3x3=(a.astype("uint8")+2*b)[sl].tolist()))
    outliers = {}
    for threshold in (.05,.10,.20,.50):
        rows,cols = np.where(np.abs(delta)>threshold)
        bounds = None
        if rows.size:
            west,north = centre(int(rows.min()),int(cols.min()))
            east,south = centre(int(rows.max()),int(cols.max()))
            bounds = [west,south,east,north]
        outliers[str(threshold)] = dict(n=int(rows.size),centre_bounds=bounds)
    # Centred local slope in the original Tama samples; require all four neighbours.
    dx = (tama[1:-1,2:]-tama[1:-1,:-2])/(2*STEP)
    dy = (tama[2:,1:-1]-tama[:-2,1:-1])/(2*STEP)
    slope = np.hypot(dx,dy)
    d = delta[1:-1,1:-1]
    ok = np.isfinite(slope)&np.isfinite(d)
    correlation = None
    if ok.sum()>1 and np.std(slope[ok])>0 and np.std(np.abs(d[ok]))>0:
        correlation = float(np.corrcoef(slope[ok],np.abs(d[ok]))[0,1])
    return (dict(total=distribution(delta),by_mesh=segments,by_boundary_distance=bands,
                 extremes=extremes, outliers=outliers,
                 slope=dict(n=int(ok.sum()),pearson_abs_difference=correlation)),
            delta,a.astype("uint8")+2*b,[np.where(shared,d,np.nan) for d in distances])


def policy(first, second, tile_first, tile_second, first_name):
    """Evaluate all oriented east/south edges without writing a selected-height raster."""
    prefer = np.isfinite(first)
    chosen = np.where(prefer,first,second)
    tile = np.where(prefer,tile_first,tile_second)
    other_name = "WARD" if first_name=="TAMA" else "TAMA"
    rows, comparisons = [], {}
    for label, left, right in (("east",np.s_[:,:-1],np.s_[:,1:]),
                               ("south",np.s_[:-1,:],np.s_[1:,:])):
        jump = chosen[right]-chosen[left]
        switch = prefer[left]!=prefer[right]
        mesh_edge = tile[left]!=tile[right]
        local = maximum_filter(switch.astype("uint8"),size=9,mode="constant")>0
        comparisons[label] = dict(
            cross_source=distribution(jump[switch]),
            cross_source_also_mesh=distribution(jump[switch&mesh_edge]),
            within_source_mesh_edge=distribution(jump[~switch&mesh_edge]),
            local_same_source_same_tile=distribution(jump[local&~switch&~mesh_edge]),
            local_reference_radius_m=2.0)
        for row,col in np.argwhere(switch|mesh_edge):
            r,c = int(row),int(col)
            end = (r+int(label=="south"),c+int(label=="east"))
            rows.append(dict(direction=label,x0=centre(r,c)[0],y0=centre(r,c)[1],
                             x1=centre(*end)[0],y1=centre(*end)[1],
                             source_from=first_name if prefer[r,c] else other_name,
                             source_to=first_name if prefer[end] else other_name,
                             mesh_from=int(tile[r,c]),mesh_to=int(tile[end]),
                             source_switch=bool(switch[r,c]),mesh_boundary=bool(mesh_edge[r,c]),
                             jump_m=float(jump[r,c])))
    switches = [row for row in rows if row["source_switch"]]
    return (dict(chosen={first_name:int(prefer.sum()),other_name:int((~prefer).sum())},
                 switch_edges=len(switches), directions=comparisons,
                 largest_switch=max(switches,key=lambda row:abs(row["jump_m"]),default=None)),rows)


def diagnostic_map(path, arrays, dtype, nodata, labels):
    with rasterio.open(path,"w",driver="GTiff",width=arrays[0].shape[1],height=arrays[0].shape[0],
                       count=len(arrays),dtype=dtype,crs="EPSG:6677",transform=AFFINE,
                       nodata=nodata,compress="deflate") as dst:
        for band,(array,label) in enumerate(zip(arrays,labels),1):
            dst.write(array.astype(dtype),band)
            dst.set_band_description(band,label)


def source_grid(tiles):
    require(not np.any(np.isfinite(tiles[0])&np.isfinite(tiles[1])), "same-source tile overlap is ambiguous")
    return np.where(np.isfinite(tiles[0]),tiles[0],tiles[1]), np.where(np.isfinite(tiles[0]),3423,3433)


def run(inputs, out):
    out.mkdir()
    report = dict(status="BLOCKED",terrain_integration_ready=False, scope="T1 diagnostic only",
                  aoi=dict(epsg=6677,bounds=AOI,affine=list(AFFINE)[:6]), inputs={})
    try:
        grids = {}
        for key,expected in HASHES.items():
            path = inputs/(key+".tif")
            require(digest(path)==expected,f"SHA-256 mismatch: {key}")
            metadata,values,_ = raster_cells(path,AOI,catalogue_declares_ix=key.startswith("23ku/"))
            require(metadata["sha256"]==expected,f"read-time SHA-256 mismatch: {key}")
            grids[key] = values
            report["inputs"][key] = metadata | {"raw_geotiff":raw_geotags(path)}
        tama,tm = source_grid([grids[f"tama/09LD{i}"] for i in (3423,3433)])
        ward,wm = source_grid([grids[f"23ku/09LD{i}"] for i in (3423,3433)])
        measured = tuple(int(mask.sum()) for mask in (np.isfinite(tama),np.isfinite(ward),
                         np.isfinite(tama)|np.isfinite(ward),np.isfinite(tama)&np.isfinite(ward)))
        require(tama.shape==(200,200) and measured==(28233,16103,40000,4336),
                f"preflight mask counts differ: {measured}")
        overlap,delta,validity,distances = overlap_diagnostics(tama,ward)
        require(tuple(item["n"] for item in overlap["by_mesh"].values()) == (3261,1075),
                "preflight overlap mesh counts differ")
        policies = {}
        for name,values in (("TAMA_FIRST",(tama,ward,tm,wm,"TAMA")),
                            ("WARD_FIRST",(ward,tama,wm,tm,"WARD"))):
            policies[name],rows = policy(*values)
            with (out/(name.lower()+"_edges.csv")).open("x",encoding="utf-8",newline="") as stream:
                writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        diagnostic_map(out/"ward_minus_tama.tif",[delta],"float64",np.nan,["WARD_FIRST minus TAMA_FIRST on overlap (m)"])
        diagnostic_map(out/"source_validity.tif",[validity],"uint8",255,["0 neither; 1 Tama; 2 ward; 3 both"])
        diagnostic_map(out/"overlap_distance.tif",distances,"float64",np.nan,
                       ["Tama nearest invalid centre (m)","Ward nearest invalid centre (m)"])
        for key,expected in HASHES.items():
            require(digest(inputs/(key+".tif"))==expected,f"input changed: {key}")
        difference = np.where(np.isfinite(delta),delta,0.)
        report.update(status="PASS", coverage=dict(tama=measured[0],ward=measured[1],union=measured[2],overlap=measured[3]),
                      overlap=overlap, policies=policies,
                      policy_difference=dict(changed_source_centres=measured[3],
                          changed_value_centres=int(np.count_nonzero(np.isfinite(delta)&(delta!=0))),
                          ward_first_minus_tama_first=overlap["total"],
                          edge_jump_change={axis:distribution(np.diff(difference,axis=i))
                                            for axis,i in (("east",1),("south",0))},
                          equal_outside_overlap=measured[2]-measured[3]))
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    pending = out/"report.pending.json"
    pending.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    pending.rename(out/"diagnostic_report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-run",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args = parser.parse_args()
    report = run(args.input_run,args.output_dir)
    print(report["status"],report.get("error",""))
    return int(report["status"]!="PASS")


if __name__ == "__main__":
    raise SystemExit(main())
