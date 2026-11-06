"""STEP 2-C4 saved Candidate B -> unchanged B2 CPU weighted first-TREE index."""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import rowcol

from ouem import b2_gvi as b2
from ouem import candidate_b_solar as solar
from ouem import candidate_b_canopy_run as c2
from ouem import height_envelope as env
from ouem.consumers.source_h_standard import Watch
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require

SOLAR_SHA = "afefa79524efbf911f0019f663235a3115b8158cd79efcd1da67cea18122cfb7"
THREADS = 2
LIMIT_SECONDS = 600.
LIMIT_BYTES = 2*1024**3


def settings():
    return json.loads(json.dumps(dict(b2.SETTINGS, num_threads=THREADS)))


def load_inputs(pair_run, solar_run, source_run):
    pair, sun, source = [Path(p).resolve(strict=True) for p in (pair_run, solar_run, source_run)]
    watch = Watch(sun)
    record = watch.capture("manifest", "manifest.json", SOLAR_SHA, json_data=True)
    require(record["profile"] == "ouem-candidate-b-real-solar/v0.1" and record["status"] == "COMPLETED"
            and record["terrain_integration_ready"] is False, "Solar", "completed experimental Solar required")
    for name, ref in record["outputs"].items():
        watch.capture(name, name, ref["sha256"], ref["bytes"])
    saved = solar.load_inputs(pair, source, record["input_roots"]["step2a"])
    saved["watches"]["solar"] = watch
    for key, refs in record["inputs"].items():
        require(key in saved["watches"] and str(saved["watches"][key].root) == record["input_roots"][key],
                "Solar.inputs", "Solar/C2 input roots differ")
        for name, ref in refs.items():
            require(saved["watches"][key].identities[name]["sha256"] == ref["sha256"],
                    "Solar.inputs", "Solar/C2 input SHA differs")
    a, meta = saved["arrays"], saved["metadata"]
    common = solar.common_observers(saved["current"], saved["absent"], a["ids"], a["centres_xy"], meta["d0_effective_abs_m"])
    def array(name):
        require(name+".npy" in record["outputs"], "Solar.array", "unbound array")
        return np.load(watch.resolve(name+".npy"), allow_pickle=False, mmap_mode="r")
    for key, values in common.items():
        require(np.array_equal(values, array(key), equal_nan=True), "GVI.observers", "Solar/B2 differ: "+key)
    for key, values in (("roi", a["roi"]), ("centres_xy", a["centres_xy"])):
        require(np.array_equal(values, array(key)), "GVI.geography", "Solar/T5 differ: "+key)
    # Geometry-only independent B2 check with the exact settings used by calculate.
    index, valid, origin = b2.observers(saved["current"], height=b2.SETTINGS["view_point_height"])
    require(np.array_equal(index, common["observer_index"]) and np.array_equal(valid, common["observer_valid"])
            and np.array_equal(origin, common["origin_class_current"]), "GVI.observers", "B2 settings/diagnostic mismatch")
    saved.update(observer=common, solar_record=record, solar_reduction=array("reduction"), solar_watch=watch)
    reference = record["outputs"]["evaluation_current.tif"]["grid"]
    target = env.GridSpec(tuple(reference["bounds"]))
    with rasterio.open(watch.resolve("evaluation_current.tif")) as ds:
        require(ds.crs.to_epsg() == 6677 and ds.transform == target.transform
                and ds.shape == (target.height, target.width) and ds.nodata == env.NODATA,
                "Solar.raster", "saved Solar EPSG:6677 grid differs from manifest")
    return saved


def implementation_identity():
    return dict(solar.implementation_identity(), gvi_adapter_sha256=env.sha256(__file__), b2_sha256=env.sha256(b2.__file__))


def synthetic_probe(grid):
    current = np.zeros((5, 7, 6), dtype="int8")
    current[..., 0] = 1
    current[0, 0, 1:4] = -3
    current[3, 2:5, 2:4] = -2
    current.flags.writeable = False
    valid = b2.observers(current)[1]
    first, t1 = b2.calculate(current, grid, THREADS)
    second, t2 = b2.calculate(current, grid, THREADS)
    b2.check_result(first, valid)
    b2.check_result(second, valid)
    require(np.array_equal(first, second, equal_nan=True) and np.any(first[valid] > 0), "probe", "synthetic target/repeat failed")
    absent = np.where(current == -2, 0, current).astype("int8")
    zero, t0 = b2.calculate(absent, grid, THREADS)
    b2.check_result(zero, valid)
    require(not np.any(absent == -2) and np.all(zero[valid] == 0), "probe.no_tree", "TREE-free public result is not zero")
    return dict(shape=list(current.shape), current_timings=[t1, t2], no_canopy_timing=t0,
        repeat_equal=True, no_canopy_public_zero=True, current=b2.distribution(first[valid]),
        no_canopy=b2.distribution(zero[valid]), first_call_scope="Includes JIT/cache load/map/plot; first-minus-repeat is not pure compilation time")


def statistics(values, valid, roi, origin):
    result = {}
    for name, region in dict(domain=np.ones(roi.shape, bool), evaluation=roi, outside_evaluation=~roi).items():
        use = region & valid
        result[name] = dict(cells=int(region.sum()), excluded=int((region & ~valid).sum()),
            values=b2.distribution(values[use]), positive_fraction=float((values[use] > 0).mean()) if use.any() else None,
            AIR=b2.distribution(values[use & (origin == 0)]), TREE=b2.distribution(values[use & (origin == -2)]))
    return result


def export_raster(path, values, xy, roi, reference, *, kind):
    grid = env.GridSpec(tuple(reference["grid"]["bounds"]))
    require(json.loads(json.dumps(grid.metadata())) == reference["grid"] and values.shape == roi.shape and roi.dtype == bool
            and xy.shape == roi.shape+(2,) and int(roi.sum()) == grid.width*grid.height,
            "GVI.export", "Solar target grid/ROI differs")
    points = xy[roi]
    rows, cols = (np.asarray(v) for v in rowcol(grid.transform, points[:, 0], points[:, 1]))
    require(((rows >= 0) & (rows < grid.height) & (cols >= 0) & (cols < grid.width)).all()
            and np.unique(rows*grid.width+cols).size == points.shape[0], "GVI.registration", "outside/duplicate/missing cells")
    gx, gy = grid.centres()
    error = np.linalg.norm(points-np.column_stack((gx[rows, cols], gy[rows, cols])), axis=1)
    require(np.isfinite(error).all() and error.max() <= solar.shadow.REGISTRATION_TOLERANCE_M,
            "GVI.registration", "actual centre exceeds .01m")
    floating = kind == "GVI"
    nodata = env.NODATA if floating else 255
    data = np.full((grid.height, grid.width), nodata, dtype="float64" if floating else "uint8")
    data[rows, cols] = np.where(np.isfinite(values[roi]), values[roi], nodata)
    with rasterio.open(path, "w", driver="GTiff", count=1, width=grid.width, height=grid.height,
                       dtype=data.dtype, crs=6677, transform=grid.transform, nodata=nodata, compress="deflate") as ds:
        ds.write(data, 1)
        if floating: ds.set_band_unit(1, "1")
        ds.update_tags(OUEM_SCOPE="EXPERIMENTAL_GVI_NOT_ACCEPTANCE", metric=b2.METRIC if floating else kind,
                       mapping="actual saved EPSG:6677 centres -> inverse-affine floor; same Solar registration",
                       classes="continuous dimensionless 0..1" if floating else
                       ("0 excluded; 1 AIR; 2 TREE" if kind == "origin_class" else "0 excluded; 1 valid"))
    with rasterio.open(path) as ds:
        require(ds.crs.to_epsg() == 6677 and ds.transform == grid.transform and ds.shape == data.shape
                and ds.dtypes == (str(data.dtype),) and ds.nodata == nodata and tuple(ds.bounds) == grid.bounds
                and np.array_equal(ds.read(1), data) and np.array_equal(ds.read_masks(1) > 0, data != nodata)
                and ds.units == (("1",) if floating else (None,)), "GVI.TIFF", "readback grid/value/mask/unit mismatch")
        checks = []
        for previous in reference["coordinate_checks"]:
            r, c = previous["row"], previous["col"]
            k = int(np.flatnonzero((rows == r) & (cols == c))[0])
            require(list(ds.xy(r, c)) == previous["pixel_centre"] and points[k].tolist() == previous["actual_centre"],
                    "GVI.coordinates", "Solar/GVI corner registration differs")
            checks.append(dict(row=r, col=c, pixel_centre=list(ds.xy(r, c)), actual_centre=points[k].tolist(), error_m=float(error[k])))
    return dict(sha256=env.sha256(path), bytes=path.stat().st_size, grid=grid.metadata(), nodata=nodata,
                max_registration_error_m=float(error.max()), coordinate_checks=checks, dtype=str(data.dtype))


def run(pair_run, solar_run, source_run, output_dir, *, benchmark=False, benchmark_report=None):
    out = Path(output_dir).resolve()
    require(not out.exists(), "output", "new run required")
    saved = load_inputs(pair_run, solar_run, source_run)
    for watch in saved["watches"].values():
        require(not out.is_relative_to(watch.root) and not watch.root.is_relative_to(out), "output", "output overlaps input bundle")
    out.mkdir(parents=True)
    report = dict(profile="ouem-candidate-b-real-gvi/v0.1", status="BLOCKED", terrain_integration_ready=False,
        scientific_validation="NOT_VERIFIED", formal_acceptance="NOT_VERIFIED", metric=b2.METRIC, settings=settings(), outputs={})
    try:
        engine, identity = voxcity_provenance(), implementation_identity()
        require(engine["verified"], "engine", "fixed VoxCity required")
        valid, origin = saved["observer"]["observer_valid"], saved["observer"]["origin_class_current"]
        roi, xy = saved["arrays"]["roi"], saved["arrays"]["centres_xy"]
        report.update(engine=engine, implementation=identity,
            pair_manifest_sha256=solar.C2_SHA, solar_manifest_sha256=SOLAR_SHA,
            inputs={key:w.identities for key, w in saved["watches"].items()},
            input_roots={key:str(w.root) for key, w in saved["watches"].items()},
            observer_agreement="PASS: exact C3 index/valid/XYZ/origin class/centres/ROI; no relocation in TREE")
        if benchmark:
            report["synthetic_probe"] = synthetic_probe(saved["grid"])
            u0, u1, v0, v1 = b2.roi_window(roi)
            u1, v1 = min(u1, u0+16), min(v1, v0+16)
            subset = saved["current"][u0:u1, v0:v1, :].copy()
            subset.flags.writeable = False
            subset_valid = b2.observers(subset)[1]
            require(subset_valid.any(), "benchmark", "subset has no valid observers")
            timings, results = [], []
            for _ in range(2):
                result, timing = b2.calculate(subset, saved["grid"], THREADS)
                b2.check_result(result, subset_valid)
                timings.append(timing)
                results.append(result)
            require(np.array_equal(*results, equal_nan=True), "benchmark.repeat", "subset repeat differs")
            ratio = valid.sum()/subset_valid.sum()
            diameter = max(saved["current"].shape[:2])/min(subset.shape[:2])
            estimated = timings[0]["wall_seconds"] + timings[1]["wall_seconds"]*ratio*diameter
            all_timings = report["synthetic_probe"]["current_timings"]+[report["synthetic_probe"]["no_canopy_timing"]]+timings
            peak = max(t["sampled_peak_working_set_bytes"] for t in all_timings)
            feasible = estimated <= LIMIT_SECONDS and peak < LIMIT_BYTES
            report.update(status="BENCHMARK_COMPLETED", feasible=bool(feasible),
                subset_uv=[u0, u1, v0, v1], subset_shape=list(subset.shape), subset_observers=int(subset_valid.sum()),
                subset_timings=timings, estimated_full_seconds=float(estimated), sampled_peak_bytes=peak,
                feasibility_limits=dict(estimated_seconds_per_pass=LIMIT_SECONDS, working_set_bytes=LIMIT_BYTES),
                estimate="B2 rule: first subset wall + repeat wall * full/subset observers * XY diameter ratio; estimate, not a bound",
                scope="Cropped rays are a cost probe only, not full-domain GVI; settings/resolution are unchanged")
            report["outputs"]["subset_gvi.npy"] = c2.write_array(out, "subset_gvi", results[0])
        else:
            require(benchmark_report is not None, "benchmark", "matching feasibility receipt required before full domain")
            receipt_path = Path(benchmark_report).resolve(strict=True)
            receipt_watch = Watch(receipt_path.parent)
            receipt = receipt_watch.capture("receipt", receipt_path.name, json_data=True)
            require(receipt["status"] == "BENCHMARK_COMPLETED" and receipt["feasible"]
                    and receipt["settings"] == settings() and receipt["solar_manifest_sha256"] == SOLAR_SHA
                    and receipt["pair_manifest_sha256"] == solar.C2_SHA
                    and receipt["implementation"] == json.loads(json.dumps(identity))
                    and receipt["inputs"] == json.loads(json.dumps(report["inputs"]))
                    and receipt["synthetic_probe"]["no_canopy_public_zero"] is True,
                    "benchmark", "receipt does not bind these inputs/settings/implementation")
            require(not np.any(saved["absent"] == -2), "NoCanopy", "TREE-free mathematical control required")
            first, timing1 = b2.calculate(saved["current"], saved["grid"], THREADS)
            b2.check_result(first, valid)
            report["full_timings"] = [timing1]
            report["outputs"]["gvi.npy"] = c2.write_array(out, "gvi", first)
            require(timing1["wall_seconds"] <= LIMIT_SECONDS and timing1["sampled_peak_working_set_bytes"] < LIMIT_BYTES,
                    "GVI.load", "full pass exceeded feasibility limits; stop before repeating")
            second, timing2 = b2.calculate(saved["current"], saved["grid"], THREADS)
            b2.check_result(second, valid)
            require(np.array_equal(first, second, equal_nan=True), "GVI.repeat", "two full-domain arrays differ")
            u0, u1, v0, v1 = b2.roi_window(roi)
            derived = np.where(valid, 0., np.nan)
            data = dict(repeat_gvi=second, evaluation_gvi=first[u0:u1, v0:v1],
                no_canopy_theoretical_zero=derived, observer_valid=valid, observer_origin_class=origin,
                observer_index=saved["observer"]["observer_index"], observer_xyz=saved["observer"]["observer_xyz"],
                roi=roi, centres_xy=xy)
            for name, values in data.items():
                report["outputs"][name+".npy"] = c2.write_array(out, name, values)
            reference = saved["solar_record"]["outputs"]["evaluation_current.tif"]
            codes = np.where(valid, np.where(origin == -2, 2, 1), 0).astype("uint8")
            for name, values, kind in (("gvi", first, "GVI"), ("observer_valid", valid.astype("uint8"), "validity"),
                                        ("observer_origin_class", codes, "origin_class")):
                report["outputs"]["evaluation_"+name+".tif"] = export_raster(out/("evaluation_"+name+".tif"), values, xy, roi, reference, kind=kind)
            receipt_watch.unchanged()
            report.update(status="COMPLETED", full_timings=[timing1, timing2], full_repeat_equal=True,
                statistics=statistics(first, valid, roi, origin), shared_shape=list(saved["current"].shape),
                observer_encoding=dict(raw_NPY="0 AIR; -2 TREE; 127 excluded (use validity mask)",
                    origin_TIFF="0 excluded; 1 AIR; 2 TREE", validity_TIFF="0 excluded; 1 valid"),
                no_canopy=dict(full_public_api_calculated=False, output="no_canopy_theoretical_zero.npy",
                    basis="inclusion target is only -2; without TREE every target-hit contribution is zero; invalid observers remain NaN",
                    synthetic_public_api_evidence=receipt["synthetic_probe"]),
                benchmark=dict(sha256=env.sha256(receipt_path), receipt=receipt),
                solar_alignment="PASS: same EPSG:6677 registered cells and saved observations; Solar read-only, not recalculated",
                interpretation="Weighted first-TREE view index, not measured green-pixel fraction. TREE-origin statistics are separate. No Solar/GVI correlation or causality validation.")
        for watch in saved["watches"].values():
            watch.unchanged()
        require(settings() == report["settings"] and identity == implementation_identity(), "implementation", "settings/code/environment changed")
        report["input_immutability"] = "PASS"
    except Exception as exc:
        report.update(status="BLOCKED", error=f"{type(exc).__name__}: {exc}")
    try:
        c2.publish(out, report)
    except Exception as exc:
        report.update(status="BLOCKED", error=f"Publication failed: {exc}")
        with (out/"failure.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pair-run", "solar-run", "source-run", "output-dir"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--benchmark-report", type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key:report[key] for key in ("status", "error", "feasible", "estimated_full_seconds", "statistics", "full_timings") if key in report}))
    return int(report["status"] not in ("COMPLETED", "BENCHMARK_COMPLETED") or report.get("feasible") is False)


if __name__ == "__main__":
    raise SystemExit(main())
