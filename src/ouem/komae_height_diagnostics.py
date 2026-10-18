"""Read-only, hash-bound diagnosis of saved Komae Adapter building heights."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem.adapters import voxcity as adapter
from ouem.komae_repair_qgis_export import _guard_output, _new_directory


RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def require(condition, message):
    if not condition:
        raise runner.Blocked(message)


def _summary(values):
    values = np.asarray(values)
    finite = values[np.isfinite(values)]
    return {"count": int(values.size), "finite_count": int(finite.size),
            "min": float(np.min(finite)) if finite.size else None,
            "median": float(np.median(finite)) if finite.size else None,
            "max": float(np.max(finite)) if finite.size else None,
            "zero_count": int(np.count_nonzero(finite == 0))}


def _raster(path):
    import rasterio
    with rasterio.open(path) as src:
        require(src.count == 1 and src.crs is not None, f"invalid DEM structure: {path}")
        values = src.read(1)
        mask = src.read_masks(1) == 0
        valid = values[~mask]
        info = {"path": str(path), "crs": str(src.crs), "shape": list(values.shape),
                "transform": list(src.transform)[:6], "nodata_value": src.nodata,
                "nodata_cells": int(np.count_nonzero(mask)),
                "valid_cells": int(valid.size), "nonfinite_valid_cells": int(np.count_nonzero(~np.isfinite(valid))),
                "valid": _summary(valid), "valid_below_minus_1000_cells":
                int(np.count_nonzero(valid < -1000))}
        return info, values, mask


def _pixel_mapping(path, rectangle, meshsize):
    """Replay pinned UTM nearest centres without a full-raster source KD-tree."""
    import rasterio
    from pyproj import CRS, Transformer
    from scipy.spatial import cKDTree
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords

    grid = compute_cell_center_coords(rectangle, meshsize)
    require(grid is not None, "invalid saved VoxCity rectangle")
    with rasterio.open(path) as src:
        require(src.crs is not None, "DEM lacks CRS")
        lons, lats = grid["lons"], grid["lats"]
        lon_mid, lat_mid = float(np.mean(lons)), float(np.mean(lats))
        zone = int((lon_mid + 180) // 6) + 1
        metric = CRS.from_epsg((32600 if lat_mid >= 0 else 32700) + zone)
        target_xy = Transformer.from_crs(4326, metric, always_xy=True).transform(lons, lats)
        targets = np.column_stack((target_xy[0].ravel(), target_xy[1].ravel()))
        source_to_metric = Transformer.from_crs(src.crs, metric, always_xy=True)
        x, y = Transformer.from_crs(4326, src.crs, always_xy=True).transform(lons, lats)
        # Rasterio rowcol implements the direct pixel containing each actual
        # VoxCity cell centre; the engine instead picks the nearest UTM centre.
        direct_rows, direct_cols = rasterio.transform.rowcol(src.transform, x.ravel(), y.ravel())
        direct_rows = np.asarray(direct_rows).reshape(lons.shape)
        direct_cols = np.asarray(direct_cols).reshape(lons.shape)
        # A clipped pixel-space envelope supplies an initial upper bound for
        # every target. Include a one-pixel margin for edge and rotated grids.
        low_row = max(0, min(src.height - 1, int(np.min(direct_rows)) - 1))
        high_row = max(0, min(src.height - 1, int(np.max(direct_rows)) + 1))
        low_col = max(0, min(src.width - 1, int(np.min(direct_cols)) - 1))
        high_col = max(0, min(src.width - 1, int(np.max(direct_cols)) + 1))
        window_rows = np.arange(low_row, high_row + 1)
        window_cols = np.arange(low_col, high_col + 1)
        initial = (window_rows[:, None] * src.width + window_cols).ravel()
        def metric_points(flat):
            px, py = rasterio.transform.xy(src.transform, flat // src.width, flat % src.width)
            mx, my = source_to_metric.transform(px, py)
            return np.column_stack((mx, my))

        initial_points = metric_points(initial)
        best_distance = cKDTree(initial_points).query(targets)[0]
        bound = float(np.max(best_distance))
        require(np.isfinite(bound), "nonfinite DEM-to-grid distance")
        # Any omitted pixel able to beat an initial neighbour must lie within
        # this bound of at least one target. Scan in chunks, retaining only
        # these pixels; the final tree keeps pinned raster row-major order.
        target_tree = cKDTree(targets)
        fringe = []
        for start in range(0, src.height * src.width, 65536):
            flat = np.arange(start, min(start + 65536, src.height * src.width))
            row, col = flat // src.width, flat % src.width
            omitted = ~((row >= low_row) & (row <= high_row) &
                        (col >= low_col) & (col <= high_col))
            flat = flat[omitted]
            if flat.size:
                distance = target_tree.query(metric_points(flat))[0]
                fringe.append(flat[distance <= np.nextafter(bound, np.inf)])
        candidates = np.sort(np.concatenate([initial, *fringe]))
        points = metric_points(candidates)
        distances, selections = cKDTree(points).query(targets, k=2)
        tie_fallback = bool(np.any(distances[:, 0] == distances[:, 1]))
        if tie_fallback:
            # cKDTree's exact-tie choice can depend on tree partitioning.
            # Recreate the pinned full tree only for this exceptional case.
            all_pixels = np.arange(src.height * src.width)
            nearest = cKDTree(metric_points(all_pixels)).query(targets)[1].reshape(lons.shape)
        else:
            nearest = candidates[selections[:, 0]].reshape(lons.shape)
        inside = (direct_rows >= 0) & (direct_rows < src.height) & (direct_cols >= 0) & (direct_cols < src.width)
        return {"grid_shape": list(lons.shape), "utm_epsg": metric.to_epsg(),
                "source_pixel_count": src.height * src.width,
                "candidate_pixel_count": int(candidates.size),
                "full_tree_tie_fallback": tie_fallback,
                "nearest_rows": nearest // src.width, "nearest_cols": nearest % src.width,
                "direct_rows": direct_rows, "direct_cols": direct_cols, "direct_inside": inside,
                "different_pixel": inside & ((nearest // src.width != direct_rows) |
                                             (nearest % src.width != direct_cols))}


def _source_pixels(path, rectangle, meshsize, *, mapping=None, values=None, mask=None):
    """Sample DEM values using the pinned nearest-pixel mapping."""
    if mapping is None:
        mapping = _pixel_mapping(path, rectangle, meshsize)
    if values is None or mask is None:
        _, values, mask = _raster(path)
    direct_rows, direct_cols = mapping["direct_rows"], mapping["direct_cols"]
    inside = mapping["direct_inside"]
    direct = np.full(direct_rows.shape, np.nan, dtype=np.float64)
    direct_nodata = np.ones(direct_rows.shape, dtype=bool)
    direct[inside] = values[direct_rows[inside], direct_cols[inside]]
    direct_nodata[inside] = mask[direct_rows[inside], direct_cols[inside]]
    return {**mapping,
                "nearest_values": values[mapping["nearest_rows"], mapping["nearest_cols"]],
                "nearest_nodata": mask[mapping["nearest_rows"], mapping["nearest_cols"]],
                "direct_values": direct, "direct_nodata": direct_nodata}


def _sample_summary(values, nodata):
    selected = np.asarray(values)
    missing = np.asarray(nodata) | ~np.isfinite(selected)
    return {"valid": _summary(selected[~missing]), "nodata_cells": int(np.count_nonzero(missing)),
            "nodata_fraction": float(np.mean(missing)),
            "zero_fraction": float(np.mean((selected == 0) & ~missing))}


def _classification(row):
    """Classify observed mechanisms; roof truth needs independent measurement."""
    if row["height"] < 39:
        return {"level": "UNRESOLVED", "reason": "below requested 39 m review threshold"}
    if not row["evidence_matches_saved_adapter"] or not row["engine_nearest_replay_matches"]:
        return {"level": "UNRESOLVED", "reason": "saved Adapter or pinned DEM replay differs"}
    if row["engine_zero_filled_nodata_cells"]:
        return {"level": "CONFIRMED", "reason": "pinned VoxCity replaced selected NoData (< -1000 m) by 0 m; ground and derived height include it"}
    if row["engine_zero_filled_valid_low_cells"]:
        return {"level": "CONFIRMED", "reason": "pinned VoxCity replaced selected valid elevations below -1000 m by 0 m"}
    if row["direct_outside_raster_cells"]:
        return {"level": "LIKELY", "reason": "VoxCity cell centres extend beyond DEM bounds; nearest source pixels require spatial review"}
    if row["engine_zero_cells"]:
        return {"level": "LIKELY", "reason": "selected 0 m terrain cells lower the sampled ground; source elevation/roof plausibility needs local review"}
    if row["engine_vs_direct_median_m"] is not None and abs(row["engine_vs_direct_median_m"]) > 1:
        return {"level": "LIKELY", "reason": "engine nearest-UTM selection differs materially from direct cell-centre elevations; inspect coordinates"}
    return {"level": "UNRESOLVED", "reason": "engine ground agrees with sampled terrain; independent roof-height evidence is needed"}


def _buildings(manifest, frame, ids, dem, pixels, raw_pixels, replay_ok):
    from ouem.adapters.voxcity import _z_values
    require(frame.crs is not None and frame.crs.to_epsg() == 6677 and
            len(frame) == len(manifest["buildings"]), "Standard Building/Adapter lineage differs")
    source = {str(row.ouem_id): row.geometry for row in frame.itertuples()}
    result = []
    for saved in manifest["buildings"]:
        ouem_id, number = str(saved["ouem_id"]), int(saved["voxcity_id"])
        require(ouem_id in source, f"missing Standard Building {ouem_id}")
        mask = ids == number
        require(np.any(mask), f"ID {number} has no VoxCity cells")
        samples = dem[mask]
        ground = math.fsum(float(v) for v in samples) / samples.size
        z_top = max(_z_values(source[ouem_id]))
        derived = z_top - ground
        fields = ("z_top_abs", "ground_eff_abs", "ground_sample_min_abs",
                  "ground_sample_max_abs", "height")
        actual = (z_top, ground, float(np.min(samples)), float(np.max(samples)), derived)
        field_matches = {key: math.isclose(float(saved[key]), value, rel_tol=0, abs_tol=1e-6)
                         for key, value in zip(fields, actual)}
        match = all(field_matches.values()) and int(saved["ground_sample_count"]) == samples.size
        nearest = pixels["nearest_values"][mask]
        nearest_missing = pixels["nearest_nodata"][mask]
        direct = pixels["direct_values"][mask]
        direct_missing = pixels["direct_nodata"][mask]
        raw_nearest = raw_pixels["nearest_values"][mask]
        raw_direct = raw_pixels["direct_values"][mask]
        index_examples = []
        indexes = np.argwhere(mask)
        order = sorted(range(len(indexes)), key=lambda n: (
            dem[tuple(indexes[n])] != 0,
            not pixels["different_pixel"][tuple(indexes[n])], n))
        for position in order[:5]:
            i, j = map(int, indexes[position])
            index_examples.append({"grid_ij": [i, j], "engine_dem_m": float(dem[i, j]),
                                   "nearest_source_row_col": [int(pixels["nearest_rows"][i, j]),
                                                              int(pixels["nearest_cols"][i, j])],
                                   "nearest_standard_m": float(pixels["nearest_values"][i, j]),
                                   "nearest_nodata": bool(pixels["nearest_nodata"][i, j]),
                                   "direct_source_row_col": [int(pixels["direct_rows"][i, j]),
                                                             int(pixels["direct_cols"][i, j])],
                                   "direct_inside": bool(pixels["direct_inside"][i, j])})
        row = {"ouem_id": ouem_id, "voxcity_id": number, "z_top_abs": z_top,
               "ground_eff_abs": ground, "ground_sample_min_abs": float(np.min(samples)),
               "ground_sample_max_abs": float(np.max(samples)), "ground_sample_count": int(samples.size),
               "height": derived, "engine_dem": _summary(samples),
               "raw_dem_nearest": _sample_summary(raw_nearest, raw_pixels["nearest_nodata"][mask]),
               "standard_dem_nearest": _sample_summary(nearest, nearest_missing),
               "raw_dem_direct": _sample_summary(raw_direct, raw_pixels["direct_nodata"][mask]),
               "standard_dem_direct": _sample_summary(direct, direct_missing),
               "engine_zero_cells": int(np.count_nonzero(samples == 0)),
               "engine_zero_fraction": float(np.mean(samples == 0)),
               "engine_zero_filled_nodata_cells": int(np.count_nonzero(
                   (samples == 0) & nearest_missing & (nearest < -1000))),
               "engine_zero_filled_valid_low_cells": int(np.count_nonzero(
                   (samples == 0) & ~nearest_missing & (nearest < -1000))),
               "direct_outside_raster_cells": int(np.count_nonzero(~pixels["direct_inside"][mask])),
               "nearest_vs_direct_pixel_mismatch_cells": int(np.count_nonzero(pixels["different_pixel"][mask])),
               "grid_to_source_pixel_examples": index_examples,
               "engine_vs_direct_median_m": (float(np.median(samples) - np.median(direct[~direct_missing]))
                                             if np.any(~direct_missing) else None),
               "saved_adapter_field_matches": field_matches,
               "evidence_matches_saved_adapter": bool(match),
               "engine_nearest_replay_matches": bool(replay_ok)}
        row["classification"] = _classification(row)
        result.append(row)
    return sorted(result, key=lambda row: row["voxcity_id"])


def diagnose_run(root):
    import geopandas as gpd
    from voxcity.geoprocessor.raster import (create_building_height_grid_from_gdf_polygon,
                                             create_dem_grid_from_geotiff_polygon)
    evidence = provenance.Evidence(root)
    provenance_record = runner.voxcity_provenance()
    require(provenance_record["verified"], "installed pinned VoxCity source is unverified")
    raw = evidence.input("raw_terrain")
    native_path = evidence.input("native_terrain")
    native = evidence.document(native_path)
    require(native.get("schema") == "ouem-native-terrain-manifest/v0.1" and
            Path(native["terrain"]["source_path"]).resolve() == raw.resolve(),
            "Native Terrain does not reference recorded RAW DEM")
    raw_info, raw_values, raw_mask = _raster(raw)
    require(raw_info["valid_cells"] == native["terrain"]["valid_cells"] and
            raw_info["nodata_cells"] == native["terrain"]["nodata_cells"],
            "RAW raster changed from Native Terrain registration")
    repeats = []
    mapping_cache = {}
    terrain_cache = {}
    for number in (1, 2):
        command = provenance.command(evidence.report, number, "a3")
        building = evidence.artifact(command[2])
        terrain = evidence.artifact(command[3])
        output = evidence.artifact(provenance.option(command, "--adapter-output"))
        arrays = evidence.document(evidence.artifact(provenance.option(command, "--array-evidence")))
        manifest = evidence.manifest(output)
        standard_manifest = evidence.manifest(terrain)
        require(manifest["voxcity"] == {"version": runner.VOXCITY_VERSION,
                                        "commit": runner.VOXCITY_COMMIT} and
                evidence.artifact(manifest["inputs"]["standard_building"]["path"]) == building and
                evidence.artifact(manifest["inputs"]["standard_terrain"]["path"]) == terrain and
                evidence.artifact(manifest["output"]["path"]) == output and
                manifest["inputs"]["standard_building"]["sha256"] == runner.sha256_file(building) and
                manifest["inputs"]["standard_terrain"]["sha256"] == runner.sha256_file(terrain) and
                manifest["output"]["sha256"] == runner.sha256_file(output) and
                standard_manifest["source"]["sha256"] == runner.sha256_file(raw),
                "saved Adapter or Standard Terrain lineage differs")
        terrain_hash = manifest["inputs"]["standard_terrain"]["sha256"]
        if terrain_hash not in terrain_cache:
            terrain_cache[terrain_hash] = _raster(terrain)
        std_info, std_values, std_mask = terrain_cache[terrain_hash]
        std_info = {**std_info, "path": str(terrain)}
        require(raw_values.shape == std_values.shape and raw_info["transform"] == std_info["transform"] and
                raw_info["crs"] == std_info["crs"] and np.array_equal(raw_mask, std_mask) and
                np.array_equal(raw_values[~raw_mask], std_values[~std_mask]),
                "RAW/Standard grids, masks or valid elevations differ")
        rectangle, mesh = manifest["voxcity_grid"]["rectangle_vertices_lonlat"], float(manifest["meshsize"])
        dem = create_dem_grid_from_geotiff_polygon(terrain, mesh, rectangle, dem_interpolation=False)
        dem_evidence = arrays["first"]["dem"]
        require(arrays["first"] == arrays["second"] and dem.dtype.str == dem_evidence["dtype"] and
                list(dem.shape) == dem_evidence["shape"] and
                hashlib.sha256(dem.tobytes(order="C")).hexdigest() == dem_evidence["sha256"],
                "replayed pinned DEM differs from saved A3 array evidence")
        frame = gpd.read_file(building, layer="building")
        adapter_frame = gpd.read_file(output)
        _, _, ids, _ = create_building_height_grid_from_gdf_polygon(
            adapter_frame, mesh, rectangle,
            overlapping_footprint=adapter.VOXCITY_PRECISE_RASTERIZATION)
        ids_evidence = arrays["first"]["ids"]
        require(ids.dtype.str == ids_evidence["dtype"] and list(ids.shape) == ids_evidence["shape"] and
                hashlib.sha256(ids.tobytes(order="C")).hexdigest() == ids_evidence["sha256"],
                "replayed building ID grid differs from saved A3 array evidence")
        mapping_key = runner.content_hash({"crs": std_info["crs"], "shape": std_info["shape"],
                                           "transform": std_info["transform"],
                                           "rectangle": rectangle, "mesh": mesh})
        if mapping_key not in mapping_cache:
            mapping_cache[mapping_key] = _pixel_mapping(terrain, rectangle, mesh)
        mapping = mapping_cache[mapping_key]
        pixels = _source_pixels(terrain, rectangle, mesh, mapping=mapping,
                                values=std_values, mask=std_mask)
        raw_pixels = _source_pixels(raw, rectangle, mesh, mapping=mapping,
                                    values=raw_values, mask=raw_mask)
        require(pixels["grid_shape"] == list(dem.shape) and
                np.array_equal(pixels["nearest_rows"], raw_pixels["nearest_rows"]) and
                np.array_equal(pixels["nearest_cols"], raw_pixels["nearest_cols"]),
                "RAW/Standard CRS or nearest-pixel mapping differs")
        predicted = np.where(std_values < -1000, 0, std_values)[
            pixels["nearest_rows"], pixels["nearest_cols"]]
        parity = bool(np.array_equal(predicted, dem))
        rows = _buildings(manifest, frame, ids, dem, pixels, raw_pixels, parity)
        repeats.append({"repeat": number, "standard_terrain": std_info,
                        "engine_dem": _summary(dem), "engine_zero_fraction": float(np.mean(dem == 0)),
                        "engine_nearest_replay_matches": parity,
                        "engine_zero_fill_selected_nodata_cells": int(np.count_nonzero(
                            pixels["nearest_nodata"] & (pixels["nearest_values"] < -1000))),
                        "direct_cell_centres_outside_raster": int(np.count_nonzero(~pixels["direct_inside"])),
                        "nearest_vs_direct_pixel_mismatch_cells": int(np.count_nonzero(pixels["different_pixel"])),
                        "engine_nearest_metric_crs": f"EPSG:{pixels['utm_epsg']}",
                        "nearest_source_candidates": pixels["candidate_pixel_count"],
                        "nearest_source_total_pixels": pixels["source_pixel_count"],
                        "nearest_full_tree_tie_fallback": pixels["full_tree_tie_fallback"],
                        "buildings": rows})
    require(runner.content_hash(repeats[0]["buildings"]) == runner.content_hash(repeats[1]["buildings"]),
            "repeat building-height diagnostics differ")
    evidence.finish()
    high = [row for row in repeats[0]["buildings"] if row["height"] >= 39]
    levels = {row["classification"]["level"] for row in high}
    overall = ("CONFIRMED" if levels == {"CONFIRMED"} else
               "LIKELY" if high and "UNRESOLVED" not in levels else "UNRESOLVED")
    report = {"schema": "ouem-komae-height-diagnosis/v0.1",
              "scope": "READ_ONLY_DIAGNOSIS_NOT_ACCEPTANCE", "run": str(root),
              "pinned_voxcity": provenance_record, "native_manifest": str(native_path),
              "dem_sampling": "pinned create_dem_grid_from_geotiff_polygon: source values < -1000 become 0; source and uv_m cell centres transform to local UTM; scipy.griddata nearest selects source pixel centre; no extrapolation guard",
              "source_file_sha256": {str(path): item["sha256"] for path, item in sorted(evidence.before.items())},
              "raw_terrain": raw_info, "native_terrain": {"registration": native["terrain"],
                                                  "actual_raw_statistics": raw_info},
              "repeats": repeats, "repeat_diagnostics_equal": True,
              "high_building_count": len(high), "overall_mechanism_classification": overall,
              "classification_scope": "CONFIRMED verifies a replayed processing mechanism only; it does not establish the final or sole cause of an anomalous building height.",
              "high_buildings": [{"ouem_id": row["ouem_id"], "voxcity_id": row["voxcity_id"],
                                  "height": row["height"], "classification": row["classification"]}
                                 for row in high],
              "limitations": ["No independent roof survey or terrain truth is available.",
                              "CONFIRMED does not establish the final or sole cause of anomalous building heights or whether source NoData is correct.",
                              "A saved-run replay alone cannot establish the final real-data cause; independent local roof and terrain evidence is required."]}
    return report, evidence


def _markdown(report):
    rows = report["high_buildings"]
    lines = ["# Komae building-height diagnosis", "", "Diagnostic only; no acceptance or input correction.", "",
             f"Run: `{report['run']}`", f"Buildings ≥39 m: {len(rows)}",
             f"Overall mechanism classification: {report['overall_mechanism_classification']}",
             report["classification_scope"], "",
             "| OUEM ID | VoxCity ID | Height (m) | Classification | Reason |",
             "| --- | ---: | ---: | --- | --- |"]
    for row in rows:
        item = row["classification"]
        lines.append(f"| {row['ouem_id']} | {row['voxcity_id']} | {row['height']:.3f} | "
                     f"{item['level']} | {item['reason']} |")
    lines += ["", "See diagnosis.json for RAW/Native/Standard/engine statistics, pixel mapping and all buildings.",
              "Compare roof Z against independent source evidence before treating an upstream roof as erroneous.", ""]
    return "\n".join(lines)


def export_run(root, output_base):
    root = Path(root).absolute()
    report, evidence = diagnose_run(root)
    directory, identity = _new_directory(output_base, root, root.name)
    for name, content in (("diagnosis.json", json.dumps(report, indent=2, ensure_ascii=False,
                                                        sort_keys=True, allow_nan=False) + "\n"),
                          ("summary.md", _markdown(report))):
        _guard_output(directory.parent, directory, identity)
        with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    evidence.finish()
    return directory, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="existing integration run ID")
    args = parser.parse_args(argv)
    if not RUN_ID.fullmatch(args.run_id) or args.run_id.upper() in RESERVED:
        parser.error("use one portable 1–64 character run ID")
    try:
        folder, report = export_run(runner.REPOSITORY / "data/work/integration" / args.run_id,
                                    runner.REPOSITORY / "data/work/dem-height-diagnostics")
    except (OSError, KeyError, TypeError, ValueError, runner.Blocked) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"Diagnosis: {folder / 'diagnosis.json'}")
    print(f"Summary: {folder / 'summary.md'}")
    print(f"Buildings >=39 m: {report['high_building_count']}; acceptance unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
