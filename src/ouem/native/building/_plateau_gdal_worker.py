"""Standalone OGR worker for PLATEAU GIS Converter GeoPackage ingest.

It is executed only as a child process of OUEM and imports no OUEM modules.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def _resolve_layer(dataset, requested):
    if requested:
        layer = dataset.GetLayerByName(requested)
        if layer is None:
            raise RuntimeError(f"requested building layer not found: {requested}")
        return layer

    layers = [dataset.GetLayer(index) for index in range(dataset.GetLayerCount())]
    exact = [
        layer
        for layer in layers
        if layer.GetName().rsplit(":", 1)[-1].casefold()
        in {"building", "buildings", "bldg"}
    ]
    if len(exact) == 1:
        return exact[0]
    named = [
        layer for layer in layers
        if "building" in layer.GetName().lower()
        or "bldg" in layer.GetName().lower()
    ]
    if len(named) == 1:
        return named[0]
    available = ", ".join(layer.GetName() for layer in layers)
    if not named:
        raise RuntimeError(
            "could not find a building layer; "
            f"use --source-layer (available: {available})"
        )
    raise RuntimeError(
        "could not resolve exactly one building layer; "
        f"use --source-layer (available: {available})"
    )


def _field_names(layer):
    definition = layer.GetLayerDefn()
    return [
        definition.GetFieldDefn(index).GetName()
        for index in range(definition.GetFieldCount())
    ]


def _crs_label(spatial_reference):
    if spatial_reference is None:
        raise RuntimeError("building layer CRS is undefined")
    authority_name = spatial_reference.GetAuthorityName(None)
    authority_code = spatial_reference.GetAuthorityCode(None)
    if authority_name and authority_code:
        return f"{authority_name}:{authority_code}"
    if not spatial_reference.ExportToWkt():
        raise RuntimeError("building layer CRS is undefined")
    return "defined (WKT)"


def _has_xyz_coordinate(geometry):
    for index in range(geometry.GetPointCount()):
        point = geometry.GetPoint(index)
        if len(point) >= 3 and all(math.isfinite(value) for value in point[:3]):
            return True
    return any(
        _has_xyz_coordinate(geometry.GetGeometryRef(index))
        for index in range(geometry.GetGeometryCount())
    )


def _validate_layer(layer, required_fields):
    feature_count = layer.GetFeatureCount()
    if feature_count <= 0:
        raise RuntimeError("building layer has no features")
    fields = _field_names(layer)
    fields_lower = {name.lower() for name in fields}
    missing = [name for name in required_fields if name.lower() not in fields_lower]
    if missing:
        raise RuntimeError("required building attributes missing: " + ", ".join(missing))

    non_empty = 0
    with_z = 0
    layer.ResetReading()
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.IsEmpty():
            continue
        non_empty += 1
        if (
            geometry.Is3D()
            and geometry.GetCoordinateDimension() >= 3
            and _has_xyz_coordinate(geometry)
        ):
            with_z += 1
    if non_empty != feature_count:
        raise RuntimeError(
            f"empty building geometry found: {non_empty}/{feature_count} non-empty"
        )
    if with_z != feature_count:
        raise RuntimeError(
            f"building geometry without Z found: {with_z}/{feature_count} have Z"
        )
    return {
        "features": feature_count,
        "non_empty_geometries": non_empty,
        "z_geometries": with_z,
        "crs": _crs_label(layer.GetSpatialRef()),
        "fields": fields,
    }


def _layer_geometry_name(ogr, layer):
    return ogr.GeometryTypeToName(layer.GetLayerDefn().GetGeomType())


def _require_3d_multipolygon(geometry_type):
    normalized = geometry_type.lower().replace(" ", "")
    if "multipolygon" not in normalized or not normalized.startswith("3d"):
        raise RuntimeError(
            "building layer must be 3D Multi Polygon, found: " + geometry_type
        )


def _inspect(ogr, dataset_path, requested_layer, required_fields):
    dataset = ogr.Open(str(dataset_path), 0)
    if dataset is None:
        raise RuntimeError(f"cannot open GeoPackage: {dataset_path}")
    layer = _resolve_layer(dataset, requested_layer)
    values = _validate_layer(layer, required_fields)
    values["layer"] = layer.GetName()
    values["geometry_type"] = _layer_geometry_name(ogr, layer)
    _require_3d_multipolygon(values["geometry_type"])
    return dataset, layer, values


def _ingest(ogr, job):
    source_dataset, source_layer, source = _inspect(
        ogr, job["source"], job.get("source_layer"), job["required_fields"]
    )
    output_path = Path(job["output"])
    driver = ogr.GetDriverByName("GPKG")
    if driver is None:
        raise RuntimeError("GDAL GeoPackage driver is unavailable")
    if output_path.exists() and driver.DeleteDataSource(str(output_path)) != 0:
        raise RuntimeError(f"cannot replace output: {output_path}")
    target = driver.CreateDataSource(str(output_path))
    if target is None:
        raise RuntimeError(f"cannot create output: {output_path}")
    output_layer = target.CreateLayer(
        job["output_layer"],
        source_layer.GetSpatialRef(),
        source_layer.GetLayerDefn().GetGeomType(),
        options=["SPATIAL_INDEX=YES"],
    )
    if output_layer is None:
        raise RuntimeError("cannot create Native building layer")
    source_definition = source_layer.GetLayerDefn()
    for index in range(source_definition.GetFieldCount()):
        if output_layer.CreateField(source_definition.GetFieldDefn(index)) != 0:
            raise RuntimeError("cannot preserve a source field")
    output_definition = output_layer.GetLayerDefn()

    output_layer.StartTransaction()
    source_layer.ResetReading()
    for source_feature in source_layer:
        target_feature = ogr.Feature(output_definition)
        for index in range(source_definition.GetFieldCount()):
            if source_feature.IsFieldSetAndNotNull(index):
                target_feature.SetField(index, source_feature.GetField(index))
        geometry = source_feature.GetGeometryRef()
        target_feature.SetGeometry(geometry.Clone())
        if output_layer.CreateFeature(target_feature) != 0:
            output_layer.RollbackTransaction()
            raise RuntimeError("failed to write a building feature")
    output_layer.CommitTransaction()
    target = None
    source_dataset = None

    _, _, output = _inspect(
        ogr, output_path, job["output_layer"], job["required_fields"]
    )
    return _comparison_result(source, output)


def _comparison_result(source, output):
    if source["features"] != output["features"]:
        raise RuntimeError(
            f"feature count changed: {source['features']} -> {output['features']}"
        )
    if source["fields"] != output["fields"]:
        raise RuntimeError("source attributes were not preserved")
    if source["geometry_type"] != output["geometry_type"]:
        raise RuntimeError(
            "geometry type changed: "
            f"{source['geometry_type']} -> {output['geometry_type']}"
        )
    if source["crs"] != output["crs"]:
        raise RuntimeError(f"CRS changed: {source['crs']} -> {output['crs']}")
    return {
        "input_layer": source["layer"],
        "output_layer": output["layer"],
        "input_features": source["features"],
        "output_features": output["features"],
        "non_empty_geometries": output["non_empty_geometries"],
        "z_geometries": output["z_geometries"],
        "geometry_type": output["geometry_type"],
        "crs": output["crs"],
        "preserved_fields": output["fields"],
        "warnings": [],
        "errors": [],
    }


def _compare(ogr, job):
    _, _, source = _inspect(
        ogr, job["source"], job.get("source_layer"), job["required_fields"]
    )
    _, _, output = _inspect(
        ogr, job["output"], job["output_layer"], job["required_fields"]
    )
    return _comparison_result(source, output)


def main(job_path, result_path):
    from osgeo import ogr

    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    if job["mode"] == "ingest":
        result = _ingest(ogr, job)
    elif job["mode"] == "compare":
        result = _compare(ogr, job)
    else:
        raise RuntimeError(f"unsupported worker mode: {job['mode']}")
    Path(result_path).write_text(json.dumps(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1], sys.argv[2]))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
