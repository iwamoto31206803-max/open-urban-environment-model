"""Native Building to OUEM Standard Building v0.1 conversion."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
import uuid

from ouem.native.building.plateau import (
    GISRuntime,
    _decode_output,
    load_gis_runtime,
    require_gdal,
)
from ouem.study_area import StudyAreaConfigError, load_study_area

SOURCE_DATASET = "PLATEAU CityGML"
OUTPUT_LAYER = "building"
ID_RULE = "oub- + UUIDv5(URL namespace, 'ouem-standard-building-v0.1|PLATEAU CityGML|<source_id>')"


class StandardBuildingError(RuntimeError):
    """Actionable failure in Native-to-Standard Building conversion."""


@dataclass
class StandardBuildingResult:
    input_path: str = ""
    output_path: str = ""
    input_layer: str = ""
    output_layer: str = OUTPUT_LAYER
    input_features: int = 0
    output_features: int = 0
    input_crs: str = ""
    output_crs: str = ""
    geometry_type: str = ""
    z_geometries: int = 0
    study_area_extent: list[float] = field(default_factory=list)
    required_metadata: bool = False
    z_preserved: bool = False
    max_z_delta: float = 0.0
    deterministic_ids: bool = False

    def summary(self) -> str:
        status = "PASS" if all((
            self.output_crs == "EPSG:6677",
            self.output_features == self.z_geometries,
            self.required_metadata,
            self.z_preserved,
            self.deterministic_ids,
        )) else "FAIL"
        return "\n".join((
            f"Input path: {self.input_path}",
            f"Output path: {self.output_path}",
            f"Input features: {self.input_features}",
            f"Selected/output features: {self.output_features}",
            f"Input CRS: {self.input_crs}",
            f"Output CRS: {self.output_crs}",
            f"Geometry type / 3D: {self.geometry_type} / {self.z_geometries == self.output_features}",
            f"Study-area extent: {self.study_area_extent}",
            f"Required metadata: {'PASS' if self.required_metadata else 'FAIL'}",
            f"Z preservation (max delta {self.max_z_delta:.3g} m): {'PASS' if self.z_preserved else 'FAIL'}",
            f"Deterministic IDs: {'PASS' if self.deterministic_ids else 'FAIL'}",
            f"Result: {status}",
        ))


def deterministic_ouem_id(source_id: str) -> str:
    """Return the documented stable identifier without depending on input order."""
    value = f"ouem-standard-building-v0.1|{SOURCE_DATASET}|{source_id}"
    return f"oub-{uuid.uuid5(uuid.NAMESPACE_URL, value)}"


def _run_worker(runtime: GISRuntime, job: dict[str, Any]) -> dict[str, Any]:
    worker = Path(__file__).with_name("_gdal_worker.py")
    with tempfile.TemporaryDirectory(prefix="ouem-standard-building-") as temporary:
        job_path = Path(temporary) / "job.json"
        result_path = Path(temporary) / "result.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        completed = subprocess.run(
            [runtime.python, str(worker), str(job_path), str(result_path)],
            capture_output=True,
            env=runtime.environment,
        )
        if completed.returncode:
            diagnostic = (_decode_output(completed.stderr, runtime).strip()
                          or _decode_output(completed.stdout, runtime).strip())
            raise StandardBuildingError(f"external GIS standardization worker failed: {diagnostic}")
        try:
            return json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StandardBuildingError(f"invalid GIS worker result: {exc}") from exc


def standardize_native_buildings(
    source: str | Path,
    output: str | Path,
    *,
    study_area_config: str | Path,
    runtime: GISRuntime,
    source_layer: str = "building",
) -> StandardBuildingResult:
    """Select intersecting buildings, reproject XY, and preserve complete XYZ geometry."""
    require_gdal(runtime)
    source_path = Path(source).resolve()
    output_path = Path(output)
    if not source_path.is_file() or source_path.suffix.lower() != ".gpkg":
        raise StandardBuildingError(f"input must be an accepted Native Building GeoPackage: {source_path}")
    area = load_study_area(study_area_config)
    if area.epsg != 6677:
        raise StandardBuildingError(f"Komae Standard Building requires EPSG:6677, config has EPSG:{area.epsg}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    values = _run_worker(runtime, {
        "source": str(source_path),
        "output": str(output_path),
        "source_layer": source_layer,
        "output_layer": OUTPUT_LAYER,
        "target_epsg": area.epsg,
        "extent": list(area.extent),
        "source_dataset": SOURCE_DATASET,
        "z_tolerance": 1e-9,
    })
    result = StandardBuildingResult(**values)
    manifest = {
        "schema": "ouem-standard-building-manifest/v0.1",
        "status": "PROVISIONAL pending A1 end-to-end VoxCity validation",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "native_input": str(source_path),
        "standard_output": str(output_path.resolve()),
        "study_area": {"id": area.id, "epsg": area.epsg, "extent": list(area.extent)},
        "coordinate_operation": (
            "accepted Native EPSG:4979 XY (EPSG:4326 horizontal component) "
            "to EPSG:6677; do not interpret Z as ellipsoidal height and restore "
            "every absolute T.P. source Z unchanged"
        ),
        "z_reference": "absolute T.P. elevation in metres",
        "selection": "2D intersection with study-area rectangle; complete selected geometry retained",
        "source_dataset": SOURCE_DATASET,
        "ouem_id_rule": ID_RULE,
        "validation": asdict(result),
    }
    output_path.with_suffix(output_path.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert accepted Native Building to OUEM Standard Building v0.1")
    parser.add_argument("source", help="accepted Native Building GeoPackage")
    parser.add_argument("--output", required=True, help="Standard Building GeoPackage under data/standard/building")
    parser.add_argument("--study-area", required=True, help="study-area YAML configuration")
    parser.add_argument("--source-layer", default="building")
    parser.add_argument("--gis-runtime", required=True, help="snapshot produced by the separate GIS runtime stage")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = standardize_native_buildings(
            args.source, args.output, study_area_config=args.study_area,
            runtime=load_gis_runtime(args.gis_runtime), source_layer=args.source_layer,
        )
    except (StandardBuildingError, StudyAreaConfigError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    return 0
