"""Temporary Komae diagnostic for VoxCity overlap-merging of building ID 37.

Run from the repository root in the pinned OUEM environment:

    python scripts/work/diagnose_voxcity_id37_overlap.py

An alternate Standard Building GeoPackage can be passed with ``--buildings``.
This script is diagnostic-only and does not write or modify any artifact.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from ouem.adapters.voxcity import (
    VOXCITY_VERSION,
    _set_normalized_footprints,
    build_normalized_footprint,
    numeric_id_mapping,
)

TARGET_ID = 37
TARGET_OUEM_ID = "oub-589ee7e2-c016-5b74-b199-af2e052e0ff1"
OVERLAP_THRESHOLD = 0.5


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose normalized-footprint overlaps for Komae VoxCity ID 37"
    )
    parser.add_argument(
        "--buildings",
        default="data/standard/building/komae.gpkg",
        help="accepted Standard Building v0.1 GeoPackage",
    )
    args = parser.parse_args()

    import geopandas as gpd
    import voxcity
    from voxcity.geoprocessor.overlap import process_building_footprints_by_overlap

    if getattr(voxcity, "__version__", None) != VOXCITY_VERSION:
        raise RuntimeError(f"VoxCity {VOXCITY_VERSION} is required")
    source = Path(args.buildings)
    buildings = gpd.read_file(source, layer="building")
    if buildings.crs is None or buildings.crs.to_epsg() != 6677:
        raise RuntimeError(f"expected EPSG:6677 Standard Building, found {buildings.crs}")
    mapping = numeric_id_mapping(buildings.ouem_id.tolist())
    inverse = {voxcity_id: ouem_id for ouem_id, voxcity_id in mapping.items()}
    if inverse.get(TARGET_ID) != TARGET_OUEM_ID:
        raise RuntimeError(
            f"lexical ID {TARGET_ID} maps to {inverse.get(TARGET_ID)!r}, "
            f"not expected {TARGET_OUEM_ID!r}"
        )
    buildings = buildings[["ouem_id", "geometry"]].copy()
    footprints = {
        row.ouem_id: build_normalized_footprint(row.geometry, row.ouem_id)
        for row in buildings.itertuples()
    }
    buildings = _set_normalized_footprints(buildings, footprints)
    buildings["voxcity_id"] = buildings.ouem_id.map(mapping)
    buildings["id"] = buildings.voxcity_id

    target = buildings.loc[buildings.voxcity_id == TARGET_ID].iloc[0]
    target_geometry = target.geometry
    target_area = float(target_geometry.area)
    print(f"VoxCity overlap threshold: {OVERLAP_THRESHOLD:.1%}")
    print(f"ID 37 ouem_id: {target.ouem_id}")
    print(f"geom_type: {target_geometry.geom_type}")
    print(f"valid: {target_geometry.is_valid}")
    print(f"bounds: {tuple(float(value) for value in target_geometry.bounds)}")
    print(f"ID 37 area: {target_area:.12g}")
    print("Overlaps:")

    overlaps = []
    for other in buildings.loc[buildings.voxcity_id != TARGET_ID].itertuples():
        intersection = target_geometry.intersection(other.geometry)
        area = float(intersection.area)
        if intersection.is_empty or not math.isfinite(area) or area <= 0:
            continue
        other_area = float(other.geometry.area)
        ratio_target = area / target_area
        ratio_other = area / other_area
        overlaps.append({
            "other_voxcity_id": int(other.voxcity_id),
            "other_ouem_id": other.ouem_id,
            "id37_area": target_area,
            "other_area": other_area,
            "intersection_area": area,
            "ratio_to_id37": ratio_target,
            "ratio_to_other": ratio_other,
            "exceeds_voxcity_threshold": ratio_target > OVERLAP_THRESHOLD,
        })
    overlaps.sort(
        key=lambda item: (-item["ratio_to_id37"], -item["intersection_area"],
                          item["other_voxcity_id"])
    )
    if not overlaps:
        print("  (no positive-area overlaps)")
    for overlap in overlaps:
        print(
            "  other_id={other_voxcity_id} other_ouem_id={other_ouem_id}\n"
            "    id37_area={id37_area:.12g} other_area={other_area:.12g}\n"
            "    overlap_area={intersection_area:.12g}\n"
            "    ratio_to_id37={ratio_to_id37:.9%}\n"
            "    ratio_to_other={ratio_to_other:.9%}\n"
            "    exceeds_voxcity_threshold={exceeds_voxcity_threshold}".format(**overlap)
        )

    # Reproduce the pinned upstream policy directly on a copy so the diagnostic
    # reports the actual ID rewrite in addition to the pairwise measurements.
    candidate = buildings.copy()
    returned = process_building_footprints_by_overlap(
        candidate, overlap_threshold=OVERLAP_THRESHOLD
    )
    processed = candidate if returned is None else returned
    processed_target = processed.loc[processed.ouem_id == TARGET_OUEM_ID]
    if len(processed_target) != 1:
        raise RuntimeError("target building missing or duplicated after VoxCity overlap processing")
    id_after = int(processed_target.iloc[0].id)
    print("VoxCity upstream overlap-policy result:")
    print(f"  id_before={TARGET_ID}")
    print(f"  id_after={id_after}")
    print(f"  merged_by_voxcity_overlap_policy={id_after != TARGET_ID}")


if __name__ == "__main__":
    main()
