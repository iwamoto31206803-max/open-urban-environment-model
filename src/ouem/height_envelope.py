"""Experimental CHM + accepted Terrain + CR envelopes; no canopy presence claims."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
from typing import Protocol

import numpy as np
import pyproj
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window

from ouem.acquire.meta_chmv2 import file_record, sha256, raster_metadata
from ouem.study_area import load_study_area

VERSION = "0.1"
NODATA = -9999.0
STATE_BITS = {"missing_chm": 2, "missing_dem": 4, "invalid_chm": 8,
              "invalid_dem": 16, "outside_chm": 32, "outside_dem": 64,
              "invalid_model_or_float32_result": 128}
VALID = 1


class EnvelopeBlocked(ValueError):
    """Required semantics, source identity or output QA is not established."""


@dataclass(frozen=True)
class GridSpec:
    bounds: tuple[float, float, float, float]
    resolution: float = 1.0
    epsg: int = 6677

    def __post_init__(self):
        x0, y0, x1, y1 = self.bounds
        if (self.epsg != 6677 or not all(math.isfinite(v) for v in (*self.bounds, self.resolution))
                or self.resolution <= 0 or x1 <= x0 or y1 <= y0):
            raise EnvelopeBlocked("Initial PoC requires finite ordered EPSG:6677 metre grid")
        for v in self.bounds:
            if not math.isclose(v/self.resolution, round(v/self.resolution), rel_tol=0, abs_tol=1e-8):
                raise EnvelopeBlocked("Bounds must align exactly to the explicit resolution")
        if self.width <= 0 or self.height <= 0 or self.width*self.height > 16_000_000:
            raise EnvelopeBlocked("PoC grid exceeds 16 million cells")

    @property
    def width(self): return round((self.bounds[2]-self.bounds[0])/self.resolution)

    @property
    def height(self): return round((self.bounds[3]-self.bounds[1])/self.resolution)

    @property
    def transform(self):
        return Affine(self.resolution, 0, self.bounds[0], 0, -self.resolution, self.bounds[3])

    def centres(self):
        rows, cols = np.indices((self.height, self.width))
        return (self.bounds[0]+(cols+.5)*self.resolution,
                self.bounds[3]-(rows+.5)*self.resolution)

    def metadata(self):
        return {**asdict(self), "crs": f"EPSG:{self.epsg}", "width": self.width,
                "height": self.height, "transform": list(self.transform)[:6],
                "sampling_location": "cell centre", "orientation": "north-up",
                "boundary_rule": "source inverse-affine floor; left/top inclusive, right/bottom exclusive"}

    @classmethod
    def from_study_area(cls, path, resolution=1.0):
        area = load_study_area(path)
        return cls(area.extent, resolution, area.epsg)


class CrownRatioModel(Protocol):
    def specification(self) -> dict: ...
    def ratios(self, grid: GridSpec, chm: np.ndarray, dem: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True)
class ConstantCR:
    cr: float = 0.60

    def __post_init__(self):
        if not math.isfinite(self.cr) or not 0 < self.cr <= 1:
            raise EnvelopeBlocked("constant_cr_v0.1 requires finite 0 < CR <= 1")

    def specification(self):
        return {"model_id": "constant_cr_v0.1", "version": "0.1", "parameters": {"cr": self.cr},
                "bottom_evidence": "estimated from constant Crown Ratio; not measured",
                "applicability": "experimental height envelope; no ecological validation"}

    def ratios(self, grid, chm, dem):
        return np.full((grid.height, grid.width), self.cr, dtype="float64")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_sources(chm, acquisition_record, chm_evidence, terrain, terrain_manifest, terrain_acceptance):
    """Explicit bridge, not the legacy CHM provenance schema or a CRS inference."""
    acq, evidence, terrain_record = map(read_json, (acquisition_record, chm_evidence, terrain_manifest))
    chm_hash, dem_hash = sha256(chm), sha256(terrain)
    if (acq.get("schema") != "ouem-chmv2-acquisition-poc/v0.1" or acq.get("status") != "COMPLETED"
            or acq.get("output", {}).get("sha256") != chm_hash or not acq.get("tiles")):
        raise EnvelopeBlocked("CHM must match a COMPLETED CHMv2 acquisition output")
    if (evidence.get("schema") != "ouem-height-envelope-evidence/v0.1"
            or evidence.get("chm_sha256") != chm_hash
            or evidence.get("acquisition_record_sha256") != sha256(acquisition_record)
            or evidence.get("height_semantics") != "height_above_ground_m"
            or evidence.get("height_reference") != "local_ground"):
        raise EnvelopeBlocked("Missing hash-bound CHM HAG/metres evidence bridge")
    support = evidence.get("evidence", {})
    if not all(isinstance(support.get(k), str) and support[k].strip()
               for k in ("source", "citation", "statement", "snapshot_path", "snapshot_sha256")):
        raise EnvelopeBlocked("Source statement, citation and local evidence snapshot required")
    snapshot = Path(chm_evidence).parent / support["snapshot_path"]
    if sha256(snapshot) != support["snapshot_sha256"] or support["statement"] not in snapshot.read_text(encoding="utf-8"):
        raise EnvelopeBlocked("Evidence snapshot hash or quoted source statement mismatch")
    review = evidence.get("compatibility_review", {})
    if (review.get("vertical_combination") != "relative_height_plus_dem_no_offset"
            or not all(isinstance(review.get(k), str) and review[k].strip()
                       for k in ("reviewer", "reviewed_at", "basis"))):
        raise EnvelopeBlocked("Explicit CHM/local-ground to DEM compatibility review required")
    vertical = terrain_record.get("vertical_reference", {})
    standard = terrain_record.get("standard", {})
    validation = terrain_record.get("validation", {})
    if (terrain_record.get("schema") != "ouem-standard-terrain-manifest/v0.1"
            or standard.get("sha256") != dem_hash
            or vertical.get("status") not in ("source-declared", "verified")
            or not all(isinstance(vertical.get(k), str) and vertical[k].strip() for k in ("name", "source"))
            or validation.get("grid_preserved") is not True or validation.get("elevations_preserved") is not True):
        raise EnvelopeBlocked("Terrain requires matching Standard identity and explicit vertical evidence")
    if (evidence.get("dem_quantity") != "absolute_elevation_m"
            or review.get("dem_vertical_reference") != vertical["name"]
            or review.get("dem_sha256") != dem_hash):
        raise EnvelopeBlocked("DEM absolute-elevation semantics / vertical reference incompatible")
    # Generated historical pending strings are not formal acceptance decisions.
    acceptance = Path(terrain_acceptance).read_text(encoding="utf-8")
    accepted = re.search(r"\|\s*Status\s*\|\s*\*\*ACCEPTED\*\*\s*\|", acceptance)
    identified = re.search(r"\|\s*Standard output SHA-256\s*\|\s*`" + dem_hash + r"`\s*\|", acceptance)
    if not accepted or not identified:
        raise EnvelopeBlocked("Terrain acceptance evidence must explicitly identify these accepted bytes")
    with rasterio.open(terrain) as src:
        if (src.crs != rasterio.crs.CRS.from_epsg(6677) or src.count != 1
                or src.dtypes != ("float32",) or src.nodata != NODATA
                or src.transform.b != 0 or src.transform.d != 0
                or src.transform.a <= 0 or src.transform.e >= 0
                or standard.get("crs") != str(src.crs)
                or standard.get("resolution") != list(src.res)
                or standard.get("dtype") != "float32" or standard.get("nodata") != src.nodata):
            raise EnvelopeBlocked("Terrain raster does not satisfy its existing v0.1 contract/metadata")
        tags = src.tags()
        if (tags.get("VERTICAL_REFERENCE_STATUS") != vertical["status"]
                or tags.get("VERTICAL_REFERENCE") != vertical["name"]):
            raise EnvelopeBlocked("Terrain tags disagree with manifest vertical semantics")
    return {"height_semantics": evidence["height_semantics"], "evidence": support,
            "compatibility_review": review, "dem_quantity": evidence["dem_quantity"],
            "vertical_reference": vertical, "snapshot": file_record(snapshot),
            "chm_lineage": {"schema": acq["schema"], "source": acq.get("source"),
                            "tiles": [{key: tile.get(key) for key in ("quadkey", "url", "sha256")} for tile in acq["tiles"]]}}


@dataclass
class Samples:
    values: np.ndarray
    missing: np.ndarray
    outside: np.ndarray
    metadata: dict


def sample_raster(path, grid, *, method="nearest"):
    """Sampling strategy boundary: bilinear is deliberately not implemented yet."""
    if method != "nearest":
        raise EnvelopeBlocked("Only nearest sampling is implemented; bilinear needs masked-neighbour rules")
    shape = (grid.height, grid.width)
    values = np.full(shape, np.nan, dtype="float64")
    missing = np.zeros(shape, dtype=bool)
    with rasterio.open(path) as src:
        if src.crs is None or src.count != 1 or np.dtype(src.dtypes[0]).kind not in "uif":
            raise EnvelopeBlocked("Sources need one numeric band and a declared horizontal CRS")
        if src.scales != (1.0,) or src.offsets != (0.0,) or src.units[0] not in (None, "m", "metre", "meter"):
            raise EnvelopeBlocked("Unsupported scale/offset/unit; no implicit elevation offset")
        if abs(src.transform.determinant) == 0:
            raise EnvelopeBlocked("Source transform is singular")
        xs, ys = grid.centres()
        tx = pyproj.Transformer.from_crs(grid.epsg, src.crs, always_xy=True)
        xs, ys = tx.transform(xs, ys)
        inverse = ~src.transform
        cols = inverse.a*xs + inverse.b*ys + inverse.c
        rows = inverse.d*xs + inverse.e*ys + inverse.f
        inside = np.isfinite(cols) & np.isfinite(rows) & (cols >= 0) & (rows >= 0) & (cols < src.width) & (rows < src.height)
        if inside.any():
            r, c = np.floor(rows[inside]).astype(int), np.floor(cols[inside]).astype(int)
            r0, c0 = int(r.min()), int(c.min())
            window = Window(c0, r0, int(c.max())-c0+1, int(r.max())-r0+1)
            block = src.read(1, window=window)
            mask = src.read_masks(1, window=window)
            values[inside] = block[r-r0, c-c0]
            missing[inside] = mask[r-r0, c-c0] == 0
        return Samples(values, missing, ~inside, raster_metadata(src))


def calculate(grid, chm, dem, model):
    """Height validity only; zero height remains valid, never confirmed absence."""
    state = np.zeros((grid.height, grid.width), dtype="uint8")
    for sample, name in ((chm, "chm"), (dem, "dem")):
        state[sample.outside] |= STATE_BITS["outside_"+name]
        state[sample.missing & ~sample.outside] |= STATE_BITS["missing_"+name]
        invalid = ~np.isfinite(sample.values)
        if name == "chm": invalid |= sample.values < 0
        state[invalid & ~sample.missing & ~sample.outside] |= STATE_BITS["invalid_"+name]
    ratios = np.asarray(model.ratios(grid, chm.values.copy(), dem.values.copy()), dtype="float64")
    if ratios.shape != state.shape:
        raise EnvelopeBlocked("CR model must return one ratio per grid cell")
    candidate = state == 0
    bad_ratio = ~np.isfinite(ratios) | (ratios <= 0) | (ratios > 1)
    state[candidate & bad_ratio] |= STATE_BITS["invalid_model_or_float32_result"]
    candidate = state == 0
    with np.errstate(over="ignore", invalid="ignore"):
        top64 = dem.values + chm.values
        bottom64 = dem.values + chm.values*(1-ratios)
        top, bottom = top64.astype("float32"), bottom64.astype("float32")
    bad = (~np.isfinite(top) | ~np.isfinite(bottom) | (top == NODATA) | (bottom == NODATA)
           | (bottom < dem.values) | (top < bottom))
    state[candidate & bad] |= STATE_BITS["invalid_model_or_float32_result"]
    valid = state == 0
    top[~valid], bottom[~valid] = NODATA, NODATA
    state[valid] = VALID
    counts = {key: int(((state & bit) != 0).sum()) for key, bit in STATE_BITS.items()}
    counts.update(valid=int(valid.sum()), nonvalid=int((~valid).sum()), total=int(state.size),
                  zero_height_valid=int((valid & (chm.values == 0)).sum()))
    qa = {"state_counts": counts, "finite_valid_outputs": bool(np.isfinite(top[valid]).all() and np.isfinite(bottom[valid]).all()),
          "dem_le_bottom_le_top": bool(np.all(dem.values[valid] <= bottom[valid]) and np.all(bottom[valid] <= top[valid])),
          "invalid_outputs_are_nodata": bool(np.all(top[~valid] == NODATA) and np.all(bottom[~valid] == NODATA)),
          "top_range": [float(top[valid].min()), float(top[valid].max())] if valid.any() else None,
          "bottom_range": [float(bottom[valid].min()), float(bottom[valid].max())] if valid.any() else None,
          "max_top_float32_rounding_error_m": float(np.abs(top[valid].astype("float64")-top64[valid]).max()) if valid.any() else None,
          "max_bottom_float32_rounding_error_m": float(np.abs(bottom[valid].astype("float64")-bottom64[valid]).max()) if valid.any() else None}
    return top, bottom, state, qa


def implementation_identity():
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True).splitlines()
    except (OSError, subprocess.CalledProcessError):
        commit, status = None, None
    try:
        blob = subprocess.check_output(["git", "show", "HEAD:src/ouem/height_envelope.py"], cwd=root, stderr=subprocess.DEVNULL)
        head_hash = hashlib.sha256(blob).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        head_hash = None
    return {"version": VERSION, "module_sha256": sha256(__file__), "git_commit": commit,
            "head_module_sha256": head_hash, "module_matches_head": sha256(__file__) == head_hash if head_hash else None,
            "supporting_module_sha256": {"acquisition_helpers": sha256(file_record.__code__.co_filename),
                                         "study_area": sha256(load_study_area.__code__.co_filename)},
            "git_status_porcelain": status, "git_clean": not status if status is not None else None,
            "python": platform.python_version(), "numpy": np.__version__,
            "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__, "pyproj": pyproj.__version__}


def write_verified(path, array, grid, nodata, vertical):
    with rasterio.open(path, "w", driver="GTiff", width=grid.width, height=grid.height,
                       count=1, dtype=array.dtype, crs=grid.epsg, transform=grid.transform,
                       nodata=nodata, compress="deflate") as dst:
        dst.write(array, 1)
        if nodata is not None: dst.set_band_unit(1, "m")
        dst.update_tags(OUEM_SCOPE="EXPERIMENTAL_HEIGHT_ENVELOPE_NOT_STANDARD_CANOPY",
                        VERTICAL_REFERENCE=vertical, VERTICAL_QUANTITY="absolute_elevation_m" if nodata is not None else "height_validity_flags")
    with rasterio.open(path) as src:
        if (src.transform != grid.transform or src.crs.to_epsg() != grid.epsg
                or src.width != grid.width or src.height != grid.height or src.count != 1
                or src.dtypes != (str(array.dtype),) or src.nodata != nodata
                or not np.array_equal(src.read(1), array)
                or src.units != (("m",) if nodata is not None else (None,))
                or src.tags().get("VERTICAL_REFERENCE") != vertical
                or src.tags().get("VERTICAL_QUANTITY") != ("absolute_elevation_m" if nodata is not None else "height_validity_flags")):
            raise EnvelopeBlocked("Written output failed pixel/grid/metadata QA")
        expected_mask = np.where(array == nodata, 0, 255) if nodata is not None else np.full(array.shape, 255)
        if not np.array_equal(src.read_masks(1), expected_mask):
            raise EnvelopeBlocked("Written output failed mask QA")
    return {"filename": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}


def generate(chm, acquisition_record, chm_evidence, terrain, terrain_manifest,
             terrain_acceptance, study_area, output_dir, *, model=None, resolution=1.0, dem_sampling="nearest"):
    model = model or ConstantCR()
    model_spec = model.specification()
    if (not isinstance(model_spec, dict) or not isinstance(model_spec.get("parameters"), dict)
            or not all(isinstance(model_spec.get(key), str) and model_spec[key].strip() for key in ("model_id", "version"))):
        raise EnvelopeBlocked("CR model requires ID, version and explicit parameter metadata")
    paths = dict(chm=chm, acquisition_record=acquisition_record, chm_evidence=chm_evidence,
                 terrain=terrain, terrain_manifest=terrain_manifest, terrain_acceptance=terrain_acceptance, study_area=study_area)
    inputs = {key: file_record(path) for key, path in paths.items()}
    semantics = validate_sources(chm, acquisition_record, chm_evidence, terrain, terrain_manifest, terrain_acceptance)
    inputs["evidence_snapshot"] = semantics.pop("snapshot")
    out = Path(output_dir)
    if out.exists() or any(out.resolve() == Path(item["path"]) or out.resolve() in Path(item["path"]).parents for item in inputs.values()):
        raise EnvelopeBlocked("Use a new output directory separate from every input")
    grid = GridSpec.from_study_area(study_area, resolution)
    chm_samples = sample_raster(chm, grid)
    dem_samples = sample_raster(terrain, grid, method=dem_sampling)
    top, bottom, state, qa = calculate(grid, chm_samples, dem_samples, model)
    identity = implementation_identity()
    stable = {"schema": "ouem-height-envelope-poc/v0.1", "scope": "EXPERIMENTAL_PARTIAL_NOT_STANDARD_CANOPY_ACCEPTANCE",
              "inputs": {key: item["sha256"] for key, item in inputs.items()}, "source_semantics": semantics,
              "grid_spec": grid.metadata(), "sampling": {"chm": "nearest", "dem": dem_sampling},
              "cr_model": model_spec, "state_encoding": {"valid": VALID, "error_bits": STATE_BITS,
                "combination": "bitwise OR; no presence or absence claim", "nodata": None},
              "float_nodata": NODATA, "qa": qa,
              "source_rasters": {"chm": chm_samples.metadata, "dem": dem_samples.metadata}}
    out.parent.mkdir(parents=True, exist_ok=True)
    # Stage all files and verify them before publishing. The manifest is the final
    # bundle completion marker. Never replace existing files or source artifacts.
    out.mkdir()
    published = []
    with tempfile.TemporaryDirectory(prefix=".unverified-", dir=out) as temporary:
        stage = Path(temporary)
        try:
            outputs = {}
            for name, array, nodata in (("canopy_top_z.tif", top, NODATA), ("canopy_bottom_z.tif", bottom, NODATA),
                                        ("height_envelope_state.tif", state, None)):
                outputs[name] = write_verified(stage/name, array, grid, nodata, semantics["vertical_reference"]["name"])
            stable["outputs"] = outputs
            for item in inputs.values():
                if sha256(item["path"]) != item["sha256"]:
                    raise EnvelopeBlocked("Input changed during generation")
            final_identity = implementation_identity()
            if identity != final_identity:
                raise EnvelopeBlocked("Implementation or Git state changed during generation")
            fingerprint = hashlib.sha256(json.dumps(stable, sort_keys=True, allow_nan=False).encode()).hexdigest()
            manifest = {**stable, "status": "COMPLETED", "input_files": inputs,
                        "implementation": identity, "reproducibility_sha256": fingerprint,
                        "recorded_at": datetime.now(timezone.utc).isoformat()}
            filename = "height_envelope_manifest.json"
            (stage/filename).write_text(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            for name in [*outputs, filename]:
                os.link(stage/name, out/name)
                published.append(out/name)
        except Exception as exc:
            retained = []
            for path in reversed(published):
                try:
                    path.unlink()
                except OSError:
                    retained.append(str(path))
            if retained:
                raise EnvelopeBlocked(
                    f"Publication failed; rollback incomplete; quarantine this run directory: {retained}"
                ) from exc
            raise
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("chm", "acquisition-record", "chm-evidence", "terrain", "terrain-manifest", "terrain-acceptance", "study-area", "output-dir"):
        parser.add_argument("--"+arg, required=True)
    parser.add_argument("--cr", type=float, default=0.60)
    parser.add_argument("--resolution", type=float, default=1.0)
    parser.add_argument("--dem-sampling", choices=["nearest"], default="nearest")
    args = vars(parser.parse_args(argv))
    try:
        args["model"] = ConstantCR(args.pop("cr"))
        manifest = generate(**args)
    except (ValueError, OSError, KeyError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}")
        return 1
    print(json.dumps({"status": manifest["status"], "qa": manifest["qa"], "scope": manifest["scope"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
