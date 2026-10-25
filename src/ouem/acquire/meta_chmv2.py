"""Opt-in CHMv2 acquisition PoC; no Native/Standard or engine promotion."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import urllib.request

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window
from rasterio.warp import transform_bounds
from shapely.geometry import box, shape
from shapely.ops import unary_union

from ouem.study_area import load_study_area

BASE_URL = "https://dataforgood-fb-data.s3.amazonaws.com/forests/v2/global/dinov3_global_chm_v2_ml3"
REGISTRY = "https://registry.opendata.aws/dataforgood-fb-forestsv2/"


class AcquisitionError(ValueError):
    """An acquisition or lossless-mosaic prerequisite failed."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path):
    path = Path(path)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)}


def download(url, path, max_bytes):
    """Retain a complete original object, never reuse an unverified cache."""
    path = Path(path)
    partial = path.with_suffix(path.suffix + ".part")
    if path.exists() or partial.exists():
        raise AcquisitionError(f"Refusing existing download: {path}")
    started = utc_now()
    with urllib.request.urlopen(url, timeout=60) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > max_bytes:
            raise AcquisitionError(f"Object exceeds byte limit: {url} ({length})")
        size = 0
        with partial.open("xb") as stream:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise AcquisitionError(f"Object exceeds byte limit: {url}")
                stream.write(chunk)
        if length is not None and size != int(length):
            raise AcquisitionError(f"Truncated object: {url}")
        receipt = {"method": "https_download", "url": url, "resolved_url": response.url,
                   "started_at": started, "acquired_at": utc_now(),
                   "etag": response.headers.get("ETag"),
                   "last_modified": response.headers.get("Last-Modified")}
    partial.rename(path)
    return {**receipt, **file_record(path)}


def retain_local(source, target, url):
    """Offline supplied bytes are not evidence of a successful remote acquisition."""
    with Path(source).open("rb") as src, Path(target).open("xb") as dst:
        shutil.copyfileobj(src, dst)
    return {"method": "local_copy", "url": url, "source_path": str(Path(source).resolve()),
            "acquired_at": None, "retained_at": utc_now(), **file_record(target)}


def select_tiles(index, area):
    """Select actual index features, not hypothetical computed quadkeys."""
    if not all(math.isfinite(v) for v in area.extent):
        raise AcquisitionError("AOI coordinates must be finite")
    bounds = transform_bounds(f"EPSG:{area.epsg}", "EPSG:4326", *area.extent, densify_pts=21)
    aoi = box(*bounds)
    if index.get("type") != "FeatureCollection":
        raise AcquisitionError("Expected GeoJSON FeatureCollection")
    if "crs" in index:
        name = index["crs"].get("properties", {}).get("name", "")
        if name not in ("urn:ogc:def:crs:OGC:1.3:CRS84", "EPSG:4326", "urn:ogc:def:crs:EPSG::4326"):
            raise AcquisitionError("Index must use WGS84 longitude/latitude")
    selected = {}
    for feature in index["features"]:
        geometry = shape(feature["geometry"])
        if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ("Polygon", "MultiPolygon"):
            raise AcquisitionError("Invalid tile-index polygon")
        if geometry.intersection(aoi).area <= 0:
            continue
        key = str(feature.get("properties", {}).get("tile", ""))
        if not re.fullmatch(r"[0-3]{10}", key) or key in selected:
            raise AcquisitionError("Expected unique zoom-10 quadkey")
        selected[key] = geometry
    if not selected or not unary_union(list(selected.values())).covers(aoi):
        raise AcquisitionError("Tile index does not cover the AOI envelope")
    return sorted(selected)


def json_number(value):
    if value is None or math.isfinite(value):
        return value
    return str(value)


def raster_metadata(src):
    return {"crs": str(src.crs), "width": src.width, "height": src.height,
            "dtype": src.dtypes[0], "count": src.count, "resolution": list(src.res),
            "transform": list(src.transform)[:6], "bounds": list(src.bounds),
            "nodata": json_number(src.nodata), "scales": list(src.scales),
            "offsets": list(src.offsets), "units": list(src.units),
            "mask_flags": [[flag.name for flag in flags] for flags in src.mask_flag_enums],
            "image_structure": src.tags(ns="IMAGE_STRUCTURE"), "tags": src.tags()}


def same_nodata(a, b):
    return a == b or (a is not None and b is not None and math.isnan(a) and math.isnan(b))


def mosaic_crop(paths, area, output, *, max_pixels=16_000_000):
    """Copy native pixels to an outward-snapped AOI envelope; never resample."""
    output = Path(output)
    if output.exists():
        raise AcquisitionError("Output already exists")
    bounds = transform_bounds(f"EPSG:{area.epsg}", "EPSG:3857", *area.extent, densify_pts=21)
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(path)) for path in paths]
        if not sources:
            raise AcquisitionError("No source tiles")
        first = sources[0]
        transform = first.transform
        for src in sources:
            t = src.transform
            if (src.crs != rasterio.crs.CRS.from_epsg(3857) or src.count != 1
                    or t.b != 0 or t.d != 0 or t.a <= 0 or t.e >= 0
                    or src.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") != "COG"):
                raise AcquisitionError("Expected single-band north-up EPSG:3857 COG")
            if (t.a != transform.a or t.e != transform.e or src.dtypes != first.dtypes
                    or not same_nodata(src.nodata, first.nodata)
                    or src.scales != first.scales or src.offsets != first.offsets
                    or src.units != first.units):
                raise AcquisitionError("Incompatible source pixel metadata; no implicit conversion")
            for offset in ((t.c-transform.c)/t.a, (t.f-transform.f)/t.e):
                if not math.isclose(offset, round(offset), abs_tol=1e-6, rel_tol=0):
                    raise AcquisitionError("Source grids are not aligned")
        left, bottom, right, top = bounds
        col0 = math.floor((left-transform.c)/transform.a)
        col1 = math.ceil((right-transform.c)/transform.a)
        row0 = math.floor((top-transform.f)/transform.e)
        row1 = math.ceil((bottom-transform.f)/transform.e)
        width, height = col1-col0, row1-row0
        if width <= 0 or height <= 0 or width*height > max_pixels:
            raise AcquisitionError("AOI exceeds output pixel limit or has invalid size")
        dst_transform = transform @ Affine.translation(col0, row0)
        fill = first.nodata if first.nodata is not None else 0
        values = np.full((height, width), fill, dtype=first.dtypes[0])
        masks = np.zeros((height, width), dtype="uint8")
        covered = np.zeros((height, width), dtype=bool)
        for src in sources:
            x = round((src.transform.c-dst_transform.c)/transform.a)
            y = round((src.transform.f-dst_transform.f)/transform.e)
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(width, x+src.width), min(height, y+src.height)
            if x1 <= x0 or y1 <= y0:
                continue
            window = Window(x0-x, y0-y, x1-x0, y1-y0)
            data = src.read(1, window=window)
            mask = src.read_masks(1, window=window)
            dest = np.s_[y0:y1, x0:x1]
            overlap = covered[dest]
            equal = (values[dest] == data) | (np.isnan(values[dest]) & np.isnan(data))
            if np.any(overlap & (~equal | (masks[dest] != mask))):
                raise AcquisitionError("Conflicting overlapping tiles; no implicit priority")
            values[dest] = data
            masks[dest] = mask
            covered[dest] = True
        if not covered.all():
            raise AcquisitionError("Source rasters do not cover the snapped AOI; no fabricated fill")
        profile = {"driver": "GTiff", "count": 1, "dtype": first.dtypes[0],
                   "crs": first.crs, "transform": dst_transform, "width": width,
                   "height": height, "nodata": first.nodata, "compress": "deflate"}
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(output, "w", **profile) as dst:
                dst.write(values, 1)
                dst.write_mask(masks)
                dst.scales, dst.offsets = first.scales, first.offsets
                if first.units[0] is not None:
                    dst.set_band_unit(1, first.units[0])
        with rasterio.open(output) as dst:
            if (not np.array_equal(values, dst.read(1), equal_nan=True)
                    or not np.array_equal(masks, dst.read_masks(1))):
                raise AcquisitionError("Written samples or mask changed")
            metadata = raster_metadata(dst)
        return {"requested_bounds_3857": list(bounds), "operation": "native-grid aligned envelope crop; no resampling",
                "nodata_pixels": int((masks == 0).sum()), "raster": metadata,
                "sources": [raster_metadata(src) for src in sources]}


def acquire(study_area, raw_dir, work_dir, *, index=None, tiles_dir=None,
            max_tile_bytes=1024**3, max_pixels=16_000_000):
    """New directories only. Keep partial acquisition and failure evidence."""
    raw_dir, work_dir = Path(raw_dir), Path(work_dir)
    raw, work = raw_dir.resolve(), work_dir.resolve()
    if raw == work or raw in work.parents or work in raw.parents:
        raise AcquisitionError("Raw and Work directories must be separate")
    if raw_dir.exists() or work_dir.exists():
        raise AcquisitionError("Use new Raw and Work directories; no overwrite/resume")
    area = load_study_area(study_area)
    raw_dir.mkdir(parents=True)
    work_dir.mkdir(parents=True)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    record = {"schema": "ouem-chmv2-acquisition-poc/v0.1", "status": "RUNNING",
              "started_at": utc_now(), "code_revision": revision,
              "implementation": file_record(__file__),
              "environment": {"python": platform.python_version(), "rasterio": rasterio.__version__,
                              "gdal": rasterio.__gdal_version__, "numpy": np.__version__},
              "source": {"registry": REGISTRY, "prefix": BASE_URL,
                         "provider_release": "dinov3_global_chm_v2_ml3",
                         "imagery_dates": None, "model_weights_revision": None},
              "scope": "Acquisition/crop PoC only; no Native/Standard or canopy acceptance",
              "aoi": {"id": area.id, "crs": f"EPSG:{area.epsg}", "extent": list(area.extent),
                      "config": file_record(study_area)}, "tiles": [],
              "parameters": {"max_tile_bytes": max_tile_bytes, "max_pixels": max_pixels}}
    try:
        target = raw_dir / "tiles.geojson"
        url = BASE_URL + "/tiles.geojson"
        record["request_in_progress"] = url
        record["index"] = (retain_local(index, target, url) if index else download(url, target, 128*1024**2))
        keys = select_tiles(json.loads(target.read_bytes()), area)
        record["selected_quadkeys"] = keys
        for key in keys:
            path, url = raw_dir / f"{key}.tif", BASE_URL + f"/chm/{key}.tif"
            record["request_in_progress"] = url
            receipt = (retain_local(Path(tiles_dir)/f"{key}.tif", path, url)
                       if tiles_dir else download(url, path, max_tile_bytes))
            record["tiles"].append({"quadkey": key, **receipt})
        output = work_dir / "chmv2_aoi.tif"
        result = mosaic_crop([tile["path"] for tile in record["tiles"]], area, output, max_pixels=max_pixels)
        for tile, metadata in zip(record["tiles"], result.pop("sources")):
            tile["raster"] = metadata
        record["output"] = {**file_record(output), **result}
        record.pop("request_in_progress", None)
        record["status"] = "COMPLETED"
    except Exception as exc:
        record.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        record["finished_at"] = utc_now()
        (work_dir / "acquisition-record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-area", required=True)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--index", help="Existing GeoJSON, copied locally; no remote index download")
    parser.add_argument("--tiles-dir", help="Existing selected COGs for offline replay")
    parser.add_argument("--max-tile-bytes", type=int, default=1024**3)
    parser.add_argument("--max-pixels", type=int, default=16_000_000)
    args = parser.parse_args(argv)
    if args.max_tile_bytes <= 0 or args.max_pixels <= 0:
        parser.error("Limits must be positive")
    try:
        record = acquire(**vars(args))
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1
    print(json.dumps({"status": record["status"], "tiles": record["selected_quadkeys"],
                      "output": record["output"]["path"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
