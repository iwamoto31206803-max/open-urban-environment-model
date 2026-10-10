"""Komae A3 acceptance through pinned VoxCity's actual Voxelizer."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"acceptance report contains unsupported value: {type(value).__name__}")


def digest(array):
    if array.dtype.hasobject:
        raise TypeError("object arrays require semantic segment serialization")
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def _cell_segments(min_height_value, height_value):
    """Return VoxCity ``(min_height, height)`` segments for one grid cell.

    Precise rasterization stores a list of segments in the min-height grid.
    Keep a scalar fallback for non-overlap cells so this diagnostic also works
    with the representation used by the fast path.
    """
    if hasattr(min_height_value, "tolist"):
        min_height_value = min_height_value.tolist()
    if isinstance(min_height_value, (list, tuple)):
        if not min_height_value:
            return []
        if all(isinstance(value, (list, tuple)) and len(value) == 2
               for value in min_height_value):
            return [(float(low), float(high)) for low, high in min_height_value]
        return [(float(value), float(height_value)) for value in min_height_value]
    if float(height_value) <= 0:
        return []
    return [(float(min_height_value), float(height_value))]


def _matching_segment_ids(gdf, segments, tolerance=1e-7):
    """Recover IDs whose adapter height matches a cell segment, when possible."""
    tops = [high for _, high in segments]
    return sorted({
        int(row.voxcity_id) for row in gdf.itertuples()
        if any(abs(float(row.height) - top) <= tolerance for top in tops)
    })


def _segment_grid_digest(min_heights, heights):
    """Hash the semantic segment content, not object-array pointer bytes."""
    serializable = [
        _cell_segments(min_heights[i, j], heights[i, j])
        for i in range(heights.shape[0]) for j in range(heights.shape[1])
    ]
    return hashlib.sha256(json.dumps(serializable, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def array_evidence(dem, heights, min_heights, ids, voxels):
    """Portable comparison metadata; never hash object-array memory addresses."""
    evidence = {
        name: {"dtype": array.dtype.str, "shape": list(array.shape),
               "encoding": "C-order bytes", "sha256": digest(array)}
        for name, array in (("dem", dem), ("heights", heights),
                            ("ids", ids), ("voxels", voxels))
    }
    evidence["segments"] = {
        "dtype": min_heights.dtype.str, "shape": list(min_heights.shape),
        "encoding": "row-major cell segment JSON", "sha256": _segment_grid_digest(min_heights, heights),
    }
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("standard_building")
    parser.add_argument("standard_terrain")
    parser.add_argument("--adapter-output", required=True)
    parser.add_argument("--meshsize", type=float, required=True)
    parser.add_argument("--expected", type=int, default=111)
    parser.add_argument("--report", required=True)
    parser.add_argument("--array-evidence", help="optional separate JSON with both executions' array fingerprints")
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
        return dem, heights, min_heights, ids, voxels

    dem, heights, min_heights, ids, voxels = once()
    dem2, heights2, min_heights2, ids2, voxels2 = once()
    if args.array_evidence:
        evidence_path = Path(args.array_evidence)
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps({
            "schema": "ouem-voxcity-array-evidence/v0.1",
            "first": array_evidence(dem, heights, min_heights, ids, voxels),
            "second": array_evidence(dem2, heights2, min_heights2, ids2, voxels2),
        }, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    present = {int(value) for value in ids.flat if int(value) > 0}
    expected = set(map(int, gdf.voxcity_id))
    flattened = process_grid(ids, dem.copy())
    dem_min = float(np.min(dem))
    first_mask = ids == next(iter(expected))
    first_raw_ground = float(np.mean(dem[first_mask], dtype=np.float64))
    flattened_is_normalized = bool(np.allclose(
        flattened[first_mask] + dem_min, first_raw_ground
    ))
    building_code = -3
    tolerance = 2.0 * args.meshsize
    building_invariant_errors = []
    legacy_diagnostics = []
    for row in gdf.itertuples():
        mask = ids == row.id
        raw_ground = float(np.mean(dem[mask], dtype=np.float64))
        building_invariant_errors.append(float(abs(
            raw_ground + float(row.height) - float(row.z_top_abs)
        )))
        flat = flattened[mask]
        building_invariant_errors.append(0.0 if (
            np.allclose(flat, raw_ground) or np.allclose(flat + dem_min, raw_ground)
        ) else float("inf"))
        row_segments = [
            segment
            for i, j in np.argwhere(mask)
            for segment in _cell_segments(min_heights[i, j], heights[i, j])
        ]
        if not any(abs(high - float(row.height)) <= 1e-7 for _, high in row_segments):
            building_invariant_errors.append(float("inf"))
        candidates = []
        for i, j in np.argwhere(mask):
            ks = np.flatnonzero(voxels[i, j, :] == building_code)
            if ks.size:
                candidates.append((int(ks[-1]), int(i), int(j)))
        if candidates:
            k, i, j = max(candidates)
            voxel_roof_abs = float(dem_min + (k + 1) * args.meshsize)
            legacy_diagnostics.append({
                "ouem_id": str(row.ouem_id),
                "voxcity_id": int(row.voxcity_id),
                "expected_z_top_abs": float(row.z_top_abs),
                "voxel_roof_abs": voxel_roof_abs,
                "absolute_error": float(abs(voxel_roof_abs - float(row.z_top_abs))),
                "i": i, "j": j,
            })

    # BUILDING_CODE deliberately carries no building identity.  Validate its
    # per-cell roof envelope against every segment emitted by the precise
    # rasterizer instead of attributing the tallest overlapping voxel to the
    # last-wins building_id_grid value.
    cell_diagnostics = []
    overlap_cell_count = 0
    for i, j in np.argwhere(ids > 0):
        segments = _cell_segments(min_heights[i, j], heights[i, j])
        if not segments:
            continue
        overlap_cell_count += int(len(segments) > 1)
        ks = np.flatnonzero(voxels[i, j, :] == building_code)
        actual_roof = float("nan") if not ks.size else float(
            dem_min + (int(ks[-1]) + 1) * args.meshsize
        )
        flat_ground = float(flattened[i, j])
        ground_abs = flat_ground + dem_min if flattened_is_normalized else flat_ground
        expected_roof = float(ground_abs + max(high for _, high in segments))
        contiguous = bool(ks.size and (ks.size == 1 or np.all(np.diff(ks) == 1)))
        error = (
            float(abs(actual_roof - expected_roof))
            if contiguous else float("inf")
        )
        cell_diagnostics.append({
            "i": int(i), "j": int(j), "last_wins_id": int(ids[i, j]),
            "segment_count": int(len(segments)),
            "segment_building_ids": _matching_segment_ids(gdf, segments),
            "expected_roof_abs": expected_roof,
            "voxel_roof_abs": actual_roof,
            "absolute_error": error,
            "building_occupancy_contiguous": contiguous,
        })
    worst = max(cell_diagnostics, key=lambda item: item["absolute_error"])
    max_vertical_error = float(worst["absolute_error"])
    tolerance = float(tolerance)
    legacy_worst = max(legacy_diagnostics, key=lambda item: item["absolute_error"])
    legacy_segments = _cell_segments(
        min_heights[legacy_worst["i"], legacy_worst["j"]],
        heights[legacy_worst["i"], legacy_worst["j"]],
    )
    legacy_segment_ids = _matching_segment_ids(gdf, legacy_segments)
    prior_contamination = bool(
        len(legacy_segments) > 1
        and any(value != legacy_worst["voxcity_id"] for value in legacy_segment_ids)
    )
    id_to_ouem = {
        int(row.voxcity_id): str(row.ouem_id) for row in gdf.itertuples()
    }
    report = json_safe({
        "voxcity_version": "1.7.0", "voxcity_commit": PIN,
        "input_buildings": int(len(gdf)), "building_id_grid_produced": bool(ids.size),
        "building_voxels_produced": bool(np.any(voxels == building_code)),
        "ids_present": sorted(present), "ids_expected": sorted(expected),
        "no_unexplained_loss": bool(present == expected),
        "max_absolute_roof_error_m": max_vertical_error,
        "vertical_tolerance_m": tolerance,
        "vertical_geometry_consistent": bool(
            max(building_invariant_errors) <= 1e-7 and max_vertical_error <= tolerance
        ),
        "worst_offending_ouem_id": id_to_ouem.get(int(worst["last_wins_id"])),
        "worst_offending_voxcity_id": int(worst["last_wins_id"]),
        "worst_expected_z_top_abs": float(worst["expected_roof_abs"]),
        "worst_voxel_roof_absolute_elevation": float(worst["voxel_roof_abs"]),
        "worst_absolute_error": max_vertical_error,
        "worst_cell_indices": [int(worst["i"]), int(worst["j"])],
        "worst_cell_overlap_segment_count": int(len(legacy_segments)),
        "worst_cell_overlapping_building_ids": legacy_segment_ids,
        "prior_per_building_worst_ouem_id": legacy_worst["ouem_id"],
        "prior_per_building_worst_voxcity_id": int(legacy_worst["voxcity_id"]),
        "prior_per_building_max_absolute_roof_error_m": float(
            legacy_worst["absolute_error"]
        ),
        "overlap_cell_count": int(overlap_cell_count),
        "prior_roof_failure_was_overlap_contamination": prior_contamination,
        "building_specific_absolute_invariant_max_error_m": float(
            max(building_invariant_errors)
        ),
        "adapter_serialization_deterministic": bool(adapter_deterministic),
        "grid_and_voxel_deterministic": bool(all((
            digest(dem) == digest(dem2), digest(heights) == digest(heights2),
            _segment_grid_digest(min_heights, heights)
            == _segment_grid_digest(min_heights2, heights2),
            digest(ids) == digest(ids2), digest(voxels) == digest(voxels2)))),
    })
    required = (report["building_voxels_produced"], report["no_unexplained_loss"],
                report["vertical_geometry_consistent"],
                report["adapter_serialization_deterministic"],
                report["grid_and_voxel_deterministic"])
    report_text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    if not all(required):
        raise RuntimeError(
            "VoxCity acceptance failed: "
            + json.dumps(report, sort_keys=True, allow_nan=False)
        )


if __name__ == "__main__":
    main()
