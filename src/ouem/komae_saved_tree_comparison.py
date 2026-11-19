"""Experimental same-grid comparison of Meta HAG and saved PR #99 TREE."""
import argparse
import json
from pathlib import Path

import numpy as np

from ouem import height_envelope as env
from ouem.canopy_height_candidate import effective_hag, map_envelope_fields, meta_presence_fields
from ouem.komae_saved_preflight import (
    BASE_REPORT_SHA, ENVELOPE_SHA, FINAL_REPORT_SHA, FrozenWatch, bind, child,
)
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_solar import integrate_common_canopy, sample_canopy


def summarize(mapped, canopy, current, no_canopy, roi):
    """Compare observed saved occupancy with source and numeric decisions."""
    shape = mapped["present"].shape
    require(current.ndim == 3 and current.shape[:2] == shape
            and current.shape == no_canopy.shape
            and roi.shape == shape and roi.dtype == np.dtype(bool),
            "comparison", "saved array shape or ROI dtype differs")
    tree = current == -2
    require(np.array_equal(np.where(tree, 0, current), no_canopy),
            "comparison", "saved non-TREE scenario differs")
    occupied = tree.any(axis=2)
    valid, candidate = canopy["valid"], canopy["candidate"]
    present_empty = mapped["present"] & ~occupied
    result = {}
    for name, area in (("scene", np.ones(shape, dtype=bool)), ("roi", roi)):
        def count(mask):
            return int(np.count_nonzero(area & mask))

        result[name] = {
            "cells": int(area.sum()),
            "source_support": count(mapped["source_support"]),
            "source_valid": count(mapped["assessed_domain"]),
            "z_valid": count(valid),
            "tree_candidate": count(candidate),
            "tree_columns": count(occupied),
            "tree_voxels": int(tree[area].sum()),
            "presence_vs_tree_columns": {
                label: {"occupied": count(mapped[label] & occupied),
                        "empty": count(mapped[label] & ~occupied)}
                for label in ("present", "absent", "unknown")
            },
            "present_without_tree": {
                "invalid_z": count(present_empty & ~valid),
                "valid_no_candidate": count(present_empty & valid & ~candidate),
                "candidate_unresolved": count(present_empty & candidate),
            },
        }
    return result


def compare_saved(root, report_locator, *, regenerate_tree=False):
    watch = FrozenWatch(root)
    report = watch.capture("final", report_locator, FINAL_REPORT_SHA, json_data=True)
    require(report["status"] == "COMPLETED", "report", "saved run must be complete")

    def input_file(key, *, parse=False):
        ref = report["input_artifacts"][key]
        return bind(watch, key, ref["path"], ref, parse=parse)

    def output_file(name, *, parse=False):
        return bind(watch, name, child(report_locator, name), report["outputs"][name], parse=parse)

    def array(path):
        return np.load(path, allow_pickle=False)

    envelope = input_file("envelope_manifest", parse=True)
    require(watch.identities["envelope_manifest"]["sha256"] == ENVELOPE_SHA,
            "envelope", "historical manifest identity differs")
    spec = envelope["grid_spec"]
    grid = env.GridSpec(tuple(spec["bounds"]), spec["resolution"], spec["epsg"])
    require((grid.width, grid.height) == (spec["width"], spec["height"])
            and list(grid.transform)[:6] == spec["transform"],
            "envelope", "grid identity differs")
    chm_path = input_file("envelope_input:chm")
    chm_ref = watch.identities["envelope_input:chm"]
    require(chm_ref["sha256"] == envelope["input_files"]["chm"]["sha256"],
            "envelope", "source CHM identity differs")
    chm = env.sample_raster(chm_path, grid)
    model = meta_presence_fields(chm, effective_hag(chm))

    x, y = (array(input_file("base_output:" + name)) for name in ("centre_x.npy", "centre_y.npy"))
    saved_grid = output_file("grid.json", parse=True)
    require(saved_grid["layout"] == "uv_m/SOUTH_UP" and saved_grid["shape"] == [128, 128, 27]
            and x.shape == y.shape == (128, 128),
            "engine", "unexpected saved lattice")
    mapped = map_envelope_fields(grid, model, x, y, centre_epsg=6677)
    paths = [input_file("canopy_output:" + name) for name in
             ("canopy_top_z.tif", "canopy_bottom_z.tif", "height_envelope_state.tif")]
    canopy = sample_canopy(paths, x, y)
    require(canopy["valid"].all(), "envelope", "saved baseline expects complete numeric coverage")

    current, no_canopy, roi = (array(output_file(name)) for name in
                              ("current_voxels.npy", "no_canopy_voxels.npy", "roi_mask.npy"))
    require(list(current.shape) == saved_grid["shape"] and np.count_nonzero(roi) == 4096,
            "engine", "voxel shape or ROI size differs")
    result = summarize(mapped, canopy, current, no_canopy, roi)
    regeneration = {}
    if regenerate_tree:
        previous = input_file("PR98_report", parse=True)
        require(watch.identities["PR98_report"]["sha256"] == BASE_REPORT_SHA
                and previous["status"] == "COMPLETED"
                and report["preflight"]["status"] == "PASS"
                and previous["model"]["grid"] == saved_grid
                and report["preflight"]["source_model_report_sha256"] == BASE_REPORT_SHA
                and envelope["input_files"]["terrain"]["sha256"]
                    == previous["input_artifacts"]["terrain"]["sha256"]
                and envelope["cr_model"]["parameters"]["cr"] == report["preflight"]["source_CR"] == .6,
                "binding", "saved model, grid or Envelope differs")
        for name in ("voxels.npy", "building_ids.npy", "building_heights.npy", "terrain_H.npy",
                     "effective_ground_H.npy", "effective_dem.npy", "ground_indices.npy",
                     "building_segments.json", "centre_x.npy", "centre_y.npy", "roi_mask.npy"):
            bound = report["input_artifacts"]["base_output:" + name]
            expected = previous["outputs"][name]
            require(bound["sha256"] == expected["sha256"] and bound["size_bytes"] == expected["size_bytes"],
                    "binding", "base output identity differs")
        base = array(input_file("base_output:voxels.npy"))
        require(np.array_equal(base, no_canopy)
                and np.array_equal(array(input_file("base_output:roi_mask.npy")), roi),
                "binding", "base voxels or ROI differ from saved control")
        ground = {name: array(input_file("base_output:" + name + ".npy"))
                  for name in ("building_ids", "building_heights", "terrain_H",
                               "effective_ground_H", "effective_dem", "ground_indices")}
        segments = input_file("base_output:building_segments.json", parse=True)
        engine = voxcity_provenance()
        recorded_engine = report["environment"]["voxcity"]
        require(engine["verified"] and all(engine[key] == recorded_engine[key] for key in
                ("version", "commit", "source_content_sha256")),
                "engine", "installed Voxelizer differs from recorded engine")
        regeneration = regenerate_and_compare(
            base, ground, segments, mapped, canopy, saved_grid["D0_effective_H_m"],
            previous["model"]["numba"], current, no_canopy, roi,
            provenance=f"PR #99 Envelope {ENVELOPE_SHA}")
        regeneration.update(engine={key: engine[key] for key in ("version", "commit")},
                            numba=previous["model"]["numba"],
                            base_report_sha256=BASE_REPORT_SHA, envelope_sha256=ENVELOPE_SHA)
    watch.unchanged()
    return {
        "report_sha256": FINAL_REPORT_SHA,
        "scope": "experimental_saved_tree_diagnostic",
        "saved_non_tree_control_equal": True,
        "candidate_without_tree_attribution": "UNRESOLVED",
        **result,
        **regeneration,
    }


def regenerate_and_compare(base, ground, segment_record, mapped, canopy, d0, numba,
                           saved_current, saved_control, roi, *, provenance):
    """Call the existing placement on the full XY context, then compare all Z layers."""
    require(type(numba) is bool, "engine", "expected recorded Boolean kernel mode")
    require(tuple(segment_record["shape"]) == base.shape[:2],
            "segments", "saved segment grid differs")
    segments = np.empty(base.shape[:2], dtype=object)
    for index in np.ndindex(segments.shape):
        segments[index] = []
    for cell in segment_record["cells"]:
        index = cell["i"], cell["j"]
        require(all(type(i) is int and 0 <= i < n for i, n in zip(index, segments.shape))
                and not segments[index], "segments", "invalid or repeated segment cell")
        segments[index] = cell["segments"]

    current, control, tree, _, _, _ = integrate_common_canopy(
        base, ground, segments, mapped, canopy["top"], canopy["bottom"], canopy["valid"], d0,
        profile="meta_estimated_canopy_hag", provenance=provenance, numba=numba)
    comparisons = {}
    for name, new, saved in (("current", current, saved_current),
                             ("no_canopy", control, saved_control),
                             ("tree", tree, saved_current == -2)):
        same_shape = new.shape == saved.shape
        difference = new != saved if same_shape else None
        comparisons[name] = {
            "equal": same_shape and not bool(difference.any()),
            "new_shape": list(new.shape),
            "saved_shape": list(saved.shape),
            "scene_mismatches": int(difference.sum()) if same_shape else None,
            "roi_mismatches": int(difference[roi].sum()) if same_shape else None,
        }
    return {
        "status": "MATCH" if all(item["equal"] for item in comparisons.values()) else "MISMATCH",
        "array_comparison": comparisons,
        "generated": summarize(mapped, canopy, current, control, roi),
        "generated_non_tree_control_equal": bool(np.array_equal(np.where(tree, 0, current), control)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--final-report", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--regenerate-tree", action="store_true",
                        help="Generate TREE with the common-input path and compare full saved arrays")
    args = parser.parse_args()
    source, output = args.artifact_root.resolve(), args.output_dir.resolve()
    require(not output.is_relative_to(source) and not output.exists(),
            "output", "new directory outside copied artifacts required")
    result = compare_saved(source, args.final_report, regenerate_tree=args.regenerate_tree)
    output.mkdir()
    with (output / "comparison.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return int(result.get("status") == "MISMATCH")


if __name__ == "__main__":
    raise SystemExit(main())