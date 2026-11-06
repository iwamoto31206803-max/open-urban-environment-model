"""STEP 2-C3: immutable saved canopy pair -> common-observer direct solar PoC."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import rowcol

from ouem import candidate_b_canopy_run as c2
from ouem import candidate_b_shadow as shadow
from ouem import height_envelope as env
from ouem.b2_gvi import observers  # geometry diagnostic only; no GVI calculation
from ouem.compatibility_probe import load_candidate
from ouem.consumers.source_h_standard import Watch
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_solar import direct_solar_at_saved_grid
from ouem.real_komae_source_h import distribution

C2_SHA = "1160efdb4a8e689f2b5cb0baf8c6f829d83d88463e8a9e4de332d86392692b45"
SETTINGS = dict(azimuth_true_deg=180., elevation_deg=45., dni_W_m2=800.,
    observer_height_request_m=1.5, tree_k=.6, tree_lad=1., include_building_roofs=False,
    hit_values=[0], inclusion_mode=False, irradiance_tolerance_W_m2=1e-9,
    units="W/m2", metric="horizontal direct irradiance; no diffuse or temporal integration")


def common_observers(current, absent, ids, xy, d0):
    require(current.shape == absent.shape and current.dtype == absent.dtype == np.int8
            and current.shape[:2] == ids.shape and xy.shape == ids.shape+(2,)
            and np.isfinite(xy).all() and np.isfinite(d0), "solar.grid", "inconsistent saved pair/grid")
    require(set(map(int, np.unique(current))) <= {-3, -2, -1, 0, 1}
            and not np.any(absent == -2) and np.array_equal(np.where(current == -2, 0, current), absent)
            and np.array_equal(np.any(absent == -3, axis=2), ids > 0), "solar.pair", "non-TREE or owner occupancy differs")
    index, valid, origin_current = observers(current, height=1.5)
    other_index, other_valid, origin_absent = observers(absent, height=1.5)
    require(np.array_equal(index, other_index) and np.array_equal(valid, other_valid)
            and np.array_equal(valid, ids == 0), "solar.observers", "canopy moved/excluded a common observer")
    surface = np.argmax(absent == 1, axis=2)
    require(np.array_equal(index[valid], (surface+2)[valid]), "solar.observers", "surface/observer convention differs")
    z = np.where(valid, d0+index+.5, np.nan)
    xyz = np.concatenate((xy, z[..., None]), axis=2)
    return dict(observer_index=index, observer_valid=valid, observer_xyz=xyz, surface_index=surface,
                origin_class_current=origin_current, origin_class_no_canopy=origin_absent)


def statistics(now, absent, valid, region):
    use = valid & region
    delta = (absent-now)[use]
    tol = SETTINGS["irradiance_tolerance_W_m2"]
    return dict(cells=int(region.sum()), observers=int(use.sum()), excluded=int((region & ~valid).sum()),
        current=distribution(now[use]), no_canopy=distribution(absent[use]), reduction=distribution(delta),
        mean_current_W_m2=float(now[use].mean()) if use.any() else None,
        mean_no_canopy_W_m2=float(absent[use].mean()) if use.any() else None,
        mean_reduction_W_m2=float(delta.mean()) if use.any() else None,
        reduction_cells=int((delta > tol).sum()), reduction_fraction=float((delta > tol).mean()) if use.any() else None)


def validate_solar(now, absent, valid):
    tol = SETTINGS["irradiance_tolerance_W_m2"]
    baseline = SETTINGS["dni_W_m2"]*np.sin(np.deg2rad(SETTINGS["elevation_deg"]))
    for values in (now, absent):
        require(values.shape == valid.shape and np.array_equal(np.isfinite(values), valid)
                and np.isnan(values[~valid]).all(), "solar.mask", "invalid/NaN observer support differs")
        require((values[valid] >= 0).all() and (values[valid] <= baseline+tol).all(),
                "solar.range", "negative or above-unobstructed irradiance")
    reduction = absent-now
    increase = reduction[valid] < 0
    significant = reduction[valid] < -tol
    qa = dict(tolerance_W_m2=tol, flat_horizontal_W_m2=float(baseline),
        negative_reduction_cells=int(increase.sum()), beyond_tolerance_cells=int(significant.sum()),
        maximum_increase_W_m2=float(max(0., -reduction[valid].min())) if valid.any() else 0.)
    require(not significant.any(), "solar.sign", "canopy increased irradiance beyond tolerance: "+json.dumps(qa))
    return reduction, qa


def calculate_pair(current, absent, a, grid, high, low, xy, d0):
    observer = common_observers(current, absent, a["building_ids"], xy, d0)
    before = {key: value.copy() for key, value in a.items() if key != "building_segments"}
    segments = json.dumps(a["building_segments"].tolist(), allow_nan=False)
    cases_before = [v.copy() for v in (current, absent, high, low)]
    result = [direct_solar_at_saved_grid(vox, a, grid, high, low, azimuth=SETTINGS["azimuth_true_deg"],
              elevation=SETTINGS["elevation_deg"], dni=SETTINGS["dni_W_m2"])
              for vox in (current, absent)]
    for key, value in before.items():
        require(np.array_equal(value, a[key]), "solar.inputs", "API changed array: "+key)
    require(segments == json.dumps(a["building_segments"].tolist(), allow_nan=False)
            and all(np.array_equal(old, new) for old, new in zip(cases_before, (current, absent, high, low))),
            "solar.inputs", "API changed saved cases/canopy/segments")
    now, no_canopy = result
    reduction, qa = validate_solar(now, no_canopy, observer["observer_valid"])
    if not np.any(current == -2):
        require(np.array_equal(now, no_canopy, equal_nan=True), "solar.no_tree", "identical no-TREE cases differ")
    return dict(current=now, no_canopy=no_canopy, reduction=reduction, **observer), qa


def export_raster(path, values, xy, roi, bounds, *, mask=False, reduction=False):
    grid = env.GridSpec(tuple(bounds))
    require(values.shape == roi.shape and xy.shape == roi.shape+(2,) and roi.dtype == bool
            and int(roi.sum()) == grid.height*grid.width, "solar.export", "ROI/shape must fill target grid")
    points = xy[roi]
    rows, cols = (np.asarray(v) for v in rowcol(grid.transform, points[:, 0], points[:, 1]))
    require(((rows >= 0) & (rows < grid.height) & (cols >= 0) & (cols < grid.width)).all()
            and np.unique(rows*grid.width+cols).size == len(points), "solar.registration", "outside/duplicate/missing registration")
    gx, gy = grid.centres()
    errors = np.linalg.norm(points-np.column_stack((gx[rows, cols], gy[rows, cols])), axis=1)
    require(np.isfinite(errors).all() and errors.max() <= shadow.REGISTRATION_TOLERANCE_M,
            "solar.registration", "actual centre differs by more than .01m")
    nodata = 255 if mask else env.NODATA
    data = np.full((grid.height, grid.width), nodata, dtype="uint8" if mask else "float64")
    data[rows, cols] = np.where(np.isfinite(values[roi]), values[roi], nodata)
    with rasterio.open(path, "w", driver="GTiff", count=1, width=grid.width, height=grid.height,
                       dtype=data.dtype, crs=6677, transform=grid.transform, nodata=nodata, compress="deflate") as ds:
        ds.write(data, 1)
        if not mask:
            ds.set_band_unit(1, "W/m2")
        ds.update_tags(OUEM_SCOPE="EXPERIMENTAL_SOLAR_NOT_ACCEPTANCE", source_mapping="actual EPSG:6677 centres -> inverse-affine floor",
                       quantity="0 excluded building; 1 observer in AIR; 2 observer in TREE" if mask else
                       ("canopy solar reduction (No-Canopy - Current) W/m2" if reduction else "horizontal direct solar irradiance W/m2"))
    with rasterio.open(path) as ds:
        require(ds.crs.to_epsg() == 6677 and ds.transform == grid.transform and ds.shape == data.shape
                and ds.dtypes == (str(data.dtype),) and ds.nodata == nodata and tuple(ds.bounds) == tuple(bounds)
                and np.array_equal(ds.read(1), data) and np.array_equal(ds.read_masks(1) > 0, data != nodata)
                and ds.units == ((None,) if mask else ("W/m2",)), "solar.TIFF", "saved grid/data/mask/units differs")
        checks = []
        for r, c in ((0, 0), (0, grid.width-1), (grid.height-1, 0), (grid.height-1, grid.width-1), (grid.height//2, grid.width//2)):
            centre = ds.xy(r, c)
            require(centre == (gx[r, c], gy[r, c]), "solar.coordinates", "corner/centre mismatch")
            k = int(np.flatnonzero((rows == r) & (cols == c))[0])
            checks.append(dict(row=r, col=c, pixel_centre=list(centre), actual_centre=points[k].tolist(), error_m=float(errors[k])))
    return dict(sha256=env.sha256(path), bytes=path.stat().st_size, grid=grid.metadata(), nodata=nodata,
                max_registration_error_m=float(errors.max()), coordinate_checks=checks, dtype=str(data.dtype))


def load_inputs(pair_run, source_run, step2a_run):
    pair, source, prior = [Path(p).resolve(strict=True) for p in (pair_run, source_run, step2a_run)]
    watch = Watch(pair)
    record = watch.capture("manifest", "manifest.json", C2_SHA, json_data=True)
    require(record["status"] == "COMPLETED" and record["profile"] == "ouem-candidate-b-real-canopy-pair/v0.1"
            and record["terrain_integration_ready"] is False, "C2", "completed experimental pair required")
    for name, ref in record["outputs"].items():
        watch.capture(name, name, ref["sha256"], ref["bytes"])
    watches = {"pair": watch}
    for label, refs in record["inputs"].items():
        upstream = watches[label] = Watch(Path(record["input_roots"][label]))
        for key, ref in refs.items():
            upstream.capture(key, ref["path"], ref["sha256"], ref["size_bytes"])
    require(watches["t5"].root == source and watches["step2a"].root == prior,
            "inputs.roots", "explicit T5/STEP2A paths differ from C2 provenance")
    arrays, metadata, probe, t5, model_watch = load_candidate(source, shadow.T5_SHA, observer_height=1.5)
    watches["model"] = model_watch
    previous = env.read_json(prior/"report.json")
    require(watches["step2a"].identities["report"]["sha256"] == c2.STEP2A_SHA,
            "STEP2A", "baseline report identity differs")
    def array(name):
        require(name+".npy" in record["outputs"], "C2.array", "unbound saved array")
        return np.load(watch.resolve(name+".npy"), mmap_mode="r", allow_pickle=False)
    current, absent = array("current"), array("no_canopy")
    require(np.array_equal(current == -2, array("tree_mask"))
            and absent.shape[:2] == arrays["voxels"].shape[:2] and absent.shape[2] >= arrays["voxels"].shape[2]
            and np.array_equal(absent[..., :arrays["voxels"].shape[2]], arrays["voxels"])
            and not absent[..., arrays["voxels"].shape[2]:].any()
            and np.array_equal(array("centres_xy"), arrays["centres_xy"])
            and np.array_equal(array("evaluation_mask"), arrays["roi"]), "C2.base", "saved pair/grid differs from T5")
    segments = c2.restore_segments(env.read_json(model_watch.resolve("t5-3/segments.json")), arrays["ids"].shape, arrays["ids"])
    height = np.load(model_watch.resolve("t5-2/building_height.npy"), allow_pickle=False, mmap_mode="r")
    direction, settings = shadow.sun_direction(metadata)
    grid = dict(axis0_true_azimuth_deg=settings["axis0_true_azimuth_deg"],
                rectangle_vertices_lonlat=t5["grid"]["rectangle_lonlat"])
    require(previous["settings"]["azimuth_true_deg"] == 180. and previous["settings"]["elevation_deg"] == 45.,
            "STEP2A.sun", "binary baseline sun differs")
    a = dict(building_ids=arrays["ids"], building_heights=height, building_segments=segments,
             effective_dem=arrays["ground_abs"]-metadata["d0_effective_abs_m"])
    return dict(current=current, absent=absent, a=a, grid=grid, high=array("B/relative_top"), low=array("B/relative_bottom"),
        arrays=arrays, metadata=metadata, probe=probe, direction=list(direction), watches=watches, record=record,
        baseline=np.load(watches["step2a"].resolve("domain_classes.npy"), allow_pickle=False, mmap_mode="r"))


def implementation_identity():
    from numba import get_num_threads
    return dict(c2.implementation_identity(), solar_adapter_sha256=env.sha256(__file__),
        numba_version=version("numba"), numba_threads=get_num_threads(),
        solar_helper_sha256=env.sha256(direct_solar_at_saved_grid.__code__.co_filename),
        observers_sha256=env.sha256(observers.__code__.co_filename), shadow_sha256=env.sha256(shadow.__file__))


def run(pair_run, source_run, step2a_run, output_dir):
    out = Path(output_dir).resolve()
    require(not out.exists(), "output", "new run required")
    saved = load_inputs(pair_run, source_run, step2a_run)  # audit before any Solar call or output
    for watch in saved["watches"].values():
        require(not out.is_relative_to(watch.root) and not watch.root.is_relative_to(out), "output", "output overlaps protected inputs")
    out.mkdir(parents=True)
    report = dict(profile="ouem-candidate-b-real-solar/v0.1", status="BLOCKED", terrain_integration_ready=False,
                  scientific_validation="NOT_VERIFIED", formal_acceptance="NOT_VERIFIED", outputs={})
    try:
        engine = voxcity_provenance()
        require(engine["verified"], "engine", "pinned engine not verified")
        identity = implementation_identity()
        arrays, meta = saved["arrays"], saved["metadata"]
        result, qa = calculate_pair(saved["current"], saved["absent"], saved["a"], saved["grid"], saved["high"], saved["low"],
                                    arrays["centres_xy"], meta["d0_effective_abs_m"])
        valid = result["observer_valid"]
        roi = arrays["roi"]
        baseline = saved["baseline"]
        require(baseline.shape == valid.shape and np.array_equal(baseline != 255, valid)
                and np.isin(baseline, [0, 1, 255]).all(), "baseline", "STEP2A observer support differs")
        no_canopy_shadow = result["no_canopy"] <= SETTINGS["irradiance_tolerance_W_m2"]
        require(np.all(no_canopy_shadow[valid] | np.isclose(result["no_canopy"][valid], qa["flat_horizontal_W_m2"],
                atol=SETTINGS["irradiance_tolerance_W_m2"], rtol=0)), "control", "TREE-free control is not opaque-or-unobstructed")
        mask = np.where(valid, np.where(result["origin_class_current"] == -2, 2, 1), 0).astype("uint8")
        result.update(roi=roi, centres_xy=arrays["centres_xy"], observer_mask=mask)
        for name, values in result.items():
            report["outputs"][name+".npy"] = c2.write_array(out, name, values)
        for name in ("current", "no_canopy", "reduction", "observer_mask"):
            report["outputs"]["evaluation_"+name+".tif"] = export_raster(out/("evaluation_"+name+".tif"),
                result[name], arrays["centres_xy"], roi, meta["evaluation_bounds"], mask=name == "observer_mask", reduction=name == "reduction")
        statistics_by_scope = {name:statistics(result["current"], result["no_canopy"], valid, region)
            for name, region in dict(domain=np.ones(roi.shape, bool), evaluation=roi, outside_evaluation=~roi).items()}
        comparison = {name:dict(observers=int((valid & region).sum()),
            step2a_shadow=int(((baseline == 0) & region).sum()), solar_no_canopy_zero=int((no_canopy_shadow & valid & region).sum()),
            step2a_shadow_to_solar_lit=int(((baseline == 0) & ~no_canopy_shadow & valid & region).sum()),
            step2a_lit_to_solar_shadow=int(((baseline == 1) & no_canopy_shadow & valid & region).sum()),
            different=int(((no_canopy_shadow != (baseline == 0)) & valid & region).sum()))
            for name, region in dict(domain=np.ones(roi.shape, bool), evaluation=roi).items()}
        for watch in saved["watches"].values():
            watch.unchanged()
        require(identity == implementation_identity(), "implementation", "code/environment changed during calculation")
        report.update(status="COMPLETED", engine=engine, implementation=identity, settings=SETTINGS,
            api="get_direct_solar_irradiance_map via B1 direct_solar_at_saved_grid; exactly 2 full-domain calls",
            grid=dict(saved["grid"], geography=meta, shared_shape=list(saved["current"].shape), direction_uv_up=saved["direction"]),
            observer_qa=dict(common_count=int(valid.sum()), excluded_buildings=int((~valid).sum()),
                inside_TREE=int(((mask == 2) & valid).sum()), inside_TREE_in_roi=int(((mask == 2) & roi).sum()),
                index_range=[int(result["observer_index"][valid].min()), int(result["observer_index"][valid].max())],
                absolute_Z_m=distribution(result["observer_xyz"][..., 2][valid]),
                rule="first walkable AIR/TREE transition + int(1.5/1m); centre Z=D0+k+.5; no movement inside TREE"),
            solar_qa=qa, statistics=statistics_by_scope, step2a_comparison=comparison,
            comparison_limit="STEP2A: requested height 0m, binary, hit_values=(0,-1,1); here: 1.5m, W/m2, only AIR passes except attenuating TREE. Equality is not required; no binary shadow used as canopy attenuation.",
            limitations="Uncalibrated k/LAD/CR and canopy presence; conditional vertical datum; voxel geometry and external-domain occluders/field irradiance accuracy NOT_VERIFIED",
            input_immutability="PASS", inputs={key:w.identities for key, w in saved["watches"].items()},
            input_roots={key:str(w.root) for key, w in saved["watches"].items()})
        report["reproducibility_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, allow_nan=False).encode()).hexdigest()
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
    for name in ("pair-run", "source-run", "step2a-run", "output-dir"):
        parser.add_argument("--"+name, type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key:report[key] for key in ("status", "error", "statistics", "observer_qa", "step2a_comparison") if key in report}))
    return int(report["status"] != "COMPLETED")


if __name__ == "__main__":
    raise SystemExit(main())
