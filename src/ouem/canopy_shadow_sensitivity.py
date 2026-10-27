"""Phase 3 isotropic voxel/observer sensitivity; no accepted contract changes."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import replace
from datetime import datetime
import gc
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np

from ouem.canopy_shadow_poc import (
    DOMAIN, ROI, Pair, crop_pair, digest, grid_north, json_write, load_inputs,
    relative_grids, require, stats, window,
)
from ouem.komae_integration import voxcity_provenance


def subdivide(a, size):
    """Aligned nearest children; all parent values retained, no new information."""
    require(size in (1.0, 0.5), "only reviewed isotropic sizes 1 and 0.5 m")
    factor = int(1 / size)
    return np.repeat(np.repeat(a, factor, axis=0), factor, axis=1)


def area_mean(a, factor):
    require(factor in (1, 2) and a.ndim == 2 and np.isfinite(a).all(),
            "aggregation requires finite paired observations")
    rows, cols = a.shape
    require(rows % factor == cols % factor == 0, "incomplete parent coverage")
    return a.reshape(rows//factor, factor, cols//factor, factor).mean(axis=(1, 3))


def build_isotropic(dem, top, bottom, bounds, rotation, size):
    """Public engine generation, audited with independent expected occupancy."""
    from voxcity.generator.voxelizer import Voxelizer
    from voxcity.models import (VoxCity, VoxelGrid, GridMetadata, BuildingGrid,
                                DemGrid, LandCoverGrid, CanopyGrid)
    require(size in (1.0, .5), "unreviewed size")
    dem, top, bottom = (np.asarray(a, dtype=np.float64) for a in (dem, top, bottom))
    require(dem.ndim == 2 and dem.shape == top.shape == bottom.shape, "shape mismatch")
    require(all(np.isfinite(a).all() for a in (dem, top, bottom)) and
            np.all((0 <= bottom) & (bottom <= top)), "invalid relative grids")
    require(dem.shape == (round((bounds[3]-bounds[1])/size),
                          round((bounds[2]-bounds[0])/size)), "size/bounds mismatch")
    zeros = np.zeros_like(dem)
    ids = np.zeros(dem.shape, dtype=np.int64)
    cover = np.ones(dem.shape, dtype=np.int64)
    segments = np.empty(dem.shape, dtype=object)
    for index in np.ndindex(dem.shape):
        segments[index] = []
    engine = Voxelizer(size, "Standard")
    a = engine.generate_combined(zeros, segments, ids, cover, dem, zeros, zeros, print_class_info=False)
    b = engine.generate_combined(zeros, segments, ids, cover, dem, top, bottom, print_class_info=False)
    nz = max(a.shape[2], b.shape[2])
    a, b = (np.pad(v, ((0, 0), (0, 0), (0, nz-v.shape[2]))) for v in (a, b))
    ea, eb = np.zeros_like(a), np.zeros_like(b)
    d0 = float(dem.min())
    for i, j in np.ndindex(dem.shape):
        ground = int(float(np.float32(dem[i, j]-d0))/size+.5)+1
        ea[i, j, :ground] = -1
        ea[i, j, ground-1] = 1
        eb[i, j] = ea[i, j]
        if top[i, j] > 0:
            lo = int(float(np.float32(bottom[i, j]))/size+.5)
            hi = int(float(np.float32(top[i, j]))/size+.5)
            if lo == hi and lo > 0:
                lo -= 1
            require(ground+hi <= nz, "engine clips crown allocation")
            eb[i, j, ground+lo:ground+hi] = -2
    require(np.array_equal(a, ea) and np.array_equal(b, eb), "voxel audit failed")
    require(np.array_equal(a == -1, b == -1) and np.array_equal(a == 1, b == 1), "terrain differs")
    require(not np.any(a == -2) and (not np.any(top > 0) or np.any(b == -2)), "TREE audit failed")
    meta = GridMetadata("EPSG:6677", bounds, size)
    def city(vox, hi, lo):
        return VoxCity(VoxelGrid(vox, meta), BuildingGrid(zeros.copy(), segments, ids.copy(), meta),
                       LandCoverGrid(cover.copy(), meta), DemGrid(dem.copy(), meta),
                       CanopyGrid(hi.copy(), meta, lo.copy()), {"rotation_angle": rotation})
    return Pair(city(a, zeros, zeros), city(b, top, bottom), {"d0": d0, "size": size})


def geometry(pair, height):
    """Derive actual faces and ray centres from the generated classes, not h alone."""
    a, b = pair.a.voxels.classes, pair.b.voxels.classes
    dem = pair.b.dem.elevation
    size, d0 = pair.b.voxels.meta.meshsize, float(dem.min())
    # First surface transition selected by the building-free CPU path.
    surface = a == 1
    require(np.all(surface.sum(axis=2) == 1), "nonunique walkable surface")
    ground = surface.argmax(axis=2)+1
    require(np.all(ground < a.shape[2]) and
            np.all(np.take_along_axis(a, ground[..., None], axis=2) == 0), "no air transition")
    tree = b == -2
    require(np.array_equal(surface, b == 1), "surface mismatch")
    occupied = tree.any(axis=2)
    low = tree.argmax(axis=2)
    high = b.shape[2]-np.flip(tree, axis=2).argmax(axis=2)
    bottom_error = d0+low*size-(dem+pair.b.tree_canopy.bottom)
    top_error = d0+high*size-(dem+pair.b.tree_canopy.top)
    ray_z = d0+(ground+int(height/size)+.5)*size
    relative_ray = ray_z-dem
    return {"ray_z": ray_z, "ray_height": relative_ray, "ground_top_error": d0+ground*size-dem,
            "bottom_error": bottom_error, "top_error": top_error, "occupied": occupied,
            "tree_count": tree.sum(axis=2)}


def direct(pair, azimuth, elevation, height):
    from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
    require(np.isfinite([azimuth, elevation, height]).all() and 0 < elevation <= 90 and height >= 0,
            "invalid sun or height")
    a, b = (get_direct_solar_irradiance_map(c, azimuth, elevation, 800., show_plot=False,
                tree_k=.6, tree_lad=1., view_point_height=height, include_building_roofs=False)
            for c in (pair.a, pair.b))
    require(np.array_equal(np.isfinite(a), np.isfinite(b)), "observer masks differ")
    require(np.isfinite(a).all() and np.all(b <= a), "invalid/increased irradiance")
    return np.flipud(a).copy(), np.flipud(b).copy()


def _rss_bytes():
    """Current Windows working set; sampling is labelled, not peak allocation."""
    require(platform.system() == "Windows", "RSS meter currently reviewed for Windows only")
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]
    counters = Counters(); counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    fn = ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    require(bool(fn(get_process(), ctypes.byref(counters), counters.cb)), "RSS query failed")
    return int(counters.WorkingSetSize)


class MemoryWindow:
    """Sample process RSS every 10 ms; includes shared libraries/JIT/state."""
    def __enter__(self):
        self.values = [_rss_bytes()]
        self.stop = threading.Event()
        def poll():
            while not self.stop.wait(.01):
                self.values.append(_rss_bytes())
        self.thread = threading.Thread(target=poll, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop.set(); self.thread.join()
        self.values.append(_rss_bytes())

    def report(self):
        return {"rss_start_bytes": self.values[0], "rss_end_bytes": self.values[-1],
                "rss_sampled_max_bytes": max(self.values), "samples": len(self.values),
                "interval_seconds": .01, "scope": "whole process, libraries/JIT included; not isolated allocation"}


def _roi(a, size):
    margin = int(32/size)
    return a[margin:-margin, margin:-margin]


def crop_isotropic(pair, bounds, margin_m=32):
    """Reuse Phase 2 cropping while explicitly preserving scalar mesh metadata."""
    size = pair.b.voxels.meta.meshsize
    cropped = crop_pair(pair, bounds, margin=int(margin_m/size))
    meta = replace(pair.b.voxels.meta, bounds=bounds)
    def restore(city):
        return replace(city, **{name: replace(getattr(city, name), meta=meta) for name in
            ("voxels", "buildings", "land_cover", "dem", "tree_canopy")})
    return Pair(restore(cropped.a), restore(cropped.b), cropped.qa)


def run(args):
    out = Path(args.output_dir)
    require(not out.exists(), "new output directory required")
    source = Path(args.envelope_run).resolve()
    require(source != out.resolve() and source not in out.resolve().parents, "input/output overlap")
    out.mkdir(parents=True)
    try:
        suites = list(ET.parse(args.fixture_report).getroot().iter("testsuite"))
        names = {t.get("name") for s in suites for t in s.findall("testcase")}
        require(suites and sum(int(s.get("tests", 0)) for s in suites) >= 15 and
                all(int(s.get(k, 0)) == 0 for s in suites for k in ("failures", "errors", "skipped")) and
                any(n and n.startswith("test_ray_origin_confirmed_by_public_zenith_api") for n in names), "fixture gate failed")
        pin = voxcity_provenance(); require(pin["verified"], "pin failed")
        (out/"fixtures.xml").write_bytes(Path(args.fixture_report).read_bytes())
        arrays, dem, protected = load_inputs(source, args.expected_manifest_sha,
                                            args.dem_reference, args.expected_reference_sha)
        protected.update({str(p.resolve()): digest(p) for p in source.rglob("*") if p.is_file()})
        old = Path(args.phase2_run)
        old_record = json.loads((old/"run.json").read_text())
        require(digest(old/"run.json") == args.expected_phase2_sha and old_record["status"] == "COMPLETED",
                "Phase 2 record mismatch")
        protected.update({str(p.resolve()): digest(p) for p in old.rglob("*") if p.is_file()})
        for name, sha in old_record["outputs"].items():
            require(digest(old/name) == sha, "Phase 2 output identity failed")
        with np.load(old/"comparison_arrays.npz") as previous:
            baseline = {k: previous[k].copy() for k in ("case_a", "case_b")}
        from numba import set_num_threads
        from voxcity.simulator.solar.temporal import get_solar_positions_astral
        import pandas as pd
        set_num_threads(4)
        rotation, lon, lat = grid_north(ROI)
        stamp = "2026-06-21T12:00:00+09:00"
        sun = get_solar_positions_astral(pd.DatetimeIndex([stamp]), lon, lat).iloc[0]
        az, el = float(sun.azimuth), float(sun.elevation)
        for key, val in (("azimuth_deg", az), ("elevation_deg", el), ("rotation_clockwise_deg", rotation)):
            require(val == old_record["conditions"][key], "sun/rotation differs from Phase 2")
        sl = window(DOMAIN)
        d, hi, lo = relative_grids(arrays[0][sl], arrays[1][sl], dem[sl], arrays[2][sl])
        cases, saved = {}, {}
        for size, label, heights in ((1., "S1", (1.5, .5)), (.5, "S2", (1.5, 1.))):
            gc.collect()
            started = time.perf_counter()
            with MemoryWindow() as memory:
                pair = build_isotropic(*(subdivide(a, size) for a in (d, hi, lo)), DOMAIN, rotation, size)
                build_seconds = time.perf_counter()-started
                for height, suffix in zip(heights, ("", "_low")):
                    tick = time.perf_counter()
                    a, b = direct(pair, az, el, height)
                    solar_seconds = time.perf_counter()-tick
                    g = geometry(pair, height)
                    factor = int(1/size)
                    aa, bb = (_roi(x, size) for x in (a, b))
                    ap, bp = (area_mean(x, factor) for x in (aa, bb))
                    key = label+suffix
                    if key == "S1":
                        require(np.array_equal(ap, baseline["case_a"]) and np.array_equal(bp, baseline["case_b"]),
                                "S1 does not reproduce Phase 2 exactly")
                    saved[key+"_a"] = ap; saved[key+"_b"] = bp
                    for name in ("ray_z", "ray_height", "bottom_error", "top_error", "occupied", "tree_count", "ground_top_error"):
                        saved[key+"_"+name] = _roi(np.flipud(g[name]), size)
                    occupied = saved[key+"_occupied"]
                    bottom_roi, top_roi = (saved[key+"_"+n][occupied] for n in ("bottom_error", "top_error"))
                    # Conservative source ceiling used in Phase 2, plus a full 2 m vertical allowance.
                    reach = (max(float(arrays[0].max()), float(dem.max()))-float(dem.min())+2)/np.tan(np.deg2rad(el))
                    require(reach+2 < 32, "halo too short")
                    cropped = crop_isotropic(pair, ROI)
                    ca, cb = direct(cropped, az, el, height)
                    halo_delta = cb-bb
                    yy, xx = np.indices(bb.shape)
                    edge = np.minimum.reduce((yy, xx, bb.shape[0]-1-yy, bb.shape[1]-1-xx))*size
                    require(not np.any(halo_delta[edge >= 8] != 0), "unexpected interior boundary influence")
                    saved[key+"_b_native"] = bb
                    saved[key+"_a_native"] = aa
                    ray_error = saved[key+"_ray_height"]-1.5
                    cases[key] = {"size_m": size, "requested_height_m": height,
                        "native_roi_shape": list(aa.shape), "parent_shape": list(ap.shape),
                        "finite_native_cells": int(np.isfinite(aa).sum()), "masks_equal": True,
                        "terrain_equal": True, "a_tree_voxels": int((pair.a.voxels.classes == -2).sum()),
                        "b_tree_voxels_domain": int((pair.b.voxels.classes == -2).sum()),
                        "b_tree_voxels_roi": int(saved[key+"_tree_count"].sum()),
                        "tree_volume_roi_m3": float(saved[key+"_tree_count"].sum()*size**3),
                        "tree_volume_domain_m3": float((pair.b.voxels.classes == -2).sum()*size**3),
                        "bottom_error_m": stats(bottom_roi), "top_error_m": stats(top_roi),
                        "ray_absolute_z_m": stats(saved[key+"_ray_z"]),
                        "ray_height_above_dem_m": stats(saved[key+"_ray_height"]),
                        "ray_error_from_target_1_5m": stats(ray_error),
                        "ground_top_error_m": stats(saved[key+"_ground_top_error"]),
                        "a_w_m2": stats(ap), "b_w_m2": stats(bp), "b_minus_a_w_m2": stats(bp-ap),
                        "decreased_parent_cells": int((bp < ap).sum()), "increased_parent_cells": int((bp > ap).sum()),
                        "halo_reach_bound_m": float(reach), "no_halo_changed_native_cells": int((halo_delta != 0).sum()),
                        "no_halo_max_excess_w_m2": float(halo_delta.max()),
                        "no_halo_interior8_changed": int((halo_delta[edge >= 8] != 0).sum()),
                        "voxel_array_bytes_a_plus_b": pair.a.voxels.classes.nbytes+pair.b.voxels.classes.nbytes,
                        "build_seconds": build_seconds, "solar_ab_seconds": solar_seconds,
                        "common_voxel_shape": list(pair.b.voxels.classes.shape)}
                elapsed = time.perf_counter()-started
            for suffix in ("", "_low"):
                cases[label+suffix]["memory_window"] = memory.report()
                cases[label+suffix]["size_window_seconds_including_audits"] = elapsed
            del pair, cropped
        contrasts = {"S2_minus_S1_b": saved["S2_b"]-saved["S1_b"],
            "S1_low_minus_S1_b": saved["S1_low_b"]-saved["S1_b"],
            "S2_low_minus_S2_b": saved["S2_low_b"]-saved["S2_b"],
            "S2_low_minus_S1_low_b": saved["S2_low_b"]-saved["S1_low_b"]}
        saved.update(contrasts)
        np.savez_compressed(out/"sensitivity_arrays.npz", **saved)
        draw(out/"sensitivity.png", saved)
        require(all(digest(p) == sha for p, sha in protected.items()), "protected input changed")
        report = {"status": "COMPLETED", "assessment": "CONDITIONAL", "time_jst": datetime.now().astimezone().isoformat(),
            "main_sha": subprocess.check_output(["git", "rev-parse", "origin/main"], text=True).strip(),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_status": subprocess.check_output(["git", "status", "--short"], text=True).strip(),
            "implementation_sha256": digest(__file__), "phase2_module_sha256": digest(Path(__file__).with_name("canopy_shadow_poc.py")),
            "environment": {"python": platform.python_version(), "packages": {n: version(n) for n in
                ("voxcity", "numpy", "numba", "rasterio", "pyproj", "astral", "pandas")}, "pin": pin},
            "inputs": protected, "fixture_sha256": digest(args.fixture_report),
            "conditions": {"roi": ROI, "domain": DOMAIN, "datetime": stamp, "azimuth": az, "elevation": el,
                "rotation": rotation, "dni_w_m2": 800, "tree_k": .6, "tree_lad": 1., "cr": .6,
                "resampling": "nearest 2x2 replication of 1m DEM/relative top/bottom; no new source detail"},
            "cases": cases, "contrasts_w_m2": {k: stats(a) for k, a in contrasts.items()},
            "s1_phase2_exact": True, "inputs_unchanged": True,
            "outputs": {p.name: digest(p) for p in out.iterdir() if p.is_file()}}
        json_write(out/"run.json", report)
        return report
    except Exception as exc:
        json_write(out/"FAILED.json", {"status": "FAILED", "error": str(exc), "type": type(exc).__name__})
        raise


def draw(path, arrays):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
    for ax, key, title, vmin, vmax in zip(axes.flat,
            ("S1_b", "S2_b", "S2_minus_S1_b", "S1_ray_height", "S2_ray_height", "S2_low_minus_S2_b"),
            ("S1 B: 1m, h=1.5", "S2 B: 0.5m, h=1.5", "S2 - S1 B (parent area means)",
             "S1 actual ray height above DEM", "S2 actual ray height above DEM", "Fixed S2 geometry: h=1.0 minus 1.5"),
            (0, 0, -800, 1.5, 1.5, -800), (800, 800, 800, 3.1, 3.1, 800)):
        im = ax.imshow(arrays[key], origin="upper", extent=(ROI[0], ROI[2], ROI[1], ROI[3]),
            vmin=vmin, vmax=vmax, cmap="RdBu_r" if "minus" in key else "viridis")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("EPSG:6677 easting (m)"); ax.set_ylabel("northing (m)")
        ax.xaxis.set_major_locator(MaxNLocator(3)); ax.yaxis.set_major_locator(MaxNLocator(4))
        ax.ticklabel_format(style="plain", useOffset=False)
        fig.colorbar(im, ax=ax, label="m" if "ray_height" in key else "W/m²")
    fig.suptitle("Exploratory discretization sensitivity | no scientific accuracy / Standard Canopy acceptance", fontsize=12)
    fig.savefig(path, dpi=140); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("envelope-run", "expected-manifest-sha", "dem-reference", "expected-reference-sha",
                 "phase2-run", "expected-phase2-sha", "fixture-report", "output-dir"):
        parser.add_argument("--"+name, required=True)
    result = run(parser.parse_args())
    print(json.dumps({k: result[k] for k in ("status", "assessment", "s1_phase2_exact")}))


if __name__ == "__main__":
    main()
