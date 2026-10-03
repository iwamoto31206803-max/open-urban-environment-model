"""Accepted OUEM Standard artifacts to VoxCity 1.7.0 adapter.

All GeoPandas and VoxCity work runs in the OUEM Python environment. Captured
QGIS/OSGeo4W runtimes remain confined to the upstream A1/A2 preparation stages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

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


def interface_id_properties(ouem_id: str, mapping: dict[str, int]) -> dict[str, Any]:
    """Return both the audit ID and the field actually consumed by VoxCity."""
    voxcity_id = mapping[ouem_id]
    if voxcity_id <= 0:
        raise VoxCityAdapterError("VoxCity building IDs must be positive; zero is background")
    return {"ouem_id": ouem_id, "voxcity_id": voxcity_id, "id": voxcity_id}


def grid_ground_samples(building_id_grid: Any, dem_grid: Any, building_id: int) -> list[float]:
    """Select raw VoxCity DEM cells assigned to one positive building ID."""
    if building_id <= 0:
        raise VoxCityAdapterError("building_id must be positive")
    try:
        values = dem_grid[building_id_grid == building_id]
        samples = [float(value) for value in values.flat]
    except (AttributeError, IndexError, TypeError, ValueError):
        try:
            if len(building_id_grid) != len(dem_grid):
                raise ValueError
            samples = [float(dem_value)
                       for id_row, dem_row in zip(building_id_grid, dem_grid)
                       for id_value, dem_value in zip(id_row, dem_row)
                       if id_value == building_id]
            if any(len(id_row) != len(dem_row)
                   for id_row, dem_row in zip(building_id_grid, dem_grid)):
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise VoxCityAdapterError("building and DEM grids must be aligned arrays") from exc
    if not samples:
        raise VoxCityAdapterError(f"no VoxCity grid cell assigned to building ID {building_id}")
    if not all(math.isfinite(value) for value in samples):
        raise VoxCityAdapterError(f"non-finite VoxCity DEM cell for building ID {building_id}")
    return samples


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
    """Derive height from absolute top and already grid-derived effective ground.

    ``ground_samples`` must be the raw VoxCity DEM cells selected by the actual
    ``building_id_grid``, not samples selected from the source raster directly.
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


def _z_values(geometry: Any) -> list[float]:
    if hasattr(geometry, "geoms"):
        return [z for part in geometry.geoms for z in _z_values(part)]
    if hasattr(geometry, "exterior"):
        rings = [geometry.exterior, *geometry.interiors]
        return [coordinate[2] for ring in rings for coordinate in ring.coords
                if len(coordinate) >= 3]
    return [coordinate[2] for coordinate in geometry.coords if len(coordinate) >= 3]


def build_normalized_footprint(geometry: Any, ouem_id: str) -> tuple[Any, dict[str, Any]]:
    """Union all positive-area XY projections of a Standard 3D surface set."""
    try:
        from shapely import force_2d, make_valid, normalize
        from shapely.geometry import MultiPolygon, Polygon
        from shapely.ops import unary_union
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise VoxCityAdapterError("A3 footprint construction requires Shapely 2") from exc

    def source_polygons(value: Any) -> list[Any]:
        if isinstance(value, Polygon):
            return [value]
        if hasattr(value, "geoms"):
            return [part for child in value.geoms for part in source_polygons(child)]
        return []

    def polygonal_parts(value: Any) -> list[Any]:
        if isinstance(value, Polygon):
            return [value]
        if isinstance(value, MultiPolygon) or hasattr(value, "geoms"):
            return [part for child in value.geoms for part in polygonal_parts(child)]
        return []

    surfaces = source_polygons(geometry)
    retained: list[Any] = []
    discarded = 0
    for surface in surfaces:
        projected = force_2d(surface)
        if projected.is_empty or not math.isfinite(projected.area) or projected.area <= 0:
            discarded += 1
            continue
        repaired = make_valid(projected) if not projected.is_valid else projected
        parts = [part for part in polygonal_parts(repaired)
                 if not part.is_empty and math.isfinite(part.area) and part.area > 0]
        if not parts:
            discarded += 1
            continue
        retained.extend(parts)
    if not retained:
        raise VoxCityAdapterError(
            f"building {ouem_id} has no positive-area XY footprint after projection"
        )
    # Normalization and WKB sorting make union input independent of source
    # surface ordering while retaining every plan-view support component.
    retained = sorted((normalize(part) for part in retained), key=lambda part: part.wkb)
    footprint = unary_union(retained)
    if not footprint.is_valid:
        footprint = make_valid(footprint)
    final_parts = [part for part in polygonal_parts(footprint)
                   if not part.is_empty and math.isfinite(part.area) and part.area > 0]
    if not final_parts:
        raise VoxCityAdapterError(f"building {ouem_id} footprint union is empty or degenerate")
    final_parts = sorted((normalize(part) for part in final_parts), key=lambda part: part.wkb)
    footprint = normalize(unary_union(final_parts))
    if (footprint.is_empty or footprint.geom_type not in {"Polygon", "MultiPolygon"}
            or not math.isfinite(footprint.area) or footprint.area <= 0
            or not footprint.is_valid):
        raise VoxCityAdapterError(f"building {ouem_id} has no valid normalized 2D footprint")
    diagnostics = {
        "source_geometry_type": geometry.geom_type,
        "source_surface_part_count": len(surfaces),
        "projected_positive_area_part_count": len(retained),
        "projected_discarded_zero_area_part_count": discarded,
        "projected_union_area": float(footprint.area),
        "footprint_geometry_type": footprint.geom_type,
        "footprint_valid": bool(footprint.is_valid),
    }
    return footprint, diagnostics


def _run_voxcity_grids(building_path: Path, terrain_path: Path, meshsize: float) -> dict[str, Any]:
    """Run every VoxCity operation in the current OUEM Python environment."""
    try:
        import geopandas as gpd
        import numpy as np
        import voxcity
        from voxcity.geoprocessor.raster import (
            create_building_height_grid_from_gdf_polygon,
            create_dem_grid_from_geotiff_polygon,
            process_grid,
        )
    except ImportError as exc:  # pragma: no cover - exercised in deployment environment
        raise VoxCityAdapterError(
            "A3 requires GeoPandas, Shapely, NumPy and pinned VoxCity in the OUEM environment"
        ) from exc
    if getattr(voxcity, "__version__", None) != VOXCITY_VERSION:
        raise VoxCityAdapterError(f"VoxCity {VOXCITY_VERSION} is required")
    buildings = gpd.read_file(building_path, layer="building")
    if buildings.crs is None or buildings.crs.to_epsg() != 6677:
        raise VoxCityAdapterError("Standard Building must be EPSG:6677")
    if buildings.empty or "ouem_id" not in buildings or buildings.ouem_id.isna().any():
        raise VoxCityAdapterError("Standard Building requires non-empty ouem_id")
    mapping = numeric_id_mapping(buildings.ouem_id.tolist())
    buildings = buildings[["ouem_id", "geometry"]].copy()
    z_by_ouem = {row.ouem_id: _z_values(row.geometry) for row in buildings.itertuples()}
    if any(not values or not all(math.isfinite(z) for z in values)
           for values in z_by_ouem.values()):
        raise VoxCityAdapterError("Standard Building contains missing or non-finite Z")
    footprints = {
        row.ouem_id: build_normalized_footprint(row.geometry, row.ouem_id)
        for row in buildings.itertuples()
    }
    buildings.geometry = buildings.ouem_id.map(
        {ouem_id: value[0] for ouem_id, value in footprints.items()}
    )
    buildings["voxcity_id"] = buildings.ouem_id.map(mapping)
    buildings["id"] = buildings.voxcity_id
    buildings["min_height"] = 0.0
    buildings["height"] = 1.0  # bootstrap only; replaced from grid-derived ground
    xmin, ymin, xmax, ymax = buildings.to_crs(4326).total_bounds
    rectangle = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]
    dem = create_dem_grid_from_geotiff_polygon(
        str(terrain_path), meshsize, rectangle, dem_interpolation=False
    )
    if not np.isfinite(dem).all():
        raise VoxCityAdapterError("VoxCity DEM grid contains non-finite values")
    previous_ids = None
    for _ in range(8):
        _, _, building_ids = create_building_height_grid_from_gdf_polygon(
            buildings, meshsize, rectangle, overlapping_footprint=False
        )[:3]
        records = []
        for row in buildings.itertuples():
            samples = grid_ground_samples(building_ids, dem, row.id)
            derived = derive_attributes(z_by_ouem[row.ouem_id], samples)
            records.append({"ouem_id": row.ouem_id, "voxcity_id": row.id, **derived,
                            "footprint": footprints[row.ouem_id][1]})
        buildings["height"] = buildings.ouem_id.map(
            {record["ouem_id"]: record["height"] for record in records}
        )
        if previous_ids is not None and np.array_equal(previous_ids, building_ids):
            break
        previous_ids = building_ids.copy()
    else:
        raise VoxCityAdapterError("VoxCity building-grid assignment did not converge")
    flattened = process_grid(building_ids, dem.copy())
    shift = float(np.min(dem))
    for record in records:
        actual = flattened[building_ids == record["voxcity_id"]]
        absolute_match = actual.size and np.allclose(
            actual, record["ground_eff_abs"], atol=1e-9
        )
        normalized_match = actual.size and np.allclose(
            actual + shift, record["ground_eff_abs"], atol=1e-9
        )
        if not absolute_match and not normalized_match:
            raise VoxCityAdapterError("A3 ground disagrees with VoxCity process_grid")
    geojson = json.loads(buildings.to_json(drop_id=True))
    geojson["name"] = "voxcity_buildings"
    geojson["crs"] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6677"}}
    return {"records": records, "geojson": geojson,
            "aoi": list(map(float, buildings.total_bounds)),
            "rectangle_vertices_lonlat": [[float(x), float(y)] for x, y in rectangle],
            "grid_shape": list(dem.shape), "warnings": []}


@dataclass(frozen=True)
class AdapterResult:
    buildings: int
    output: str
    manifest: str


def adapt_standard_to_voxcity(
    buildings: str | Path, terrain: str | Path, output: str | Path, *,
    meshsize: float, aoi: Sequence[float] | None = None,
) -> AdapterResult:
    """Create deterministic GeoJSON plus an audit manifest from accepted artifacts."""
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
    worker_result = _run_voxcity_grids(building_path, terrain_path, meshsize)
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
        feature["properties"].update(
            {key: value for key, value in record.items() if key != "footprint"}
        )
        feature["properties"].update(interface_id_properties(record["ouem_id"], mapping))
        ordered.append(feature)
    collection["features"] = ordered
    output_path.write_bytes(canonical_json(collection))
    manifest = {"schema": SCHEMA, "adapter_version": ADAPTER_VERSION,
        "voxcity": {"version": VOXCITY_VERSION, "commit": VOXCITY_COMMIT},
        "runtime": {"voxcity": "ouem-python-environment", "gis_runtime_role": "none"},
        "inputs": {"standard_building": {"path": str(building_path), "sha256": sha256_file(building_path)},
                   "standard_terrain": {"path": str(terrain_path), "sha256": sha256_file(terrain_path)}},
        "aoi": list(aoi) if aoi else worker_result["aoi"], "meshsize": meshsize,
        "crs": {"source": "EPSG:6677", "target": "EPSG:6677", "transform": "none"},
        "vertical_compatibility": {"status": "PASS", "building": bm["z_reference"], "terrain": tm["vertical_reference"]},
        "height_derivation": "z_top_abs - ground_eff_abs from pinned VoxCity grids",
        "ground_derivation": "mean of raw VoxCity DEM grid cells where building_id_grid == voxcity_id",
        "min_height_derivation": "constant 0.0; no inference from geometry bottom",
        "id_derivation": "lexicographic ouem_id sort, consecutive positive integers starting at 1",
        "voxcity_grid": {"shape": worker_result["grid_shape"],
                         "rectangle_vertices_lonlat": worker_result["rectangle_vertices_lonlat"]},
        "buildings": records, "warnings": worker_result.get("warnings", []),
        "output": {"path": str(output_path.resolve()), "sha256": sha256_file(output_path), "format": "GeoJSON"}}
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest_path.write_bytes(canonical_json(manifest))
    return AdapterResult(len(records), str(output_path.resolve()), str(manifest_path.resolve()))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Adapt accepted OUEM Standard Building + Terrain to VoxCity 1.7.0")
    parser.add_argument("buildings"); parser.add_argument("terrain"); parser.add_argument("--output", required=True)
    parser.add_argument("--meshsize", required=True, type=float)
    parser.add_argument("--aoi", nargs=4, type=float, metavar=("XMIN", "YMIN", "XMAX", "YMAX"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = adapt_standard_to_voxcity(args.buildings, args.terrain, args.output,
            meshsize=args.meshsize, aoi=args.aoi)
    except (VoxCityAdapterError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2
    print(f"Adapter buildings: {result.buildings}\nOutput: {result.output}\nManifest: {result.manifest}\nResult: PASS")
    return 0
