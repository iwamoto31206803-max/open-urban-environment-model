"""STEP 4-B2: saved roof H + saved Candidate B DEM; conditional numerical overlay."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import rasterio

from ouem import real_roof_voxel as base
from ouem.height_envelope import sample_raster

roof, voxel, consumer = base.roof, base.voxel, base.consumer
require = voxel.require
PROFILE = "ouem-real-lod2-saved-terrain-voxel/conditional/v0.1"
BASELINE = "99fc3a3d44bf85fdf60b783f4570dffc46008591"
B1_SHA = "5f1b0e1c11414889aa2ee305faf74989da65d590130bf85a0b61128ecf2662e9"
B1_REPORT_SHA = "5a615675276402bd10563a29cf8b74aff4768bf1c34187d8ac0707e862ed7646"
T5_SHA = "1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f"
DEM_SHA = "ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2"


def span(values):
    return [float(np.min(values)), float(np.max(values))]


def vertical_conditions(building, t5):
    require(building == roof.VERTICAL and t5["vertical"] == "CONDITIONAL"
            and t5["vertical_evidence"]["ward_tp"] == "INFERRED_FROM_SOURCE_LINEAGE"
            and all(t5["vertical_evidence"][k] == "NOT_VERIFIED" for k in ("epoch", "accuracy", "datum_realization")),
            "vertical declaration conflict/unsupported evidence")
    return dict(status="CONDITIONAL", building=deepcopy(building), dem=deepcopy(t5["vertical_evidence"]),
                assumption="T.P. inheritance working assumption; no height offset; not verified HAG",
                realization_epoch_accuracy="NOT_VERIFIED")


def sample_dem(path, grid):
    """Reuse inverse-affine floor sampling; independently check selected 0.5 m cells."""
    sample = sample_raster(path, grid)
    require(not sample.outside.any() and not sample.missing.any() and np.isfinite(sample.values).all(),
            "DEM uncovered/NoData/nonfinite; no fill")
    with rasterio.open(path) as src:
        require(src.crs.to_epsg() == 6677 and src.transform.a == .5 and src.transform.e == -.5
                and src.transform.b == src.transform.d == 0, "saved DEM CRS/0.5 m registration differs")
        x, y = grid.centres()
        col_f = (x-src.transform.c)/.5
        row_f = (src.transform.f-y)/.5
        rows, cols = np.floor(row_f).astype(int), np.floor(col_f).astype(int)
        require(((rows >= 0) & (cols >= 0) & (rows < src.height) & (cols < src.width)).all(), "source index outside")
        raw, mask = src.read(1), src.read_masks(1)
        require(np.array_equal(sample.values, raw[rows, cols]) and (mask[rows, cols] > 0).all(),
                "independent DEM pixel/mask mismatch")
        selected_x = src.transform.c+(cols+.5)*.5
        selected_y = src.transform.f-(rows+.5)*.5
    return sample.values.copy(), np.stack((rows, cols), axis=-1), dict(metadata=sample.metadata,
        method="nearest: containing source pixel via inverse-affine floor; boundary selects east/south pixel",
        x_offset_from_selected_source_centre_m=span(x-selected_x), y_offset_from_selected_source_centre_m=span(y-selected_y),
        boundary_ties=int(((row_f == rows) & (col_f == cols)).sum()), cells=int(rows.size), missing=0, outside=0)


def prepare(item, dem, vertical):
    require(vertical["status"] == "CONDITIONAL" and vertical["building"] == roof.VERTICAL, "vertical condition mismatch")
    old = item["inputs"]
    require(dem.shape == old["ids"].shape and np.isfinite(dem).all(), "invalid DEM shape/values")
    inputs = deepcopy(old)
    inputs["dem"] = np.array(dem, dtype=np.float64, copy=True)
    effective, d0 = voxel.effective_ground(inputs["ids"], inputs["dem"])
    present = inputs["ids"] > 0
    high = item["maps"]["top"][present]-effective[present]
    require(np.isfinite(high).all() and (high > 0).all(), "roof at/below effective ground")
    inputs["height"][:] = 0
    inputs["height"][present] = high
    for index in np.ndindex(dem.shape):
        inputs["segments"][index] = [[0., float(inputs["height"][index])]] if present[index] else []
    metadata = inputs["metadata"]
    metadata.pop("anchor_H")
    metadata.pop("anchor_rule")
    metadata.update(profile=PROFILE, input_kind="saved_real_cell_max_with_saved_terrain", vertical=deepcopy(vertical),
                    extrusion="[0, absolute_roof_H - owner_conditioned_ground_H]", terrain_sha256=DEM_SHA,
                    expected_d0=d0, expected_effective_ground=effective.tolist())
    anchor = item["qa"]["anchor_H"]
    return inputs, dict(raw_dem_H_range=span(dem), effective_ground_H_range=span(effective),
        building_effective_ground_H_range=span(effective[present]), expected_d0=d0,
        relative_height_range=span(high), owner_ground_adjustment_m=span(effective-dem),
        sampled_building_dem_minus_GroundSurface_H_m=span(dem[present]-anchor),
        effective_building_ground_minus_GroundSurface_H_m=span(effective[present]-anchor))


def load_inputs(distribution_run, audit_run, b1_run, t5_run, artifact_root):
    items, watch, chain = base.load_inputs(distribution_run, audit_run, artifact_root)
    b1, t5_path = Path(b1_run).resolve(strict=True), Path(t5_run).resolve(strict=True)
    roof.audit._capture(watch, "B1_manifest", b1/"manifest.json", B1_SHA)
    roof.audit._capture(watch, "B1_report", b1/"report.json", B1_REPORT_SHA)
    previous = consumer.load(b1/"report.json")
    require(previous["technical_execution"] == previous["geometric_numerical_qa"] == "PASS", "B1 incomplete")
    for name, sha in consumer.load(b1/"manifest.json")["outputs"].items():
        path = b1/name
        require(path.resolve().is_relative_to(b1), "unconfined B1 output")
        roof.audit._capture(watch, "B1_output_"+name, path, sha)
    roof.audit._capture(watch, "B2_T5_report", t5_path/"report.json", T5_SHA)
    t5 = consumer.load(t5_path/"report.json")
    dem_path = t5_path/"t5-2/terrain.tif"
    require(t5["outputs"]["t5-2/terrain.tif"] == DEM_SHA and t5["gate2"] == "PASS", "T5 terrain lineage differs")
    roof.audit._capture(watch, "B2_terrain", dem_path, DEM_SHA)
    prepared = {}
    for label, item in items.items():
        require(previous["buildings"][label]["input_identity"] == voxel.input_identity(item["inputs"]), "B1 source/grid input differs")
        old = np.load(b1/label/"voxels.npy", allow_pickle=False)
        expected, _ = voxel.occupancy_oracle(item["inputs"], numba=True)
        require(np.array_equal(old, expected), "saved B1 volume/oracle differs")
        grid = roof.geometry.GridSpec(tuple(item["inputs"]["metadata"]["grid"]["bounds"]))
        dem, row_col, sampling = sample_dem(dem_path, grid)
        vertical = vertical_conditions(item["inputs"]["metadata"]["source"]["vertical"], t5)
        inputs, qa = prepare(item, dem, vertical)
        prepared[label] = dict(item, inputs=inputs, qa=qa, baseline_inputs=item["inputs"], baseline_voxels=old,
                               baseline_upper=np.load(b1/label/"voxel_upper_H.npy", allow_pickle=False),
                               source_row_col=row_col, sampling=sampling)
    roof.audit._capture(watch, "B2_adapter", __file__)
    roof.audit._capture(watch, "B2_sampling_code", sample_raster.__code__.co_filename)
    watch.unchanged()
    return prepared, watch, chain


def reconstruct(result):
    qa, voxels = result["qa"], result["voxels"]
    present = result["inputs"]["ids"] > 0
    upper, lower = np.full(present.shape, np.nan), np.full(present.shape, np.nan)
    for row in qa["integer_intervals"]:
        index = tuple(row["cell_index"])
        lower[index], upper[index] = qa["d0"]+row["start"], qa["d0"]+row["stop"]
    surface = qa["d0"]+np.array(qa["ground_index"])
    require(np.array_equal(np.any(voxels == -3, axis=2), present), "horizontal occupancy differs")
    return lower, upper, surface


def execute(item):
    source = dict(item, inputs=item["baseline_inputs"], qa=dict(anchor_H=item["baseline_inputs"]["metadata"]["anchor_H"]))
    rebuilt, _ = prepare(source, item["inputs"]["dem"], item["inputs"]["metadata"]["vertical"])
    require(voxel.input_identity(rebuilt) == voxel.input_identity(item["inputs"]), "terrain handoff changed")
    result = voxel.execute_arrays(item["inputs"])
    qa = result["qa"]
    require(qa["d0"] == item["qa"]["expected_d0"] and qa["effective_ground"] == item["inputs"]["metadata"]["expected_effective_ground"],
            "effective ground/D0 differs")
    bottom, upper, surface = reconstruct(result)
    present = item["inputs"]["ids"] > 0
    old = item["baseline_voxels"]
    require(np.array_equal(np.any(old == -3, axis=2), present), "B1 horizontal support differs")
    old_bottom = item["baseline_inputs"]["metadata"]["anchor_H"]+1.
    old_upper = item["baseline_upper"]
    # Interval lengths in absolute H, not direct comparison of unrelated Z indices.
    intersection = np.maximum(0., np.minimum(upper[present], old_upper[present])-np.maximum(bottom[present], old_bottom))
    symmetric = (upper[present]-bottom[present])+(old_upper[present]-old_bottom)-2*intersection
    comparison = dict(frame="absolute source-declared H; interval edge comparisons (m), not common integer indices",
        horizontal_columns_unchanged=True, building_columns=int(present.sum()),
        B1_building_voxels=int((old == -3).sum()), terrain_building_voxels=int((result["voxels"] == -3).sum()),
        upper_H_minus_B1_m=span(upper[present]-old_upper[present]), bottom_H_minus_B1_m=span(bottom[present]-old_bottom),
        absolute_interval_symmetric_difference_m3=float(symmetric.sum()),
        B1_anchor_H=float(old_bottom-1), terrain_D0_H=qa["d0"])
    qa.update(item["qa"], status="PASS", roof_upper_edge_error_m=span(upper[present]-item["maps"]["top"][present]),
        uppermost_voxel_lower_edge_error_m=span(upper[present]-1-item["maps"]["top"][present]),
        surface_H_range=span(surface), surface_index_values=np.unique(qa["ground_index"]).tolist(),
        surface_lower_edge_minus_effective_ground_m=span(surface-np.array(qa["effective_ground"])),
        comparison=comparison, sampling=item["sampling"])
    result.update(qa=qa, upper=upper, lower=upper-1, bottom=bottom, surface=surface)
    return result


def plot(path, item, result):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    figure = Figure(figsize=(12, 7), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots(2, 2)
    effective = np.array(result["qa"]["effective_ground"])
    for axis, data, title in zip(axes[0], (item["inputs"]["dem"], effective), ("Sampled DEM H", "Owner-conditioned ground H")):
        image = axis.imshow(data, origin="upper", vmin=item["inputs"]["dem"].min(), vmax=item["inputs"]["dem"].max())
        axis.set(title=title+" (m)", xlabel="column eastward", ylabel="row southward")
        figure.colorbar(image, ax=axis)
    top = item["maps"]["top"]
    row = max(range(top.shape[0]), key=lambda i:np.ptp(top[i][np.isfinite(top[i])]) if np.isfinite(top[i]).any() else -1)
    for data, label in ((top,"source roof H"), (result["upper"],"terrain voxel upper H"),
                        (item["baseline_upper"],"B1 voxel upper H"), (item["inputs"]["dem"],"raw DEM H"),
                        (effective,"effective ground H"), (result["surface"],"surface lower H")):
        axes[1, 0].plot(data[row], label=label)
    axes[1, 0].set(title=f"Absolute-H section row {row}", xlabel="column", ylabel="H (m)")
    axes[1, 0].legend(fontsize=7)
    axes[1, 1].imshow(result["voxels"][row].T, origin="lower", interpolation="nearest", aspect="auto")
    axes[1, 1].set(title=f"Actual classes row {row} (-3 building / 0 air / 1 surface)", xlabel="column", ylabel="Z index above D0")
    figure.suptitle(item["inputs"]["metadata"]["source"]["label"]+": saved Terrain / CONDITIONAL numerical overlay")
    figure.savefig(path, dpi=130, metadata={"Software":"OUEM STEP 4-B2"})


def run(distribution_run, audit_run, b1_run, t5_run, output, artifact_root):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    stage = "B2-0"
    try:
        items, watch, chain = load_inputs(distribution_run, audit_run, b1_run, t5_run, artifact_root)
        roof.audit.write(output/"preflight.json", dict(status="PASS_CONDITIONAL", buildings={k:v["qa"] for k,v in items.items()}))
        stage = "B2-1"
        summaries = {}
        for label, item in items.items():
            result = execute(item)
            path = output/label
            base.save_building(path, item, result, plotter=plot)
            for name, array in dict(effective_ground_H=np.array(result["qa"]["effective_ground"]), surface_lower_H=result["surface"],
                                    building_bottom_H=result["bottom"], source_row_col=item["source_row_col"]).items():
                np.save(path/(name+".npy"), array, allow_pickle=False)
                require(np.array_equal(np.load(path/(name+".npy"), allow_pickle=False), array, equal_nan=True), "extra NPY reread differs")
            summaries[label] = dict(qa=result["qa"], engine=result["engine"], runtime=result["runtime"], input_identity=result["input_identity"])
        watch.unchanged()
        report = dict(profile=PROFILE, baseline_main=BASELINE, technical_execution="PASS", geometric_numerical_qa="PASS",
                      vertical_status="CONDITIONAL", buildings=summaries, inputs=watch.identities, source_chain=chain, **base.FLAGS)
        roof.audit.write(output/"report.json", report)
        outputs = {p.relative_to(output).as_posix():consumer.digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
        watch.unchanged()
        roof.audit.write(output/"manifest.json", dict(profile=PROFILE, status="COMPLETED_EXPERIMENTAL", outputs=outputs, **base.FLAGS))
        return report
    except Exception as exc:
        status = "NOT_EXECUTED" if isinstance(exc, FileNotFoundError) and stage == "B2-0" else "BLOCKED"
        failure = dict(profile=PROFILE, technical_execution=status, stopped_at=stage, error=f"{type(exc).__name__}: {exc}",
                       geometric_numerical_qa="NOT_VERIFIED", **base.FLAGS)
        roof.audit.write(output/"failure.json", failure)
        return failure


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("distribution-run", "audit-run", "b1-run", "t5-run", "output-dir", "artifact-root"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.distribution_run, args.audit_run, args.b1_run, args.t5_run, args.output_dir, args.artifact_root)
    print(result["technical_execution"], result.get("error", "four Terrain voxel volumes; CONDITIONAL vertical overlay"))
    return int(result["technical_execution"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
