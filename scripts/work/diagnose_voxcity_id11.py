"""Diagnostic-only investigation of missing Komae VoxCity building ID 11.

Run from the repository root in the pinned OUEM environment:

    python scripts/work/diagnose_voxcity_id11.py

The script reads the frozen Standard artifacts but does not write or modify
them. It reproduces the A3 footprint, CRS, rectangle, mesh, and VoxCity API path.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from ouem.adapters.voxcity import (
    VOXCITY_VERSION,
    _set_normalized_footprints,
    _to_voxcity_building_crs,
    build_normalized_footprint,
    numeric_id_mapping,
)

TARGET_ID = 11
OVERLAP_THRESHOLD = 0.5
MESHSIZE = 1.0
DEFAULT_BUILDINGS = "data/standard/building/komae.gpkg"


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose missing Komae VoxCity ID 11")
    parser.add_argument("--buildings", default=DEFAULT_BUILDINGS)
    args = parser.parse_args()

    import geopandas as gpd
    import numpy as np
    import voxcity
    from voxcity.geoprocessor.overlap import process_building_footprints_by_overlap
    from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon

    if getattr(voxcity, "__version__", None) != VOXCITY_VERSION:
        raise RuntimeError(f"VoxCity {VOXCITY_VERSION} is required")
    buildings = gpd.read_file(Path(args.buildings), layer="building")
    if buildings.crs is None or buildings.crs.to_epsg() != 6677:
        raise RuntimeError(f"expected EPSG:6677 Standard Building, found {buildings.crs}")
    mapping = numeric_id_mapping(buildings.ouem_id.tolist())
    inverse = {voxcity_id: ouem_id for ouem_id, voxcity_id in mapping.items()}
    target_ouem_id = inverse.get(TARGET_ID)
    if target_ouem_id is None:
        raise RuntimeError(f"lexical ID {TARGET_ID} does not exist")

    buildings = buildings[["ouem_id", "geometry"]].copy()
    footprints = {
        row.ouem_id: build_normalized_footprint(row.geometry, row.ouem_id)
        for row in buildings.itertuples()
    }
    buildings = _set_normalized_footprints(buildings, footprints)
    buildings["voxcity_id"] = buildings.ouem_id.map(mapping)
    buildings["id"] = buildings.voxcity_id
    buildings["min_height"] = 0.0
    buildings["height"] = 1.0

    target_source = buildings.loc[buildings.voxcity_id == TARGET_ID]
    if len(target_source) != 1:
        raise RuntimeError(f"target ID {TARGET_ID} is missing or duplicated")
    target_geometry = target_source.iloc[0].geometry
    target_area = float(target_geometry.area)

    overlaps = []
    for other in buildings.loc[buildings.voxcity_id != TARGET_ID].itertuples():
        intersection = target_geometry.intersection(other.geometry)
        area = float(intersection.area)
        if intersection.is_empty or not math.isfinite(area) or area <= 0:
            continue
        other_area = float(other.geometry.area)
        overlaps.append({
            "id": int(other.voxcity_id),
            "ouem_id": other.ouem_id,
            "area": area,
            "ratio_target": area / target_area,
            "ratio_other": area / other_area,
        })
    overlaps.sort(key=lambda item: (-item["ratio_target"], -item["area"], item["id"]))

    policy_input = buildings.copy()
    returned = process_building_footprints_by_overlap(
        policy_input, overlap_threshold=OVERLAP_THRESHOLD
    )
    policy_result = policy_input if returned is None else returned
    policy_target = policy_result.loc[policy_result.ouem_id == target_ouem_id]
    if len(policy_target) != 1:
        raise RuntimeError("ID 11 missing or duplicated after VoxCity overlap processing")
    policy_id_after = int(policy_target.iloc[0].id)

    voxcity_buildings = _to_voxcity_building_crs(buildings)
    xmin, ymin, xmax, ymax = voxcity_buildings.total_bounds
    rectangle = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]

    def rasterize(gdf, *, precise):
        return create_building_height_grid_from_gdf_polygon(
            gdf,
            meshsize=MESHSIZE,
            rectangle_vertices=rectangle,
            overlapping_footprint=precise,
        )[2]

    target_only = voxcity_buildings.loc[voxcity_buildings.id == TARGET_ID].copy()
    fast_single_grid = rasterize(target_only, precise=False)
    precise_single_grid = rasterize(target_only, precise=True)
    fast_all_grid = rasterize(voxcity_buildings, precise=False)
    precise_all_grid = rasterize(voxcity_buildings, precise=True)
    fast_single_mask = fast_single_grid == TARGET_ID
    fast_single_count = int(np.count_nonzero(fast_single_mask))
    precise_single_count = int(np.count_nonzero(precise_single_grid == TARGET_ID))
    fast_all_count = int(np.count_nonzero(fast_all_grid == TARGET_ID))
    precise_all_count = int(np.count_nonzero(precise_all_grid == TARGET_ID))
    occupying_values, occupying_counts = np.unique(
        fast_all_grid[fast_single_mask], return_counts=True
    )
    occupiers = sorted(
        ((int(value), int(count)) for value, count in zip(occupying_values, occupying_counts)),
        key=lambda item: (-item[1], item[0]),
    )

    print("ID 11 diagnostics")
    print(f"ouem_id: {target_ouem_id}")
    print(f"area: {target_area:.12g}")
    print(f"bounds: {tuple(float(value) for value in target_geometry.bounds)}")
    print(f"geom_type: {target_geometry.geom_type}")
    print(f"valid: {target_geometry.is_valid}")
    print(f"CRS used by VoxCity: {voxcity_buildings.crs}")
    print(f"rectangle: {rectangle}")
    print(f"meshsize: {MESHSIZE}")
    print(f"overlap threshold: {OVERLAP_THRESHOLD:.1%}")
    print("overlaps:")
    if not overlaps:
        print("  (no positive-area overlaps)")
    for overlap in overlaps:
        print(
            f"  other_id={overlap['id']} other_ouem_id={overlap['ouem_id']} "
            f"intersection_area={overlap['area']:.12g} "
            f"ratio_to_id11={overlap['ratio_target']:.9%} "
            f"ratio_to_other={overlap['ratio_other']:.9%} "
            f"exceeds_50_percent={overlap['ratio_target'] > OVERLAP_THRESHOLD}"
        )
    print(f"overlap policy id_before: {TARGET_ID}")
    print(f"overlap policy id_after: {policy_id_after}")
    print(f"overlap policy changed ID 11: {policy_id_after != TARGET_ID}")
    print(f"fast_single_cell_count: {fast_single_count}")
    print(f"precise_single_cell_count: {precise_single_count}")
    print(f"fast_all_cell_count: {fast_all_count}")
    print(f"precise_all_cell_count: {precise_all_count}")
    print(f"precise mode ID 11 cell count: {precise_all_count}")
    print("occupying IDs on ID11 footprint cells:")
    if not occupiers:
        print("  (fast single-building rasterization produced no target cells)")
    for occupying_id, count in occupiers:
        label = "background" if occupying_id == 0 else inverse.get(occupying_id, "unexpected")
        print(f"  id={occupying_id} cells={count} ouem_id={label}")


if __name__ == "__main__":
    main()
