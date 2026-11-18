"""Experimental same-grid comparison of Meta HAG and saved PR #99 TREE."""
import argparse
import json
from pathlib import Path

import numpy as np

from ouem import height_envelope as env
from ouem.canopy_height_candidate import effective_hag, map_envelope_fields, meta_presence_fields
from ouem.komae_saved_preflight import (
    ENVELOPE_SHA, FINAL_REPORT_SHA, FrozenWatch, bind, child,
)
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_solar import sample_canopy


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


def compare_saved(root, report_locator):
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
    watch.unchanged()
    return {
        "report_sha256": FINAL_REPORT_SHA,
        "scope": "experimental_saved_tree_diagnostic",
        "saved_non_tree_control_equal": True,
        "candidate_without_tree_attribution": "UNRESOLVED",
        **result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--final-report", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    source, output = args.artifact_root.resolve(), args.output_dir.resolve()
    require(not output.is_relative_to(source) and not output.exists(),
            "output", "new directory outside copied artifacts required")
    result = compare_saved(source, args.final_report)
    output.mkdir()
    with (output / "comparison.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
