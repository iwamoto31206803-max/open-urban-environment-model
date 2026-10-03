"""Native-to-Standard Terrain v0.1 conversion."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from ouem.native.terrain import NativeTerrainError, load_native_manifest, sha256_file
from ouem.study_area import StudyAreaConfigError, load_study_area

STANDARD_NODATA = -9999.0
STANDARD_SCHEMA = "ouem-standard-terrain-manifest/v0.1"


class StandardTerrainError(RuntimeError):
    """Raised when Native Terrain cannot satisfy the v0.1 contract."""


@dataclass(frozen=True)
class StandardTerrainResult:
    input_path: str
    output_path: str
    dimensions: list[int]
    input_crs: str
    output_crs: str
    input_pixel_size: list[float]
    output_pixel_size: list[float]
    input_extent: list[float]
    output_extent: list[float]
    dtype: str
    source_nodata: float
    standard_nodata: float
    valid_cells: int
    nodata_cells: int
    valid_min: float
    valid_max: float
    grid_preserved: bool
    elevations_preserved: bool
    vertical_reference_status: str

    def summary(self) -> str:
        total = self.valid_cells + self.nodata_cells
        status = "PASS" if self.grid_preserved and self.elevations_preserved else "FAIL"
        return "\n".join((
            f"Input path: {self.input_path}", f"Output path: {self.output_path}",
            f"Raster dimensions: {self.dimensions[0]} x {self.dimensions[1]}",
            f"Input/output CRS: {self.input_crs} / {self.output_crs}",
            f"Input/output pixel size: {self.input_pixel_size} / {self.output_pixel_size}",
            f"Input extent: {self.input_extent}", f"Output extent: {self.output_extent}",
            f"Data type: {self.dtype}",
            f"Source/Standard NoData: {self.source_nodata} / {self.standard_nodata}",
            f"Valid/NoData cells: {self.valid_cells}/{self.nodata_cells} ({self.nodata_cells / total:.2%} NoData)",
            f"Valid elevation min/max: {self.valid_min} / {self.valid_max}",
            f"Grid preservation: {'PASS' if self.grid_preserved else 'FAIL'}",
            f"Elevation preservation: {'PASS' if self.elevations_preserved else 'FAIL'}",
            f"Vertical reference status: {self.vertical_reference_status}",
            f"Result: {status}",
        ))


def standardize_native_terrain(
    native_manifest: str | Path, output: str | Path, *, study_area_config: str | Path
) -> StandardTerrainResult:
    """Normalize NoData while preserving the compliant EPSG:6677 grid and values."""
    try:
        import numpy as np
        import rasterio
    except ImportError as exc:  # pragma: no cover
        raise StandardTerrainError("Terrain commands require rasterio and numpy") from exc

    native = load_native_manifest(native_manifest)
    area = load_study_area(study_area_config)
    if area.epsg != 6677:
        raise StandardTerrainError(f"Terrain v0.1 requires EPSG:6677, config has EPSG:{area.epsg}")
    if native.horizontal_crs != "EPSG:6677":
        raise StandardTerrainError(
            f"Terrain v0.1 does not reproject; expected EPSG:6677, found {native.horizontal_crs}"
        )
    if native.dtype != "float32":
        raise StandardTerrainError(f"Terrain v0.1 requires Float32 input, found {native.dtype}")
    source_path = Path(native.source_path)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with rasterio.open(source_path) as src:
            values = src.read(1, masked=True)
            mask = np.ma.getmaskarray(values)
            valid_before = values.data[~mask].copy()
            output_values = values.filled(STANDARD_NODATA).astype("float32", copy=False)
            profile = src.profile.copy()
            profile.update(driver="GTiff", dtype="float32", count=1,
                           nodata=STANDARD_NODATA, compress="deflate")
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(output_values, 1)
                dst.update_tags(
                    OUEM_SCHEMA="standard-terrain/v0.1",
                    VERTICAL_REFERENCE_STATUS=native.vertical_reference_status,
                    VERTICAL_REFERENCE=native.vertical_reference or "",
                )
        with rasterio.open(output_path) as dst:
            written = dst.read(1, masked=True)
            out_mask = np.ma.getmaskarray(written)
            grid_preserved = (
                dst.width == native.width and dst.height == native.height
                and list(dst.transform)[:6] == native.transform
                and f"EPSG:{dst.crs.to_epsg()}" == native.horizontal_crs
                and [abs(dst.transform.a), abs(dst.transform.e)] == native.pixel_size
                and [dst.bounds.left, dst.bounds.bottom, dst.bounds.right, dst.bounds.top] == native.extent
            )
            elevations_preserved = np.array_equal(mask, out_mask) and np.array_equal(
                valid_before, written.data[~out_mask]
            )
            result = StandardTerrainResult(
                input_path=str(source_path), output_path=str(output_path.resolve()),
                dimensions=[dst.width, dst.height], input_crs=native.horizontal_crs,
                output_crs=f"EPSG:{dst.crs.to_epsg()}",
                input_pixel_size=native.pixel_size,
                output_pixel_size=[abs(dst.transform.a), abs(dst.transform.e)],
                input_extent=native.extent,
                output_extent=[dst.bounds.left, dst.bounds.bottom, dst.bounds.right, dst.bounds.top],
                dtype=dst.dtypes[0], source_nodata=native.source_nodata,
                standard_nodata=float(dst.nodata), valid_cells=native.valid_cells,
                nodata_cells=native.nodata_cells, valid_min=native.valid_min,
                valid_max=native.valid_max, grid_preserved=grid_preserved,
                elevations_preserved=elevations_preserved,
                vertical_reference_status=native.vertical_reference_status,
            )
    except StandardTerrainError:
        raise
    except Exception as exc:
        raise StandardTerrainError(f"could not write Standard Terrain: {exc}") from exc
    if not result.grid_preserved or not result.elevations_preserved:
        output_path.unlink(missing_ok=True)
        raise StandardTerrainError("written GeoTIFF failed grid/elevation preservation validation")
    manifest = {
        "schema": STANDARD_SCHEMA,
        "status": "PROVISIONAL pending local real-data and downstream adapter validation",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "native_manifest": str(Path(native_manifest).resolve()),
        "source": {
            "provider": native.provider, "dataset": native.source_dataset,
            "input_path": native.source_path, "sha256": native.source_sha256,
            "crs": native.horizontal_crs, "resolution": native.pixel_size,
            "nodata": native.source_nodata,
        },
        "standard": {
            "output_path": str(output_path.resolve()), "sha256": sha256_file(output_path),
            "crs": result.output_crs, "resolution": result.output_pixel_size,
            "nodata": STANDARD_NODATA, "dtype": "float32",
        },
        "vertical_reference": {
            "status": native.vertical_reference_status,
            "name": native.vertical_reference, "source": native.vertical_reference_source,
        },
        "processing": "No reprojection or resampling; source mask normalized to -9999.0; valid Float32 cells unchanged",
        "validation": asdict(result),
    }
    output_path.with_suffix(output_path.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert accepted Native Terrain to OUEM Standard Terrain v0.1")
    parser.add_argument("source", help="accepted Native Terrain manifest")
    parser.add_argument("--output", required=True)
    parser.add_argument("--study-area", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = standardize_native_terrain(args.source, args.output, study_area_config=args.study_area)
    except (StandardTerrainError, NativeTerrainError, StudyAreaConfigError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
