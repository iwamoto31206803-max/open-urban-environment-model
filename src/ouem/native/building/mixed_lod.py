"""Experimental Mixed-LoD Native writer for a verified two-pass Bridge run."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
from tempfile import TemporaryDirectory

from ouem import mixed_lod_converter_bridge as bridge
from ouem import mixed_lod_selector as raw
from ouem.native.building.source_h_geometry import (
    inspect_geopackage, open_readonly, polygons, quoted, require,
)
from ouem.native.building.source_h_lod2 import _signature

PROFILE = "ouem-native-building/plateau-mixed-lod-source-h/v0.1"
SCHEMA = "ouem-mixed-lod-native-manifest/v0.1"
TABLE = quoted(bridge.LAYER)
COLUMNS = ("id", "geometry", "ouem_id", "selected_lod", "selection_reason", "source_member",
           "source_release", "converter_pass", "source_feature_id", "geometry_blob_sha256",
           "measured_height_raw", "measuredHeight")
FIELDS = ",".join(map(quoted, COLUMNS))
SRS_FIELDS = "srs_name,srs_id,organization,organization_coordsys_id,definition,description"


def check_inputs(artifacts):
    for role, identity in artifacts.items():
        path = bridge.verify_artifact(identity)
        if role in ("lod1_gpkg", "lod2_gpkg"):
            with open_readonly(path):
                pass  # Reject newly appeared journal/WAL sidecars.


def verify_bridge(receipt_path, receipt_sha, selector, archive, *, member, release, bounds):
    """Recompute the selection and both full branch comparisons before copying."""
    geometry = selector.with_name("geometries.jsonl")
    artifacts = {key: bridge.artifact(path) for key, path in {
        "bridge_receipt": receipt_path, "selector_manifest": selector,
        "selector_geometry": geometry, "raw_zip": archive,
    }.items()}
    require(artifacts["bridge_receipt"]["sha256"] == receipt_sha, "Bridge", "receipt SHA mismatch")
    receipt = json.loads(receipt_path.read_bytes())
    require((receipt["schema"], receipt["status"], receipt["execution_status"], receipt["mixed_native_handoff"])
            == (bridge.SCHEMA, "EXPERIMENTAL", "COMPLETED", "ELIGIBLE") and "error" not in receipt,
            "Bridge", "eligible completed Bridge receipt required")
    for key in ("selector_manifest", "selector_geometry"):
        require(receipt[key] == artifacts[key], key, "receipt does not bind the supplied selector artifact")
    artifacts["bridge_implementation"] = bridge.artifact(Path(bridge.__file__).resolve())
    require(receipt["implementation"]["sha256"] == artifacts["bridge_implementation"]["sha256"],
            "Bridge", "stale implementation identity")
    converter = receipt["converter"]
    require((converter["commit"], converter["version"], converter["binary"]["sha256"])
            == (bridge.COMMIT, bridge.VERSION, bridge.CLI_SHA), "Converter", "unexpected fixed version or binary")
    artifacts["converter_binary"] = converter["binary"]
    replay, selected = bridge.load_selector(selector, archive, member, release, bounds)
    for key, expected in (("raw_source", replay["source"]), ("aoi", replay["aoi"]),
                          ("crs", replay["crs"]), ("raw_counts", replay["counts"])):
        require(receipt[key] == expected, key, "Bridge and Raw replay disagree")
    require(artifacts["raw_zip"]["sha256"] == replay["source"]["zip_sha256"],
            "ZIP", "input changed before Raw replay")
    extracted = receipt_path.parent / "extracted" / member
    identity = receipt["extracted_member"]
    require(identity["path"] == str(extracted)
            and identity["sha256"] == replay["source"]["members"][0]["sha256"],
            "member", "extracted member is not bound to Raw ZIP")
    artifacts["extracted_member"] = identity
    bridge.verify_artifact(identity)
    expected = bridge.expected_by_lod(replay["records"], selected, extracted)

    require(set(receipt["branches"]) == {"1", "2"}, "Bridge", "exactly two Converter passes required")
    snapshots = {}
    for lod in (1, 2):
        branch = receipt["branches"][str(lod)]
        gpkg = receipt_path.parent / f"lod{lod}.gpkg"
        argv = [converter["binary"]["path"], str(extracted), "--sink", "gpkg", "--output", str(gpkg),
                "--epsg", "6697", "-t", f"use_lod=lod{lod}", "-t", "split_components=false"]
        require(branch["argv"] == argv and type(branch["exit_code"]) is int and branch["exit_code"] == 0
                and "error" not in branch and branch["started_at"] and branch["ended_at"],
                "Converter", f"invalid LoD{lod} execution record")
        for key, path in (("gpkg", gpkg), ("stdout", gpkg.with_suffix(".stdout.log")),
                          ("stderr", gpkg.with_suffix(".stderr.log"))):
            require(branch[key]["path"] == str(path), key, "unexpected Converter artifact path")
            artifacts[f"lod{lod}_{key}"] = branch[key]
            bridge.verify_artifact(branch[key])
        snapshot = inspect_geopackage(gpkg, bridge.LAYER)
        comparison = bridge.reconcile(expected[lod], snapshot)
        require(all(branch[key] == value for key, value in comparison.items())
                and all(f["result"] in bridge.MATCHES for f in comparison["features"].values()),
                f"LoD{lod}", "Bridge ID, BLOB or Raw XYZ reconciliation differs")
        snapshots[lod] = snapshot

    rows = []
    for row in replay["records"]:
        sid, lod = row["source_id"], row["selected_lod"]
        feature = receipt["branches"][str(lod)]["features"][sid] if lod else None
        rows.append(dict(source_id=sid, selected_lod=lod, selection_reason=row["selection_reason"],
                         aoi_intersects=row["aoi_intersects"], feature=feature, feature_eligible=bool(feature)))
    require(receipt["selection"] == rows, "Bridge.selection", "selection does not match Raw and Converter")
    count = sum(row["aoi_intersects"] is True for row in rows)
    require(receipt["candidate"] == dict(selected=count, feature_eligible=count),
            "Bridge.candidate", "candidate counts differ")
    return artifacts, receipt, replay, selected, snapshots


def selected_rows(replay, receipt, snapshots, artifacts):
    """Copy only AOI-selected BLOBs and retain an exclusion record for every Raw ID."""
    decisions, records = [], []
    release = replay["source"]["release"]
    for row, matched in zip(replay["records"], receipt["selection"], strict=True):
        sid, lod = row["source_id"], row["selected_lod"]
        decision = dict(source_id=sid, ouem_id=row["ouem_id"], selected_lod=lod,
                        selection_reason=row["selection_reason"], source_member=row["source_member"],
                        aoi_intersects=row["aoi_intersects"])
        decisions.append(decision)
        if row["aoi_intersects"] is not True:
            decision["disposition"] = "NO_SUPPORTED_LOD" if lod is None else "OUTSIDE_AOI"
            continue
        decision.update(disposition="INCLUDED", converter_pass=f"lod{lod}", feature=matched["feature"],
                        raw_branches=row["geometry_branch_locator"], raw_polygons=row["polygons"],
                        raw_geometry_sha256=row["geometry_sha256"])

    for lod, snapshot in snapshots.items():
        path = artifacts[f"lod{lod}_gpkg"]["path"]
        with open_readonly(path) as conn:
            for item in decisions:
                if item["disposition"] != "INCLUDED" or item["selected_lod"] != lod:
                    continue
                sid = item["source_id"]
                values = conn.execute(f"SELECT {quoted(snapshot.geometry_column)}, measuredHeight "
                                      f"FROM {TABLE} WHERE id=?", (sid,)).fetchall()
                require(len(values) == 1, sid, "expected exactly one selected Converter row")
                blob, measured = values[0]
                blob_hash = item["feature"]["blob_sha256"]
                require(sha256(blob).hexdigest() == blob_hash, sid, "selected BLOB changed")
                require(measured is None or type(measured) in (int, float) and math.isfinite(measured),
                        sid, "measuredHeight must be NULL or finite numeric")
                records.append((sid, blob, item["ouem_id"], lod, item["selection_reason"],
                                item["source_member"], release, f"lod{lod}", sid, blob_hash,
                                measured, None if measured == -9999 else measured))
    require(records, "AOI", "no Native features selected")
    return decisions, records


def write_gpkg(path, records, source):
    with open_readonly(source) as conn:
        srs = conn.execute(f"SELECT {SRS_FIELDS} FROM gpkg_spatial_ref_sys WHERE srs_id IN (-1,0,4326,6697)").fetchall()
    require({row[1] for row in srs} == {-1, 0, 4326, 6697}, "GPKG", "required SRS rows absent")
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
              description TEXT DEFAULT '', last_change DATETIME NOT NULL,
              min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE,
              srs_id INTEGER REFERENCES gpkg_spatial_ref_sys(srs_id)
            );
            CREATE TABLE gpkg_geometry_columns (
              table_name TEXT PRIMARY KEY REFERENCES gpkg_contents(table_name), column_name TEXT NOT NULL,
              geometry_type_name TEXT NOT NULL, srs_id INTEGER NOT NULL REFERENCES gpkg_spatial_ref_sys(srs_id),
              z TINYINT NOT NULL, m TINYINT NOT NULL
            );
            CREATE TABLE "bldg:Building" (
              fid INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE, geometry MULTIPOLYGON NOT NULL,
              ouem_id TEXT NOT NULL UNIQUE, selected_lod INTEGER NOT NULL CHECK(selected_lod IN (1,2)),
              selection_reason TEXT NOT NULL, source_member TEXT NOT NULL, source_release TEXT NOT NULL,
              converter_pass TEXT NOT NULL CHECK(converter_pass = 'lod' || selected_lod),
              source_feature_id TEXT NOT NULL CHECK(source_feature_id = id),
              geometry_blob_sha256 TEXT NOT NULL, measured_height_raw REAL, measuredHeight REAL
            );
        """)
        db.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,?)", srs)
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        db.execute("INSERT INTO gpkg_contents(table_name,data_type,identifier,last_change,srs_id) VALUES(?,?,?,?,?)",
                   (bridge.LAYER, "features", bridge.LAYER, timestamp, 6697))
        db.execute("INSERT INTO gpkg_geometry_columns VALUES(?,?,?,?,?,?)",
                   (bridge.LAYER, "geometry", "MULTIPOLYGON", 6697, 1, 0))
        placeholders = ",".join("?" for _ in COLUMNS)
        db.executemany(f"INSERT INTO {TABLE}({FIELDS}) VALUES({placeholders})", records)


def audit_output(path, records, selected, snapshots):
    expected = {record[0]: record for record in records}
    native = inspect_geopackage(path, bridge.LAYER)
    require(native.features.keys() == expected.keys(), "Native", "ID set differs")
    with open_readonly(path) as conn:
        actual = {record[0]: record for record in conn.execute(f"SELECT {FIELDS} FROM {TABLE}")}
    require(actual == expected, "Native", "BLOB bytes or attributes differ")
    for sid, record in expected.items():
        lod, blob_hash = record[3], record[9]
        tree = native.features[sid]
        require(tree == snapshots[lod].features[sid] and native.geometry_hashes[sid] == blob_hash,
                sid, "Converter and Native BLOB or ordered geometry differ")
        require(_signature(polygons(tree)) == _signature(selected[sid]), sid, "Native differs from Raw XYZ")


def run(receipt, receipt_sha, selector, archive, out, *, member, release, bounds):
    receipt, selector, archive, out = (Path(p).resolve() for p in (receipt, selector, archive, out))
    out.mkdir()
    final = out / "native.gpkg"
    published = False
    completed = False
    try:
        artifacts, upstream, replay, selected, snapshots = verify_bridge(
            receipt, receipt_sha, selector, archive, member=member, release=release, bounds=bounds)
        decisions, records = selected_rows(replay, upstream, snapshots, artifacts)
        with TemporaryDirectory(prefix=".staged-", dir=out) as directory:
            stage = Path(directory)
            staged = stage / final.name
            write_gpkg(staged, records, artifacts["lod1_gpkg"]["path"])
            audit_output(staged, records, selected, snapshots)
            output = bridge.artifact(staged) | {"path": str(final), "layer": bridge.LAYER}
            manifest = dict(schema=SCHEMA, profile=PROFILE, status="EXPERIMENTAL",
                            execution_status="COMPLETED", formal_acceptance="NOT_VERIFIED",
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            python=platform.python_version(), platform=platform.platform(),
                            implementation=bridge.artifact(Path(__file__).resolve()), artifacts=artifacts,
                            raw_source=replay["source"], aoi=replay["aoi"], crs=replay["crs"],
                            converter=upstream["converter"], branches={
                                lod: {key: branch[key] for key in ("argv", "exit_code", "started_at", "ended_at",
                                                                    "gpkg", "stdout", "stderr")}
                                for lod, branch in upstream["branches"].items()},
                            native=output, decisions=decisions,
                            counts=dict(included=len(records), by_lod=dict(Counter(str(r[3]) for r in records)),
                                        excluded=len(decisions)-len(records)),
                            validation=dict(raw_selection="PASS", converter_reconciliation="PASS",
                                            native_attributes="PASS", blob_bytes="PASS", xyz="PASS"))
            marker = stage / "manifest.json"
            bridge.write(marker, manifest)
            check_inputs(artifacts)
            os.link(staged, final)
            published = True
            require(bridge.artifact(final) == {k: output[k] for k in ("path", "size_bytes", "sha256")},
                    "Native", "published bytes differ from audited stage")
            # The manifest is the completion marker. Recheck inputs after publishing the database.
            check_inputs(artifacts)
            os.link(marker, out / "manifest.json")
            completed = True
        return manifest
    except Exception as exc:
        if completed:
            (out / "manifest.json").unlink()
        if published:
            final.unlink()
        bridge.write(out / "failure.json", dict(schema=SCHEMA, profile=PROFILE,
                                                execution_status="FAILED", error=str(exc)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("bridge-receipt", "selector-manifest", "zip", "output-dir"):
        parser.add_argument("--"+flag, required=True, type=Path)
    for flag in ("bridge-sha256", "member", "release"):
        parser.add_argument("--"+flag, required=True)
    parser.add_argument("--bounds", required=True, type=float, nargs=4)
    args = parser.parse_args()
    result = run(args.bridge_receipt, args.bridge_sha256, args.selector_manifest, args.zip, args.output_dir,
                 member=args.member, release=args.release, bounds=args.bounds)
    print(json.dumps(result["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
