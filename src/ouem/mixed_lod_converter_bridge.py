"""Experimental two-pass nusamai bridge; produces reconciliation evidence only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from ouem import mixed_lod_selector as raw
from ouem.native.building.source_h_geometry import inspect_geopackage, polygons, require
from ouem.native.building.source_h_lod2 import _signature
from ouem.real_komae_source_h import CLI_SHA, write

SCHEMA = "ouem-mixed-lod-converter-bridge/v0.1"
LAYER = "bldg:Building"
VERSION = "nusamai 0.1.19"
COMMIT = "ce7766df9788ce391b149c55df16d33082d0bc72"
MATCHES = {"EXACT", "ORDER_ONLY"}


def artifact(path):
    return dict(path=str(path), sha256=raw.digest(path), size_bytes=path.stat().st_size)


def verify_artifact(record):
    path = Path(record["path"])
    require(artifact(path) == record, str(path), "artifact identity changed")
    return path


def load_selector(manifest_path, zip_path, member, release, bounds):
    """Replay Raw selection against explicit inputs and check both saved artifacts."""
    saved = json.loads(manifest_path.read_bytes())
    require(saved.get("execution_status") == "COMPLETED" and saved.get("input_unchanged") is True,
            "selector", "successful Raw selector manifest required")
    require(saved.get("implementation_sha256") == raw.digest(raw.__file__),
            "selector", "stale selector implementation identity")
    geometry_path = manifest_path.with_name("geometries.jsonl")
    identity = saved["geometry_output"]
    require(identity["path"] == geometry_path.name and raw.digest(geometry_path) == identity["sha256"],
            "selector", "geometry artifact hash mismatch")
    replay, selected = raw.select_raw(zip_path, [member], release=release, bounds=bounds)
    for key, value in replay.items():
        require(saved.get(key) == value, "selector."+key, "saved selection differs from Raw replay")
    with geometry_path.open("rb") as stream:
        for row in replay["records"]:
            sid = row["source_id"]
            if sid in selected:
                expected = dict(source_id=sid, selected_lod=row["selected_lod"], faces=selected[sid])
                require(stream.readline() == raw.canonical(expected)+b"\n", sid, "saved XYZ differs from Raw replay")
        require(not stream.read(1), "selector", "unexpected geometry records")
    return replay, selected


def extract(zip_path, member, destination):
    with ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not (info.filename == member or info.filename.startswith("codelists/")):
                continue
            name = PurePosixPath(info.filename)
            target = (destination / name).resolve()
            require(target.is_relative_to(destination) and "\\" not in info.filename
                    and ".." not in name.parts, "ZIP", "unsafe member path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
    return destination / member


def expected_by_lod(records, selected, extracted):
    expected = {1: {}, 2: {}}
    alternate = set()
    for row in records:
        sid, lod = row["source_id"], row["selected_lod"]
        if lod is not None:
            expected[lod][sid] = selected[sid]
        if lod == 2 and row["lod1_presence"]:
            alternate.add(sid)
    # LoD1 of dual-LoD buildings is validated by the selector, but is not in its JSONL.
    if alternate:
        for _, node in ET.iterparse(extracted, events=("end",)):
            if node.tag == raw.B+"Building":
                sid = node.get(raw.G+"id")
                if sid in alternate:
                    solid = node.find(raw.B+"lod1Solid")
                    faces = []
                    for polygon in solid.iter(raw.G+"Polygon"):
                        rings = []
                        for pos in polygon.iter(raw.G+"posList"):
                            ordinates = iter(map(float, pos.text.split()))
                            rings.append(tuple((lon, lat, h) for lat, lon, h in zip(
                                ordinates, ordinates, ordinates, strict=True)))
                        faces.append(tuple(rings))
                    expected[1][sid] = tuple(faces)
                node.clear()
            elif node.tag.endswith("}cityObjectMember"):
                node.clear()
        require(alternate <= expected[1].keys(), "LoD1", "Raw alternate geometry missing")
    return expected


def reconcile(expected, snapshot):
    actual = snapshot.features
    features = {}
    for sid in sorted(expected.keys() | actual.keys()):
        if sid not in actual:
            features[sid] = dict(result="MISSING")
        elif sid not in expected:
            features[sid] = dict(result="UNEXPECTED")
        else:
            source, converted = expected[sid], polygons(actual[sid])
            if source == converted:
                result = "EXACT"
            elif _signature(source) == _signature(converted):
                result = "ORDER_ONLY"
            else:
                result = "GEOMETRY_MISMATCH"
            features[sid] = dict(result=result, layer=snapshot.layer, id=sid,
                                 blob_sha256=snapshot.geometry_hashes[sid],
                                 raw_faces=len(source), converter_faces=len(converted),
                                 raw_interiors=sum(len(face)-1 for face in source),
                                 converter_interiors=sum(len(face)-1 for face in converted),
                                 geometry_type=actual[sid][0])
    return dict(expected_features=len(expected), converter_features=len(actual),
                results=dict(Counter(feature["result"] for feature in features.values())),
                features=features)


def convert(binary, extracted, lod, out, expected):
    output = out / f"lod{lod}.gpkg"
    argv = [str(binary), str(extracted), "--sink", "gpkg", "--output", str(output),
            "--epsg", "6697", "-t", f"use_lod=lod{lod}", "-t", "split_components=false"]
    execution = dict(argv=argv, started_at=datetime.now(timezone.utc).isoformat(),
                     expected_features=len(expected), exit_code=None)
    stdout, stderr = out / f"lod{lod}.stdout.log", out / f"lod{lod}.stderr.log"
    try:
        with stdout.open("xb") as log, stderr.open("xb") as errors:
            execution["exit_code"] = subprocess.run(argv, stdout=log, stderr=errors, check=False).returncode
        execution.update(stdout=artifact(stdout), stderr=artifact(stderr))
        if output.is_file():
            execution["gpkg"] = artifact(output)
        require(execution["exit_code"] == 0, "Converter", "nonzero exit; see logs")
        comparison = reconcile(expected, inspect_geopackage(output, LAYER))
        verify_artifact(execution["gpkg"])
        execution.update(comparison)
    except (OSError, ValueError) as exc:
        execution["error"] = str(exc)
    execution["ended_at"] = datetime.now(timezone.utc).isoformat()
    return execution


def run(manifest_path, zip_path, binary, out, *, member, release, bounds):
    manifest_path, zip_path, binary, out = (Path(p).resolve() for p in (manifest_path, zip_path, binary, out))
    out.mkdir()  # New run only, including rejected runs.
    report = dict(schema=SCHEMA, status="EXPERIMENTAL", execution_status="FAILED",
                  mixed_native_handoff="BLOCKED", python=platform.python_version(),
                  platform=platform.platform(), implementation=artifact(Path(__file__).resolve()))
    try:
        report["selector_manifest"] = artifact(manifest_path)
        report["selector_geometry"] = artifact(manifest_path.with_name("geometries.jsonl"))
        replay, selected = load_selector(manifest_path, zip_path, member, release, bounds)
        report.update(raw_source=replay["source"], crs=replay["crs"], aoi=replay["aoi"],
                      raw_counts=replay["counts"])
        verify_artifact(report["selector_manifest"])
        verify_artifact(report["selector_geometry"])
        report["converter"] = dict(binary=artifact(binary), commit=COMMIT)
        require(report["converter"]["binary"]["sha256"] == CLI_SHA, "Converter", "fixed binary SHA mismatch")
        version = subprocess.run([str(binary), "--version"], check=True, capture_output=True, text=True).stdout.strip()
        require(version == VERSION, "Converter", "unexpected version")
        report["converter"]["version"] = version
        extracted = extract(zip_path, member, out / "extracted")
        report["extracted_member"] = artifact(extracted)
        require(report["extracted_member"]["sha256"] == replay["source"]["members"][0]["sha256"],
                "ZIP", "extracted member hash mismatch")
        expected = expected_by_lod(replay["records"], selected, extracted)
        report["branches"] = {}
        for lod in (1, 2):
            verify_artifact(report["extracted_member"])
            verify_artifact(report["converter"]["binary"])
            report["branches"][str(lod)] = convert(binary, extracted, lod, out, expected[lod])
        report["selection"] = []
        for row in replay["records"]:
            sid, lod = row["source_id"], row["selected_lod"]
            comparison = report["branches"].get(str(lod), {}).get("features", {}).get(sid)
            eligible = comparison is not None and comparison["result"] in MATCHES
            report["selection"].append(dict(source_id=sid, selected_lod=lod,
                                            selection_reason=row["selection_reason"],
                                            aoi_intersects=row["aoi_intersects"], feature=comparison,
                                            feature_eligible=eligible))
        for key in ("selector_manifest", "selector_geometry", "extracted_member", "implementation"):
            verify_artifact(report[key])
        verify_artifact(report["converter"]["binary"])
        require(raw.digest(zip_path) == replay["source"]["zip_sha256"], "ZIP", "input changed")
        for branch in report["branches"].values():
            if "gpkg" in branch:
                verify_artifact(branch["gpkg"])
        candidate = [row for row in report["selection"] if row["aoi_intersects"]]
        report["candidate"] = dict(selected=len(candidate),
                                   feature_eligible=sum(row["feature_eligible"] for row in candidate))
        ready = all("error" not in branch and all(f["result"] in MATCHES for f in branch["features"].values())
                    for branch in report["branches"].values())
        report.update(execution_status="COMPLETED", mixed_native_handoff="ELIGIBLE" if ready else "BLOCKED")
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, subprocess.SubprocessError) as exc:
        report["error"] = str(exc)
    pending = out / "bridge.pending.json"
    write(pending, report)
    pending.rename(out / "bridge.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("selector-manifest", "zip", "converter", "output-dir"):
        parser.add_argument("--"+flag, required=True, type=Path)
    parser.add_argument("--member", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--bounds", required=True, nargs=4, type=float)
    args = parser.parse_args()
    report = run(args.selector_manifest, args.zip, args.converter, args.output_dir,
                 member=args.member, release=args.release, bounds=args.bounds)
    print(report.get("error", report["mixed_native_handoff"]))
    return 0 if report["mixed_native_handoff"] == "ELIGIBLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
