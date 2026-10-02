"""Ingest PLATEAU GIS Converter 3D GeoPackages as OUEM Native Building."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PROVIDER = "PLATEAU"
PREPROCESSOR = "PLATEAU GIS Converter GUI"


class PlateauBuildingError(RuntimeError):
    """Actionable failure in the PLATEAU building ingest."""


@dataclass(frozen=True)
class GISRuntime:
    """External GIS executables and environment for child processes only."""

    python: str
    ogr2ogr: str = "ogr2ogr"
    ogrinfo: str = "ogrinfo"
    output_encoding: str | None = None
    environment: dict[str, str] | None = None


@dataclass
class PlateauRunResult:
    input_layer: str = ""
    output_layer: str = "building"
    input_features: int = 0
    output_features: int = 0
    non_empty_geometries: int = 0
    z_geometries: int = 0
    geometry_type: str = ""
    crs: str = ""
    preserved_fields: list[str] = field(default_factory=list)
    reused: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return "\n".join(
            (
                f"Input/output features: {self.input_features}/{self.output_features}",
                f"Layer: {self.input_layer} -> {self.output_layer}",
                f"Geometry type: {self.geometry_type}",
                f"CRS: {self.crs}",
                f"Non-empty/Z geometries: {self.non_empty_geometries}/{self.z_geometries}",
                f"Native output: {'reused' if self.reused else 'created'}",
                f"Preserved fields: {', '.join(self.preserved_fields)}",
            )
        )


def load_gis_runtime(path: str | Path) -> GISRuntime:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        return GISRuntime(
            python=value["python"],
            ogr2ogr=value["ogr2ogr"],
            ogrinfo=value["ogrinfo"],
            output_encoding=value.get("output_encoding"),
            environment=value.get("environment"),
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise PlateauBuildingError(f"invalid GIS runtime snapshot {source}: {exc}") from exc


def _decode_output(value: bytes | str | None, runtime: GISRuntime) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    encodings = ["utf-8-sig"]
    if runtime.output_encoding:
        encodings.append(runtime.output_encoding)
    for encoding in encodings:
        try:
            return value.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return value.decode("utf-8", errors="replace")


def require_gdal(runtime: GISRuntime) -> None:
    """Validate child-process GIS Python without importing osgeo into OUEM."""
    gis_python = shutil.which(
        runtime.python, path=(runtime.environment or {}).get("PATH")
    )
    if gis_python is None:
        raise PlateauBuildingError(f"GIS Python not found: {runtime.python}")
    completed = subprocess.run(
        [gis_python, "-c", "from osgeo import ogr, osr"],
        capture_output=True,
        env=runtime.environment,
    )
    if completed.returncode:
        raise PlateauBuildingError(
            "GIS Python cannot import osgeo.ogr/osgeo.osr: "
            + _decode_output(completed.stderr, runtime).strip()
        )


def _source_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".receipt.json")


def _receipt_value(source: Path, source_layer: str | None) -> dict[str, Any]:
    return {
        "schema": "ouem-plateau-native-receipt/v0.1",
        "provider": PROVIDER,
        "preprocessor": PREPROCESSOR,
        "source_file": str(source.resolve()),
        "source_sha256": _source_fingerprint(source),
        "source_layer": source_layer,
    }


def _receipt_matches(source: Path, output: Path, source_layer: str | None) -> bool:
    receipt = _receipt_path(output)
    if not output.is_file() or output.stat().st_size == 0 or not receipt.is_file():
        return False
    try:
        recorded = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return recorded == _receipt_value(source, source_layer)


def _run_worker(
    runtime: GISRuntime,
    *,
    mode: str,
    source: Path,
    output: Path | None = None,
    source_layer: str | None = None,
) -> dict[str, Any]:
    worker = Path(__file__).with_name("_plateau_gdal_worker.py")
    job = {
        "mode": mode,
        "source": str(source),
        "output": str(output) if output else None,
        "source_layer": source_layer,
        "output_layer": "building",
        "required_fields": ["measuredHeight"],
    }
    with tempfile.TemporaryDirectory(prefix="ouem-plateau-") as temporary:
        job_path = Path(temporary) / "job.json"
        result_path = Path(temporary) / "result.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        completed = subprocess.run(
            [runtime.python, str(worker), str(job_path), str(result_path)],
            capture_output=True,
            env=runtime.environment,
        )
        if completed.returncode:
            diagnostic = (
                _decode_output(completed.stderr, runtime).strip()
                or _decode_output(completed.stdout, runtime).strip()
            )
            raise PlateauBuildingError(f"external GIS ingest worker failed: {diagnostic}")
        try:
            return json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PlateauBuildingError(f"invalid GIS worker result: {exc}") from exc


def write_manifest(
    path: str | Path,
    *,
    source: Path,
    output: Path,
    source_fingerprint: str,
    source_layer_requested: str | None,
    runtime: GISRuntime,
    result: PlateauRunResult,
) -> None:
    manifest = {
        "schema": "ouem-plateau-native-ingest/v0.1",
        "provider": PROVIDER,
        "manual_preprocessor": PREPROCESSOR,
        "source": {
            "file": str(source.resolve()),
            "sha256": source_fingerprint,
            "layer_requested": source_layer_requested,
            "layer_resolved": result.input_layer,
        },
        "native_output": str(output.resolve()),
        "gis_python": runtime.python,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "validation": asdict(result),
        "parameters": {
            "geometry_operation": "copy without clipping or dimensional reduction",
            "output_layer": result.output_layer,
        },
        "warnings": result.warnings,
        "errors": result.errors,
    }
    destination = Path(path)
    destination.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def ingest_converter_geopackage(
    source: str | Path,
    output: str | Path,
    *,
    runtime: GISRuntime,
    source_layer: str | None = None,
    force: bool = False,
) -> PlateauRunResult:
    """Copy a validated Converter building layer into OUEM Native Building."""
    require_gdal(runtime)
    source_path = Path(source).resolve()
    output_path = Path(output)
    if not source_path.is_file() or source_path.suffix.lower() != ".gpkg":
        raise PlateauBuildingError(
            f"input must be a PLATEAU GIS Converter GeoPackage: {source_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reused = not force and _receipt_matches(
        source_path, output_path, source_layer
    )
    if reused:
        worker_result = _run_worker(
            runtime,
            mode="compare",
            source=source_path,
            output=output_path,
            source_layer=source_layer,
        )
    else:
        worker_result = _run_worker(
            runtime,
            mode="ingest",
            source=source_path,
            output=output_path,
            source_layer=source_layer,
        )
        _receipt_path(output_path).write_text(
            json.dumps(_receipt_value(source_path, source_layer), indent=2) + "\n",
            encoding="utf-8",
        )

    result = PlateauRunResult(**worker_result, reused=reused)
    if result.output_features != result.input_features:
        raise PlateauBuildingError(
            "unreasonable feature loss during ingest: "
            f"{result.input_features} input, {result.output_features} output"
        )
    fingerprint = _source_fingerprint(source_path)
    write_manifest(
        output_path.with_suffix(output_path.suffix + ".manifest.json"),
        source=source_path,
        output=output_path,
        source_fingerprint=fingerprint,
        source_layer_requested=source_layer,
        runtime=runtime,
        result=result,
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest a PLATEAU GIS Converter 3D GeoPackage as OUEM Native Building"
    )
    parser.add_argument("source", help="PLATEAU GIS Converter GeoPackage")
    parser.add_argument(
        "--output",
        required=True,
        help="OUEM Native Building GeoPackage under data/native/building",
    )
    parser.add_argument(
        "--source-layer",
        help="building layer name; omit for conservative automatic resolution",
    )
    parser.add_argument("--force", action="store_true", help="rebuild output")
    parser.add_argument(
        "--gis-runtime",
        required=True,
        help="snapshot produced by the separate GIS runtime stage",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = ingest_converter_geopackage(
            args.source,
            args.output,
            runtime=load_gis_runtime(args.gis_runtime),
            source_layer=args.source_layer,
            force=args.force,
        )
    except (PlateauBuildingError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
