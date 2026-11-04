"""Read-only Candidate B ground DEM source and aligned cell-coverage preflight."""
import argparse
from datetime import datetime, timezone
from hashlib import file_digest
from itertools import combinations
import json
import math
from pathlib import Path
import re
import shutil
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import pyogrio
from pyproj import CRS, Transformer
import rasterio
from rasterio.windows import Window
from shapely.geometry import box

from ouem.native.terrain import NativeTerrainError, inspect_dem

AOI = (-22575, -39925, -22475, -39825)
S3 = "https://gic-tokyo.s3.ap-northeast-1.amazonaws.com"
SOURCES = {"tama": ("2023", "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_show?id=t000029d0000000020"),
           "23ku": ("2024", "https://odm.bodik.jp/api/3/action/package_show?id=t000029d00000000241")}
CKAN = "https://www.geospatial.jp/ckan/api/3/action/package_show?id="
MAX_BYTES = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def download(url, path, log):
    receipt = dict(url=url, file=path.name, requested_at=datetime.now(timezone.utc).isoformat())
    log.append(receipt)
    try:
        with urlopen(url, timeout=30) as reply:
            receipt["http_status"] = reply.status
            receipt["final_url"] = reply.geturl()
            require(reply.status == 200 and reply.geturl() == url, "unexpected HTTP status or redirect")
            declared = reply.headers.get("Content-Length")
            require(declared is None or 0 < int(declared) <= MAX_BYTES, "download size limit")
            with path.open("xb") as output:
                size = 0
                while chunk := reply.read(64 * 1024):
                    size += len(chunk)
                    require(size <= MAX_BYTES, "download size limit")
                    output.write(chunk)
            require(size > 0 and (declared is None or size == int(declared)), "incomplete download")
        receipt.update(bytes=size, sha256=digest(path))
        return path
    except Exception as exc:
        receipt.update(error=f"{type(exc).__name__}: {exc}")
        if hasattr(exc, "code"):
            receipt["http_status"] = exc.code
        raise


def catalogue(path):
    data = json.loads(path.read_bytes())
    require(data["success"] is True, "CKAN request unsuccessful")
    return data["result"]


def index_tiles(bounds, zoom=14):
    x0, y0, x1, y1 = Transformer.from_crs(6677, 3857, always_xy=True).transform_bounds(*bounds)
    half = 6378137 * math.pi
    scale = 2**zoom / (2*half)
    return [(zoom, x, y)
            for x in range(math.floor((x0+half)*scale), math.floor((x1+half)*scale)+1)
            for y in range(math.floor((half-y1)*scale), math.floor((half-y0)*scale)+1)]


def tile_urls(frame, year, search):
    require(frame.crs is not None and frame.crs.to_epsg() == 3857, "MVT CRS must be EPSG:3857")
    require({"MESH_NO", "URL"} <= set(frame.columns), "MVT fields missing")
    results = {}
    projected = frame.to_crs(6677)
    for mesh, url in projected.loc[projected.intersects(search), ["MESH_NO", "URL"]].itertuples(index=False, name=None):
        require(isinstance(mesh, str) and re.fullmatch(r"[0-9]{2}[A-Z]{2}[0-9]{4}", mesh), "invalid index mesh ID")
        require(url == f"{S3}/{year}/dig/grd50/{mesh}.zip", "unexpected terrain URL in index")
        results[mesh] = url
    return results


def unpack(path, mesh):
    output = path.with_suffix(".tif")
    with ZipFile(path) as archive:
        expected = mesh+".tif"
        members = [item for item in archive.infolist() if item.filename == expected]
        require(len(members) == 1 and 0 < members[0].file_size <= MAX_BYTES, "expected one bounded original TIFF")
        with archive.open(members[0]) as source, output.open("xb") as target:
            shutil.copyfileobj(source, target)  # Read through EOF for the ZIP CRC check.
    return output


def integer_grid(value):
    require(math.isfinite(value) and abs(value-round(value)) < 1e-8, "grid misalignment; no resampling performed")
    return round(value)


def horizontal_status(crs, *, catalogue_declares_ix=False):
    if crs and crs.to_epsg() == 6677:
        return "identified EPSG:6677"
    require(crs and catalogue_declares_ix, "ambiguous horizontal CRS")
    reported, reference = CRS.from_wkt(crs.to_wkt()), CRS.from_epsg(6677)
    first, second = reported.coordinate_operation, reference.coordinate_operation
    require(reported.is_projected and first and first.method_name == second.method_name
            and len(first.params) == len(second.params)
            and all(a.name == b.name and abs(a.value-b.value) <= 1e-10
                    and a.unit_conversion_factor == b.unit_conversion_factor
                    for a,b in zip(first.params,second.params))
            and reported.ellipsoid.semi_major_metre == reference.ellipsoid.semi_major_metre
            and abs(reported.ellipsoid.inverse_flattening-reference.ellipsoid.inverse_flattening) < 1e-9
            and [(a.direction,a.unit_conversion_factor) for a in reported.axis_info] == [("east",1.),("north",1.)]
            and re.search(r'AUTHORITY\["EPSG","6677"\]\]$',crs.to_wkt()),
            "unidentified CRS does not support a catalogue-based grid comparison")
    return "conditional EPSG:6677 comparison; declared authority and matching projection, unnamed embedded datum"


def raster_cells(path, bounds, *, catalogue_declares_ix=False):
    x0, y0, x1, y1 = bounds
    shape = (integer_grid((y1-y0)*2), integer_grid((x1-x0)*2))
    require(0 < math.prod(shape) <= 1_000_000 and min(shape) > 0, "invalid AOI grid size")
    data = np.full(shape, np.nan)
    footprint = np.zeros(shape, bool)
    with rasterio.open(path) as ds:
        require(ds.driver == "GTiff" and ds.count == 1, "expected single-band GeoTIFF")
        horizontal = horizontal_status(ds.crs,catalogue_declares_ix=catalogue_declares_ix)
        t = ds.transform
        require((t.a,t.b,t.d,t.e) == (.5,0,0,-.5), "expected north-up 0.5 m grid")
        require(ds.scales == (1.,) and ds.offsets == (0.,), "nonidentity scale/offset")
        require(ds.nodata is not None and math.isfinite(ds.nodata), "finite declared NoData required")
        x, y = integer_grid((t.c-x0)*2), integer_grid((y1-t.f)*2)
        left, right, top, bottom = max(x,0), min(x+ds.width,shape[1]), max(y,0), min(y+ds.height,shape[0])
        if left < right and top < bottom:
            values = ds.read(1, window=Window(left-x,top-y,right-left,bottom-top), masked=True)
            valid = np.asarray(values.data,dtype=float)
            valid[np.ma.getmaskarray(values) | ~np.isfinite(valid)] = np.nan
            data[top:bottom,left:right] = valid
            footprint[top:bottom,left:right] = True
        metadata = dict(sha256=digest(path), crs=ds.crs.to_string(), wkt=ds.crs.to_wkt(),
                        affine=list(t)[:6], extent=list(ds.bounds), shape=list(ds.shape), dtype=ds.dtypes[0],
                        band_count=ds.count, resolution=list(ds.res), nodata=ds.nodata,
                        scale=ds.scales[0], offset=ds.offsets[0], units=list(ds.units),
                        horizontal_status=horizontal, area_or_point=ds.tags().get("AREA_OR_POINT"),
                        mask_flags=[[flag.name for flag in flags] for flags in ds.mask_flag_enums],
                        footprint_cells=int(footprint.sum()), valid_cells=int(np.isfinite(data).sum()),
                        elevation=stats(data[np.isfinite(data)]))
    try:
        inspect_dem(path)
    except NativeTerrainError as exc:
        metadata["native_structure"] = str(exc)
    else:
        metadata["native_structure"] = "compatible raster structure only"
    return metadata, data, footprint


def stats(values):
    if values.size == 0:
        return None
    return dict(min=float(values.min()), max=float(values.max()), mean=float(values.mean()),
                median=float(np.median(values)))


def coverage(tiles, footprints):
    valid = np.count_nonzero(np.isfinite(tiles),axis=0)
    covered = np.any(footprints,axis=0)
    return dict(cells=int(valid.size), valid=int(np.count_nonzero(valid)),
                footprint=int(covered.sum()), nodata_only=int((covered & (valid == 0)).sum()),
                uncovered=int((valid == 0).sum()), overlapping=int((valid > 1).sum()))


def compare(a, b):
    both = np.isfinite(a) & np.isfinite(b)
    return dict(cells=int(both.sum()), b_minus_a_m=stats(b[both]-a[both]))


def seam(a, b, other):
    # Report adjacent native centres on opposite exclusive sides; no filling.
    jumps = []
    for axis in (0,1):
        left = [slice(None)]*2
        right = left.copy()
        left[axis], right[axis] = slice(None,-1), slice(1,None)
        left,right = tuple(left),tuple(right)
        for sa,sb in ((left,right),(right,left)):
            valid = np.isfinite(a[sa]) & np.isfinite(b[sb]) & ~other[sa] & ~other[sb]
            jumps.extend((b[sb]-a[sa])[valid])
    return dict(edges=len(jumps), b_minus_a_m=stats(np.asarray(jumps)))


def inspect_source(source, directory, report):
    year, vertical_url = SOURCES[source]
    log = report["downloads"]
    dist = catalogue(download(CKAN+f"tokyopc-{source}-{year}",directory/"catalogue.json",log))
    template = f"{S3}/{year}/dig/Vectortile/{source}/grd50/{{z}}/{{x}}/{{y}}.pbf"
    resources = [row for row in dist["resources"] if row["url"] == template]
    require(len(resources) == 1 and "グラウンドデータ" in resources[0]["description"],
            "ground DEM index not confirmed by catalogue")
    report.update(title=dist["title"], author=dist["author"], license=dist["license_id"],
                  license_url=dist.get("license_url"), index_template=template,
                  catalogue_resource=resources[0]["id"], vertical="UNRESOLVED")
    try:
        vertical = catalogue(download(vertical_url,directory/"vertical.json",log))
        report["vertical_catalogue_license"] = vertical.get("license_id")
        evidence = [line for line in vertical.get("notes","").splitlines() if "東京湾平均海面" in line]
        if evidence:
            report.update(vertical="Tokyo Bay mean sea level (T.P.), provider-declared", vertical_evidence=evidence)
    except Exception as exc:
        report["vertical_evidence_error"] = str(exc)
    search = box(*AOI).buffer(2,join_style=2)
    meshes = {}
    report["indexes"] = []
    for z,x,y in index_tiles(search.bounds):
        index = download(template.format(z=z,x=x,y=y),directory/f"{z}-{x}-{y}.pbf",log)
        frame = pyogrio.read_dataframe(index,Z=z,X=x,Y=y)
        candidates = tile_urls(frame,year,search)
        report["indexes"].append(dict(xyz=[z,x,y], layer_features=len(frame), crs=frame.crs.to_string(),
                                      meshes=sorted(candidates)))
        meshes.update(candidates)
    require(meshes, "no source tile candidates")
    require(len(meshes) <= 12, "too many source tile candidates")
    report["tiles"] = {}
    rasters = {}
    for mesh,url in sorted(meshes.items()):
        archive = download(url,directory/(mesh+".zip"),log)
        path = unpack(archive,mesh)
        declared_ix = "日本測地系2011" in dist["notes"] and ("第9系" in dist["notes"] or "第９系" in dist["notes"])
        metadata, values, footprint = raster_cells(path,AOI,catalogue_declares_ix=declared_ix)
        report["tiles"][mesh] = dict(tiff=path.name, **metadata)
        rasters[mesh] = (values,footprint)
    report["coverage"] = coverage(*zip(*rasters.values()))
    return rasters


def summarize(rasters):
    flat = {f"{source}/{mesh}": tile for source, tiles in rasters.items() for mesh,tile in tiles.items()}
    overall = coverage(*zip(*flat.values()))
    masks = {key:np.isfinite(tile[0]) for key,tile in flat.items()}
    pairwise = {}
    # For seam diagnostics, only compare centres with exactly one supplying tile.
    multiple = np.count_nonzero(list(masks.values()),axis=0)>1
    for a,b in combinations(flat,2):
        first,second = flat[a][0],flat[b][0]
        pairwise[f"{a} -> {b}"] = dict(overlap=compare(first,second), exclusive_adjacent=seam(first,second,multiple))
    full = []
    if not overall["uncovered"]:
        for n in range(1,len(masks)+1):
            full = [list(group) for group in combinations(masks,n) if np.logical_or.reduce([masks[k] for k in group]).all()]
            if full:
                break
    return dict(combined=overall,pairs=pairwise,minimum_full_tile_sets=full,
                single_sources=[s for s,tiles in rasters.items() if coverage(*zip(*tiles.values()))["uncovered"] == 0])


def run(out):
    out.mkdir()
    report = dict(scope="EXPERIMENTAL / NOT_FORMALLY_ACCEPTED", status="BLOCKED", aoi=dict(epsg=6677,bounds=AOI),
                  method="Aligned native 0.5 m pixel centres; mask and finite values; no interpolation or mosaic.",
                  terrain_integration_ready=False,
                  terrain_integration_reason="This preflight does not approve Terrain integration. "
                                             "Confirm horizontal and vertical compatibility and review source selection and seams separately.",
                  sources={})
    rasters = {}
    for source in SOURCES:
        directory = out/source
        details = report["sources"][source] = dict(downloads=[])
        try:
            directory.mkdir()
            rasters[source] = inspect_source(source,directory,details)
        except Exception as exc:
            details["error"] = f"{type(exc).__name__}: {exc}"
    if rasters.keys() == SOURCES.keys():
        try:
            summary = summarize(rasters)
            clear = all(s["vertical"] != "UNRESOLVED" and all(
                t["horizontal_status"] == "identified EPSG:6677" for t in s["tiles"].values())
                for s in report["sources"].values())
            status = "PASS" if not summary["combined"]["uncovered"] and clear else "CONDITIONAL"
            json.dumps(summary, allow_nan=False)
        except Exception as exc:
            report["aggregation_error"] = f"{type(exc).__name__}: {exc}"
        else:
            report.update(summary, status=status)
    report["vertical_compatibility"] = "Building EPSG:6697 / vertical EPSG:6695 source declaration; survey realization and epoch compatibility unverified."
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    pending = out/"report.pending.json"
    with pending.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
    pending.rename(out/"report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    report = run(parser.parse_args().output_dir)
    print(report["status"])
    return int(report["status"] == "BLOCKED")


if __name__ == "__main__":
    raise SystemExit(main())
