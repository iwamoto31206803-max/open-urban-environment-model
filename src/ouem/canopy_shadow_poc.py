"""Exploratory, building-free Height Envelope -> pinned VoxCity CPU direct solar.

Not a Standard Canopy implementation. Inputs and accepted algorithms are immutable.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Geod, Transformer
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

from ouem.height_envelope import validate_sources
from ouem.komae_integration import voxcity_provenance

ROI = (-23320, -40760, -23256, -40696)
DOMAIN = (-23352, -40792, -23224, -40664)


class ShadowBlocked(ValueError):
    """A prerequisite or independent QA failed."""


def require(condition, message):
    if not condition:
        raise ShadowBlocked(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write(path, record):
    Path(path).write_text(json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def relative_grids(top, bottom, dem, state):
    """Strict absolute metre boundary; zero-depth exclusion is experimental only."""
    top, bottom, dem = (np.asarray(a, dtype=np.float64) for a in (top, bottom, dem))
    require(top.ndim == 2 and top.shape == bottom.shape == dem.shape == state.shape,
            "grid shape mismatch")
    require(np.all(state == 1), "missing/invalid/outside cells: no filling")
    require(all(np.isfinite(a).all() for a in (top, bottom, dem)), "nonfinite height")
    require(np.all((dem <= bottom) & (bottom <= top)), "absolute envelope/DEM mismatch")
    active = top > bottom
    return tuple(np.ascontiguousarray(np.flipud(a)) for a in
                 (dem, np.where(active, top-dem, 0), np.where(active, bottom-dem, 0)))


def grid_north(bounds):
    """Clockwise true-north azimuth of projected +Y, not a guessed EPSG rotation."""
    x, y = (bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2
    tr = Transformer.from_crs(6677, 4326, always_xy=True)
    lon, lat = tr.transform(x, y)
    ln, lt = tr.transform(x, y+10)
    az, _, _ = Geod(ellps="WGS84").inv(lon, lat, ln, lt)
    return float(az), float(lon), float(lat)


@dataclass
class Pair:
    a: object
    b: object
    qa: dict


def build_pair(dem, top, bottom, bounds, rotation):
    """South-up relative arrays -> real engine; independently audit every voxel."""
    from voxcity.generator.voxelizer import Voxelizer
    from voxcity.models import (VoxCity, VoxelGrid, GridMetadata, BuildingGrid,
                                DemGrid, LandCoverGrid, CanopyGrid)
    dem, top, bottom = (np.asarray(a, dtype=np.float64) for a in (dem, top, bottom))
    require(dem.ndim == 2 and dem.shape == top.shape == bottom.shape, "shape mismatch")
    require(all(np.isfinite(a).all() for a in (dem, top, bottom)), "nonfinite input")
    require(np.all((0 <= bottom) & (bottom <= top)), "relative height mismatch")
    zeros = np.zeros(dem.shape)
    ids = np.zeros(dem.shape, dtype=np.int64)
    cover = np.ones(dem.shape, dtype=np.int64)  # experimental common Bareland label
    segments = np.empty(dem.shape, dtype=object)
    for index in np.ndindex(dem.shape):
        segments[index] = []
    engine = Voxelizer(1.0, "Standard")
    a = engine.generate_combined(zeros, segments, ids, cover, dem, zeros, zeros, print_class_info=False)
    b = engine.generate_combined(zeros, segments, ids, cover, dem, top, bottom, print_class_info=False)
    original_nz = [a.shape[2], b.shape[2]]
    nz = max(original_nz)
    a, b = (np.pad(v, ((0, 0), (0, 0), (0, nz-v.shape[2]))) for v in (a, b))
    # Independent full expected arrays: scalar half-up arithmetic, including +1
    # surface layer and the engine's thin-crown expansion; no upstream helper.
    ea, eb = np.zeros_like(a), np.zeros_like(b)
    errors = []; expanded = 0
    d0 = float(dem.min())
    for i, j in np.ndindex(dem.shape):
        ground = int(float(np.float32(dem[i, j]-d0))+.5)+1
        ea[i, j, :ground] = -1
        ea[i, j, ground-1] = 1
        eb[i, j] = ea[i, j]
        if top[i, j] > 0:
            low = int(float(np.float32(bottom[i, j]))+.5)
            high = int(float(np.float32(top[i, j]))+.5)
            if low == high and low > 0:
                low -= 1; expanded += 1
            require(ground+high <= nz, "voxel allocation clips crown")
            eb[i, j, ground+low:ground+high] = -2
            if high > low:
                errors.append([d0+ground+low-(dem[i, j]+bottom[i, j]),
                               d0+ground+high-(dem[i, j]+top[i, j])])
    require(np.array_equal(a, ea) and np.array_equal(b, eb), "voxel geometry QA failed")
    require(np.array_equal(a == -1, b == -1) and np.array_equal(a == 1, b == 1), "terrain changed")
    require(not np.any(a == -2) and not np.any(b == -3), "unexpected classes")
    require(not np.any(top > 0) or np.any(b == -2), "canopy failed to voxelize")
    meta = GridMetadata("EPSG:6677", tuple(bounds), 1.0)
    def city(vox, hi, lo):
        return VoxCity(VoxelGrid(vox, meta), BuildingGrid(zeros.copy(), segments, ids.copy(), meta),
                       LandCoverGrid(cover.copy(), meta), DemGrid(dem.copy(), meta),
                       CanopyGrid(hi.copy(), meta, lo.copy()), {"rotation_angle": float(rotation)})
    err = np.array(errors) if errors else np.zeros((1, 2))
    qa = {"terrain_voxels_equal": True, "full_expected_voxel_arrays_equal": True,
          "original_z_lengths": original_nz, "common_shape": list(a.shape),
          "a_tree_voxels": int((a == -2).sum()), "b_tree_voxels": int((b == -2).sum()),
          "thin_crown_expanded_cells": expanded, "absolute_z_origin_m": d0,
          "bottom_face_error_m": [float(err[:, 0].min()), float(err[:, 0].max())],
          "top_face_error_m": [float(err[:, 1].min()), float(err[:, 1].max())],
          "face_convention": "D0+k; voxel centre D0+k+0.5; no offset correction"}
    return Pair(city(a, zeros, zeros), city(b, top, bottom), qa)


def irradiance(pair, azimuth, elevation, dni=800.0):
    from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
    require(np.isfinite([azimuth, elevation, dni]).all() and 0 < elevation <= 90 and dni > 0,
            "daytime positive DNI required")
    values = [get_direct_solar_irradiance_map(c, azimuth, elevation, dni, show_plot=False,
              tree_k=0.6, tree_lad=1.0, view_point_height=1.5, include_building_roofs=False)
              for c in (pair.a, pair.b)]
    require(np.array_equal(np.isfinite(values[0]), np.isfinite(values[1])), "A/B observer masks differ")
    return tuple(np.flipud(v).copy() for v in values)  # north-up outputs


def stats(a):
    v = a[np.isfinite(a)]
    require(v.size > 0, "no finite comparison cells")
    return {"count": int(v.size), "min": float(v.min()), "max": float(v.max()),
            "mean": float(v.mean()), "quantiles": dict(zip(["p0", "p5", "p25", "p50", "p75", "p95", "p100"],
             map(float, np.quantile(v, [0, .05, .25, .5, .75, .95, 1]))))}


def crop_pair(pair, bounds, margin=32):
    """Remove outside occluders without changing D0 or re-rounding any voxels."""
    from voxcity.models import GridMetadata
    meta = GridMetadata("EPSG:6677", tuple(bounds), 1.0)
    sl = np.s_[margin:-margin, margin:-margin]
    def crop(c):
        return replace(c, voxels=replace(c.voxels, classes=c.voxels.classes[sl].copy(), meta=meta),
            buildings=replace(c.buildings, heights=c.buildings.heights[sl].copy(),
                min_heights=c.buildings.min_heights[sl].copy(), ids=c.buildings.ids[sl].copy(), meta=meta),
            dem=replace(c.dem, elevation=c.dem.elevation[sl].copy(), meta=meta),
            land_cover=replace(c.land_cover, classes=c.land_cover.classes[sl].copy(), meta=meta),
            tree_canopy=replace(c.tree_canopy, top=c.tree_canopy.top[sl].copy(),
                bottom=c.tree_canopy.bottom[sl].copy(), meta=meta))
    return Pair(crop(pair.a), crop(pair.b), {"method": "crop audited halo voxels; identical D0 and z indices"})


def load_inputs(run, expected_manifest, reference, expected_reference):
    """Hash all recorded upstream files and reuse the existing semantic gate."""
    run, reference = Path(run), Path(reference)
    mp = run/"generated/height_envelope_manifest.json"
    require(digest(mp) == expected_manifest, "envelope manifest hash mismatch")
    m = json.loads(mp.read_text(encoding="utf-8"))
    require(m.get("schema") == "ouem-height-envelope-poc/v0.1" and m.get("status") == "COMPLETED", "incomplete envelope")
    require(m["cr_model"]["parameters"]["cr"] == .6 and m["sampling"] == {"chm": "nearest", "dem": "nearest"}, "unsupported input profile")
    protected = {str(mp.resolve()): digest(mp), str(reference.resolve()): digest(reference)}
    require(digest(reference) == expected_reference, "DEM reference hash mismatch")
    inputs = m["input_files"]
    for rec in inputs.values():
        require(digest(rec["path"]) == rec["sha256"], "upstream input hash mismatch")
        protected[str(Path(rec["path"]).resolve())] = rec["sha256"]
    validate_sources(*(inputs[k]["path"] for k in
        ("chm", "acquisition_record", "chm_evidence", "terrain", "terrain_manifest", "terrain_acceptance")))
    arrays = []
    expected_transform = from_origin(-23600, -40500, 1, 1)
    for name in ("canopy_top_z.tif", "canopy_bottom_z.tif", "height_envelope_state.tif"):
        p = run/"generated"/name
        require(digest(p) == m["outputs"][name]["sha256"], "output raster hash mismatch")
        protected[str(p.resolve())] = digest(p)
        with rasterio.open(p) as ds:
            require(ds.crs.to_epsg() == 6677 and ds.transform == expected_transform and ds.shape == (300, 400)
                    and ds.count == 1 and np.all(ds.read_masks(1) > 0), "input grid/mask mismatch")
            require(ds.nodata == (None if name.startswith("height") else -9999), "NoData mismatch")
            arrays.append(ds.read(1))
    with rasterio.open(reference) as ds:
        require(ds.crs.to_epsg() == 6677 and ds.transform == expected_transform and ds.shape == (300, 400)
                and ds.count == 1 and np.all(ds.read_masks(1) > 0), "reference grid/mask mismatch")
        ref = ds.read(1)
    with rasterio.open(inputs["terrain"]["path"]) as ds:
        xy = [(-23599.5+c, -40500.5-r) for r in range(300) for c in range(400)]
        samples = list(ds.sample(xy, masked=True))
        require(not any(np.ma.getmaskarray(v).any() for v in samples), "DEM sample missing")
        dem = np.array([v[0] for v in samples]).reshape(300, 400)
    require(np.array_equal(dem, ref), "DEM differs from Height Envelope generation samples")
    relative_grids(*arrays[:2], dem, arrays[2])  # full AOI validity before cropping
    return arrays, dem, protected


def window(bounds):
    w = from_bounds(*bounds, transform=from_origin(-23600, -40500, 1, 1))
    require(all(float(v).is_integer() for v in (w.row_off, w.col_off, w.height, w.width)), "unaligned bounds")
    return np.s_[int(w.row_off):int(w.row_off+w.height), int(w.col_off):int(w.col_off+w.width)]


def run_experiment(args):
    start = time.perf_counter()
    out = Path(args.output_dir)
    require(not out.exists(), "output directory must be new")
    require(not any(Path(args.envelope_run).resolve() == p or Path(args.envelope_run).resolve() in p.parents
                    for p in [out.resolve()]), "output overlaps input run")
    out.mkdir(parents=True)
    try:
        suite = ET.parse(args.fixture_report).getroot()
        suites = list(suite.iter("testsuite"))
        require(suites and sum(int(s.get("tests", "0")) for s in suites) >= 9
                and all(int(s.get("failures", "0")) == int(s.get("errors", "0")) == int(s.get("skipped", "0")) == 0 for s in suites), "fixture gate failed")
        (out/"fixture-results.xml").write_bytes(Path(args.fixture_report).read_bytes())
        pin = voxcity_provenance(); require(pin["verified"], "pinned VoxCity not established")
        arrays, dem, protected = load_inputs(args.envelope_run, args.expected_manifest_sha,
                                             args.dem_reference, args.expected_reference_sha)
        original = {str(p.resolve()): digest(p) for p in Path(args.envelope_run).rglob("*") if p.is_file()}
        protected.update(original)
        rotation, lon, lat = grid_north(ROI)
        from voxcity.simulator.solar.temporal import get_solar_positions_astral
        import pandas as pd
        from numba import set_num_threads
        set_num_threads(4)
        timestamp = pd.DatetimeIndex(["2026-06-21T12:00:00+09:00"])
        sun = get_solar_positions_astral(timestamp, lon, lat).iloc[0]
        az, el = float(sun.azimuth), float(sun.elevation)
        outputs = {}; pairs = {}
        sl = window(DOMAIN)
        d, hi, lo = relative_grids(arrays[0][sl], arrays[1][sl], dem[sl], arrays[2][sl])
        pairs["halo32"] = build_pair(d, hi, lo, DOMAIN, rotation)
        pairs["no_halo"] = crop_pair(pairs["halo32"], ROI)
        for label, pair in pairs.items():
            outputs[label] = irradiance(pair, az, el)
        a, b = (v[32:96, 32:96] for v in outputs["halo32"])
        finite = np.isfinite(a) & np.isfinite(b)
        require(finite.all(), "ROI observer masks incomplete")
        delta = b-a
        require(not np.any(delta[finite] > 0), "irradiance increase needs investigation")
        sl = window(DOMAIN)
        voxel_count = np.flipud((pairs["halo32"].b.voxels.classes == -2).sum(axis=2))
        # Conservative full-source ceiling + requested observer-height reference:
        # no canopy/terrain inside the recorded source AOI above max top+2 m.
        vertical_budget = float(max(float(arrays[0].max()), float(dem.max())) - float(dem.min()) + 2)
        reach = vertical_budget/np.tan(np.deg2rad(el))
        require(reach+2 < 32, "32m halo insufficient; choose a larger covered domain")
        yy, xx = np.indices((64, 64)); edge = np.minimum.reduce((yy, xx, 63-yy, 63-xx))
        delta_no_halo = outputs["no_halo"][1]-b
        boundary = {name: stats(delta_no_halo[mask]) for name, mask in
                    (("edge_8m", edge < 8), ("interior", edge >= 8))}
        np.savez_compressed(out/"comparison_arrays.npz", case_a=a, case_b=b, difference=delta,
                            canopy_voxel_count=voxel_count[32:96, 32:96], valid_mask=finite,
                            no_halo_b=outputs["no_halo"][1])
        np.savez_compressed(out/"voxels_local_only.npz", case_a=pairs["halo32"].a.voxels.classes,
                            case_b=pairs["halo32"].b.voxels.classes)
        plot_comparison(out/"comparison.png", a, b, delta, voxel_count[32:96, 32:96])
        require(all(digest(p) == h for p, h in protected.items()), "input changed during execution")
        from importlib.metadata import version
        report = {"status": "COMPLETED", "assessment": "CONDITIONAL", "scope": "instantaneous CPU direct irradiance only; not acceptance",
            "started_from_main": "6c211654dc3ef6320c7426bd68b5bc702cbca513",
            "time_jst": datetime.now().astimezone().isoformat(), "elapsed_seconds": time.perf_counter()-start,
            "environment": {"python": platform.python_version(), "packages": {n: version(n) for n in
                ("voxcity", "numpy", "rasterio", "numba", "astral", "pandas", "pyproj")}, "pin": pin,
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "git_status": subprocess.check_output(["git", "status", "--short"], text=True).strip(),
                "adapter_sha256": digest(__file__)},
            "fixture_report": {"path": str(Path(args.fixture_report).resolve()), "sha256": digest(args.fixture_report)},
            "inputs": protected, "roi": ROI, "domain": DOMAIN,
            "conditions": {"datetime": timestamp[0].isoformat(), "longitude": lon, "latitude": lat,
                "azimuth_deg": az, "elevation_deg": el, "rotation_clockwise_deg": rotation,
                "dni_w_m2": 800, "tree_k": .6, "tree_lad": 1, "view_point_height_m": 1.5,
                "observer": "surface transition z+int(1.5); ray starts +0.5 voxel centre",
                "land_cover": "constant experimental Bareland code 1", "buildings": "none", "threads": 4},
            "qa": {"dem_reference_equal": True, "inputs_unchanged": True, "observer_masks_equal": True,
                "roi_valid_cells": int(finite.sum()), "cases": {k: p.qa for k, p in pairs.items()},
                "halo_vertical_budget_m": vertical_budget, "halo_reach_bound_m": reach,
                "halo_margin_m": 32-reach-2, "no_halo_minus_halo_b": boundary,
                "rotation_range_deg": [grid_north((x,y,x+1,y+1))[0] for x,y in ((DOMAIN[0],DOMAIN[1]),(DOMAIN[2]-1,DOMAIN[3]-1))]},
            "statistics_w_m2": {"a": stats(a), "b": stats(b), "b_minus_a": stats(delta)},
            "decreased_cells": int((delta[finite] < 0).sum()), "decreased_fraction": float((delta[finite] < 0).mean()),
            "increased_cells": int((delta[finite] > 0).sum()),
            "outputs": {p.name: digest(p) for p in out.iterdir() if p.is_file()}}
        json_write(out/"run.json", report)
        return report
    except Exception as exc:
        json_write(out/"FAILED.json", {"status": "FAILED", "assessment": "BLOCKED", "error": str(exc),
                   "type": type(exc).__name__, "elapsed_seconds": time.perf_counter()-start})
        raise


def plot_comparison(path, a, b, delta, counts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(10, 9), constrained_layout=True)
    for ax, data, title, cmap, lo, hi in zip(axes.flat, (a,b,delta,counts),
        ("A: Terrain only", "B: Terrain + canopy", "B - A: direct irradiance", "Canopy voxels per column"),
        ("magma","magma","RdBu_r","viridis"), (0,0,float(delta.min()),0),
        (800,800,0,float(counts.max()))):
        im = ax.imshow(data, extent=(ROI[0],ROI[2],ROI[1],ROI[3]), origin="upper", cmap=cmap, vmin=lo, vmax=hi)
        ax.set_title(title); ax.set_xlabel("EPSG:6677 easting (m)"); ax.set_ylabel("northing (m)")
        fig.colorbar(im, ax=ax, label="voxels" if data is counts else "W/m²")
    fig.suptitle("Exploratory PoC | 2026-06-21 12:00 JST | CR=0.60, k=0.6, LAD=1\nNot Standard Canopy acceptance or scientific accuracy validation", fontsize=10)
    fig.savefig(path, dpi=150); plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("envelope-run", "expected-manifest-sha", "dem-reference", "expected-reference-sha", "fixture-report", "output-dir"):
        p.add_argument("--"+name, required=True)
    result = run_experiment(p.parse_args())
    print(json.dumps({k: result[k] for k in ("status", "assessment", "decreased_cells", "decreased_fraction")}))


if __name__ == "__main__":
    main()
