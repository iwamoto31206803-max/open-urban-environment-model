"""STEP 2-C1: hash-bound experimental Terrain envelope; no voxel integration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from types import SimpleNamespace

import numpy as np
import rasterio
from rasterio.warp import transform_bounds

from ouem import height_envelope as env
from ouem.candidate_b_shadow import DOMAIN, T5_SHA
from ouem.compatibility_probe import load_candidate
from ouem.consumers.source_h_standard import Watch
from ouem.komae_integration import voxcity_provenance
from ouem.terrain_candidate_b_t3 import HEIGHT_NODATA

CHM_SHA = "6313f286dca3b9f760be95d998e9648d0dd77b0a9305081b67422150340af862"
ACQUISITION_SHA = "c4c4a842a2271c12a29f62672ee57632f2a7bcea10b79806cafdd761777c98a7"
EVIDENCE_SHA = "afdf8560ac1d7a94cf599ffaa7fe17bbba29df5fca7a61df994052cdc04bf6a9"
DEM_SHA = "ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2"
VERTICAL = "T.P. inheritance working assumption; realization/epoch/accuracy NOT_VERIFIED"


def implementation_identity():
    root = Path(__file__).resolve().parents[2]
    return dict(git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        tracked_changes=subprocess.check_output(["git", "-c", "core.fsmonitor=false", "status",
            "--porcelain", "--untracked-files=no"], cwd=root, text=True).splitlines(),
        module_sha256=env.sha256(__file__), helper_sha256=env.sha256(env.__file__),
        supporting_sha256={name: env.sha256(path) for name, path in {
            "candidate_reader": load_candidate.__code__.co_filename,
            "input_watch": Watch.capture.__code__.co_filename,
            "acquisition_helpers": env.sha256.__code__.co_filename,
            "voxcity_provenance": voxcity_provenance.__code__.co_filename,
            "pyproject": root/"pyproject.toml"}.items()},
        python=platform.python_version(), numpy=np.__version__, rasterio=rasterio.__version__,
        gdal=rasterio.__gdal_version__, pyproj=env.pyproj.__version__)


def point_grid(xy):
    """Use actual saved centres without snapping, shifting or axis reversal."""
    return SimpleNamespace(height=xy.shape[0], width=xy.shape[1], epsg=6677,
                           centres=lambda: (xy[..., 0], xy[..., 1]))


def evaluate(chm, dem, grid):
    ch = env.sample_raster(chm, grid)
    ground = env.sample_raster(dem, grid)
    top, bottom, state, qa = env.calculate(grid, ch, ground, env.ConstantCR(.60))
    qa["tree_candidate_cells"] = int(((state == env.VALID) & (top > bottom)).sum())
    return top, bottom, state, qa, ch, ground


def generate(source_run, chm, acquisition_record, chm_evidence, output_dir):
    paths = [Path(p).resolve(strict=True) for p in
             (source_run, chm, acquisition_record, chm_evidence)]
    source, chm, acquisition_record, chm_evidence = paths
    out = Path(output_dir).resolve()
    # Protect complete input bundles, including outputs read by load_candidate.
    if out.exists() or any(out.is_relative_to(p if p.is_dir() else p.parent)
                           or p.is_relative_to(out) for p in paths):
        raise env.EnvelopeBlocked("Use a new output directory outside input bundles")
    watches = []

    def capture(path, sha, *, json_data=False):
        watch = Watch(path.parent)
        watches.append(watch)
        return watch.capture(path.name, path.name, sha, json_data=json_data)

    acq = capture(acquisition_record, ACQUISITION_SHA, json_data=True)
    evidence = capture(chm_evidence, EVIDENCE_SHA, json_data=True)
    capture(chm, CHM_SHA)
    tiles = [t for t in acq["tiles"] if t["quadkey"] == "1330021123"]
    if (acq["schema"] != "ouem-chmv2-acquisition-poc/v0.1" or acq["status"] != "COMPLETED"
            or len(tiles) != 1 or tiles[0]["sha256"] != CHM_SHA
            or evidence["height_semantics"] != "height_above_ground_m"
            or evidence["height_reference"] != "local_ground"):
        raise env.EnvelopeBlocked("Raw CHMv2 identity/HAG evidence not established")
    support = evidence["evidence"]
    snapshot = (chm_evidence.parent / support["snapshot_path"]).resolve(strict=True)
    capture(snapshot, support["snapshot_sha256"])
    if support["statement"] not in snapshot.read_text(encoding="utf-8"):
        raise env.EnvelopeBlocked("HAG source statement differs")
    arrays, metadata, probe, t5, model_watch = load_candidate(source, T5_SHA)
    watches.append(model_watch)
    dem = source / "t5-2/terrain.tif"
    if (t5["outputs"]["t5-2/terrain.tif"] != DEM_SHA or metadata["domain_bounds"] != DOMAIN
            or t5["terrain_integration_ready"] is not False):
        raise env.EnvelopeBlocked("Unexpected experimental Terrain/domain identity")
    capture(dem, DEM_SHA)
    grid = env.GridSpec(tuple(DOMAIN))
    with rasterio.open(dem) as ds:
        if (ds.crs.to_epsg() != 6677 or ds.shape != (254, 254)
                or ds.dtypes != ("float32",) or ds.nodata != HEIGHT_NODATA
                or list(ds.bounds) != DOMAIN or list(ds.transform)[:6] != t5["terrain"]["affine"]):
            raise env.EnvelopeBlocked("Experimental Terrain raster differs from T5")
    engine = voxcity_provenance()
    if not engine["verified"]:
        raise env.EnvelopeBlocked("Pinned VoxCity environment not verified")
    footprint = {}
    for name, path in (("chm", chm), ("dem", dem)):
        with rasterio.open(path) as ds:
            bounds = transform_bounds(6677, ds.crs, *DOMAIN, densify_pts=101)
            covered = (ds.bounds.left <= bounds[0] and ds.bounds.bottom <= bounds[1]
                       and ds.bounds.right >= bounds[2] and ds.bounds.top >= bounds[3])
            if not covered:
                raise env.EnvelopeBlocked("Source footprint does not cover complete domain")
            footprint[name] = dict(full_domain_extent_covered=True, domain_bounds_in_source_crs=list(bounds))
    top, bottom, state, qa, ch, ground = evaluate(chm, dem, grid)
    xy = arrays["centres_xy"]
    actual = point_grid(xy)
    at, ab, ast, aqa, ach, aground = evaluate(chm, dem, actual)
    if not np.array_equal(aground.values, arrays["raw_dem"]):
        raise env.EnvelopeBlocked("DEM samples differ from saved T5 raw DEM")
    if not (np.all(state == env.VALID) and np.all(ast == env.VALID)):
        raise env.EnvelopeBlocked("Incomplete/invalid processing-domain or actual-centre coverage")
    inverse = ~grid.transform
    cols = np.floor(inverse.a*xy[..., 0]+inverse.c).astype(int)
    rows = np.floor(inverse.e*xy[..., 1]+inverse.f).astype(int)
    gx, gy = grid.centres()
    distance = np.hypot(xy[..., 0]-gx[rows, cols], xy[..., 1]-gy[rows, cols])
    correspondence = dict(method="EPSG:6677 inverse-affine floor at saved centres; no shift",
        max_distance_to_envelope_centre_m=float(distance.max()),
        unique_envelope_cells=int(np.unique(rows*grid.width+cols).size),
        chm_sample_differences=int((ach.values != ch.values[rows, cols]).sum()),
        dem_sample_differences=int((aground.values != ground.values[rows, cols]).sum()),
        max_top_difference_m=float(np.abs(at-top[rows, cols]).max()),
        max_bottom_difference_m=float(np.abs(ab-bottom[rows, cols]).max()),
        raw_dem_matches_saved_t5=True,
        next_step="Sample top/bottom/state together at saved centres using inverse-affine floor; "
                  "do not reshape/flip as a substitute. Recheck conditioned ground, D0 and below-ground "
                  "intervals in STEP 2-C2; no implicit correction or integration approval.")
    identity = implementation_identity()
    implementation = {"candidate_b_envelope_sha256": env.sha256(__file__), "helpers": identity}
    out.mkdir(parents=True)
    try:
        outputs = {}
        for name, values, nodata in (("canopy_top_z.tif", top, env.NODATA),
                ("canopy_bottom_z.tif", bottom, env.NODATA), ("height_envelope_state.tif", state, None)):
            outputs[name] = env.write_verified(out/name, values, grid, nodata, VERTICAL)
        sampled = [env.sample_raster(out/name, actual) for name in outputs]
        if not all((~s.missing & ~s.outside).all() for s in sampled):
            raise env.EnvelopeBlocked("Written envelope does not cover actual centres")
        for sample, values in zip(sampled, (top, bottom, state)):
            if not np.array_equal(sample.values, values[rows, cols]):
                raise env.EnvelopeBlocked("Written actual-centre sampling differs")
        for watch in watches:
            watch.unchanged()
        if identity != implementation_identity() or env.sha256(__file__) != implementation["candidate_b_envelope_sha256"]:
            raise env.EnvelopeBlocked("Implementation changed during generation")
        stable = dict(schema="ouem-candidate-b-experimental-height-envelope/v0.1",
            terrain_integration_ready=False, scientific_validation="NOT_VERIFIED", formal_acceptance="NOT_VERIFIED",
            grid_spec=grid.metadata(), cr_model=env.ConstantCR(.60).specification(),
            formulas={"top": "DEM + CHM", "bottom": "DEM + (1 - CR) * CHM"},
            height_semantics="height_above_ground_m; local_ground; zero valid; no presence/absence claim",
            source_units={"chm": "metres from hash-bound Meta HAG source statement",
                          "dem": "elevation metres inherited from experimental T5 source lineage; not formal acceptance"},
            vertical_reference={"working_assumption": VERTICAL, "t5_evidence": t5["vertical_evidence"],
                "limitations": "CHM model ground versus DEM, time mismatch, horizontal displacement and CR error unresolved; no vertical offset"},
            chm_lineage={"acquisition": acq["source"], "tile": tiles[0], "hag_evidence": support,
                "old_dem_review": "Not transferred; this profile uses STEP 2-C1 authorization only"},
            terrain_identity={"report_sha256": T5_SHA, "terrain_sha256": DEM_SHA, "profile": t5["profile"]},
            inputs=[w.identities for w in watches], footprint_qa=footprint,
            source_rasters={"chm": ch.metadata, "dem": ground.metadata},
            sampling="nearest; inverse-affine floor; original masks; outside separate from missing; no filling",
            state_encoding={"valid": env.VALID, "error_bits": env.STATE_BITS, "nodata": None},
            float_nodata=env.NODATA, qa=qa, actual_centres_qa=aqa, correspondence=correspondence,
            written_actual_centres_qa={"valid": int(sampled[2].values.size), "outside": 0, "missing": 0},
            source_immutability="PASS", candidate_probe=probe, engine=engine, outputs=outputs)
        fingerprint = hashlib.sha256(json.dumps(stable, sort_keys=True, allow_nan=False).encode()).hexdigest()
        manifest = dict(stable, status="COMPLETED", implementation=implementation, reproducibility_sha256=fingerprint)
        # Completion marker is exclusive and last; a partial TIFF bundle is never COMPLETED.
        payload = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False)+"\n"
        marker = out/"height_envelope_manifest.json.pending"
        with marker.open("x", encoding="utf-8") as stream:
            stream.write(payload)
        os.rename(marker, out/"height_envelope_manifest.json")
    except Exception as exc:
        with (out/"failure.json").open("x", encoding="utf-8") as stream:
            json.dump(dict(status="BLOCKED", error=f"{type(exc).__name__}: {exc}"), stream)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "chm", "acquisition-record", "chm-evidence", "output-dir"):
        parser.add_argument("--"+name, required=True, type=Path)
    try:
        result = generate(**vars(parser.parse_args()))
    except (ValueError, OSError, KeyError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(json.dumps({k: result[k] for k in ("status", "qa", "actual_centres_qa", "correspondence")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
