"""STEP 2-C2 saved-model canopy experiment; never runs Solar/GVI or rebuilds GIS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

import numpy as np

from ouem import candidate_b_envelope as c1
from ouem import height_envelope as env
from ouem.candidate_b_canopy import integrate
from ouem.compatibility_probe import load_candidate
from ouem.consumers.source_h_standard import Watch
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_solar import sample_canopy, integrate_canopy
from ouem.real_komae_source_h import distribution

C1_SHA = "544c526ce7078c72b89da6757662c4ec6b13924598458c5ae95ac57f88cab7ef"
STEP2A_SHA = "c968c8a754e2a9bc0eeb2fa4a4b24a165021c1a518f6d99e76643ad8a8af81af"
DERIVED_PROFILE = "ouem-candidate-b-actual-centres-derived-envelope/v0.1"


def restore_segments(value, shape, ids):
    """Strict saved JSON restoration, without estimating any building geometry."""
    require(len(shape) == 2 and ids.shape == shape and ids.dtype.kind in "iu" and (ids >= 0).all(),
            "segments.grid", "matching nonnegative integer owner grid required")
    require(type(value) is list and len(value) == shape[0], "segments.shape", "row count differs")
    result = np.empty(shape, dtype=object)
    for i, row in enumerate(value):
        require(type(row) is list and len(row) == shape[1], "segments.shape", "column count differs")
        for j, cell in enumerate(row):
            require(type(cell) is list, "segments.cell", "list of intervals required")
            pairs = []
            for pair in cell:
                require(type(pair) is list and len(pair) == 2
                        and all(type(v) in (int, float) and np.isfinite(v) for v in pair),
                        "segments.interval", "two finite JSON numbers required; no bool/string")
                low, high = pair
                require(0 <= low < high, "segments.order", "nonnegative ordered interval required")
                pairs.append([float(low), float(high)])
            require(bool(pairs) == bool(ids[i, j]), "segments.support", "saved owner/interval support differs")
            result[i, j] = pairs
    return result


def direct_samples(chm, dem, grid):
    top, bottom, state, qa, ch, ground = c1.evaluate(chm, dem, grid)
    missing = ch.missing | ground.missing
    outside = ch.outside | ground.outside
    valid = (state == env.VALID) & ~missing & ~outside
    sampled = dict(top=top, bottom=bottom, state=state, missing=missing, outside=outside,
                   valid=valid, candidate=valid & (top > bottom))
    return sampled, ch.values, ground.values, qa


def placement(sampled, arrays, metadata):
    """Vector QA oracle only; public Voxelizer remains the sole model generator."""
    ground = arrays["ground_abs"]
    below = sampled["candidate"] & (sampled["bottom"] < ground)
    active = sampled["candidate"] & ~below
    dtype = np.float32 if metadata["numba"] else np.float64
    relative = [np.where(active, sampled[k]-ground, 0).astype(dtype).astype(float)
                for k in ("bottom", "top")]
    require(all(np.isfinite(v).all() and (v >= 0).all() for v in relative),
            "placement.relative", "unrepresentable relative envelope")
    lower, upper = [np.floor(v+.5).astype(np.int64) for v in relative]
    thin = active & (lower == upper) & (lower > 0)
    lower[thin] -= 1
    nonempty = active & (upper > lower)
    surface = np.argmax(arrays["voxels"] == 1, axis=2)
    starts, ends = surface+1+lower, surface+1+upper
    return dict(active=active, below_ground=below, nonempty=nonempty, start=starts, end=ends,
                thin_expanded=thin, rounded_empty=active & ~nonempty)


def predicted_tree(plan, base, nz):
    k = np.arange(nz)
    predicted = plan["nonempty"][..., None] & (k >= plan["start"][..., None]) & (k < plan["end"][..., None])
    reference = np.pad(base, ((0, 0), (0, 0), (0, nz-base.shape[2])))
    return predicted & (reference != -3), reference


def compare(a, b, arrays, metadata, a_dem, b_dem):
    both = a["valid"] & b["valid"]
    qa = {}
    plans = [placement(s, arrays, metadata) for s in (a, b)]
    nz = max(arrays["voxels"].shape[2], *(int(p["end"][p["nonempty"]].max())
             if p["nonempty"].any() else 0 for p in plans))
    predictions = [predicted_tree(p, arrays["voxels"], nz)[0] for p in plans]
    for label, sampled, dem, plan in zip(("A", "B"), (a, b), (a_dem, b_dem), plans):
        valid = sampled["valid"]
        qa[label] = dict(valid=int(valid.sum()), missing_inside=int((sampled["missing"] & ~sampled["outside"]).sum()),
            outside=int(sampled["outside"].sum()), invalid_state=int((~sampled["missing"] & ~sampled["outside"] & ~valid).sum()),
            zero_depth_valid=int((valid & ~sampled["candidate"]).sum()), candidates=int(sampled["candidate"].sum()),
            top_m=distribution(sampled["top"][valid]), bottom_m=distribution(sampled["bottom"][valid]),
            dem_matches_saved_t5=bool(np.array_equal(dem, arrays["raw_dem"])),
            dem_different_cells=int((dem != arrays["raw_dem"]).sum()),
            top_minus_effective_ground_m=distribution((sampled["top"]-arrays["ground_abs"])[valid]),
            bottom_minus_effective_ground_m=distribution((sampled["bottom"]-arrays["ground_abs"])[valid]),
            below_ground_candidates=int(plan["below_ground"].sum()),
            valid_zero_below_ground=int((valid & ~sampled["candidate"] & (sampled["bottom"] < arrays["ground_abs"])).sum()),
            predicted_tree_voxels=int(predictions[("A", "B").index(label)].sum()))
    difference = np.any(predictions[0] != predictions[1], axis=2)
    qa.update(candidate_position_differences=int((a["candidate"] != b["candidate"]).sum()),
        state_differences=int((a["state"] != b["state"]).sum()),
        top_B_minus_A_m=distribution((b["top"]-a["top"])[both]),
        bottom_B_minus_A_m=distribution((b["bottom"]-a["bottom"])[both]),
        top_different_cells=int((both & (a["top"] != b["top"])).sum()),
        bottom_different_cells=int((both & (a["bottom"] != b["bottom"])).sum()),
        predicted_different_tree_columns=int(difference.sum()),
        predicted_different_tree_voxels=int((predictions[0] != predictions[1]).sum()),
        predicted_different_tree_columns_in_roi=int((difference & arrays["roi"]).sum()))
    return qa, plans, difference


def write_array(out, name, values):
    path = out/(name+".npy")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        np.save(stream, values, allow_pickle=False)
    saved = np.load(path, allow_pickle=False)
    require(saved.dtype == values.dtype and saved.shape == values.shape
            and np.array_equal(saved, values, equal_nan=True), "output.array", "saved NPY differs")
    return dict(sha256=env.sha256(path), bytes=path.stat().st_size, shape=list(saved.shape), dtype=str(saved.dtype))


def publish(out, record):
    path = out/"manifest.json.pending"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True, allow_nan=False)+"\n")
    os.rename(path, out/"manifest.json")


def implementation_identity():
    return dict(c1.implementation_identity(), workflow_sha256=env.sha256(__file__),
        adapter_sha256=env.sha256(integrate.__code__.co_filename),
        b1_sha256=env.sha256(integrate_canopy.__code__.co_filename),
        host=platform.node(), os=platform.platform(), executable=sys.executable)


def run(source_run, envelope_manifest, chm, acquisition_record, chm_evidence, step2a_run, output_dir):
    source, envelope, chm, acq, evidence, step2a = [Path(p).resolve(strict=True) for p in
        (source_run, envelope_manifest, chm, acquisition_record, chm_evidence, step2a_run)]
    out = Path(output_dir).resolve()
    for root in (source, envelope.parent, chm.parent, acq.parent, evidence.parent, step2a):
        require(not out.is_relative_to(root) and not root.is_relative_to(out), "output", "new output outside inputs required")
    out.mkdir(parents=True)  # no overwrite/resume; concurrent writers unsupported
    report = dict(profile="ouem-candidate-b-real-canopy-pair/v0.1", status="BLOCKED",
        terrain_integration_ready=False, scientific_validation="NOT_VERIFIED", formal_acceptance="NOT_VERIFIED",
        selected="B", derived_profile=DERIVED_PROFILE, outputs={})
    watches = {}
    try:
        identity = implementation_identity()
        engine = voxcity_provenance()
        require(engine["verified"], "engine", "fixed VoxCity installation required")
        arrays, metadata, probe, t5, model_watch = load_candidate(source, c1.T5_SHA)
        watches["t5"] = model_watch
        ewatch = watches["c1"] = Watch(envelope.parent)
        record = ewatch.capture("manifest", envelope.name, C1_SHA, json_data=True)
        require(record["status"] == "COMPLETED"
                and record["schema"] == "ouem-candidate-b-experimental-height-envelope/v0.1"
                and record["terrain_integration_ready"] is False
                and record["terrain_identity"]["terrain_sha256"] == c1.DEM_SHA
                and record["cr_model"] == env.ConstantCR(.60).specification()
                and record["vertical_reference"]["working_assumption"] == c1.VERTICAL,
                "envelope.profile", "unexpected C1 identity or semantics")
        refs = {key: ref for group in record["inputs"] for key, ref in group.items()}
        for name, ref in record["outputs"].items():
            ewatch.capture(name, name, ref["sha256"], ref["bytes"])
        for label, path, expected in (("chm", chm, c1.CHM_SHA), ("acquisition", acq, c1.ACQUISITION_SHA),
                                       ("evidence", evidence, c1.EVIDENCE_SHA)):
            watch = watches[label] = Watch(path.parent)
            require(refs[path.name]["sha256"] == expected, "envelope.input", "C1 source hash differs")
            watch.capture(label, path.name, expected)
        support = record["chm_lineage"]["hag_evidence"]
        watches["evidence"].capture("snapshot", support["snapshot_path"], support["snapshot_sha256"])
        swatch = watches["step2a"] = Watch(step2a)
        prior = swatch.capture("report", "report.json", STEP2A_SHA, json_data=True)
        require(prior["source_report_sha256"] == c1.T5_SHA, "STEP2A.T5", "protected run refers to a different model")
        for name, sha in prior["outputs"].items():
            swatch.capture(name, name, sha)
        for key, ref in prior["inputs"].items():
            require(key in model_watch.identities and ref["sha256"] == model_watch.identities[key]["sha256"],
                    "STEP2A.inputs", "protected model input identity differs")
        for key, ref in refs.items():
            if key in model_watch.identities:
                require(ref["sha256"] == model_watch.identities[key]["sha256"], "C1.T5", "saved source differs")
        require(t5["outputs"]["t5-2/terrain.tif"] == c1.DEM_SHA, "DEM", "T5/C1 DEM mismatch")
        shape = arrays["ids"].shape
        segments = restore_segments(env.read_json(model_watch.resolve("t5-3/segments.json")), shape, arrays["ids"])
        height = np.load(model_watch.resolve("t5-2/building_height.npy"), allow_pickle=False, mmap_mode="r")
        require(height.shape == shape and height.dtype.kind == "f" and np.isfinite(height).all()
                and (height >= 0).all() and np.array_equal(height > 0, arrays["ids"] > 0),
                "building.height", "saved height/owner grid differs")
        segments_before = json.dumps(segments.tolist(), allow_nan=False)
        grid = c1.point_grid(arrays["centres_xy"])
        paths = [envelope.parent/name for name in ("canopy_top_z.tif", "canopy_bottom_z.tif", "height_envelope_state.tif")]
        a = sample_canopy(paths, *grid.centres())
        b, ch_values, b_dem, bqa = direct_samples(chm, source/"t5-2/terrain.tif", grid)
        north_grid = env.GridSpec(tuple(record["grid_spec"]["bounds"]))
        north, north_chm, north_dem, _ = direct_samples(chm, source/"t5-2/terrain.tif", north_grid)
        x, y = grid.centres()
        inverse = ~north_grid.transform
        cols, rows = np.floor(inverse.a*x+inverse.c).astype(int), np.floor(inverse.e*y+inverse.f).astype(int)
        require(((cols >= 0) & (cols < north_grid.width) & (rows >= 0) & (rows < north_grid.height)).all(),
                "coordinates", "saved centre outside C1 grid")
        for key in ("top", "bottom", "state"):
            require(np.array_equal(a[key], north[key][rows, cols]), "C1.reproduction", "north-up samples differ")
        a_dem = north_dem[rows, cols]
        a_chm = north_chm[rows, cols]
        comparison, plans, difference = compare(a, b, arrays, metadata, a_dem, b_dem)
        comparison["chm_different_cells"] = int((a_chm != ch_values).sum())
        require(comparison["B"]["dem_matches_saved_t5"], "DEM.samples", "B DEM differs from T5")
        report.update(engine=engine, implementation=identity, probe=probe,
            geography=dict(metadata, processing_cells=int(np.prod(shape)), evaluation_cells=int(arrays["roi"].sum())),
            sampling_comparison=comparison, direct_calculation_qa=bqa,
            sampling_profiles=dict(A=dict(profile=record["schema"], manifest_sha256=C1_SHA,
                rasters=record["outputs"], method="nearest original C1 TIFFs at saved actual centres"),
                B=dict(profile=DERIVED_PROFILE, chm_sha256=c1.CHM_SHA, dem_sha256=c1.DEM_SHA,
                    centres_sha256=t5["outputs"]["t5-2/centres_xy.npy"],
                    method="original HAG/DEM nearest at saved actual centres; ConstantCR(.60); no shift")),
            selection=dict(method="B", profile=DERIVED_PROFILE,
                basis="Direct original HAG/DEM lookup at saved actual centres reproduces T5 raw DEM; A remains separate and unchanged",
                quantity="absolute_elevation_m", vertical_reference="T.P.",
                vertical_status="WORKING_ASSUMPTION_ONLY", vertical_evidence=record["vertical_reference"],
                source_dem_sha256=c1.DEM_SHA, cr_model=env.ConstantCR(.60).specification(),
                formulas=record["formulas"], presence="ESTIMATED / NOT_OBSERVED"))
        def save(name, values):
            report["outputs"][name+".npy"] = write_array(out, name, values)
        for label, samples, plan in zip(("A", "B"), (a, b), plans):
            for key, values in samples.items():
                save(label+"/"+key, values)
            for key in ("below_ground", "active", "nonempty", "rounded_empty", "thin_expanded"):
                save(label+"/"+key, plan[key])
            save(label+"/uncertain", ~samples["valid"])
            save(label+"/zero_depth_valid", samples["valid"] & ~samples["candidate"])
        save("A/source_dem", a_dem)
        save("A/source_chm", a_chm)
        save("B/source_dem", b_dem)
        save("B/source_chm", ch_values)
        save("predicted_AB_different_columns", difference)
        save("centres_xy", arrays["centres_xy"])
        save("evaluation_mask", arrays["roi"])
        # T.P. is an explicitly conditional computational frame, not newly verified datum evidence.
        current, absent, tree, high, low, qa = integrate(arrays, metadata, segments, b, report["selection"],
            source_dem_sha256=c1.DEM_SHA, building_height_grid=height)
        require(not plans[1]["nonempty"].any() or
                int(plans[1]["end"][plans[1]["nonempty"]].max()) <= current.shape[2],
                "pair.capacity", "independent TREE end exceeds saved capacity")
        expected, reference = predicted_tree(plans[1], arrays["voxels"], current.shape[2])
        require(np.array_equal(tree, expected) and np.array_equal(absent, reference)
                and np.array_equal(np.where(tree, 0, current), absent)
                and not np.any(tree & (reference != 0)), "pair.independent", "occupancy differs from independent oracle")
        require(json.dumps(segments.tolist(), allow_nan=False) == segments_before,
                "segments.immutable", "engine modified nested input segments")
        for name, values in (("current", current), ("no_canopy", absent), ("tree_mask", tree),
                             ("B/relative_top", high), ("B/relative_bottom", low)):
            save(name, values)
        occupied = tree.any(axis=2)
        first = np.argmax(tree, axis=2)
        last_edge = tree.shape[2]-np.argmax(tree[..., ::-1], axis=2)
        d0 = metadata["d0_effective_abs_m"]
        report.update(integration_qa=qa, independent_pair_qa="PASS",
            occupied_tree_edges=dict(bottom_minus_estimated_bottom_m=distribution((d0+first-b["bottom"])[occupied]),
                top_minus_estimated_top_m=distribution((d0+last_edge-b["top"])[occupied]),
                interpretation="Actual occupied TREE edges after building priority; separate from pre-occlusion interval edges"),
            roi_qa=dict(tree_voxels=int(tree[arrays["roi"]].sum()), tree_columns=int(tree.any(axis=2)[arrays["roi"]].sum()),
                        cells=int(arrays["roi"].sum())),
            uncertainty="Every crown is estimated, even when state=1; uncertain mask denotes invalid source, not ecological confidence")
        for watch in watches.values():
            watch.unchanged()
        require(identity == implementation_identity(), "implementation", "code/environment changed during run")
        report.update(inputs={key: w.identities for key, w in watches.items()},
            input_roots={key: str(w.root) for key, w in watches.items()}, input_immutability="PASS", status="COMPLETED")
        report["reproducibility_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, allow_nan=False).encode()).hexdigest()
    except Exception as exc:
        report.update(status="BLOCKED", error=f"{type(exc).__name__}: {exc}")
        try:
            for watch in watches.values():
                watch.unchanged()
            report["input_immutability"] = "PASS"
        except Exception as changed:
            report["input_immutability"] = f"FAILED: {changed}"
        report["inputs"] = {key: w.identities for key, w in watches.items()}
        report["input_roots"] = {key: str(w.root) for key, w in watches.items()}
    try:
        publish(out, report)
    except Exception as exc:
        report.update(status="BLOCKED", error=f"Publication failed: {exc}")
        with (out/"failure.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("source-run", "envelope-manifest", "chm", "acquisition-record", "chm-evidence", "step2a-run", "output-dir"):
        parser.add_argument("--"+key, type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("status", "error", "sampling_comparison", "integration_qa") if key in report}))
    return int(report["status"] != "COMPLETED")


if __name__ == "__main__":
    raise SystemExit(main())
