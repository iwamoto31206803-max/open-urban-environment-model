"""Read-only diagnosis of Komae reference DEM coverage (no clipping or filling)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from ouem.adapters.voxcity import (
    build_normalized_footprint, _set_normalized_footprints, _to_voxcity_building_crs,
)

ROOT = Path(__file__).resolve().parents[2]
BUILDING = ROOT / "data/standard/building/komae.gpkg"
DEM = ROOT / "data/raw/terrain/tokyo_23ku_dem_05m/komae/09LD3451.tif"
STUDY = ROOT / "config/study_areas/komae_09LD3451.yaml"


def study_extent(path):
    """Read the four literal scalar extent values; reject missing/duplicate keys."""
    result = {}
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "extent:":
            inside = True
            continue
        if inside and line and not line[0].isspace():
            break
        if inside and ":" in line:
            key, val = line.strip().split(":", 1)
            if key in ("xmin", "ymin", "xmax", "ymax"):
                if key in result:
                    raise ValueError("duplicate study extent key " + key)
                result[key] = float(val.strip())
    if set(result) != {"xmin", "ymin", "xmax", "ymax"}:
        raise ValueError("incomplete study extent")
    return [result[k] for k in ("xmin", "ymin", "xmax", "ymax")]


def main():
    frame = gpd.read_file(BUILDING, layer="building")
    shapes = {r.ouem_id: build_normalized_footprint(r.geometry, r.ouem_id) for r in frame.itertuples()}
    normalized = _set_normalized_footprints(frame, shapes)
    lonlat = _to_voxcity_building_crs(normalized)
    xmin, ymin, xmax, ymax = map(float, lonlat.total_bounds)
    needed = transform_bounds("EPSG:4326", "EPSG:6677", xmin, ymin, xmax, ymax, densify_pts=101)
    with rasterio.open(DEM) as src:
        if src.crs is None or src.crs.to_epsg() != 6677 or src.count != 1:
            raise ValueError("expected single-band EPSG:6677 DEM")
        actual = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]
        window = from_bounds(*needed, transform=src.transform)
        pixel_window = [math.floor(window.col_off), math.floor(window.row_off),
                        math.ceil(window.col_off + window.width),
                        math.ceil(window.row_off + window.height)]
        deficits = {"west": max(0.0, actual[0]-needed[0]),
                    "south": max(0.0, actual[1]-needed[1]),
                    "east": max(0.0, needed[2]-actual[2]),
                    "north": max(0.0, needed[3]-actual[3])}
        report = {
            "scope": "READ_ONLY_DIAGNOSTIC_NOT_ACCEPTANCE",
            "building_count": len(frame),
            "study_area_epsg6677": study_extent(STUDY),
            "reference_building_lonlat_rectangle": [xmin, ymin, xmax, ymax],
            "required_dem_envelope_epsg6677_m": list(needed),
            "actual_dem_bounds_epsg6677_m": actual,
            "shortfall_m_by_direction": deficits,
            "dem_resolution_m": list(src.res),
            "dem_dimensions": [src.width, src.height],
            "required_pixel_window_left_top_right_bottom": pixel_window,
            "raster_pixel_extent": [0, 0, src.width, src.height],
            "coverage_within_raster_bounds": all(v == 0 for v in deficits.values()),
            "note": "This diagnoses raster extent only; NoData, actual engine output and formal acceptance remain unchecked.",
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
