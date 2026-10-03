"""Validation and registration of source DEMs as OUEM Native Terrain v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

NATIVE_SCHEMA = "ouem-native-terrain-manifest/v0.1"
VERTICAL_STATUSES = frozenset({"verified", "source-declared", "unresolved"})


class NativeTerrainError(RuntimeError):
    """Raised when a raster cannot be accepted as Native Terrain."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class NativeTerrain:
    source_path: str
    source_sha256: str
    provider: str
    source_dataset: str
    width: int
    height: int
    band_count: int
    dtype: str
    horizontal_crs: str
    transform: list[float]
    pixel_size: list[float]
    extent: list[float]
    source_nodata: float
    valid_cells: int
    nodata_cells: int
    valid_min: float
    valid_max: float
    vertical_reference_status: str
    vertical_reference: str | None
    vertical_reference_source: str | None


def inspect_dem(path: str | Path) -> dict:
    """Inspect a DEM with rasterio, rejecting ambiguous raster structure."""
    try:
        import numpy as np
        import rasterio
    except ImportError as exc:  # pragma: no cover - dependency installation failure
        raise NativeTerrainError("Terrain commands require rasterio and numpy") from exc

    source = Path(path).resolve()
    if not source.is_file() or source.suffix.lower() not in {".tif", ".tiff"}:
        raise NativeTerrainError(f"input must be a GeoTIFF: {source}")
    try:
        with rasterio.open(source) as dataset:
            if dataset.count != 1:
                raise NativeTerrainError("Terrain v0.1 requires exactly one raster band")
            if dataset.width <= 0 or dataset.height <= 0:
                raise NativeTerrainError("raster dimensions must be positive")
            if dataset.crs is None:
                raise NativeTerrainError("source raster has no horizontal CRS")
            epsg = dataset.crs.to_epsg()
            if epsg is None:
                raise NativeTerrainError("source horizontal CRS has no unambiguous EPSG code")
            transform = dataset.transform
            if transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0:
                raise NativeTerrainError("Terrain v0.1 requires a north-up, unrotated grid")
            if dataset.nodata is None or not np.isfinite(dataset.nodata):
                raise NativeTerrainError("source raster must declare a finite NoData value")
            values = dataset.read(1, masked=True)
            valid = values.compressed()
            if valid.size == 0:
                raise NativeTerrainError("source raster contains no valid terrain cells")
            if not np.all(np.isfinite(valid)):
                raise NativeTerrainError("valid terrain cells must be finite")
            mask = np.ma.getmaskarray(values)
            return {
                "width": dataset.width,
                "height": dataset.height,
                "band_count": dataset.count,
                "dtype": dataset.dtypes[0],
                "horizontal_crs": f"EPSG:{epsg}",
                "transform": list(transform)[:6],
                "pixel_size": [abs(transform.a), abs(transform.e)],
                "extent": [dataset.bounds.left, dataset.bounds.bottom,
                           dataset.bounds.right, dataset.bounds.top],
                "source_nodata": float(dataset.nodata),
                "valid_cells": int(valid.size),
                "nodata_cells": int(mask.sum()),
                "valid_min": float(valid.min()),
                "valid_max": float(valid.max()),
            }
    except NativeTerrainError:
        raise
    except Exception as exc:
        raise NativeTerrainError(f"could not inspect GeoTIFF {source}: {exc}") from exc


def accept_native_terrain(
    source: str | Path,
    manifest: str | Path,
    *,
    provider: str,
    source_dataset: str,
    vertical_reference_status: str = "unresolved",
    vertical_reference: str | None = None,
    vertical_reference_source: str | None = None,
) -> NativeTerrain:
    """Validate and register a source raster without making a redundant raster copy."""
    if vertical_reference_status not in VERTICAL_STATUSES:
        raise NativeTerrainError(f"invalid vertical-reference status: {vertical_reference_status}")
    if vertical_reference_status == "unresolved" and (vertical_reference or vertical_reference_source):
        raise NativeTerrainError("unresolved vertical reference cannot have a name or evidence")
    if vertical_reference_status != "unresolved" and not (vertical_reference and vertical_reference_source):
        raise NativeTerrainError("declared/verified vertical reference requires a name and evidence")
    source_path = Path(source).resolve()
    result = NativeTerrain(
        source_path=str(source_path), source_sha256=sha256_file(source_path),
        provider=provider, source_dataset=source_dataset,
        vertical_reference_status=vertical_reference_status,
        vertical_reference=vertical_reference,
        vertical_reference_source=vertical_reference_source,
        **inspect_dem(source_path),
    )
    destination = Path(manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({
        "schema": NATIVE_SCHEMA,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "native_design": "validated source registration; raster bytes remain in RAW",
        "terrain": asdict(result),
    }, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return result


def load_native_manifest(path: str | Path) -> NativeTerrain:
    source = Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
        if document["schema"] != NATIVE_SCHEMA:
            raise ValueError("unsupported schema")
        terrain = NativeTerrain(**document["terrain"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise NativeTerrainError(f"invalid Native Terrain manifest {source}: {exc}") from exc
    raw = Path(terrain.source_path)
    if not raw.is_file() or sha256_file(raw) != terrain.source_sha256:
        raise NativeTerrainError("registered RAW raster is missing or its fingerprint changed")
    if asdict(terrain) != asdict(NativeTerrain(
        source_path=terrain.source_path, source_sha256=terrain.source_sha256,
        provider=terrain.provider, source_dataset=terrain.source_dataset,
        vertical_reference_status=terrain.vertical_reference_status,
        vertical_reference=terrain.vertical_reference,
        vertical_reference_source=terrain.vertical_reference_source,
        **inspect_dem(raw),
    )):
        raise NativeTerrainError("registered raster metadata no longer matches the Native manifest")
    return terrain


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Accept a source DEM as OUEM Native Terrain v0.1")
    parser.add_argument("source")
    parser.add_argument("--output", required=True, help="Native Terrain manifest (.json)")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--source-dataset", required=True)
    parser.add_argument("--vertical-reference-status", choices=sorted(VERTICAL_STATUSES), default="unresolved")
    parser.add_argument("--vertical-reference")
    parser.add_argument("--vertical-reference-source")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = accept_native_terrain(
            args.source, args.output, provider=args.provider,
            source_dataset=args.source_dataset,
            vertical_reference_status=args.vertical_reference_status,
            vertical_reference=args.vertical_reference,
            vertical_reference_source=args.vertical_reference_source,
        )
    except (NativeTerrainError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Native Terrain accepted: {result.width} x {result.height}, {result.horizontal_crs}")
    print(f"Manifest: {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
