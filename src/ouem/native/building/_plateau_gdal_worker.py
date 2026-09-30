"""Standalone OGR worker executed by OSGeo4W/QGIS Python.

This file deliberately imports no OUEM modules. The OUEM venv orchestrates the
run; the external GIS Python owns only GDAL/OGR geometry operations.
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path

from osgeo import ogr, osr

ID_NAMESPACE = uuid.UUID("c99b9acf-e4c4-5ab0-83b0-c72cdad6a585")


def field_value(feature, candidates):
    names = {
        feature.GetFieldDefnRef(index).GetName().lower(): index
        for index in range(feature.GetFieldCount())
    }
    for candidate in candidates:
        if candidate.lower() in names:
            return feature.GetField(names[candidate.lower()])
    return None


def ouem_id(source_dataset, source_id, fingerprint):
    identity = f"PLATEAU\0{source_dataset}\0{source_id or fingerprint}"
    return str(uuid.uuid5(ID_NAMESPACE, identity))


def main(job_path, result_path):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    output = Path(job["output"])
    driver = ogr.GetDriverByName("GPKG")
    if output.exists():
        driver.DeleteDataSource(str(output))
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(job["target_epsg"])
    target = driver.CreateDataSource(str(output))
    layer = target.CreateLayer("building", target_srs, ogr.wkbUnknown, options=["SPATIAL_INDEX=YES"])
    for name, field_type in (
        ("ouem_id", ogr.OFTString),
        ("source_id", ogr.OFTString),
        ("source_dataset", ogr.OFTString),
        ("source_lod", ogr.OFTString),
        ("measured_height", ogr.OFTReal),
    ):
        layer.CreateField(ogr.FieldDefn(name, field_type))
    definition = layer.GetLayerDefn()
    xmin, ymin, xmax, ymax = job["extent"]
    bbox = ogr.CreateGeometryFromWkt(
        f"POLYGON (({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, "
        f"{xmin} {ymax}, {xmin} {ymin}))"
    )
    counts = {
        "standard_features": 0,
        "study_area_intersections": 0,
        "invalid_geometries": 0,
        "failed_geometries": 0,
        "warnings": [],
    }
    for item in job["native_sources"]:
        dataset = ogr.Open(item["native"], 0)
        source_layer = dataset.GetLayerByName("building") or dataset.GetLayer(0)
        source_srs = source_layer.GetSpatialRef()
        if source_srs is None:
            source_srs = osr.SpatialReference()
            source_srs.ImportFromEPSG(6697)
            counts["warnings"].append(f"Native CRS missing; assumed EPSG:6697: {item['native']}")
        horizontal_srs = source_srs.CloneGeogCS() or source_srs
        transform = osr.CoordinateTransformation(horizontal_srs, target_srs)
        for feature in source_layer:
            geometry = feature.GetGeometryRef()
            if geometry is None:
                counts["failed_geometries"] += 1
                continue
            geometry = geometry.Clone()
            if not geometry.IsValid():
                counts["invalid_geometries"] += 1
            if geometry.Transform(transform) != 0:
                counts["failed_geometries"] += 1
                continue
            if not geometry.Intersects(bbox):
                continue
            source_id = field_value(feature, ("gml_id", "gml:id", "id", "identifier"))
            fingerprint = hashlib.sha256(bytes(geometry.ExportToWkb())).hexdigest()
            standard = ogr.Feature(definition)
            standard.SetField("ouem_id", ouem_id(item["source"], str(source_id or ""), fingerprint))
            standard.SetField("source_id", str(source_id or ""))
            standard.SetField("source_dataset", item["source"])
            lod = field_value(feature, ("source_lod", "lod", "lod_type", "lod0", "lod1", "lod2", "lod3", "lod4"))
            if lod is not None:
                standard.SetField("source_lod", str(lod))
            height = field_value(feature, ("measuredheight", "measured_height", "bldg_measuredheight"))
            if height is not None:
                try:
                    standard.SetField("measured_height", float(height))
                except (TypeError, ValueError):
                    counts["warnings"].append(f"invalid measured height for {source_id} in {item['source']}")
            standard.SetGeometry(geometry)
            if layer.CreateFeature(standard) != 0:
                counts["failed_geometries"] += 1
                continue
            counts["study_area_intersections"] += 1
    target = None
    counts["standard_features"] = counts["study_area_intersections"]
    Path(result_path).write_text(json.dumps(counts), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
