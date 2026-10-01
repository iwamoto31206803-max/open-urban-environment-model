"""PLATEAU CityGML to OUEM Standard Building v0.1 pipeline.

GDAL is intentionally loaded at run time: importing OUEM and inspecting the
CLI remain possible on hosts where the external geospatial runtime has not yet
been installed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ouem.study_area import StudyArea, load_study_area

PROVIDER = "PLATEAU"
SOURCE_CRS = "EPSG:6697"
VERTICAL_INTERPRETATION = "absolute T.P. (Tokyo Peil) elevation"
ID_NAMESPACE = uuid.UUID("c99b9acf-e4c4-5ab0-83b0-c72cdad6a585")


class PlateauBuildingError(RuntimeError):
    """Actionable failure in the PLATEAU building pipeline."""


@dataclass(frozen=True)
class GISRuntime:
    """External GIS executables and environment for child processes only."""

    python: str
    ogr2ogr: str = "ogr2ogr"
    ogrinfo: str = "ogrinfo"
    environment: dict[str, str] | None = None


def load_gis_runtime(path: str | Path) -> GISRuntime:
    """Load a runtime snapshot created by the separate GIS acceptance stage."""
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        return GISRuntime(
            python=value["python"],
            ogr2ogr=value["ogr2ogr"],
            ogrinfo=value["ogrinfo"],
            environment=value.get("environment"),
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise PlateauBuildingError(f"invalid GIS runtime snapshot {source}: {exc}") from exc


@dataclass(frozen=True)
class DiscoveryResult:
    accepted: tuple[Path, ...]
    skipped: tuple[Path, ...]

    @property
    def discovered(self) -> int:
        return len(self.accepted) + len(self.skipped)


@dataclass
class PlateauRunResult:
    gml_discovered: int = 0
    gml_accepted: int = 0
    gml_skipped: int = 0
    source_features: int = 0
    native_features: int = 0
    standard_features: int = 0
    study_area_intersections: int = 0
    native_reused: int = 0
    native_created: int = 0
    invalid_geometries: int = 0
    failed_geometries: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return "\n".join(
            (
                f"GML discovered/accepted/skipped: {self.gml_discovered}/{self.gml_accepted}/{self.gml_skipped}",
                f"Source/native/standard features: {self.source_features}/{self.native_features}/{self.standard_features}",
                f"Study-area intersections: {self.study_area_intersections}",
                f"Native reused/new: {self.native_reused}/{self.native_created}",
                f"Invalid/failed geometries: {self.invalid_geometries}/{self.failed_geometries}",
            )
        )


def discover_building_gml(dataset_dir: str | Path) -> DiscoveryResult:
    """Find packaged and conservatively named standalone building GML files."""
    root = Path(dataset_dir)
    if not root.is_dir():
        raise PlateauBuildingError(f"provider dataset directory not found: {root}")
    accepted: list[Path] = []
    skipped: list[Path] = []
    for path in sorted((p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".gml"), key=lambda p: p.as_posix()):
        parts = [part.lower() for part in path.relative_to(root).parts[:-1]]
        in_building_tree = any(
            parts[index : index + 2] == ["udx", "bldg"]
            for index in range(len(parts) - 1)
        )
        name = path.name.lower()
        standalone_building = (
            path.parent == root
            and "_bldg_" in name
            and name.endswith("_op.gml")
        )
        is_building = in_building_tree or standalone_building
        (accepted if is_building else skipped).append(path)
    return DiscoveryResult(tuple(accepted), tuple(skipped))


def deterministic_ouem_id(source_dataset: str, source_id: str, geometry_fingerprint: str = "") -> str:
    """Return a stable ID independent of source iteration order."""
    identity = f"{PROVIDER}\0{source_dataset}\0{source_id or geometry_fingerprint}"
    return str(uuid.uuid5(ID_NAMESPACE, identity))


def intersects_extent(envelope: Sequence[float], extent: Sequence[float]) -> bool:
    """Test closed 2D envelope intersection; touching the boundary counts."""
    min_x, max_x, min_y, max_y = envelope
    xmin, ymin, xmax, ymax = extent
    return not (max_x < xmin or min_x > xmax or max_y < ymin or min_y > ymax)


def build_native_command(source: Path, output: Path, source_layer: str = "Building", ogr2ogr: str = "ogr2ogr") -> list[str]:
    """Build the GDAL conversion command used for one source package file."""
    return [
        ogr2ogr, "-f", "GPKG", str(output), str(source), source_layer,
        "-nln", "building", "-dim", "XYZ",
        "-lco", "SPATIAL_INDEX=YES",
    ]


def _native_name(root: Path, source: Path) -> str:
    relative = source.relative_to(root).as_posix()
    return f"{source.stem}-{hashlib.sha256(relative.encode()).hexdigest()[:12]}.gpkg"


def _native_receipt(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _receipt_value(source: Path, command: Sequence[str]) -> dict[str, Any]:
    stat = source.stat()
    return {
        "provider": PROVIDER,
        "source_file": str(source.resolve()),
        "source_crs": SOURCE_CRS,
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "command": list(command),
    }


def _receipt_matches(source: Path, output: Path, command: Sequence[str]) -> bool:
    receipt = _native_receipt(output)
    if not output.is_file() or not receipt.is_file() or output.stat().st_size == 0:
        return False
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data == _receipt_value(source, command)


def _write_receipt(source: Path, output: Path, command: Sequence[str]) -> None:
    _native_receipt(output).write_text(
        json.dumps(_receipt_value(source, command), indent=2) + "\n",
        encoding="utf-8",
    )


def require_gdal(runtime: GISRuntime) -> None:
    """Validate external GIS tools without importing GDAL into OUEM Python."""
    missing = []
    for executable in (runtime.ogr2ogr, runtime.ogrinfo):
        if shutil.which(executable, path=(runtime.environment or {}).get("PATH")) is None:
            missing.append(f"{executable} executable")
    gis_python_path = shutil.which(runtime.python, path=(runtime.environment or {}).get("PATH"))
    if gis_python_path is None:
        missing.append(f"GIS Python ({runtime.python})")
    if missing:
        raise PlateauBuildingError("GDAL is required; missing " + " and ".join(missing))
    check = subprocess.run(
        [gis_python_path, "-c", "from osgeo import ogr, osr"],
        text=True,
        capture_output=True,
        env=runtime.environment,
    )
    if check.returncode:
        raise PlateauBuildingError(
            f"GIS Python cannot import osgeo.ogr/osgeo.osr: {gis_python_path}: "
            f"{check.stderr.strip()}"
        )


def _count_layer(path: Path, runtime: GISRuntime) -> int:
    completed = subprocess.run(
        [runtime.ogrinfo, "-json", "-so", str(path), "building"],
        text=True,
        capture_output=True,
        env=runtime.environment,
    )
    if completed.returncode:
        raise PlateauBuildingError(
            f"GDAL could not inspect Native output {path}: {completed.stderr.strip()}"
        )
    try:
        info = json.loads(completed.stdout)
        return max(0, int(info["layers"][0]["featureCount"]))
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PlateauBuildingError(f"unexpected ogrinfo output for {path}: {exc}") from exc


def _valid_native(path: Path, runtime: GISRuntime) -> bool:
    try:
        _count_layer(path, runtime)
    except PlateauBuildingError:
        return False
    return True


def _create_standard(runtime: GISRuntime, native_sources: Sequence[tuple[Path, Path]], output: Path, area: StudyArea, result: PlateauRunResult) -> None:
    """Delegate OGR work to a standalone worker in the external GIS Python."""
    output.parent.mkdir(parents=True, exist_ok=True)
    job = {
        "native_sources": [
            {"native": str(native), "source": source.as_posix()}
            for native, source in native_sources
        ],
        "output": str(output),
        "target_epsg": area.epsg,
        "extent": list(area.extent),
    }
    worker = Path(__file__).with_name("_plateau_gdal_worker.py")
    with tempfile.TemporaryDirectory(prefix="ouem-plateau-") as temporary:
        job_path = Path(temporary) / "job.json"
        result_path = Path(temporary) / "result.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        completed = subprocess.run(
            [runtime.python, str(worker), str(job_path), str(result_path)],
            text=True,
            capture_output=True,
            env=runtime.environment,
        )
        if completed.returncode:
            raise PlateauBuildingError(
                "external GDAL worker failed: " + (completed.stderr.strip() or completed.stdout.strip())
            )
        worker_result = json.loads(result_path.read_text(encoding="utf-8"))
    result.standard_features = worker_result["standard_features"]
    result.study_area_intersections = worker_result["study_area_intersections"]
    result.invalid_geometries = worker_result["invalid_geometries"]
    result.failed_geometries = worker_result["failed_geometries"]
    result.warnings.extend(worker_result["warnings"])


def write_manifest(path: str | Path, *, dataset_dir: Path, sources: Sequence[Path], native_outputs: Sequence[Path], standard_output: Path, area: StudyArea, parameters: dict[str, Any], result: PlateauRunResult) -> None:
    """Write the restart/audit manifest adjacent to the Standard dataset."""
    root = dataset_dir.resolve()
    def relative(value: Path) -> str:
        try:
            return value.resolve().relative_to(root).as_posix()
        except ValueError:
            return str(value.resolve())
    manifest = {
        "schema": "ouem-plateau-building-run/v0.1",
        "provider": PROVIDER,
        "source": {
            "dataset": str(root),
            "files": [relative(p) for p in sources],
            "crs": SOURCE_CRS,
            "coordinate_reference": "JGD2011 geographic coordinates with T.P. elevation",
        },
        "native_outputs": [str(p.resolve()) for p in native_outputs],
        "standard_output": str(standard_output.resolve()),
        "target_crs": f"EPSG:{area.epsg}",
        "vertical": {"interpretation": VERTICAL_INTERPRETATION, "unit": "metre"},
        "study_area": {"id": area.id, "extent": list(area.extent)},
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "parameters": parameters,
        "counts": {key: value for key, value in asdict(result).items() if isinstance(value, int)},
        "warnings": result.warnings,
        "errors": result.errors,
    }
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_plateau_building_pipeline(dataset_dir: str | Path, study_area_config: str | Path, native_dir: str | Path, standard_output: str | Path, *, runtime: GISRuntime, source_layer: str = "Building", force: bool = False) -> PlateauRunResult:
    """Run discovery, restartable Native conversion, and Standard selection."""
    require_gdal(runtime)
    root = Path(dataset_dir).resolve()
    area = load_study_area(study_area_config)
    discovery = discover_building_gml(root)
    if not discovery.accepted:
        raise PlateauBuildingError(f"no PLATEAU building GML found beneath {root} (expected udx/bldg/*.gml)")
    result = PlateauRunResult(discovery.discovered, len(discovery.accepted), len(discovery.skipped))
    native_root = Path(native_dir)
    native_root.mkdir(parents=True, exist_ok=True)
    native_sources: list[tuple[Path, Path]] = []
    for source in discovery.accepted:
        output = native_root / _native_name(root, source)
        command = build_native_command(source, output, source_layer, runtime.ogr2ogr)
        if not force and _receipt_matches(source, output, command) and _valid_native(output, runtime):
            result.native_reused += 1
        else:
            completed = subprocess.run(command, text=True, capture_output=True, env=runtime.environment)
            if completed.returncode:
                result.errors.append(f"Native conversion failed for {source}: {completed.stderr.strip()}")
                raise PlateauBuildingError(result.errors[-1])
            _write_receipt(source, output, command)
            result.native_created += 1
        count = _count_layer(output, runtime)
        result.source_features += count
        result.native_features += count
        native_sources.append((output, source.relative_to(root)))
    standard = Path(standard_output)
    _create_standard(runtime, native_sources, standard, area, result)
    parameters = {"source_layer": source_layer, "force": force, "gis_python": runtime.python, "selection": "intersects; complete geometry retained"}
    write_manifest(standard.with_suffix(standard.suffix + ".manifest.json"), dataset_dir=root, sources=list(discovery.accepted), native_outputs=[item[0] for item in native_sources], standard_output=standard, area=area, parameters=parameters, result=result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build OUEM Standard Building v0.1 from a downloaded PLATEAU dataset")
    parser.add_argument("dataset_dir", help="PLATEAU package root containing udx/bldg GML files")
    parser.add_argument("--study-area", required=True, help="canonical OUEM study-area YAML")
    parser.add_argument("--native-dir", required=True, help="directory for restartable Native GeoPackages")
    parser.add_argument("--output", required=True, help="single Standard Building GeoPackage")
    parser.add_argument("--source-layer", default="Building", help="OGR CityGML building layer name")
    parser.add_argument("--force", action="store_true", help="rebuild Native outputs even when valid receipts match")
    parser.add_argument("--gis-runtime", required=True, help="snapshot produced by the separate GIS runtime stage")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        runtime = load_gis_runtime(args.gis_runtime)
        result = run_plateau_building_pipeline(args.dataset_dir, args.study_area, args.native_dir, args.output, runtime=runtime, source_layer=args.source_layer, force=args.force)
    except (PlateauBuildingError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
