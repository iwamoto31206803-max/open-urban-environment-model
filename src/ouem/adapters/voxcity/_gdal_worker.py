"""Pinned-VoxCity worker run by the captured geospatial Python runtime.

Despite the historical filename this worker deliberately calls VoxCity's own
rasterizers.  This avoids maintaining an OUEM approximation of its grid rules.
"""
import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import voxcity
from shapely.ops import transform
from voxcity.geoprocessor.raster import (
    create_building_height_grid_from_gdf_polygon,
    create_dem_grid_from_geotiff_polygon,
    process_grid,
)

PINNED_VERSION = "1.7.0"


def _z_values(geometry):
    if hasattr(geometry, "geoms"):
        return [z for part in geometry.geoms for z in _z_values(part)]
    if hasattr(geometry, "exterior"):
        rings = [geometry.exterior, *geometry.interiors]
        return [coordinate[2] for ring in rings for coordinate in ring.coords if len(coordinate) >= 3]
    return [coordinate[2] for coordinate in geometry.coords if len(coordinate) >= 3]


def _footprint(geometry):
    return transform(lambda x, y, z=None: (x, y), geometry)


def _rectangle_lonlat(gdf):
    xmin, ymin, xmax, ymax = gdf.to_crs(4326).total_bounds
    return [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]


def _rasterize(gdf, meshsize, rectangle):
    return create_building_height_grid_from_gdf_polygon(
        gdf, meshsize, rectangle, overlapping_footprint=False
    )[:3]


def run(job):
    if getattr(voxcity, "__version__", None) != PINNED_VERSION:
        raise RuntimeError(f"VoxCity {PINNED_VERSION} is required")
    buildings = gpd.read_file(job["buildings"], layer="building")
    if buildings.crs is None or buildings.crs.to_epsg() != 6677:
        raise RuntimeError("Standard Building must be EPSG:6677")
    if buildings.empty or buildings.ouem_id.isna().any() or not buildings.ouem_id.is_unique:
        raise RuntimeError("Standard Building requires non-empty, unique ouem_id")
    buildings = buildings[["ouem_id", "geometry"]].copy()
    z_by_ouem = {row.ouem_id: _z_values(row.geometry) for row in buildings.itertuples()}
    if any(not values or not all(math.isfinite(z) for z in values) for values in z_by_ouem.values()):
        raise RuntimeError("Standard Building contains missing or non-finite Z")
    buildings.geometry = buildings.geometry.map(_footprint)
    mapping = {value: index for index, value in enumerate(sorted(buildings.ouem_id), 1)}
    buildings["voxcity_id"] = buildings.ouem_id.map(mapping)
    buildings["id"] = buildings.voxcity_id
    buildings["min_height"] = 0.0
    buildings["height"] = 1.0  # bootstrap only; replaced from the grid-derived ground
    rectangle = _rectangle_lonlat(buildings)
    dem = create_dem_grid_from_geotiff_polygon(
        job["terrain"], job["meshsize"], rectangle, dem_interpolation=False
    )
    if not np.isfinite(dem).all():
        raise RuntimeError("VoxCity DEM grid contains non-finite values")

    previous_ids = None
    for _ in range(8):
        _, _, building_ids = _rasterize(buildings, job["meshsize"], rectangle)
        records = []
        for row in buildings.itertuples():
            samples = dem[building_ids == row.id]
            if not samples.size:
                raise RuntimeError(f"no VoxCity grid cell assigned to building {row.ouem_id}")
            ground = float(np.mean(samples, dtype=np.float64))
            top, bottom = max(z_by_ouem[row.ouem_id]), min(z_by_ouem[row.ouem_id])
            height = top - ground
            if not math.isfinite(height) or height <= 0:
                raise RuntimeError(f"non-positive derived height for building {row.ouem_id}")
            records.append({"ouem_id": row.ouem_id, "voxcity_id": row.id,
                "z_top_abs": top, "z_bottom_geom_abs": bottom,
                "ground_eff_abs": ground, "height": height, "min_height": 0.0,
                "ground_sample_count": int(samples.size),
                "ground_sample_min_abs": float(samples.min()),
                "ground_sample_max_abs": float(samples.max())})
        heights = {record["ouem_id"]: record["height"] for record in records}
        buildings["height"] = buildings.ouem_id.map(heights)
        if previous_ids is not None and np.array_equal(previous_ids, building_ids):
            break
        previous_ids = building_ids.copy()
    else:
        raise RuntimeError("VoxCity building-grid assignment did not converge")

    # Regression guard for the reviewed process_grid contract.  Its global
    # normalization is removed before comparing its per-building flattened DEM.
    flattened = process_grid(building_ids, dem.copy())
    shift = float(np.min(dem))
    for record in records:
        actual = flattened[building_ids == record["voxcity_id"]]
        if actual.size and np.allclose(actual + shift, record["ground_eff_abs"], atol=1e-9):
            continue
        # Some pinned builds return absolute rather than normalized values.
        if not actual.size or not np.allclose(actual, record["ground_eff_abs"], atol=1e-9):
            raise RuntimeError("A3 ground disagrees with VoxCity process_grid")

    features = json.loads(buildings.to_json(drop_id=True))["features"]
    extent = list(map(float, buildings.total_bounds))
    return {"records": records,
        "geojson": {"type": "FeatureCollection", "name": "voxcity_buildings",
                    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6677"}},
                    "features": features},
        "aoi": job.get("aoi") or extent, "rectangle_vertices_lonlat": rectangle,
        "grid_shape": list(dem.shape), "warnings": []}


try:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[2]).write_text(json.dumps(run(job)), encoding="utf-8")
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1)
