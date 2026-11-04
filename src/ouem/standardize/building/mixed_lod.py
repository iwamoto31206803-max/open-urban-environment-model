"""Experimental Mixed-LoD Standard Building projection and reopen audit."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import struct
from tempfile import TemporaryDirectory

import pyproj
from pyproj import CRS, Proj, Transformer

from ouem.consumers._source_h_geometry import decode
from ouem.native.building import mixed_lod as native
from ouem.native.building.source_h_geometry import counts, inspect_geopackage, open_readonly, require
from .source_h import strict_json
from .source_h_geometry import XY_TOLERANCE_M, intersects, map_xy, points, wkb

PROFILE = "ouem-standard-building/plateau-mixed-lod-source-h/v0.1"
SCHEMA = "ouem-mixed-lod-standard-manifest/v0.1"
LAYER = "building"
DATASET = "PLATEAU CityGML"
FIELDS = ("source_id,ouem_id,source_dataset,source_lod,selection_reason,source_member,"
          "source_release,converter_pass,measured_height,measured_height_raw")
SETTINGS = dict(always_xy=True, allow_ballpark=False, only_best=True)


def validate_native(manifest_path, manifest_sha, bounds):
    """Rebuild expected Native records from Raw and the verified Converter files."""
    artifact = native.bridge.artifact
    identity = artifact(manifest_path)
    require(identity["sha256"] == manifest_sha, "Native.manifest", "pinned SHA mismatch")
    record = strict_json(manifest_path)
    require((record["schema"], record["profile"], record["status"], record["execution_status"],
             record["formal_acceptance"]) ==
            (native.SCHEMA, native.PROFILE, "EXPERIMENTAL", "COMPLETED", "NOT_VERIFIED"),
            "Native.profile", "completed Mixed Native manifest required")
    require(record["implementation"]["sha256"] == native.raw.digest(native.__file__),
            "Native.manifest", "stale writer identity")
    native_path = manifest_path.with_name("native.gpkg")
    output = artifact(native_path)
    require(record["native"] == output | {"layer": native.bridge.LAYER},
            "Native.gpkg", "adjacent Native artifact identity mismatch")
    supplied = record["artifacts"]
    bridge_ref = supplied["bridge_receipt"]
    artifacts, upstream, replay, selected, snapshots = native.verify_bridge(
        Path(bridge_ref["path"]), bridge_ref["sha256"], Path(supplied["selector_manifest"]["path"]),
        Path(supplied["raw_zip"]["path"]), member=record["raw_source"]["members"][0]["member"],
        release=record["raw_source"]["release"], bounds=bounds)
    require(artifacts == supplied and all(record[key] == replay[key] for key in ("aoi", "crs"))
            and record["raw_source"] == replay["source"] and record["converter"] == upstream["converter"],
            "Native.provenance", "source graph or AOI/CRS differs from replay")
    require(record["branches"] == {
        lod: {key: branch[key] for key in ("argv", "exit_code", "started_at", "ended_at", "gpkg", "stdout", "stderr")}
        for lod, branch in upstream["branches"].items()}, "Native.branches", "Converter execution graph differs")
    decisions, rows = native.selected_rows(replay, upstream, snapshots, artifacts)
    require(record["decisions"] == decisions and record["counts"] == {
        "included": len(rows), "excluded": len(decisions)-len(rows),
        "by_lod": dict(Counter(str(r[3]) for r in rows))},
        "Native.decisions", "Native selection or exclusions differ from replay")
    native.audit_output(native_path, rows, selected, snapshots)
    with open_readonly(native_path) as db:
        require(db.execute("SELECT * FROM gpkg_geometry_columns").fetchall()
                == [(native.bridge.LAYER, "geometry", "MULTIPOLYGON", 6697, 1, 0)],
                "Native.CRS", "Mixed Native geometry declaration required")
        source_attributes = db.execute(f"SELECT {native.FIELDS} FROM {native.TABLE}").fetchall()
    source = inspect_geopackage(native_path, native.bridge.LAYER).features
    inputs = artifacts | {"native_manifest": identity, "native_gpkg": output}
    check_inputs(inputs)

    attributes = {r[0]: (r[0], r[2], DATASET, r[3], *r[4:8], r[11], r[10]) for r in source_attributes}
    return inputs, record, source, attributes


def check_inputs(inputs):
    native.check_inputs(inputs)
    with open_readonly(inputs["native_gpkg"]["path"]):
        pass


def write_gpkg(path, features, attributes, timestamp):
    crs = CRS.from_epsg(6677)
    vertices = [p for tree in features.values() for p in points(tree)]
    x, y, _ = zip(*vertices)
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            PRAGMA application_id=1196444487;
            PRAGMA user_version=10300;
            PRAGMA foreign_keys=ON;
            CREATE TABLE gpkg_spatial_ref_sys (
              srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY, organization TEXT NOT NULL,
              organization_coordsys_id INTEGER NOT NULL, definition TEXT NOT NULL, description TEXT
            );
            CREATE TABLE gpkg_contents (
              table_name TEXT PRIMARY KEY, data_type TEXT NOT NULL, identifier TEXT UNIQUE,
              description TEXT, last_change DATETIME NOT NULL, min_x DOUBLE, min_y DOUBLE,
              max_x DOUBLE, max_y DOUBLE, srs_id INTEGER REFERENCES gpkg_spatial_ref_sys(srs_id)
            );
            CREATE TABLE gpkg_geometry_columns (
              table_name TEXT PRIMARY KEY REFERENCES gpkg_contents(table_name), column_name TEXT NOT NULL,
              geometry_type_name TEXT NOT NULL, srs_id INTEGER NOT NULL REFERENCES gpkg_spatial_ref_sys(srs_id),
              z TINYINT NOT NULL, m TINYINT NOT NULL
            );
            CREATE TABLE building (
              fid INTEGER PRIMARY KEY, geometry MULTIPOLYGON NOT NULL, source_id TEXT NOT NULL UNIQUE,
              ouem_id TEXT NOT NULL UNIQUE, source_dataset TEXT NOT NULL,
              source_lod INTEGER NOT NULL CHECK(source_lod IN (1,2)), selection_reason TEXT NOT NULL,
              source_member TEXT NOT NULL, source_release TEXT NOT NULL, converter_pass TEXT NOT NULL,
              measured_height REAL CHECK(measured_height IS NULL OR measured_height <> -9999), measured_height_raw REAL
            );
        """)
        for code, name, org in ((-1, "Undefined Cartesian", "NONE"), (0, "Undefined Geographic", "NONE"),
                                (4326, "WGS 84", "EPSG"), (6677, crs.name, "EPSG")):
            definition = CRS.from_epsg(code).to_wkt("WKT1_GDAL") if code > 0 else "undefined"
            db.execute("INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,NULL)", (name, code, org, code, definition))
        db.execute("INSERT INTO gpkg_contents VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (LAYER, "features", LAYER, "Experimental Mixed-LoD Standard", timestamp,
                    min(x), min(y), max(x), max(y), 6677))
        db.execute("INSERT INTO gpkg_geometry_columns VALUES(?,?,?,?,?,?)",
                   (LAYER, "geometry", "MULTIPOLYGON", 6677, 1, 0))
        header = b"GP\x00\x01"+struct.pack("<i", 6677)
        db.executemany(f"INSERT INTO building(geometry,{FIELDS}) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       ((header+wkb(tree), *attributes[sid]) for sid, tree in features.items()))


def audit(path, source, projected, attributes, bounds):
    """Decode actual ordered ISO WKB and compare every coordinate to a Proj oracle."""
    reference = Proj(CRS.from_epsg(6677))
    summary, max_delta, nonintersecting = {}, 0.0, []
    with open_readonly(path) as db:
        require(db.execute("PRAGMA application_id").fetchone() == (0x47504B47,)
                and db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
                and not db.execute("PRAGMA foreign_key_check").fetchall(), "Standard", "invalid GeoPackage")
        require(db.execute("SELECT table_name,data_type,srs_id FROM gpkg_contents").fetchall()
                == [(LAYER, "features", 6677)] and db.execute("SELECT * FROM gpkg_geometry_columns").fetchall()
                == [(LAYER, "geometry", "MULTIPOLYGON", 6677, 1, 0)], "Standard.CRS", "invalid layer declaration")
        require(db.execute("SELECT organization,organization_coordsys_id,definition FROM gpkg_spatial_ref_sys "
                           "WHERE srs_id=6677").fetchall() == [("EPSG", 6677, CRS.from_epsg(6677).to_wkt("WKT1_GDAL"))],
                "Standard.CRS", "invalid CRS definition")
        for blob, *values in db.execute(f"SELECT geometry,{FIELDS} FROM building"):
            sid = values[0]
            require(sid not in summary and sid in source and tuple(values) == attributes[sid]
                    and type(values[3]) is int, sid, "Standard IDs or attributes differ")
            tree = decode(blob)
            stat = counts(tree)
            require(tree == projected[sid] and stat == counts(source[sid]), sid, "geometry structure/order differs")
            for (lon, lat, old_h), (x, y, h) in zip(points(source[sid]), points(tree), strict=True):
                require(struct.pack("<d", h) == struct.pack("<d", old_h), sid, "H bits changed")
                px, py = reference(lon, lat, errcheck=True)
                delta = max(abs(px-x), abs(py-y))
                require(math.isfinite(delta) and delta <= XY_TOLERANCE_M, sid, "independent XY tolerance exceeded")
                max_delta = max(max_delta, delta)
            if not intersects(tree, bounds):
                nonintersecting.append(sid)
            summary[sid] = stat
    require(summary.keys() == source.keys(), "Standard.ids", "reopened ID set differs")
    require(not nonintersecting, "Standard.AOI", f"reopened geometry disagrees with Native: {nonintersecting}")
    by_lod = {}
    for sid, stat in summary.items():
        lod = str(attributes[sid][3])
        totals = by_lod.setdefault(lod, Counter())
        totals.update({key: value for key, value in stat.items() if key != "geometry_type"})
        totals["features"] += 1
    return dict(max_xy_error_m=max_delta, xy_tolerance_m=XY_TOLERANCE_M, h_exact=True,
                aoi_intersecting=len(summary), aoi_disagreement_ids=[], by_lod=by_lod)


def run(native_manifest, native_sha, out, *, bounds):
    native_manifest, out = Path(native_manifest).resolve(), Path(out).resolve()
    out.mkdir()
    published = []
    try:
        inputs, record, source, attributes = validate_native(native_manifest, native_sha, bounds)
        transformer = Transformer.from_crs(6668, 6677, **SETTINGS)
        projected = {sid: map_xy(tree, lambda x, y: transformer.transform(x, y, errcheck=True))
                     for sid, tree in source.items()}
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        with TemporaryDirectory(prefix=".staged-", dir=out) as tmp:
            stage = Path(tmp)
            staged, final = stage/"standard.gpkg", out/"standard.gpkg"
            write_gpkg(staged, projected, attributes, timestamp)
            qa = audit(staged, source, projected, attributes, bounds)
            output = native.bridge.artifact(staged) | {"path": str(final), "layer": LAYER}
            manifest = dict(
                schema=SCHEMA, profile=PROFILE, status="EXPERIMENTAL", execution_status="COMPLETED",
                formal_acceptance="NOT_VERIFIED", completed_at=timestamp, native_profile=record["profile"],
                inputs=inputs, output=output, raw_source=record["raw_source"], aoi=record["aoi"],
                crs=dict(input=record["crs"], output_horizontal_epsg=6677, output_axes=["X", "Y", "H"],
                         vertical_epsg=6695, vertical_operation="identity_H"),
                operation=SETTINGS | dict(source_epsg=6668, target_epsg=6677, definition=transformer.definition,
                                          description=transformer.description, accuracy_m=transformer.accuracy,
                                          arguments=["longitude", "latitude"]),
                environment=dict(python=platform.python_version(), platform=platform.platform(),
                                 pyproj=pyproj.__version__, proj=pyproj.proj_version_str),
                implementation=native.bridge.artifact(Path(__file__).resolve()),
                buildings=[dict(zip(FIELDS.split(","), values)) for values in attributes.values()],
                mapping=dict(source_id="Native id", ouem_id="Native ouem_id", source_dataset=DATASET,
                             source_lod="Native selected_lod, integer 1/2",
                             measured_height="Native measuredHeight, nullable",
                             measured_height_raw="Native measured_height_raw, audit only",
                             provenance="selection_reason, source_member, source_release, converter_pass copied"),
                validation=qa, unverified=["GUI display", "vertical datum realization and survey accuracy",
                                           "independent consumer and downstream use"])
            marker = stage/"manifest.json"
            native.bridge.write(marker, manifest)
            check_inputs(inputs)
            os.link(staged, final)
            published.append(final)
            check_inputs(inputs)
            require(native.bridge.artifact(final) == {k: output[k] for k in ("path", "sha256", "size_bytes")},
                    "Standard", "published bytes differ from audited stage")
            os.link(marker, out/"manifest.json")
            published.append(out/"manifest.json")
        return manifest
    except Exception as exc:
        for path in reversed(published):
            path.unlink()
        native.bridge.write(out/"failure.json", dict(schema=SCHEMA, profile=PROFILE, execution_status="FAILED",
                                                    error=str(exc), field=getattr(exc, "field", None)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-manifest", required=True, type=Path)
    parser.add_argument("--native-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--bounds", required=True, nargs=4, type=float)
    args = parser.parse_args()
    result = run(args.native_manifest, args.native_sha256, args.output_dir, bounds=args.bounds)
    print(json.dumps(result["validation"], sort_keys=True))


if __name__ == "__main__":
    main()
