"""Independent, experimental source-H ingestion; no Standardizer integration."""
from __future__ import annotations

import copy
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime, timezone

from .provenance import NATIVE_SCHEMA, SOURCE_H_PROFILE, validate_source_h_inputs, validate_source_h_record
from .source_h_geometry import GeometryValidationError, compare_snapshots, inspect_geopackage, open_readonly, require
from .source_h_lod2 import compare_lod2, read_lod2


class SourceHIngestionError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(json.dumps(report, ensure_ascii=False))


def _digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check(report):
    if not report.foundation_valid:
        raise SourceHIngestionError({"status": "FAILED", "provenance": report.to_dict()})


def _copy_database(source, output):
    # sqlite3's transaction context does NOT close the connection on exit.
    with open_readonly(source) as origin, closing(sqlite3.connect(output)) as target:
        origin.backup(target)
        target.commit()


def _publish(source, destination):
    # All database handles closed. Never overwrite even a concurrent destination.
    os.link(source, destination)


def ingest_source_h(record, *, artifact_root):
    """Create a new, verified Native file; errors never establish eligibility."""
    try:
        return _ingest_source_h(record, artifact_root=artifact_root)
    except SourceHIngestionError:
        raise
    except Exception as exc:
        raise SourceHIngestionError({"status": "FAILED", "issue": {
            "code": getattr(exc, "code", "INGESTION_FAILED"),
            "field": getattr(exc, "field", "ingestion"), "reason": str(exc)},
            "eligibility": "NOT_ESTABLISHED"}) from exc


def _ingest_source_h(record, *, artifact_root):
    """Accept a plan with unmaterialized Native path/layer, return final records.

    Output parent must be a new directory inside artifact_root. The manifest is
    the completion marker; ordinary exceptions roll back this run's outputs.
    """
    plan = copy.deepcopy(record)
    _check(validate_source_h_inputs(plan, artifact_root=artifact_root))
    root = Path(artifact_root).resolve(strict=True)
    native_id = plan["native"]["output_artifact_id"]
    source_id = plan["native"]["input_artifact_id"]
    native_ref, source_ref = plan["artifacts"][native_id], plan["artifacts"][source_id]
    locator = Path(native_ref["path"])
    require(not locator.is_absolute() and not locator.drive and ".." not in locator.parts,
            "native.path", "new relative Native path required")
    output = (root/locator).resolve()
    require(output.is_relative_to(root) and output.parent != root, "native.path", "new child run directory required")
    require(output.suffix.lower() == ".gpkg", "native.path", "Native must be GeoPackage")
    require(native_ref["layer"] == source_ref["layer"], "native.layer", "Step 2 preserves original layer name")
    source = root/source_ref["path"]
    published = []
    claimed = False
    try:
        source_snapshot = inspect_geopackage(source, source_ref["layer"])
        raw, excluded = read_lod2(root/a["path"] for a in plan["artifacts"].values() if a["role"] == "raw_citygml")
        lod_qa = compare_lod2(source_snapshot, raw)
        # No ancestor creation or existing directory reuse; exclusive ownership.
        output.parent.mkdir()
        claimed = True
        with tempfile.TemporaryDirectory(prefix=".unverified-", dir=output.parent) as temporary:
            temporary = Path(temporary)
            staged = temporary/"native.gpkg"
            _copy_database(source, staged)
            native_snapshot = inspect_geopackage(staged, native_ref["layer"])
            qa = compare_snapshots(source_snapshot, native_snapshot) | lod_qa
            qa.update({"gpkg_structure": "PASS", "source_h_eligibility": "NOT_ESTABLISHED",
                       "human_review": "NOT_VERIFIED", "formal_acceptance": "NOT_VERIFIED",
                       "excluded_no_lod2_ids": excluded})
            # Revalidate all actual inputs after reading/copying; no stale reuse.
            _check(validate_source_h_inputs(plan, artifact_root=root))
            final = copy.deepcopy(plan)
            final["artifacts"][native_id].update(size_bytes=staged.stat().st_size, sha256=_digest(staged))
            staged_record = copy.deepcopy(final)
            staged_record["artifacts"][native_id]["path"] = staged.relative_to(root).as_posix()
            _check(validate_source_h_record(staged_record, artifact_root=root))
            _publish(staged, output)
            published.append(output)
            # Final validation refers to the actual final Native file, not plan or stage.
            final_report = validate_source_h_record(final, artifact_root=root)
            _check(final_report)
            compare_snapshots(source_snapshot, inspect_geopackage(output, native_ref["layer"]))
            final["validation"] = {"execution_status": "COMPLETED", "processed_at": datetime.now(timezone.utc).isoformat(),
                                   "foundation": final_report.to_dict(), "ingestion": qa}
            final["eligibility_review"] = {"status": "NOT_VERIFIED"}
            final["acceptance"] = {"status": "NOT_VERIFIED"}
            manifest = output.with_suffix(".gpkg.manifest.json")
            receipt = output.with_suffix(".gpkg.receipt.json")
            staged_manifest = temporary/"manifest.json"
            staged_manifest.write_text(json.dumps(final, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            receipt_value = {"schema": "ouem-plateau-native-receipt/v0.2", "profile": SOURCE_H_PROFILE,
                "native_sha256": _digest(output), "manifest_sha256": _digest(staged_manifest),
                "eligibility": "NOT_ESTABLISHED", "status": "COMPLETED"}
            staged_receipt = temporary/"receipt.json"
            staged_receipt.write_text(json.dumps(receipt_value, indent=2)+"\n", encoding="utf-8")
            _publish(staged_receipt, receipt)
            published.append(receipt)
            _check(validate_source_h_record(final, artifact_root=root))
            _publish(staged_manifest, manifest)  # Completion marker published last.
            published.append(manifest)
        return {"status": "COMPLETED", "profile": SOURCE_H_PROFILE, "manifest_schema": NATIVE_SCHEMA,
                "output": str(output), "manifest": str(manifest), "receipt": str(receipt), "qa": qa}
    except Exception as exc:
        cleanup_errors = []
        for path in reversed(published):
            try:
                path.unlink()
            except OSError as cleanup:
                cleanup_errors.append({"path": str(path), "reason": str(cleanup)})
        if claimed:
            try:
                output.parent.rmdir()
            except OSError as cleanup:
                cleanup_errors.append({"path": str(output.parent), "reason": str(cleanup)})
        if isinstance(exc, SourceHIngestionError) and not cleanup_errors:
            raise
        issue = {"code": getattr(exc, "code", "INGESTION_FAILED"),
                 "field": getattr(exc, "field", "ingestion"), "reason": str(exc)}
        raise SourceHIngestionError({"status": "FAILED", "issue": issue,
                                     "cleanup_errors": cleanup_errors,
                                     "eligibility": "NOT_ESTABLISHED"}) from exc
