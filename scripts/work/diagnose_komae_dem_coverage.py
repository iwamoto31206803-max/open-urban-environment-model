"""Read-only diagnosis of Komae reference DEM coverage (no clipping or filling)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import rasterio
from shapely.geometry import box
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from ouem.adapters.voxcity import (
    build_normalized_footprint, _set_normalized_footprints, _to_voxcity_building_crs,
)

ROOT = Path(__file__).resolve().parents[2]
BUILDING = ROOT / "data/standard/building/komae.gpkg"
TERRAIN_MANIFEST = ROOT / "data/native/terrain/komae_09LD3451.json"
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


def classify_study_intersections(frame, study_bounds):
    """Classify full normalized 2D building footprints without clipping them."""
    study = box(*study_bounds)
    groups = {"fully_within": [], "boundary_crossing": [], "touch_only": [], "outside": []}
    extremes = {direction: {"distance_m": 0.0, "ouem_ids": []}
                for direction in ("west", "south", "east", "north")}
    for row in frame.itertuples():
        geometry = row.geometry
        if geometry is None or geometry.is_empty:
            raise ValueError(f"Missing normalized footprint for {row.ouem_id}")
        if study.covers(geometry):
            category = "fully_within"
        elif not study.intersects(geometry):
            category = "outside"
        elif study.touches(geometry):
            category = "touch_only"
        else:
            category = "boundary_crossing"
        groups[category].append(str(row.ouem_id))
        x0, y0, x1, y1 = geometry.bounds
        distances = {"west": max(0.0, study_bounds[0] - x0),
                     "south": max(0.0, study_bounds[1] - y0),
                     "east": max(0.0, x1 - study_bounds[2]),
                     "north": max(0.0, y1 - study_bounds[3])}
        for direction, distance in distances.items():
            record = extremes[direction]
            if distance > record["distance_m"] + 1e-8:
                record["distance_m"] = float(distance)
                record["ouem_ids"] = [str(row.ouem_id)]
            elif distance > 0 and abs(distance - record["distance_m"]) <= 1e-8:
                record["ouem_ids"].append(str(row.ouem_id))
    for ids in groups.values():
        ids.sort()
    for record in extremes.values():
        record["ouem_ids"].sort()
    return {
        "classification_rule": "study.covers(full normalized 2D footprint); else disjoint, touches-only, or positive-area crossing",
        "counts": {key: len(value) for key, value in groups.items()},
        "ouem_ids_by_class": groups,
        "maximum_boundary_excursion_m": extremes,
        "selected_buildings_without_study_intersection": len(groups["outside"]),
        "note": "Intersection classification is spatial only; source selection provenance and shade contribution are not established.",
    }


def main():
    frame = gpd.read_file(BUILDING, layer="building")
    shapes = {r.ouem_id: build_normalized_footprint(r.geometry, r.ouem_id) for r in frame.itertuples()}
    normalized = _set_normalized_footprints(frame, shapes)
    lonlat = _to_voxcity_building_crs(normalized)
    building_bounds = list(map(float, normalized.total_bounds))
    study_bounds = study_extent(STUDY)
    if normalized.crs is None or normalized.crs.to_epsg() != 6677:
        raise ValueError(f"Expected normalized EPSG:6677 building CRS, got {normalized.crs}")
    boundary_diagnostic = classify_study_intersections(normalized, study_bounds)
    def outside(bounds, container):
        return {"west": max(0.0, container[0] - bounds[0]),
                "south": max(0.0, container[1] - bounds[1]),
                "east": max(0.0, bounds[2] - container[2]),
                "north": max(0.0, bounds[3] - container[3])}
    xmin, ymin, xmax, ymax = map(float, lonlat.total_bounds)
    needed = transform_bounds("EPSG:4326", "EPSG:6677", xmin, ymin, xmax, ymax, densify_pts=101)
    # Match the integration runner: resolve the actual RAW DEM from Native Terrain provenance.
    from ouem.komae_integration import read_json
    source_path = Path(read_json(TERRAIN_MANIFEST)["terrain"]["source_path"])
    if not source_path.is_absolute():
        raise ValueError(f"Native Terrain source_path must be absolute: {source_path}")
    with rasterio.open(source_path) as src:
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
            "study_boundary_building_classification": boundary_diagnostic,
            "terrain_manifest": str(TERRAIN_MANIFEST),
            "raw_dem_source_path": str(source_path),
            "study_area_epsg6677": study_bounds,
            "normalized_building_bounds_epsg6677_m": building_bounds,
            "normalized_buildings_outside_study_m": outside(building_bounds, study_bounds),
            "normalized_buildings_within_study": all(v == 0 for v in outside(building_bounds, study_bounds).values()),
            "conservative_rectangle_expansion_beyond_buildings_m": outside(needed, building_bounds),
            "required_rectangle_outside_study_m": outside(needed, study_bounds),
            "normalized_buildings_within_current_dem": all(v == 0 for v in outside(building_bounds, actual).values()),
            "reference_building_lonlat_rectangle": [xmin, ymin, xmax, ymax],
            "required_dem_envelope_epsg6677_m": list(needed),
            "actual_dem_bounds_epsg6677_m": actual,
            "shortfall_m_by_direction": deficits,
            "dem_resolution_m": list(src.res),
            "dem_dimensions": [src.width, src.height],
            "required_pixel_window_left_top_right_bottom": pixel_window,
            "raster_pixel_extent": [0, 0, src.width, src.height],
            "coverage_within_raster_bounds": all(v == 0 for v in deficits.values()),
            "note": "Compares building bounds, densified VoxCity rectangle, Study Area and DEM extent; does not determine whether engine rectangle policy should change. NoData, actual engine output and formal acceptance remain unchecked.",
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
