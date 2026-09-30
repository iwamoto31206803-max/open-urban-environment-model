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
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from ouem.study_area import StudyArea, load_study_area

PROVIDER = "PLATEAU"
SOURCE_CRS = "EPSG:6697"
VERTICAL_INTERPRETATION = "absolute T.P. (Tokyo Peil) elevation"
ID_NAMESPACE = uuid.UUID("c99b9acf-e4c4-5ab0-83b0-c72cdad6a585")


class PlateauBuildingError(RuntimeError):
    """Actionable failure in the PLATEAU building pipeline."""


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
    """Recursively find GML files located in a PLATEAU ``udx/bldg`` tree."""
    root = Path(dataset_dir)
    if not root.is_dir():
        raise PlateauBuildingError(f"provider dataset directory not found: {root}")
    accepted: list[Path] = []
    skipped: list[Path] = []
    for path in sorted((p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".gml"), key=lambda p: p.as_posix()):
        parts = [part.lower() for part in path.relative_to(root).parts[:-1]]
        is_building = any(parts[index : index + 2] == ["udx", "bldg"] for index in range(len(parts) - 1))
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


def build_native_command(source: Path, output: Path, source_layer: str = "Building") -> list[str]:
    """Build the GDAL conversion command used for one source package file."""
    return [
        "ogr2ogr", "-f", "GPKG", str(output), str(source), source_layer,
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


def require_gdal() -> tuple[Any, Any]:
    """Return OGR/OSR or raise a clear installation error before processing."""
    missing = []
    if shutil.which("ogr2ogr") is None:
        missing.append("ogr2ogr executable")
    try:
        from osgeo import ogr, osr
    except ImportError:
        ogr = osr = None
        missing.append("Python GDAL bindings (osgeo)")
    if missing:
        raise PlateauBuildingError("GDAL is required; missing " + " and ".join(missing))
    return ogr, osr


def _field_value(feature: Any, candidates: Iterable[str]) -> Any:
    names = {feature.GetFieldDefnRef(index).GetName().lower(): index for index in range(feature.GetFieldCount())}
    for candidate in candidates:
        if candidate.lower() in names:
            return feature.GetField(names[candidate.lower()])
    return None


def _count_layer(ogr: Any, path: Path) -> int:
    dataset = ogr.Open(str(path), 0)
    if dataset is None or dataset.GetLayerCount() < 1:
        raise PlateauBuildingError(f"GDAL could not open Native output: {path}")
    layer = dataset.GetLayerByName("building") or dataset.GetLayer(0)
    return max(0, layer.GetFeatureCount())


def _valid_native(ogr: Any, path: Path) -> bool:
    try:
        _count_layer(ogr, path)
    except PlateauBuildingError:
        return False
    return True


def _create_standard(ogr: Any, osr: Any, native_sources: Sequence[tuple[Path, Path]], output: Path, area: StudyArea, result: PlateauRunResult) -> None:
    driver = ogr.GetDriverByName("GPKG")
    if driver is None:
        raise PlateauBuildingError("GDAL GPKG driver is unavailable")
    if output.exists():
        driver.DeleteDataSource(str(output))
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(area.epsg)
    output.parent.mkdir(parents=True, exist_ok=True)
    target = driver.CreateDataSource(str(output))
    if target is None:
        raise PlateauBuildingError(f"cannot create Standard output: {output}")
    layer = target.CreateLayer("building", target_srs, ogr.wkbUnknown, options=["SPATIAL_INDEX=YES"])
    for name, field_type in (("ouem_id", ogr.OFTString), ("source_id", ogr.OFTString), ("source_dataset", ogr.OFTString), ("source_lod", ogr.OFTString), ("measured_height", ogr.OFTReal)):
        layer.CreateField(ogr.FieldDefn(name, field_type))
    definition = layer.GetLayerDefn()
    bbox = ogr.CreateGeometryFromWkt(f"POLYGON (({area.xmin} {area.ymin}, {area.xmax} {area.ymin}, {area.xmax} {area.ymax}, {area.xmin} {area.ymax}, {area.xmin} {area.ymin}))")

    for native_path, source_path in native_sources:
        dataset = ogr.Open(str(native_path), 0)
        source_layer = dataset.GetLayerByName("building") or dataset.GetLayer(0)
        source_srs = source_layer.GetSpatialRef()
        if source_srs is None:
            source_srs = osr.SpatialReference()
            source_srs.ImportFromEPSG(6697)
            result.warnings.append(f"Native CRS missing; assumed {SOURCE_CRS}: {native_path}")
        # Transform only the horizontal component. Passing the compound source
        # CRS to PROJ could apply an unintended vertical operation; Standard
        # Building v0.1 requires source T.P. Z values to remain absolute T.P.
        horizontal_srs = source_srs.CloneGeogCS() or source_srs
        transform = osr.CoordinateTransformation(horizontal_srs, target_srs)
        relative_source = source_path.as_posix()
        for feature in source_layer:
            geometry = feature.GetGeometryRef()
            if geometry is None:
                result.failed_geometries += 1
                continue
            geometry = geometry.Clone()
            if not geometry.IsValid():
                result.invalid_geometries += 1
            if geometry.Transform(transform) != 0:
                result.failed_geometries += 1
                continue
            if not intersects_extent(geometry.GetEnvelope(), area.extent) or not geometry.Intersects(bbox):
                continue
            source_id = _field_value(feature, ("gml_id", "gml:id", "id", "identifier"))
            fingerprint = hashlib.sha256(bytes(geometry.ExportToWkb())).hexdigest()
            standard = ogr.Feature(definition)
            standard.SetField("ouem_id", deterministic_ouem_id(relative_source, str(source_id or ""), fingerprint))
            standard.SetField("source_id", str(source_id or ""))
            standard.SetField("source_dataset", relative_source)
            lod = _field_value(feature, ("source_lod", "lod", "lod_type", "lod0", "lod1", "lod2", "lod3", "lod4"))
            if lod is not None:
                standard.SetField("source_lod", str(lod))
            height = _field_value(feature, ("measuredheight", "measured_height", "bldg_measuredheight"))
            if height is not None:
                try:
                    standard.SetField("measured_height", float(height))
                except (TypeError, ValueError):
                    result.warnings.append(f"invalid measured height for {source_id} in {source_path}")
            standard.SetGeometry(geometry)  # complete geometry: selection, never clipping
            if layer.CreateFeature(standard) != 0:
                result.failed_geometries += 1
                continue
            result.study_area_intersections += 1
    target = None
    result.standard_features = result.study_area_intersections


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


def run_plateau_building_pipeline(dataset_dir: str | Path, study_area_config: str | Path, native_dir: str | Path, standard_output: str | Path, *, source_layer: str = "Building", force: bool = False) -> PlateauRunResult:
    """Run discovery, restartable Native conversion, and Standard selection."""
    ogr, osr = require_gdal()
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
        command = build_native_command(source, output, source_layer)
        if not force and _receipt_matches(source, output, command) and _valid_native(ogr, output):
            result.native_reused += 1
        else:
            completed = subprocess.run(command, text=True, capture_output=True)
            if completed.returncode:
                result.errors.append(f"Native conversion failed for {source}: {completed.stderr.strip()}")
                raise PlateauBuildingError(result.errors[-1])
            _write_receipt(source, output, command)
            result.native_created += 1
        count = _count_layer(ogr, output)
        result.source_features += count
        result.native_features += count
        native_sources.append((output, source.relative_to(root)))
    standard = Path(standard_output)
    _create_standard(ogr, osr, native_sources, standard, area, result)
    parameters = {"source_layer": source_layer, "force": force, "selection": "intersects; complete geometry retained"}
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_plateau_building_pipeline(args.dataset_dir, args.study_area, args.native_dir, args.output, source_layer=args.source_layer, force=args.force)
    except (PlateauBuildingError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
