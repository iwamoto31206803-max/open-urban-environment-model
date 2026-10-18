"""Isolated Meta CHM to Komae VoxCity-grid conversion and scenario checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod, Transformer
from rasterio.windows import Window


class CanopyBlocked(ValueError):
    """An input prerequisite is not established; never send it to VoxCity."""

    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_provenance(chm, provenance):
    """Require a hash-bound, explicit source statement of ground-relative metres."""
    try:
        record = json.loads(Path(provenance).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CanopyBlocked(f"cannot read CHM provenance JSON: {exc}") from exc
    if not isinstance(record, dict):
        raise CanopyBlocked("CHM provenance JSON must be an object")
    if (record.get("schema") != "ouem-meta-chm-provenance/v0.1"
            or record.get("height_semantics") != "height_above_ground_m"
            or not isinstance(record.get("evidence"), dict)
            or not all(isinstance(record["evidence"].get(key), str)
                       and record["evidence"][key].strip()
                       for key in ("source", "citation", "height_statement"))
            or record.get("raster_sha256") != sha256(chm)):
        raise CanopyBlocked("CHM requires hash-matched provenance with an explicit cited height-above-ground metres statement")
    return {"raster_sha256": record["raster_sha256"],
            "provenance_sha256": sha256(provenance),
            "height_semantics": record["height_semantics"],
            "evidence": record["evidence"]}


def convert_chm(chm, provenance, rectangle, meshsize, dem, *, min_height=3.0):
    """Sample at VoxCity uv_m cell centres, blocking on every uncovered/invalid cell."""
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords

    evidence = validate_provenance(chm, provenance)
    if not np.isfinite(meshsize) or meshsize <= 0 or min_height < 0:
        raise CanopyBlocked("invalid mesh size or canopy threshold")
    if not np.isfinite(dem).all() or np.any(dem == -9999):
        raise CanopyBlocked("DEM contains NaN, infinity or Standard NoData sentinel")
    grid = compute_cell_center_coords(rectangle, meshsize)
    if grid is None or tuple(grid["grid_size"]) != tuple(dem.shape):
        raise CanopyBlocked("VoxCity grid geometry does not match existing DEM grid")
    with rasterio.open(chm) as src:
        if src.count != 1 or src.crs is None:
            raise CanopyBlocked("CHM needs one band and a valid declared CRS")
        transform = src.transform
        x_size = float(np.hypot(transform.a, transform.d))
        y_size = float(np.hypot(transform.b, transform.e))
        if not np.isfinite((x_size, y_size)).all() or min(x_size, y_size) <= 0 or abs(transform.determinant) < 1e-20:
            raise CanopyBlocked("CHM raster transform/pixel size is invalid")
        xy = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        x, y = xy.transform(grid["lons"], grid["lats"])
        back = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
        x0, y0 = float(x.flat[0]), float(y.flat[0])
        lon0, lat0 = back.transform(x0, y0)
        lon_u, lat_u = back.transform(x0 + transform.a, y0 + transform.d)
        lon_v, lat_v = back.transform(x0 + transform.b, y0 + transform.e)
        geod = Geod(ellps="WGS84")
        pixel_m = [float(geod.inv(lon0, lat0, lon_u, lat_u)[2]),
                   float(geod.inv(lon0, lat0, lon_v, lat_v)[2])]
        if not np.isfinite(pixel_m).all() or min(pixel_m) <= 0 or max(pixel_m) > 2.0:
            raise CanopyBlocked(f"CHM pixel size {pixel_m} m is incompatible with the 1 m PoC")
        inverse = ~transform
        cols_f = inverse.a * x + inverse.b * y + inverse.c
        rows_f = inverse.d * x + inverse.e * y + inverse.f
        finite_xy = np.isfinite(cols_f) & np.isfinite(rows_f)
        cols = np.floor(np.where(finite_xy, cols_f, -1)).astype(np.int64)
        rows = np.floor(np.where(finite_xy, rows_f, -1)).astype(np.int64)
        inside = finite_xy & (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        uncovered = int((~inside).sum())
        nodata = src.nodata
        nodata_record = ("NaN" if nodata is not None and np.isnan(nodata)
                         else nodata)
        details = {"crs": str(src.crs), "transform": list(transform)[:6],
                   "pixel_size_crs_units": [x_size, y_size],
                   "pixel_size_m_at_first_cell": pixel_m, "nodata": nodata_record,
                   "target_shape": list(dem.shape), "uncovered_cells": uncovered,
                   "resampling": "nearest at VoxCity uv_m cell centres",
                   "threshold_m": float(min_height), "bottom_ratio": 0.4,
                   "nodata_policy": "BLOCK", **evidence}
        values = np.zeros(dem.shape, dtype=np.float64)
        missing_mask = np.zeros(dem.shape, dtype=bool)
        if np.any(inside):
            r0, c0 = int(rows[inside].min()), int(cols[inside].min())
            block = src.read(1, window=Window(c0, r0, int(cols[inside].max()) - c0 + 1,
                                              int(rows[inside].max()) - r0 + 1), masked=True)
            sampled = block[rows[inside] - r0, cols[inside] - c0]
            values[inside] = np.asarray(sampled.data, dtype=np.float64)
            missing_mask[inside] = np.ma.getmaskarray(sampled)
        missing = int(missing_mask.sum())
        valid_mask = inside & ~missing_mask
        invalid = int((~np.isfinite(values) & valid_mask).sum())
        negative = int(((values < 0) & valid_mask).sum())
        details.update(nodata_cells=missing, nonfinite_cells=invalid, negative_cells=negative)
        if uncovered or missing or invalid or negative:
            raise CanopyBlocked(f"CHM target cells: uncovered={uncovered}, NoData={missing}, nonfinite={invalid}, negative={negative}; policy BLOCK", details)
        top = np.where(values >= min_height, values, 0.0)
        bottom = np.where(top > 0, 0.4 * top, 0.0)
        if not (np.isfinite(top).all() and np.isfinite(bottom).all()
                and np.all((bottom >= 0) & (bottom <= top))):
            raise CanopyBlocked("derived canopy arrays violate VoxCity numeric contract")
        details["active_cells"] = int(np.count_nonzero(top))
        if not details["active_cells"]:
            raise CanopyBlocked("CHM has no canopy cells at or above the 3 m PoC threshold", details)
        return top, bottom, details


def scenario_arrays(dem, heights, segments, ids, land_cover, baseline, top, bottom, meshsize, rectangle):
    """Use pinned update_voxcity without passing building_gdf or rerasterizing."""
    from voxcity.generator.update import update_voxcity
    from voxcity.models import (BuildingGrid, CanopyGrid, DemGrid, GridMetadata,
                                LandCoverGrid, VoxelGrid, VoxCity)
    from voxcity.generator.voxelizer import BUILDING_CODE, TREE_CODE

    if any(array.shape != dem.shape for array in (heights, segments, ids, land_cover, top, bottom)):
        raise CanopyBlocked("component-grid shapes differ")
    if not np.isfinite(dem).all() or np.any(dem == -9999):
        raise CanopyBlocked("DEM contains invalid cells")
    if not (np.isfinite(top).all() and np.isfinite(bottom).all()
            and np.all(top >= 0) and np.all(bottom >= 0) and np.all(bottom <= top)):
        raise CanopyBlocked("canopy top/bottom contain invalid heights")
    lons, lats = zip(*rectangle)
    meta = GridMetadata("EPSG:4326", (min(lons), min(lats), max(lons), max(lats)), meshsize)
    empty = np.zeros(dem.shape, dtype=np.float64)
    city = VoxCity(VoxelGrid(baseline, meta), BuildingGrid(heights, segments, ids, meta),
                   LandCoverGrid(land_cover, meta), DemGrid(dem, meta),
                   CanopyGrid(empty, meta, empty), {"land_cover_source": "Standard"})
    current = update_voxcity(city, canopy_top=top, canopy_bottom=bottom)
    no_canopy = update_voxcity(city, canopy_top=empty, canopy_bottom=empty)
    for scenario in (current, no_canopy):
        if (scenario.buildings.heights is not heights or scenario.buildings.ids is not ids
                or scenario.buildings.min_heights is not segments
                or scenario.dem.elevation is not dem or scenario.land_cover.classes is not land_cover):
            raise CanopyBlocked("component arrays were replaced")
    a, b = current.voxels.classes, no_canopy.voxels.classes
    common = min(a.shape[2], b.shape[2])
    buildings_preserved = (np.array_equal(a[:, :, :common] == BUILDING_CODE,
                                          b[:, :, :common] == BUILDING_CODE)
                           and not np.any(a[:, :, common:] == BUILDING_CODE)
                           and not np.any(b[:, :, common:] == BUILDING_CODE))
    if not np.array_equal(b, baseline) or not buildings_preserved:
        raise CanopyBlocked("baseline or building voxels changed")
    if np.any(b == TREE_CODE) or (np.any(top > 0) and not np.any(a == TREE_CODE)):
        raise CanopyBlocked("unexpected tree voxel occupancy")
    return a, b
