"""Komae A3 acceptance through pinned VoxCity's actual Voxelizer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PIN = "fa212656305328a9a657973bae26f352bfe813bc"


def json_safe(value):
    """Recursively convert NumPy-like scalar values to JSON built-in types."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        return json_safe(value.item())
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"acceptance report contains unsupported value: {type(value).__name__}")


def digest(array):
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("standard_building")
    parser.add_argument("standard_terrain")
    parser.add_argument("--adapter-output", required=True)
    parser.add_argument("--meshsize", type=float, required=True)
    parser.add_argument("--expected", type=int, default=111)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    import geopandas as gpd
    import numpy as np
    import voxcity
    from ouem.adapters.voxcity import (
        VOXCITY_PRECISE_RASTERIZATION,
        adapt_standard_to_voxcity,
    )
    from voxcity.generator import Voxelizer
    from voxcity.geoprocessor.raster import (
        create_building_height_grid_from_gdf_polygon,
        create_dem_grid_from_geotiff_polygon,
        process_grid,
    )

    if getattr(voxcity, "__version__", None) != "1.7.0":
        raise RuntimeError("VoxCity 1.7.0 is required")
    result = adapt_standard_to_voxcity(
        args.standard_building, args.standard_terrain, args.adapter_output,
        meshsize=args.meshsize,
    )
    first_geojson_hash = hashlib.sha256(Path(result.output).read_bytes()).hexdigest()
    first_manifest_hash = hashlib.sha256(Path(result.manifest).read_bytes()).hexdigest()
    rerun = adapt_standard_to_voxcity(
        args.standard_building, args.standard_terrain, args.adapter_output,
        meshsize=args.meshsize,
    )
    adapter_deterministic = (
        first_geojson_hash == hashlib.sha256(Path(rerun.output).read_bytes()).hexdigest()
        and first_manifest_hash == hashlib.sha256(Path(rerun.manifest).read_bytes()).hexdigest()
    )
    gdf = gpd.read_file(result.output)
    manifest = json.loads(Path(result.manifest).read_text(encoding="utf-8"))
    if len(gdf) != args.expected:
        raise RuntimeError(f"expected {args.expected} buildings, got {len(gdf)}")
    if not (gdf.id == gdf.voxcity_id).all():
        raise RuntimeError("VoxCity id does not match voxcity_id")
    rectangle = manifest["voxcity_grid"]["rectangle_vertices_lonlat"]

    def once():
        dem = create_dem_grid_from_geotiff_polygon(
            args.standard_terrain, args.meshsize, rectangle, dem_interpolation=False
        )
        heights, min_heights, ids, _ = create_building_height_grid_from_gdf_polygon(
            gdf, args.meshsize, rectangle,
            overlapping_footprint=VOXCITY_PRECISE_RASTERIZATION,
        )
        land_cover = np.ones(dem.shape, dtype=int)  # minimal valid bareland
        trees = np.zeros(dem.shape, dtype=float)    # no A3 vegetation
        voxels = Voxelizer(args.meshsize, "Standard").generate_combined(
            heights, min_heights, ids, land_cover, dem, trees,
            canopy_bottom_height_grid_ori=trees,
        )
        return dem, heights, ids, voxels

    dem, heights, ids, voxels = once()
    dem2, heights2, ids2, voxels2 = once()
    present = {int(value) for value in ids.flat if int(value) > 0}
    expected = set(map(int, gdf.voxcity_id))
    flattened = process_grid(ids, dem.copy())
    dem_min = float(np.min(dem))
    building_code = -3
    tolerance = 2.0 * args.meshsize
    vertical_diagnostics = []
    for row in gdf.itertuples():
        mask = ids == row.id
        raw_ground = float(np.mean(dem[mask], dtype=np.float64))
        if abs(raw_ground + row.height - row.z_top_abs) > 1e-7:
            raise RuntimeError(f"absolute roof invariant failed for {row.ouem_id}")
        flat = flattened[mask]
        if not (np.allclose(flat, raw_ground) or np.allclose(flat + dem_min, raw_ground)):
            raise RuntimeError(f"process_grid ground mismatch for {row.ouem_id}")
        horizontal = np.argwhere(mask)
        ks = [k for i, j in horizontal for k in np.flatnonzero(voxels[i, j, :] == building_code)]
        if not ks:
            raise RuntimeError(f"no building voxel for {row.ouem_id}")
        voxel_roof_abs = float(dem_min + (max(ks) + 1) * args.meshsize)
        expected_top = float(row.z_top_abs)
        vertical_diagnostics.append({
            "ouem_id": str(row.ouem_id),
            "voxcity_id": int(row.voxcity_id),
            "expected_z_top_abs": expected_top,
            "voxel_roof_abs": voxel_roof_abs,
            "absolute_error": float(abs(voxel_roof_abs - expected_top)),
        })
    worst = max(vertical_diagnostics, key=lambda item: item["absolute_error"])
    max_vertical_error = float(worst["absolute_error"])
    tolerance = float(tolerance)
    report = json_safe({
        "voxcity_version": "1.7.0", "voxcity_commit": PIN,
        "input_buildings": int(len(gdf)), "building_id_grid_produced": bool(ids.size),
        "building_voxels_produced": bool(np.any(voxels == building_code)),
        "ids_present": sorted(present), "ids_expected": sorted(expected),
        "no_unexplained_loss": bool(present == expected),
        "max_absolute_roof_error_m": max_vertical_error,
        "vertical_tolerance_m": tolerance,
        "vertical_geometry_consistent": bool(max_vertical_error <= tolerance),
        "worst_offending_ouem_id": worst["ouem_id"],
        "worst_offending_voxcity_id": int(worst["voxcity_id"]),
        "worst_expected_z_top_abs": float(worst["expected_z_top_abs"]),
        "worst_voxel_roof_absolute_elevation": float(worst["voxel_roof_abs"]),
        "worst_absolute_error": max_vertical_error,
        "adapter_serialization_deterministic": bool(adapter_deterministic),
        "grid_and_voxel_deterministic": bool(all((
            digest(dem) == digest(dem2), digest(heights) == digest(heights2),
            digest(ids) == digest(ids2), digest(voxels) == digest(voxels2)))),
    })
    required = (report["building_voxels_produced"], report["no_unexplained_loss"],
                report["vertical_geometry_consistent"],
                report["adapter_serialization_deterministic"],
                report["grid_and_voxel_deterministic"])
    report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    if not all(required):
        raise RuntimeError("VoxCity acceptance failed: " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
