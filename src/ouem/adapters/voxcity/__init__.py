"""Accepted OUEM Standard artifacts to VoxCity 1.7.0 adapter.

The dependency-light functions in this module define and test the deterministic
contract.  File IO is delegated to ``_gdal_worker.py`` because OUEM deliberately
uses the separately captured QGIS/GDAL runtime for GeoPackage processing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ouem.native.building.plateau import GISRuntime, _decode_output, load_gis_runtime, require_gdal

ADAPTER_VERSION = "0.1.0"
VOXCITY_VERSION = "1.7.0"
VOXCITY_COMMIT = "fa212656305328a9a657973bae26f352bfe813bc"
SCHEMA = "ouem-standard-to-voxcity-building-adapter/v0.1"


class VoxCityAdapterError(RuntimeError):
    """Raised when accepted inputs cannot satisfy the pinned adapter contract."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_id_mapping(ouem_ids: Iterable[str]) -> dict[str, int]:
    """Map canonical IDs to stable, positive, one-based IDs by lexical order."""
    values = list(ouem_ids)
    if any(not isinstance(value, str) or not value for value in values):
        raise VoxCityAdapterError("every building requires a non-empty ouem_id")
    if len(values) != len(set(values)):
        raise VoxCityAdapterError("Standard Building contains duplicate ouem_id values")
    return {value: index for index, value in enumerate(sorted(values), 1)}


def check_vertical_compatibility(building_reference: str, terrain: dict[str, Any]) -> None:
    """Reject unresolved or non-T.P. vertical semantics before numerical fusion."""
    status = terrain.get("status")
    name = terrain.get("name")
    if status not in {"verified", "source-declared"}:
        raise VoxCityAdapterError(f"Terrain vertical reference is not resolved: {status!r}")
    normalized = lambda value: "".join(ch for ch in str(value).casefold() if ch.isalnum())
    if "tp" not in normalized(building_reference) or "tp" not in normalized(name):
        raise VoxCityAdapterError(
            f"incompatible vertical references: Building={building_reference!r}, Terrain={name!r}"
        )


def derive_attributes(z_values: Iterable[float], ground_samples: Iterable[float]) -> dict[str, float]:
    """Derive canonical adapter height from absolute top and effective ground.

    VoxCity 1.7.0 places a relative-height building on its per-cell DEM.  Its
    footprint therefore sees all finite terrain cells.  The adapter uses their
    arithmetic mean as the single effective ground (the least-squares constant
    approximation); min/max and bottom are retained as placement diagnostics.
    """
    zs, grounds = list(z_values), list(ground_samples)
    if not zs or not grounds or not all(math.isfinite(v) for v in zs + grounds):
        raise VoxCityAdapterError("building Z and covered Terrain samples must be finite and non-empty")
    top, bottom = max(zs), min(zs)
    ground = math.fsum(grounds) / len(grounds)
    height = top - ground
    if height <= 0:
        raise VoxCityAdapterError(f"non-positive derived height: top={top}, effective ground={ground}")
    return {
        "z_top_abs": top, "z_bottom_geom_abs": bottom,
        "ground_eff_abs": ground, "height": height, "min_height": 0.0,
        "ground_sample_min_abs": min(grounds), "ground_sample_max_abs": max(grounds),
        "ground_sample_count": len(grounds),
    }


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


@dataclass(frozen=True)
class AdapterResult:
    buildings: int
    output: str
    manifest: str


def adapt_standard_to_voxcity(
    buildings: str | Path, terrain: str | Path, output: str | Path, *,
    meshsize: float, runtime: GISRuntime, aoi: Sequence[float] | None = None,
) -> AdapterResult:
    """Create deterministic GeoJSON plus an audit manifest from accepted artifacts."""
    require_gdal(runtime)
    building_path, terrain_path, output_path = Path(buildings).resolve(), Path(terrain).resolve(), Path(output)
    if meshsize <= 0 or not math.isfinite(meshsize):
        raise VoxCityAdapterError("meshsize must be a positive finite number")
    for path in (building_path, terrain_path):
        if not path.is_file():
            raise VoxCityAdapterError(f"input does not exist: {path}")
    b_manifest_path = building_path.with_suffix(building_path.suffix + ".manifest.json")
    t_manifest_path = terrain_path.with_suffix(terrain_path.suffix + ".manifest.json")
    try:
        bm = json.loads(b_manifest_path.read_text(encoding="utf-8"))
        tm = json.loads(t_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VoxCityAdapterError(f"accepted input manifest is missing or invalid: {exc}") from exc
    if bm.get("schema") != "ouem-standard-building-manifest/v0.1" or tm.get("schema") != "ouem-standard-terrain-manifest/v0.1":
        raise VoxCityAdapterError("inputs must be Standard Building v0.1 and Standard Terrain v0.1")
    check_vertical_compatibility(bm.get("z_reference", ""), tm.get("vertical_reference", {}))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ouem-voxcity-") as temporary:
        job_path, result_path = Path(temporary) / "job.json", Path(temporary) / "result.json"
        job_path.write_text(json.dumps({"buildings": str(building_path), "terrain": str(terrain_path),
            "output": str(output_path.resolve()), "meshsize": meshsize, "aoi": list(aoi) if aoi else None}), encoding="utf-8")
        worker = Path(__file__).with_name("_gdal_worker.py")
        completed = subprocess.run([runtime.python, str(worker), str(job_path), str(result_path)],
            capture_output=True, env=runtime.environment)
        if completed.returncode:
            diagnostic = _decode_output(completed.stderr, runtime).strip() or _decode_output(completed.stdout, runtime).strip()
            raise VoxCityAdapterError(f"external GIS adapter worker failed: {diagnostic}")
        worker_result = json.loads(result_path.read_text(encoding="utf-8"))
    records = worker_result["records"]
    mapping = numeric_id_mapping(record["ouem_id"] for record in records)
    for record in records:
        record["voxcity_id"] = mapping[record["ouem_id"]]
    records.sort(key=lambda record: record["voxcity_id"])
    # Worker output is rewritten canonically after IDs are assigned.
    collection = worker_result["geojson"]
    features_by_id = {f["properties"]["ouem_id"]: f for f in collection["features"]}
    ordered = []
    for record in records:
        feature = features_by_id[record["ouem_id"]]
        feature["properties"].update({k: record[k] for k in ("voxcity_id", "height", "min_height")})
        ordered.append(feature)
    collection["features"] = ordered
    output_path.write_bytes(canonical_json(collection))
    manifest = {"schema": SCHEMA, "adapter_version": ADAPTER_VERSION,
        "voxcity": {"version": VOXCITY_VERSION, "commit": VOXCITY_COMMIT},
        "inputs": {"standard_building": {"path": str(building_path), "sha256": sha256_file(building_path)},
                   "standard_terrain": {"path": str(terrain_path), "sha256": sha256_file(terrain_path)}},
        "aoi": list(aoi) if aoi else worker_result["aoi"], "meshsize": meshsize,
        "crs": {"source": "EPSG:6677", "target": "EPSG:6677", "transform": "none"},
        "vertical_compatibility": {"status": "PASS", "building": bm["z_reference"], "terrain": tm["vertical_reference"]},
        "height_derivation": "z_top_abs - arithmetic mean of finite Standard Terrain pixel centres covered by footprint",
        "ground_derivation": "mean footprint-covered DEM cells; VoxCity uses per-cell DEM, mean is the least-squares single-height reference",
        "min_height_derivation": "constant 0.0; no inference from geometry bottom",
        "id_derivation": "lexicographic ouem_id sort, consecutive positive integers starting at 1",
        "buildings": records, "warnings": worker_result.get("warnings", []),
        "output": {"path": str(output_path.resolve()), "sha256": sha256_file(output_path), "format": "GeoJSON"}}
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest_path.write_bytes(canonical_json(manifest))
    return AdapterResult(len(records), str(output_path.resolve()), str(manifest_path.resolve()))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Adapt accepted OUEM Standard Building + Terrain to VoxCity 1.7.0")
    parser.add_argument("buildings"); parser.add_argument("terrain"); parser.add_argument("--output", required=True)
    parser.add_argument("--meshsize", required=True, type=float); parser.add_argument("--gis-runtime", required=True)
    parser.add_argument("--aoi", nargs=4, type=float, metavar=("XMIN", "YMIN", "XMAX", "YMAX"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = adapt_standard_to_voxcity(args.buildings, args.terrain, args.output,
            meshsize=args.meshsize, runtime=load_gis_runtime(args.gis_runtime), aoi=args.aoi)
    except (VoxCityAdapterError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2
    print(f"Adapter buildings: {result.buildings}\nOutput: {result.output}\nManifest: {result.manifest}\nResult: PASS")
    return 0
