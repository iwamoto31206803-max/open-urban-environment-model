"""Standalone GDAL worker for Native-to-Standard Building conversion.

This file deliberately imports no OUEM package modules: it runs in the separate
QGIS/OSGeo4W Python selected by the OUEM parent process.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
import uuid

REQUIRED_FIELDS = ("ouem_id", "source_id", "source_dataset", "source_lod", "measured_height")


def _field_map(layer):
    definition = layer.GetLayerDefn()
    return {
        definition.GetFieldDefn(index).GetName().casefold():
        definition.GetFieldDefn(index).GetName()
        for index in range(definition.GetFieldCount())
    }


def _field(fields, candidates, *, required=False):
    for candidate in candidates:
        if candidate.casefold() in fields:
            return fields[candidate.casefold()]
    if required:
        raise RuntimeError("Native Building source identifier missing; expected field: " + candidates[0])
    return None


def _crs_label(srs):
    if srs is None:
        raise RuntimeError("Native Building layer CRS is undefined")
    name, code = srs.GetAuthorityName(None), srs.GetAuthorityCode(None)
    return f"{name}:{code}" if name and code else "defined (WKT)"


def _is_source_crs(osr, srs):
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(6697)
    if srs.IsSame(expected):
        return True
    # Some drivers expose the horizontal component's authority rather than the
    # compound CRS authority. Only accept a component that is actually 6697.
    return srs.GetAuthorityCode(None) == "6697"


def _points(geometry):
    result = []
    for index in range(geometry.GetPointCount()):
        point = geometry.GetPoint(index)
        if len(point) < 3 or not all(math.isfinite(value) for value in point[:3]):
            raise RuntimeError("Native Building contains a non-finite or missing XYZ coordinate")
        result.append(tuple(point[:3]))
    for index in range(geometry.GetGeometryCount()):
        result.extend(_points(geometry.GetGeometryRef(index)))
    return result


def _restore_z(geometry, source_points, offset=0):
    """Restore Z after OSR transformation; return next flattened point index."""
    for index in range(geometry.GetPointCount()):
        current = geometry.GetPoint(index)
        geometry.SetPoint(index, current[0], current[1], source_points[offset][2])
        offset += 1
    for index in range(geometry.GetGeometryCount()):
        offset = _restore_z(geometry.GetGeometryRef(index), source_points, offset)
    return offset


def _id(source_dataset, source_id):
    value = f"ouem-standard-building-v0.1|{source_dataset}|{source_id}"
    return f"oub-{uuid.uuid5(uuid.NAMESPACE_URL, value)}"


def _rectangle(ogr, extent):
    xmin, ymin, xmax, ymax = extent
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for point in ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)):
        ring.AddPoint_2D(*point)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    return polygon


def _run(ogr, osr, job):
    source_path, output_path = Path(job["source"]), Path(job["output"])
    source = ogr.Open(str(source_path), 0)
    if source is None:
        raise RuntimeError(f"cannot open Native Building GeoPackage: {source_path}")
    layer = source.GetLayerByName(job["source_layer"])
    if layer is None:
        raise RuntimeError(f"Native Building layer not found: {job['source_layer']}")
    input_count = layer.GetFeatureCount()
    if input_count <= 0:
        raise RuntimeError("Native Building layer has no features")
    source_srs = layer.GetSpatialRef()
    input_crs = _crs_label(source_srs)
    if not _is_source_crs(osr, source_srs):
        raise RuntimeError(f"Native Building CRS must be EPSG:6697, found {input_crs}")
    fields = _field_map(layer)
    source_id_field = _field(fields, ("gml_id",), required=True)
    lod_field = _field(fields, ("source_lod", "lod", "lodType", "lod_type"))
    height_field = _field(fields, ("measuredHeight", "measured_height"))

    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(job["target_epsg"])
    # Traditional GIS order avoids authority-axis surprises in GDAL 3.
    source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_srs, target_srs)
    boundary = _rectangle(ogr, job["extent"])

    driver = ogr.GetDriverByName("GPKG")
    if output_path.exists() and driver.DeleteDataSource(str(output_path)) != 0:
        raise RuntimeError(f"cannot replace Standard Building output: {output_path}")
    target = driver.CreateDataSource(str(output_path))
    if target is None:
        raise RuntimeError(f"cannot create Standard Building output: {output_path}")
    geometry_type = layer.GetLayerDefn().GetGeomType()
    output = target.CreateLayer(job["output_layer"], target_srs, geometry_type, options=["SPATIAL_INDEX=YES"])
    for name, field_type in (
        ("ouem_id", ogr.OFTString), ("source_id", ogr.OFTString),
        ("source_dataset", ogr.OFTString), ("source_lod", ogr.OFTString),
        ("measured_height", ogr.OFTReal),
    ):
        definition = ogr.FieldDefn(name, field_type)
        if output.CreateField(definition) != 0:
            raise RuntimeError(f"cannot create required Standard Building field: {name}")

    seen_ids, selected, z_count, max_delta = set(), 0, 0, 0.0
    output.StartTransaction()
    layer.ResetReading()
    for feature in layer:
        source_id = feature.GetFieldAsString(source_id_field).strip()
        if not source_id:
            raise RuntimeError(f"Native Building feature {feature.GetFID()} has empty gml_id")
        ouem_id = _id(job["source_dataset"], source_id)
        if ouem_id in seen_ids:
            raise RuntimeError(f"duplicate Native Building source identifier: {source_id}")
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.IsEmpty() or not geometry.Is3D():
            raise RuntimeError(f"Native Building feature {source_id} has empty or non-3D geometry")
        original_points = _points(geometry)
        transformed = geometry.Clone()
        if transformed.Transform(transform) != 0:
            raise RuntimeError(f"horizontal reprojection failed for feature {source_id}")
        if _restore_z(transformed, original_points) != len(original_points):
            raise RuntimeError(f"coordinate structure changed during reprojection for feature {source_id}")
        transformed_points = _points(transformed)
        delta = max((abs(a[2] - b[2]) for a, b in zip(original_points, transformed_points)), default=0.0)
        max_delta = max(max_delta, delta)
        if delta > job["z_tolerance"]:
            raise RuntimeError(f"Z preservation failed for feature {source_id}: delta {delta} m")
        if not transformed.Intersects(boundary):
            continue
        record = ogr.Feature(output.GetLayerDefn())
        record.SetField("ouem_id", ouem_id)
        record.SetField("source_id", source_id)
        record.SetField("source_dataset", job["source_dataset"])
        if lod_field and feature.IsFieldSetAndNotNull(lod_field):
            record.SetField("source_lod", feature.GetFieldAsString(lod_field))
        if height_field and feature.IsFieldSetAndNotNull(height_field):
            record.SetField("measured_height", feature.GetFieldAsDouble(height_field))
        record.SetGeometry(transformed)  # Complete geometry: no Clip/Intersection operation.
        if output.CreateFeature(record) != 0:
            output.RollbackTransaction()
            raise RuntimeError(f"failed to write Standard Building feature {source_id}")
        seen_ids.add(ouem_id)
        selected += 1
        z_count += 1
    if output.CommitTransaction() != 0:
        raise RuntimeError("failed to commit Standard Building output")
    target = None
    source = None

    check = ogr.Open(str(output_path), 0)
    checked_layer = check.GetLayerByName(job["output_layer"])
    actual_fields = set(_field_map(checked_layer))
    metadata_ok = all(name.casefold() in actual_fields for name in REQUIRED_FIELDS)
    output_crs = _crs_label(checked_layer.GetSpatialRef())
    if output_crs != f"EPSG:{job['target_epsg']}":
        raise RuntimeError(f"Standard Building CRS validation failed: {output_crs}")
    return {
        "input_path": str(source_path), "output_path": str(output_path),
        "input_layer": job["source_layer"], "output_layer": job["output_layer"],
        "input_features": input_count, "output_features": selected,
        "input_crs": input_crs, "output_crs": output_crs,
        "geometry_type": ogr.GeometryTypeToName(geometry_type), "z_geometries": z_count,
        "study_area_extent": job["extent"], "required_metadata": metadata_ok,
        "z_preserved": max_delta <= job["z_tolerance"], "max_z_delta": max_delta,
        "deterministic_ids": len(seen_ids) == selected,
    }


def main(job_path, result_path):
    from osgeo import ogr, osr
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    result = _run(ogr, osr, job)
    Path(result_path).write_text(json.dumps(result), encoding="utf-8")


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
