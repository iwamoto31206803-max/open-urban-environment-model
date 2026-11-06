"""STEP 4-B: four saved real roof distributions, constant numeric ground anchors."""
from copy import deepcopy
import math
from pathlib import Path
import shutil

import numpy as np
import rasterio

from ouem import real_roof_distribution as roof
from ouem import synthetic_height_voxel as voxel
from ouem.consumers import mixed_lod as consumer

PROFILE = "ouem-real-lod2-cell-max-numeric-anchor-voxel/v0.1"
BASELINE = "cebf7b96599cf72d54bb325a1c86eea5aaef1e1b"
MANIFEST_SHA = "f73e65073ed823b9155cc75a93a4cfdbc314fb9a0f1859f4d635ec5e71a952bd"
REPORT_SHA = "c9f3315795dfa8ebba2d3d96a0fd89b8814e0301569da2c19c2f5151e9a9a9f1"
FLAGS = dict(terrain_integration_ready=False, scientific_validation="NOT_VERIFIED",
             formal_acceptance="NOT_VERIFIED")
require = voxel.require


def prepare(identity, maps):
    """B0: constant min-GroundSurface-H anchor; never a physical ground/HAG claim."""
    grid = roof.geometry.GridSpec(tuple(identity["grid"]["bounds"]),
                                  identity["grid"]["resolution"], identity["grid"]["epsg"])
    require(identity["profile"] == roof.PROFILE and identity["vertical"] == roof.VERTICAL,
            "unknown real source/vertical profile")
    require(roof.json_digest(identity["grid"]) == roof.json_digest(roof.grid_metadata(grid)) and grid.resolution == 1.
            and grid.epsg == 6677 and grid.width*grid.height <= 4096, "1 m grid registration mismatch")
    top, state, coverage, fraction = (maps[k] for k in ("top", "state", "roof_coverage", "footprint_fraction"))
    require(all(a.shape == (grid.height, grid.width) for a in maps.values()), "raster shape mismatch")
    require(set(np.unique(state)) <= {0, 1, 2}, "invalid state")
    present = state != 0
    require(present.any() and np.all(state[present] == 1), "cell_max TOP_UNKNOWN")
    require(np.array_equal(np.isfinite(top), present), "top finite mask/state mismatch")
    require(all(np.isfinite(a).all() and (a >= 0).all() and (a <= 1+1e-12).all()
                for a in (coverage, fraction))
            and np.array_equal(fraction > 0, present) and np.array_equal(coverage > 0, present),
            "invalid footprint/roof coverage")
    ground = np.array([p for f in identity["ground_faces"] for ring in f["standard_xyz_rings"] for p in ring], dtype=float)
    require(ground.ndim == 2 and ground.shape[1] == 3 and np.isfinite(ground).all(), "invalid GroundSurface XYZ")
    anchor = float(ground[:, 2].min())
    relative = top[present]-anchor
    require(np.isfinite(relative).all() and (relative > 0).all(), "nonpositive/nonfinite relative height")
    height = np.zeros(top.shape, dtype=np.float64)
    height[present] = relative
    ids = present.astype(np.int32)
    segments = np.empty(top.shape, dtype=object)
    for index in np.ndindex(top.shape):
        segments[index] = [[0., float(height[index])]] if present[index] else []
    metadata = dict(profile=PROFILE, input_kind="saved_real_cell_max", source=deepcopy(identity),
        grid=deepcopy(identity["grid"]), source_owner_mapping={identity["source_id"]: 1},
        owner_rule="single fixed source per independent building run", anchor_H=anchor,
        anchor_rule="minimum original GroundSurface vertex H; numerical experiment, not verified terrain/HAG",
        vertical=deepcopy(roof.VERTICAL), extrusion="[0, cell_max_absolute_H - anchor_H]",
        horizontal_approximation="every positive-area support becomes a full 1 m square column",
        axes="row southward, column eastward, z upward; no transpose/flip", tree="none")
    inputs = dict(height=height, ids=ids, segments=segments,
                  dem=np.full(top.shape, anchor, dtype=np.float64), metadata=metadata)
    # B0 validates numeric suitability; B1 preflight checks rounding/capacity.
    qa = dict(anchor_H=anchor, ground_vertex_H_range=[anchor, float(ground[:, 2].max())],
        relative_height_range=[float(relative.min()), float(relative.max())],
        present_columns=int(present.sum()),
        footprint_area_m2=float(fraction.sum()), roof_support_area_m2=float(coverage.sum()),
        full_column_area_m2=int(present.sum()),
        expansion_vs_footprint_m2=float(present.sum()-fraction.sum()),
        expansion_vs_support_m2=float(present.sum()-coverage.sum()),
        partial_footprint_columns=int(((fraction > 0) & (fraction < 1-1e-12)).sum()),
        partial_support_columns=int(((coverage > 0) & (coverage < 1-1e-12)).sum()),
        minimum_positive_support_fraction=float(coverage[present].min()))
    return inputs, qa


def load_inputs(distribution_run, audit_run, artifact_root):
    """Read-only provenance replay plus all pinned 4-A bytes; no roof regeneration."""
    samples, watch, chain = roof.load_samples(audit_run, artifact_root)
    root = Path(distribution_run).resolve(strict=True)
    roof.audit._capture(watch, "4A_manifest", root/"manifest.json", MANIFEST_SHA)
    roof.audit._capture(watch, "4A_report", root/"report.json", REPORT_SHA)
    manifest, report = consumer.load(root/"manifest.json"), consumer.load(root/"report.json")
    require(manifest["status"] == report["status"] == "COMPLETED_EXPERIMENTAL"
            and report["geometric_numerical_qa"] == "PASS", "incomplete STEP 4-A")
    for name, sha in manifest["outputs"].items():
        path = root/name
        require(path.resolve().is_relative_to(root), "unconfined saved output")
        roof.audit._capture(watch, "4A_output_"+name, path, sha)
    # Historical source/code files are identities, not the current implementation.
    for name, item in report["inputs"].items():
        require(name in watch.identities and all(watch.identities[name][k] == item[k]
                for k in ("path", "sha256", "size_bytes")), "historical STEP 4-A input identity differs")
    results = {}
    for building, current in samples:
        label = current["label"]
        path = root/label
        identity = consumer.load(path/"inputs.json")
        require(roof.json_digest({k:identity[k] for k in current}) == roof.json_digest(current), "fixed sample/face provenance differs")
        require(roof.json_digest(consumer.load(path/"source_faces.json")) == roof.json_digest({f["polygon_id"]: f for f in current["faces"]}),
                "RoofSurface references differ")
        grid = roof.geometry.GridSpec(tuple(identity["grid"]["bounds"]))
        require(roof.json_digest(roof.grid_metadata(grid)) == roof.json_digest(identity["grid"]), "saved grid differs")
        maps = {}
        for name in ("top", "state", "roof_coverage", "footprint_fraction"):
            with rasterio.open(path/("cell_max_"+name+".tif")) as src:
                require(src.crs.to_epsg() == 6677 and src.transform == grid.transform
                        and src.shape == (grid.height, grid.width), "GeoTIFF registration mismatch")
                nodata = src.nodata
                require((name == "top" and nodata is not None and math.isnan(nodata) and src.dtypes == ("float64",))
                        or (name == "state" and nodata == 255 and src.dtypes == ("uint8",))
                        or (name not in ("top", "state") and nodata is None and src.dtypes == ("float64",)),
                        "GeoTIFF dtype/NoData mismatch")
                maps[name] = src.read(1)
                require(np.array_equal(src.read_masks(1) > 0, np.isfinite(maps[name]) if name == "top"
                                       else np.ones(src.shape, dtype=bool)), "GeoTIFF valid mask mismatch")
        inputs, qa = prepare(identity, maps)
        results[label] = dict(inputs=inputs, qa=qa, maps=maps, source_dir=path)
    require(set(results) == set(roof.LABELS), "four fixed samples required")
    for name, file in dict(adapter=__file__, voxel_core=voxel.__file__, effective_ground=voxel.effective_ground.__code__.co_filename,
                           engine_provenance=voxel.voxcity_provenance.__code__.co_filename).items():
        roof.audit._capture(watch, "4B_code_"+name, file)
    watch.unchanged()
    return results, watch, chain


def execute(item):
    # Rebuild to reject a modified handoff without assigning a synthetic profile.
    rebuilt, qa = prepare(item["inputs"]["metadata"]["source"], item["maps"])
    require(voxel.input_identity(rebuilt) == voxel.input_identity(item["inputs"]), "real input handoff changed")
    result = voxel.execute_arrays(item["inputs"])
    require(result["qa"]["d0"] == qa["anchor_H"]
            and np.all(np.asarray(result["qa"]["effective_ground"]) == qa["anchor_H"]), "constant anchor/D0 mismatch")
    present = item["inputs"]["ids"] > 0
    stop = np.zeros(present.shape, dtype=int)
    for row in result["qa"]["integer_intervals"]:
        stop[tuple(row["cell_index"])] = row["stop"]
    anchor = qa["anchor_H"]
    upper = np.full(present.shape, np.nan)
    lower = upper.copy()
    upper[present] = anchor+stop[present]
    lower[present] = upper[present]-1
    errors = upper[present]-item["maps"]["top"][present]
    lower_errors = lower[present]-item["maps"]["top"][present]
    qa.update(result["qa"])
    qa.update(status="PASS", upper_edge_minus_roof_H_range_m=[float(errors.min()), float(errors.max())],
              uppermost_voxel_lower_edge_minus_roof_H_range_m=[float(lower_errors.min()), float(lower_errors.max())],
              distinct_building_column_heights_m=np.unique(stop[present]-1).tolist(),
              source_roof_H_range=[float(item["maps"]["top"][present].min()), float(item["maps"]["top"][present].max())])
    require(np.all(errors >= .5-1e-10) and np.all(errors <= 1.5+1e-10), "unexpected quantization convention")
    result.update(qa=qa, upper=upper, lower=lower)
    return result


def plot(path, item, result):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    figure = Figure(figsize=(12, 7), layout="constrained")
    FigureCanvasAgg(figure)
    top, upper = item["maps"]["top"], result["upper"]
    axes = figure.subplots(2, 2)
    lo, hi = np.nanmin(top), np.nanmax(upper)
    for axis, data, title in zip(axes[0], (top, upper), ("Source cell_max H", "Voxel upper edge H")):
        image = axis.imshow(np.ma.masked_invalid(data), vmin=lo, vmax=hi, origin="upper")
        axis.set_title(title+" (m)")
        axis.set_xlabel("column eastward")
        axis.set_ylabel("row southward")
        figure.colorbar(image, ax=axis)
    # Occupied-column profile at the row with largest source-H range.
    ranges = [np.ptp(row[np.isfinite(row)]) if np.isfinite(row).any() else -1 for row in top]
    row = int(np.argmax(ranges))
    axes[1, 0].plot(top[row], "o-", label="source roof H")
    axes[1, 0].step(np.arange(top.shape[1]), upper[row], where="mid", label="voxel upper edge")
    axes[1, 0].set(title=f"Section row {row}", xlabel="column", ylabel="H (m)")
    axes[1, 0].legend()
    classes = result["voxels"][row].T
    axes[1, 1].imshow(classes == -3, origin="lower", aspect="auto", interpolation="nearest")
    axes[1, 1].set(title=f"BUILDING occupancy row {row}", xlabel="column", ylabel="Z layer index")
    figure.suptitle(item["inputs"]["metadata"]["source"]["label"]+": real LoD2 / numerical anchor only")
    figure.savefig(path, dpi=130, metadata={"Software": "OUEM STEP 4-B"})


def save_building(path, item, result):
    require(result["input_identity"] == voxel.input_identity(result["inputs"])
            and result["voxels_identity"] == voxel.array_identity(result["voxels"]), "result changed before save")
    path.mkdir()
    arrays = {k: result["inputs"][k] for k in ("height", "ids", "dem")}
    arrays.update(voxels=result["voxels"], voxel_upper_H=result["upper"], voxel_uppermost_lower_H=result["lower"],
                  **item["maps"])
    for name, array in arrays.items():
        file = path/(name+".npy")
        np.save(file, array, allow_pickle=False)
        require(np.array_equal(np.load(file, allow_pickle=False), array, equal_nan=True), "NPY readback mismatch")
    for name, value in dict(metadata=result["inputs"]["metadata"], segments=result["inputs"]["segments"].tolist(),
                            qa=result["qa"], engine=result["engine"], runtime=result["runtime"]).items():
        roof.audit.write(path/(name+".json"), value)
    for name in ("source_faces.json", "projections.json", "cell_max_contributions.json", "inputs.json"):
        source = item["source_dir"]/name
        shutil.copyfile(source, path/name)
        require(consumer.digest(source) == consumer.digest(path/name), "source reference copy differs")
    plot(path/"diagnostic.png", item, result)


def run(distribution_run, audit_run, output, artifact_root):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    stage = "B0"
    try:
        items, watch, chain = load_inputs(distribution_run, audit_run, artifact_root)
        roof.audit.write(output/"gate_b0.json", dict(status="PASS", buildings={k:v["qa"] for k,v in items.items()}))
        stage = "B1"
        results = {}
        for label, item in items.items():
            result = execute(item)
            save_building(output/label, item, result)
            results[label] = dict(source_id=item["inputs"]["metadata"]["source"]["source_id"],
                                  ouem_id=item["inputs"]["metadata"]["source"]["ouem_id"], qa=result["qa"],
                                  engine=result["engine"], runtime=result["runtime"], input_identity=result["input_identity"])
        watch.unchanged()
        report = dict(profile=PROFILE, baseline_main=BASELINE, technical_execution="PASS", geometric_numerical_qa="PASS",
                      gate_b0="PASS", gate_b1="PASS", buildings=results, source_chain=chain,
                      inputs=watch.identities, **FLAGS)
        roof.audit.write(output/"report.json", report)
        outputs = {p.relative_to(output).as_posix():consumer.digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
        watch.unchanged()
        roof.audit.write(output/"manifest.json", dict(profile=PROFILE, status="COMPLETED_EXPERIMENTAL", outputs=outputs, **FLAGS))
        return report
    except Exception as exc:
        status = "NOT_EXECUTED" if isinstance(exc, FileNotFoundError) and stage == "B0" else "BLOCKED"
        failure = dict(profile=PROFILE, technical_execution=status, stopped_at=stage,
                       geometric_numerical_qa="NOT_VERIFIED", error=f"{type(exc).__name__}: {exc}", **FLAGS)
        roof.audit.write(output/"failure.json", failure)
        return failure


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution-run", type=Path, required=True)
    parser.add_argument("--audit-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.distribution_run, args.audit_run, args.output_dir, args.artifact_root)
    print(report["technical_execution"], report.get("error", "four real LoD2 voxel volumes; oracle PASS"))
    return int(report["technical_execution"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
