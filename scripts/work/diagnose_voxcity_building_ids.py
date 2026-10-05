"""Diagnostic-only inventory of Komae VoxCity ``building_id_grid`` IDs.

Run from the repository root in the pinned OUEM environment:

    python scripts/work/diagnose_voxcity_building_ids.py

This script does not write artifacts or change production adapter semantics.
The height value of 1.0 m is used only to bootstrap VoxCity rasterization.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ouem.adapters.voxcity import (
    VOXCITY_VERSION,
    _set_normalized_footprints,
    _to_voxcity_building_crs,
    build_normalized_footprint,
    numeric_id_mapping,
)

DEFAULT_BUILDINGS = "data/standard/building/komae.gpkg"
DEFAULT_TERRAIN = "data/standard/terrain/komae_09LD3451.tif"
MESHSIZE = 1.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory IDs in the pinned VoxCity Komae building grid"
    )
    parser.add_argument("--buildings", default=DEFAULT_BUILDINGS)
    parser.add_argument("--terrain", default=DEFAULT_TERRAIN)
    args = parser.parse_args()

    import geopandas as gpd
    import numpy as np
    import voxcity
    from voxcity.geoprocessor.raster import (
        create_building_height_grid_from_gdf_polygon,
        create_dem_grid_from_geotiff_polygon,
    )

    if getattr(voxcity, "__version__", None) != VOXCITY_VERSION:
        raise RuntimeError(f"VoxCity {VOXCITY_VERSION} is required")
    building_path = Path(args.buildings)
    terrain_path = Path(args.terrain)
    buildings = gpd.read_file(building_path, layer="building")
    if buildings.crs is None or buildings.crs.to_epsg() != 6677:
        raise RuntimeError(f"expected EPSG:6677 Standard Building, found {buildings.crs}")
    mapping = numeric_id_mapping(buildings.ouem_id.tolist())
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
    buildings = _to_voxcity_building_crs(buildings)

    xmin, ymin, xmax, ymax = buildings.total_bounds
    rectangle = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]
    dem_grid = create_dem_grid_from_geotiff_polygon(
        str(terrain_path), MESHSIZE, rectangle, dem_interpolation=False
    )
    _, _, building_id_grid, _ = create_building_height_grid_from_gdf_polygon(
        buildings,
        meshsize=MESHSIZE,
        rectangle_vertices=rectangle,
        overlapping_footprint=False,
    )

    expected_ids = set(range(1, len(buildings) + 1))
    positive = building_id_grid[building_id_grid > 0]
    present_ids = {int(value) for value in np.unique(positive)}
    missing_ids = expected_ids - present_ids
    unexpected_ids = present_ids - expected_ids

    print(f"expected_count: {len(expected_ids)}")
    print(f"present_count: {len(present_ids)}")
    print(f"missing_count: {len(missing_ids)}")
    print(f"unexpected_count: {len(unexpected_ids)}")
    print(f"missing_ids: {sorted(missing_ids)}")
    print(f"unexpected_ids: {sorted(unexpected_ids)}")
    print(f"present_ids: {sorted(present_ids)}")
    print(f"building_id_grid shape: {tuple(building_id_grid.shape)}")
    print(f"DEM grid shape: {tuple(dem_grid.shape)}")

    print("Missing building diagnostics:")
    if not missing_ids:
        print("  (none)")
    for missing_id in sorted(missing_ids):
        row = buildings.loc[buildings.voxcity_id == missing_id].iloc[0]
        # Report the normalized footprint in the Standard source CRS so area is
        # in square metres rather than geographic degrees squared.
        geometry = footprints[row.ouem_id][0]
        print(
            f"  voxcity_id={missing_id} ouem_id={row.ouem_id} "
            f"area={float(geometry.area):.12g} "
            f"bounds={tuple(float(value) for value in geometry.bounds)} "
            f"geom_type={geometry.geom_type}"
        )

    ids, counts = np.unique(positive, return_counts=True)
    cell_counts = sorted(
        ((int(building_id), int(count)) for building_id, count in zip(ids, counts)),
        key=lambda item: (item[1], item[0]),
    )
    print("Present building rasterized cell counts (ascending):")
    if not cell_counts:
        print("  (none)")
    for building_id, count in cell_counts:
        print(f"  id={building_id} cells={count}")


if __name__ == "__main__":
    main()
