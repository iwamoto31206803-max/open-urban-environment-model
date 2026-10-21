"""Read-only, non-acceptance Z diagnosis when saved integration bytes have changed."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem import komae_vertical_provenance as vertical
from ouem.komae_repair_qgis_export import _guard_output, _new_directory
from ouem.standardize.building import deterministic_ouem_id


class ExploratoryEvidence(provenance.Evidence):
    """Record saved-byte failures, but never turn them into verified provenance."""

    def __init__(self, root):
        self.byte_mismatches = []
        super().__init__(root)

    def protect(self, path, record=None):
        path = Path(path).absolute()
        for ancestor in (path, *path.parents):
            runner.check_links(ancestor)
        if path.suffix.lower() == ".gpkg" and any(
                os.path.lexists(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")):
            raise runner.Blocked(f"active/recovery GeoPackage sidecars: {path}; close writers")
        actual = runner.fingerprint(path)
        previous = self.before.setdefault(str(path), actual)
        if previous != actual:
            raise runner.Blocked(f"file changed during exploratory diagnosis: {path}")
        if record is not None and (actual["sha256"] != record["sha256"] or
                                   ("bytes" in record and actual["bytes"] != record["bytes"])):
            finding = {"path": str(path), "recorded_sha256": record["sha256"],
                       "actual_sha256": actual["sha256"], "recorded_bytes": record.get("bytes"),
                       "actual_bytes": actual["bytes"]}
            if finding not in self.byte_mismatches:
                self.byte_mismatches.append(finding)
        return path


def _target(frame, identifier):
    if identifier.startswith("oub-"):
        matches = frame.loc[frame.ouem_id.astype(str) == identifier]
    else:
        matches = frame.loc[frame.source_id.astype(str).str.startswith(identifier)]
    vertical.require(len(matches) == 1, f"target ID {identifier!r} has {len(matches)} Standard matches")
    row = matches.iloc[0]
    source_id, ouem_id = str(row.source_id), str(row.ouem_id)
    vertical.require(deterministic_ouem_id(source_id) == ouem_id,
                     "Standard source_id does not reproduce target ouem_id")
    return source_id, ouem_id


def _adapter_record(evidence, number, ouem_id):
    command = provenance.command(evidence.report, number, "a3")
    adapter_path = evidence.artifact(provenance.option(command, "--adapter-output"))
    manifest = evidence.manifest(adapter_path)
    records = [record for record in manifest["buildings"] if record["ouem_id"] == ouem_id]
    vertical.require(len(records) == 1, f"repeat {number}: missing/duplicate Adapter target")
    return {key: records[0][key] for key in ("voxcity_id", "z_top_abs", "ground_eff_abs", "height",
                                             "ground_sample_min_abs", "ground_sample_max_abs", "ground_sample_count")}


def diagnose_run(root, target_id, citygml=vertical.DEFAULT_GML):
    import geopandas as gpd

    evidence = ExploratoryEvidence(root)
    citygml = evidence.protect(citygml)
    a1 = provenance.command(evidence.report, 1, "a1")
    full = evidence.artifact(provenance.option(a1, "--output"))
    full_manifest = evidence.manifest(full)
    layer = full_manifest["validation"]["output_layer"]
    first_frame = gpd.read_file(full, layer=layer)
    vertical.require(first_frame.crs is not None and first_frame.crs.to_epsg() == 6677,
                     "first Standard CRS is not EPSG:6677")
    source_id, ouem_id = _target(first_frame, target_id)
    try:
        gml = vertical.citygml_buildings(citygml, [source_id])[source_id]
        citygml_check = {"status": "CHECKED"}
    except vertical.UnsupportedCityGMLGeometry as exc:
        gml = None
        citygml_check = {"status": "NOT_CHECKED", "reason": str(exc)}
    native = evidence.input("native_building")
    native_manifest = evidence.document(evidence.input("native_building_manifest"))
    source = native_manifest["source"]
    converter = evidence.protect(source["file"], source)
    stages = {"converter": vertical._feature(converter, source["layer_resolved"], "id", source_id),
              "native": vertical._feature(native, native_manifest["parameters"]["output_layer"], "id", source_id)}
    if gml is not None:
        stages["citygml"] = {**gml, "path": str(citygml)}
    repeats, semantic_checks = [], []
    for number in (1, 2):
        trace = provenance.diagnose_repeat(evidence, number, ouem_id)
        command = provenance.command(evidence.report, number, "a1")
        standard = evidence.artifact(provenance.option(command, "--output"))
        manifest = evidence.manifest(standard)
        frame = first_frame if number == 1 else gpd.read_file(standard, layer=manifest["validation"]["output_layer"])
        semantic = runner.building_frame_semantics(frame)
        saved_repeats = evidence.report.get("repeats", [])
        saved = (saved_repeats[number - 1].get("comparison_evidence", {}).get("full_a1_building")
                 if len(saved_repeats) >= number else None)
        semantic_checks.append({"repeat": number, "current": semantic,
                                "recorded_comparison": "MATCH" if saved == semantic else
                                "MISMATCH" if saved is not None else "NOT_CHECKED",
                                "extra_columns": sorted(set(frame.columns) - {
                                    "ouem_id", "source_id", "source_dataset", "source_lod", "measured_height", "geometry"})})
        standard_stage = vertical._feature(standard, manifest["validation"]["output_layer"], "ouem_id", ouem_id)
        adapter = _adapter_record(evidence, number, ouem_id)
        vertical.require(math.isclose(adapter["z_top_abs"], standard_stage["z_max_m"], abs_tol=1e-6)
                         and math.isclose(adapter["height"], adapter["z_top_abs"] - adapter["ground_eff_abs"], abs_tol=1e-6),
                         f"repeat {number} Adapter/Standard Z or height formula differs")
        repeats.append({"repeat": number, "standard": standard_stage, "adapter": adapter,
                        "lineage": "ISSUES" if trace["issues"] else "CHECKED_EXPLORATORY",
                        "lineage_issues": trace["issues"]})
    vertical.require(repeats[0]["standard"]["sorted_z_sha256"] == repeats[1]["standard"]["sorted_z_sha256"]
                     and repeats[0]["adapter"] == repeats[1]["adapter"],
                     "target Standard Z or Adapter record differs between repeats")
    stages["standard"] = repeats[0]["standard"]
    verdict = vertical._classify(stages, repeats[0]["adapter"], city_link_verified=False)
    stable = evidence.finish()
    vertical.require(all(stable.values()), "an inspected file changed during diagnosis")
    same_repeats = semantic_checks[0]["current"] == semantic_checks[1]["current"]
    if not same_repeats:
        semantic_status = "MISMATCH_REPEATS"
    elif any(item["recorded_comparison"] == "MISMATCH" for item in semantic_checks):
        semantic_status = "MISMATCH_RECORDED"
    elif all(item["recorded_comparison"] == "MATCH" for item in semantic_checks):
        semantic_status = "MATCH_RECORDED_AND_REPEATS"
    else:
        semantic_status = "MATCH_REPEATS_RECORDED_UNAVAILABLE"
    byte_status = "MISMATCH_EXPLORATORY" if evidence.byte_mismatches else "MATCH_INSPECTED_FILES_ONLY"
    lineage_issues = any(item["lineage_issues"] for item in repeats)
    return {"schema": "ouem-komae-vertical-exploratory/v0.1", "scope": "EXPLORATORY_NOT_ACCEPTANCE",
            "run": str(root), "target": {"source_id": source_id, "ouem_id": ouem_id},
            "byte_provenance": {"status": byte_status, "mismatches": evidence.byte_mismatches,
                "inspected_sha256": {path: item["sha256"] for path, item in sorted(evidence.before.items())},
                "stable_during_diagnosis": True,
                "citygml_to_converter_link": "NOT_VERIFIED"},
            "geometry_semantics": {"status": semantic_status, "full_a1": semantic_checks,
                "meaning": "Compared all full-A1 XYZ geometry and contract fields; extra fields are listed, not asserted as the only changes."},
            "vertical_coordinate_diagnosis": {"status": "PARTIAL_EXPLORATORY" if lineage_issues or gml is None else
                "EXPLORATORY" if evidence.byte_mismatches else "CHECKED_SAVED_BYTES",
                "citygml": citygml_check, "stages": stages, "repeats": repeats,
                "first_z_extrema_change": verdict["first_z_extrema_change"],
                "first_z_max_change": verdict["first_z_max_change"], "transitions": verdict["transitions"]},
            "root_cause": {"status": "UNRESOLVED", "reason": "CityGML geometry is unavailable or not hash-linked to the Converter receipt; comparable XYZ points and Converter transformation settings are still required."},
            "limitations": ["Byte mismatches are reported, never waived for acceptance.",
                "Matching geometry semantics do not prove that only an added z_min field changed.",
                "Z extrema or multiset changes alone do not identify a vertical transformation mechanism."]}


def summary(report):
    stages = report["vertical_coordinate_diagnosis"]["stages"]
    lines = ["Komae vertical geometry — EXPLORATORY, NOT ACCEPTANCE",
             f"Run: {report['run']}", f"Target: {report['target']['source_id']} / {report['target']['ouem_id']}",
             f"Byte provenance: {report['byte_provenance']['status']}"]
    lines.extend(f"  MISMATCH {item['path']}: recorded {item['recorded_bytes']} bytes / {item['recorded_sha256']}; actual {item['actual_bytes']} bytes / {item['actual_sha256']}"
                 for item in report["byte_provenance"]["mismatches"])
    lines += [f"Full-A1 geometry and contract fields: {report['geometry_semantics']['status']}"]
    citygml = report["vertical_coordinate_diagnosis"]["citygml"]
    if citygml["status"] == "NOT_CHECKED":
        lines.append(f"citygml: NOT_CHECKED — {citygml['reason']}")
    for name, item in stages.items():
        lines.append(f"{name}: Z {item['z_min_m']:.3f} .. {item['z_max_m']:.3f} m ({item['vertex_count']} vertices)")
    lines += [f"First observed Z-max change: {report['vertical_coordinate_diagnosis']['first_z_max_change']}",
              f"Vertical diagnosis status: {report['vertical_coordinate_diagnosis']['status']}",
              "Root cause: UNRESOLVED — confirm comparable XYZ points and Converter settings.",
              "A byte mismatch remains a formal provenance failure even if geometry semantics match."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("target_id", help="unique PLATEAU source ID prefix or exact ouem_id")
    parser.add_argument("--citygml", type=Path, default=vertical.DEFAULT_GML)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("run ID must be a portable name of at most 64 characters")
    root = runner.REPOSITORY / "data/work/integration" / args.run_id
    citygml = args.citygml if args.citygml.is_absolute() else runner.REPOSITORY / args.citygml
    try:
        report = diagnose_run(root, args.target_id, citygml)
        directory, identity = _new_directory(runner.REPOSITORY / "data/work/vertical-exploratory", root, args.run_id)
        for name, content in (("diagnosis.json", json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"),
                              ("summary.txt", summary(report))):
            _guard_output(directory.parent, directory, identity)
            with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        print(summary(report), end="")
        print(f"Diagnostic files: {directory}")
        return 0
    except Exception as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
