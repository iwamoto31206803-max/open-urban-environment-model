"""Standalone GIS-runtime synthetic probe, NOT a production CityGML reader.

Run this file in the captured GIS Python subprocess. Only the committed small
fixture is eligible. No OUEM import, real CityGML, Native or Standard workflow.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys
import xml.etree.ElementTree as ET

G = "http://www.opengis.net/gml"
B = "http://www.opengis.net/citygml/building/2.0"
NS = {"gml": G, "bldg": B}
EXPECTED_FIXTURE_SHA = "ac2794be68822389f784c3ae896b0343dd4a046edcf46d8ca577418af52081f8"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized_ring(points):
    """Ignore cyclic start/direction, retain every XYZ and multiplicity."""
    values = tuple(tuple(p) for p in points)
    if len(values) < 4 or values[0] != values[-1]:
        raise ValueError("unclosed/short ring")
    if not all(math.isfinite(v) for p in values for v in p):
        raise ValueError("nonfinite XYZ")
    values = values[:-1]
    return min(seq[i:] + seq[:i] for seq in (values, values[::-1]) for i in range(len(seq)))


def signature(polygons):
    # Preserve exterior/interior distinction, duplicate polygons and ring counts.
    return sorted((normalized_ring(p[0]), tuple(sorted(normalized_ring(r) for r in p[1:])))
                  for p in polygons)


def geometry_polygons(geom):
    if geom is None or geom.IsEmpty():
        return []
    if geom.GetGeometryName() == "POLYGON":
        return [[[tuple(geom.GetGeometryRef(i).GetPoint(j)[:3])
                  for j in range(geom.GetGeometryRef(i).GetPointCount())]
                 for i in range(geom.GetGeometryCount())]]
    result = []
    for i in range(geom.GetGeometryCount()):
        result.extend(geometry_polygons(geom.GetGeometryRef(i)))
    return result


def source_reference(path):
    """Fixture-only coordinate oracle, not a generic parser or schema validator."""
    if sha(path) != EXPECTED_FIXTURE_SHA:
        raise ValueError("only the exact committed synthetic fixture is permitted")
    root = ET.parse(path).getroot()
    result = {}
    for building in root.findall(".//bldg:Building", NS):
        lods = {}
        for lod, selector in [(1, "bldg:lod1Solid"), (2, "bldg:boundedBy")]:
            polygons = []
            for branch in building.findall(selector, NS):
                for polygon in branch.findall(".//gml:Polygon", NS):
                    rings = []
                    for pos in polygon.findall(".//gml:posList", NS):
                        values = list(map(float, pos.text.split()))
                        if len(values) % 3:
                            raise ValueError("bad source triples")
                        # Source EPSG:6697 latitude/longitude/H -> GIS lon/lat/H.
                        rings.append([(values[i + 1], values[i], values[i + 2])
                                      for i in range(0, len(values), 3)])
                    polygons.append(rings)
            lods[lod] = polygons
        result[building.get(f"{{{G}}}id")] = lods
    return result


def feature_summary(layer):
    definition, srs = layer.GetLayerDefn(), layer.GetSpatialRef()
    rows = []
    for feature in layer:
        polygons = geometry_polygons(feature.GetGeometryRef())
        rows.append({"attributes": feature.items(), "polygons": polygons,
                     "geometry": feature.GetGeometryRef().GetGeometryName() if feature.GetGeometryRef() else None,
                     "is_3d": bool(feature.GetGeometryRef() and feature.GetGeometryRef().Is3D())})
    return {"name": layer.GetName(), "count": len(rows),
            "fields": [definition.GetFieldDefn(i).GetName() for i in range(definition.GetFieldCount())],
            "geometry_fields": [definition.GetGeomFieldDefn(i).GetName() for i in range(definition.GetGeomFieldCount())],
            "srs_wkt": srs.ExportToWkt() if srs else None,
            "srs_authority": srs.GetAuthorityCode(None) if srs else None,
            "axis_mapping": srs.GetDataAxisToSRSAxisMapping() if srs else None, "rows": rows}


def blob_srs(blob):
    if blob[:2] != b"GP" or len(blob) < 8:
        raise ValueError("not a GeoPackage geometry header")
    return struct.unpack("<i" if blob[3] & 1 else ">i", blob[4:8])[0]


def blob_wkb_type(blob):
    sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset = 8 + sizes[(blob[3] >> 1) & 7]
    return struct.unpack("<I" if blob[offset] == 1 else ">I", blob[offset + 1:offset + 5])[0]


def gpkg_inventory(path):
    with sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True) as db:
        contents = db.execute("SELECT table_name,srs_id FROM gpkg_contents").fetchall()
        columns = db.execute("SELECT table_name,column_name,geometry_type_name,srs_id,z,m FROM gpkg_geometry_columns").fetchall()
        srs = db.execute("SELECT srs_id,organization,organization_coordsys_id,definition FROM gpkg_spatial_ref_sys").fetchall()
        headers, wkb_types = {}, {}
        for table, column, *_ in columns:
            # Identifiers come only from the locally generated synthetic database.
            q = lambda x: '"' + x.replace('"', '""') + '"'
            blobs = [row[0] for row in db.execute(f"SELECT {q(column)} FROM {q(table)}") if row[0]]
            headers[table] = [blob_srs(blob) for blob in blobs]
            wkb_types[table] = [blob_wkb_type(blob) for blob in blobs]
        times = db.execute("SELECT table_name,last_change FROM gpkg_contents").fetchall()
    return {"contents": contents, "geometry_columns": columns, "srs": srs,
            "blob_srs": headers, "wkb_types": wkb_types, "last_change": times}


def verify_rows(rows, reference, lod):
    ids = [row["attributes"].get("gml_id") for row in rows]
    identity = Counter(ids) == Counter(reference.keys())
    equality = identity and all(signature(row["polygons"]) == signature(reference[row["attributes"]["gml_id"]][lod]) for row in rows)
    return {"ids_exact": identity, "all_xyz_rings_exact": equality,
            "polygon_count": sum(len(row["polygons"]) for row in rows),
            "ring_count": sum(len(p) for row in rows for p in row["polygons"]),
            "vertex_occurrences": sum(len(r) for row in rows for p in row["polygons"] for r in p)}


def write_fixture_lod2(path, reference, expected, ogr, osr):
    """Only feasibility of serializing already identified fixture polygons."""
    if path.exists():
        raise FileExistsError(path)
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(str(path))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(6697)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("building_lod2", srs, ogr.wkbMultiPolygon25D)
    for field, kind in [("gml_id", ogr.OFTString), ("source_lod", ogr.OFTInteger), ("measuredHeight", ogr.OFTReal)]:
        layer.CreateField(ogr.FieldDefn(field, kind))
    for identifier, lods in reference.items():
        geom = ogr.Geometry(ogr.wkbMultiPolygon25D)
        for rings in lods[2]:
            polygon = ogr.Geometry(ogr.wkbPolygon25D)
            for points in rings:
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for point in points:
                    ring.AddPoint(*point)
                polygon.AddGeometry(ring)
            geom.AddGeometry(polygon)
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("gml_id", identifier)
        feature.SetField("source_lod", 2)
        target = next(x for x in expected["buildings"] if x["id"] == identifier)
        feature.SetField("measuredHeight", target["lod2_top_H_m"] - target["base_H_m"])
        feature.SetGeometry(geom)
        if layer.CreateFeature(feature):
            raise RuntimeError("synthetic GPKG write failed")
        feature = None
    ds.SetMetadataItem("EXPERIMENTAL", "fixture serialization only, not Native or Standard")
    ds.SetMetadataItem("Z_QUANTITY", "synthetic source H metres; unchanged, no geoid operation")
    layer = None
    ds = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    repo, output = args.repo.resolve(), args.output_dir.resolve()
    allowed = (repo / "data/work/gdal-citygml").resolve()
    if output == allowed or not output.is_relative_to(allowed):
        raise ValueError("new isolated child of data/work/gdal-citygml required")
    output.mkdir(parents=True, exist_ok=False)
    from osgeo import gdal, ogr, osr
    gdal.UseExceptions()
    source = repo / "tests/fixtures/plateau_converter/two_buildings.gml"
    expectation = repo / "tests/fixtures/plateau_converter/expected.json"
    before = sha(source)
    reference = source_reference(source)
    expected = json.loads(expectation.read_text())
    report = {"gdal": gdal.VersionInfo("--version"), "python": sys.version,
              "fixture_sha256": before, "expected_sha256": sha(expectation), "script_sha256": sha(__file__),
              "cases": {}, "gmlas": None}
    for name, compound, fetch_all, force_type in [("default", False, False, None),
            ("compound_all", True, True, None), ("forced_multipolygon", True, True, "MULTIPOLYGONZ")]:
        gdal.SetConfigOption("GML_REPORT_COMPD_CS", "YES" if compound else "NO")
        gdal.SetConfigOption("GML_FETCH_ALL_GEOMETRIES", "YES" if fetch_all else "NO")
        options = ["WRITE_GFS=NO", "DOWNLOAD_SCHEMA=NO", "EXPOSE_GML_ID=YES", "GML_ATTRIBUTES_TO_OGR_FIELDS=YES", "FORCE_SRS_DETECTION=YES"]
        ds = gdal.OpenEx(str(source), gdal.OF_VECTOR, allowed_drivers=["GML"], open_options=options)
        case = {"driver": ds.GetDriver().ShortName, "open_options": options,
                "compound": compound, "fetch_all": fetch_all, "force_geometry_type": force_type,
                "read": [feature_summary(layer) for layer in ds]}
        path = output / f"{name}.gpkg"
        try:
            kwargs = {"geometryType": force_type} if force_type else {}
            result = gdal.VectorTranslate(str(path), ds, format="GPKG", **kwargs)
            if result is None:
                raise RuntimeError("VectorTranslate returned no dataset")
            result = None
            reopened = gdal.OpenEx(str(path), gdal.OF_VECTOR)
            case["written"] = [feature_summary(layer) for layer in reopened]
            reopened = None
            case["metadata"] = gpkg_inventory(path)
            case["sha256"] = sha(path)
            case["against_lod1"] = verify_rows(case["written"][0]["rows"], reference, 1)
            case["against_lod2"] = verify_rows(case["written"][0]["rows"], reference, 2)
        except Exception as exc:
            case["error"] = str(exc)
        ds = None
        report["cases"][name] = case
    gdal.SetConfigOption("GML_REPORT_COMPD_CS", "YES")
    config = ("<Configuration><AllowRemoteSchemaDownload>false</AllowRemoteSchemaDownload>"
              "<SchemaCache><Directory>" + (output / "schema-cache").as_posix() + "</Directory></SchemaCache></Configuration>")
    try:
        ds = gdal.OpenEx("GMLAS:" + str(source), gdal.OF_VECTOR, allowed_drivers=["GMLAS"],
                         open_options=["CONFIG_FILE=" + config, "VALIDATE=YES", "FAIL_IF_VALIDATION_ERROR=YES"])
        report["gmlas"] = {"layers": [feature_summary(layer) for layer in ds]}
        ds = None
    except Exception as exc:
        report["gmlas"] = {"error": str(exc), "remote_schema_download": False}
    for repeat in (1, 2):
        path = output / f"xml_lod2_{repeat}.gpkg"
        write_fixture_lod2(path, reference, expected, ogr, osr)
        ds = gdal.OpenEx(str(path), gdal.OF_VECTOR)
        summary = feature_summary(ds.GetLayer(0))
        ds = None
        report["cases"][f"xml_lod2_{repeat}"] = {"written": summary,
            "qa": verify_rows(summary["rows"], reference, 2), "metadata": gpkg_inventory(path), "sha256": sha(path)}
    first, second = (report["cases"][f"xml_lod2_{i}"] for i in (1, 2))
    def semantic(case):
        return sorted((r["attributes"]["gml_id"], json.dumps(r["attributes"], sort_keys=True),
                       signature(r["polygons"])) for r in case["written"]["rows"])
    report["repeat"] = {"bytes_equal": first["sha256"] == second["sha256"],
                        "normalized_geometry_attributes_equal": semantic(first) == semantic(second),
                        "crs_equal": first["written"]["srs_wkt"] == second["written"]["srs_wkt"]}
    for name, data in [("malformed", b"<invalid"), ("bad_coordinate", source.read_bytes().replace(b"10.25", b"invalid", 1))]:
        path = output / (name + ".gml")
        path.write_bytes(data)
        try:
            ds = gdal.OpenEx(str(path), gdal.OF_VECTOR, allowed_drivers=["GML"], open_options=["WRITE_GFS=NO", "DOWNLOAD_SCHEMA=NO"])
            rows = [feature_summary(layer) for layer in ds]
            report["cases"][name] = {"opened": True, "layers": rows}
            ds = None
        except Exception as exc:
            report["cases"][name] = {"opened": False, "error": str(exc)}
    report["fixture_unchanged"] = sha(source) == before
    if not report["fixture_unchanged"]:
        raise RuntimeError("fixture mutated")
    (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output / "results.json"), "fixture_unchanged": True}))


if __name__ == "__main__":
    main()
