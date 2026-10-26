"""Acquire only the hash-pinned Tokyo Tama 09LD3451 original; no promotion."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

import rasterio

from ouem.native.terrain import inspect_dem, sha256_file

URL = "https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3451.zip"
MEMBER = "09LD3451.tif"
TIFF_SHA256 = "c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824"
SURVEY_ZIP_SHA256 = "8b54c4cd58e17a6edf86ca7ad9e71672776c90669d116981d1368e871e7c393d"
CATALOG = "https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020"
GSPACE = "https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
TERMS = "https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/doc/license.pdf"
VERTICAL_NAME = "T.P. (Tokyo Peil / Tokyo Bay mean sea level)"
VERTICAL_SOURCE = f"Tokyo Metropolitan Government, Tama dataset metadata: elevation = Tokyo Bay mean sea level; {CATALOG}"
ACCEPTANCE = "docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md"
SCHEMA = "ouem-tokyo-tama-dem-acquisition-poc/v0.1"
MAX_TIFF_BYTES = 4_000_000


class TerrainAcquisitionError(RuntimeError):
    """No completed Raw bundle was established; inspect FAILED evidence."""


def now():
    return datetime.now(timezone.utc).isoformat()


def identity():
    """Disk bytes and Git state are separate evidence, including dirty worktrees."""
    module = Path(__file__).resolve()
    root = module.parents[3]
    result = {"module_sha256": sha256_file(module),
              "native_inspection_module_sha256": sha256_file(root / "src/ouem/native/terrain/__init__.py"),
              "python": platform.python_version(),
              "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__}
    try:
        def git(*args):
            return subprocess.run(["git", "-C", str(root), *args], check=True,
                                  capture_output=True, text=True, timeout=10).stdout.strip()
        result.update(git_commit=git("rev-parse", "HEAD"),
                      git_status_porcelain=git("status", "--porcelain", "--untracked-files=normal"))
    except (OSError, subprocess.SubprocessError):
        result.update(git_commit=None, git_status_porcelain=None)
    return result


def file_info(path):
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}


def download(target, *, timeout, max_bytes):
    """Fixed public HTTPS object, bounded transfer; never a final Raw filename."""
    started = now()
    deadline = time.monotonic() + timeout
    with urllib.request.urlopen(URL, timeout=timeout) as response:
        if response.status != 200 or response.geturl() != URL:
            raise TerrainAcquisitionError("Unexpected HTTP status or redirect")
        length = response.headers.get("Content-Length")
        length = int(length) if length is not None else None
        if length is not None and (length < 0 or length > max_bytes):
            raise TerrainAcquisitionError("Download Content-Length exceeds byte limit")
        size = 0
        with target.open("xb") as stream:
            while True:
                if time.monotonic() > deadline:
                    raise TerrainAcquisitionError("Download deadline exceeded")
                chunk = response.read(min(65536, max_bytes - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise TerrainAcquisitionError("Download exceeds byte limit")
                stream.write(chunk)
        if length is not None and size != length:
            raise TerrainAcquisitionError("Truncated download (Content-Length mismatch)")
        return {"url": URL, "resolved_url": response.geturl(), "status": response.status,
                "started_at": started, "acquired_at": now(),
                "content_length": length, "received_bytes": size,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "content_type": response.headers.get("Content-Type")}


def extract_original(archive, target):
    """Reject all unexpected members; no extract/extractall or pathname joining."""
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) != 1:
            raise TerrainAcquisitionError("ZIP must contain exactly the expected TIFF")
        member = members[0]
        mode = member.external_attr >> 16
        if (member.filename != MEMBER or member.orig_filename != MEMBER or member.is_dir()
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                or member.flag_bits & 1):
            raise TerrainAcquisitionError("Unsafe or unexpected ZIP member")
        if member.file_size <= 0 or member.file_size > MAX_TIFF_BYTES:
            raise TerrainAcquisitionError("ZIP expanded byte limit exceeded")
        size = 0
        with bundle.open(member) as source, target.open("xb") as dest:
            while chunk := source.read(65536):
                size += len(chunk)
                if size > MAX_TIFF_BYTES:
                    raise TerrainAcquisitionError("ZIP expanded byte limit exceeded")
                dest.write(chunk)
        # Reading through EOF verifies this sole member's CRC and ZIP integrity.
        if size != member.file_size:
            raise TerrainAcquisitionError("ZIP member size mismatch")
        return {"member": member.filename, "crc32": f"{member.CRC:08x}",
                "zip_member_timestamp": list(member.date_time)}


def validate_original(path):
    """Read-only reuse of Native inspection, plus this one tile's fixed profile."""
    metadata = inspect_dem(path)
    expected = {"horizontal_crs": "EPSG:6677", "width": 800, "height": 600,
                "band_count": 1, "dtype": "float32", "pixel_size": [0.5, 0.5],
                "extent": [-23600.0, -40800.0, -23200.0, -40500.0],
                "transform": [0.5, 0.0, -23600.0, 0.0, -0.5, -40500.0],
                "source_nodata": 1.701410009187828e38, "valid_cells": 480000,
                "nodata_cells": 0}
    for key, value in expected.items():
        if metadata[key] != value:
            raise TerrainAcquisitionError(f"Unexpected source metadata: {key}")
    with rasterio.open(path) as src:
        if src.driver != "GTiff" or src.scales != (1.0,) or src.offsets != (0.0,):
            raise TerrainAcquisitionError("Unexpected source driver/scale/offset")
    return metadata


def acquire(raw_dir, *, timeout=60.0, max_bytes=10_000_000):
    """Publish a verified original bundle; manifest last, never auto-run Native."""
    if not math.isfinite(timeout) or timeout <= 0 or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise TerrainAcquisitionError("Timeout and byte limit must be positive and finite")
    raw_dir = Path(raw_dir).absolute()
    if "tokyo_23ku_dem_050m" in {part.lower() for part in raw_dir.parts}:
        raise TerrainAcquisitionError("Use a new Tama-labelled Raw directory, not the historical 23-ku tree")
    # Exclusive reservation also rejects pre-existing empty directories/symlinks.
    raw_dir.mkdir(parents=True, exist_ok=False)
    published = []
    record = {"schema": SCHEMA, "status": "IN_PROGRESS", "started_at": now(),
              "raw_directory": str(raw_dir),
              "scope": "Raw acquisition only; no Standard regeneration or formal re-acceptance",
              "provider": "Tokyo Metropolitan Government, Bureau of Digital Services",
              "dataset": "Tokyo Digital Twin Tama point cloud / ground grid 0.50 m / 09LD3451",
              "source": {"url": URL, "catalog": CATALOG, "distribution_catalog": GSPACE,
                         "license": "CC BY 4.0", "license_url": LICENSE, "terms_url": TERMS,
                         "license_evidence": CATALOG,
                         "attribution": "Tokyo Metropolitan Government, Tokyo Digital Twin Tama dataset",
                         "changes": "None: original ZIP and extracted TIFF bytes retained",
                         "vertical_reference": {"status": "source-declared", "name": VERTICAL_NAME,
                                                "source": VERTICAL_SOURCE}},
              "baseline": {"acceptance_record": ACCEPTANCE, "tiff_sha256": TIFF_SHA256,
                           "survey_zip_sha256": SURVEY_ZIP_SHA256},
              "limits": {"timeout_seconds": timeout, "max_download_bytes": max_bytes,
                         "max_expanded_bytes": MAX_TIFF_BYTES},
              "implementation_start": identity()}
    try:
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=raw_dir) as temporary:
            stage = Path(temporary)
            archive, tiff = stage / "09LD3451.zip", stage / MEMBER
            record["http"] = download(archive, timeout=timeout, max_bytes=max_bytes)
            record["archive"] = {"filename": archive.name, **file_info(archive)}
            record["archive"]["matches_survey_zip"] = record["archive"]["sha256"] == SURVEY_ZIP_SHA256
            record["zip_validation"] = extract_original(archive, tiff)
            record["tiff"] = {"filename": MEMBER, **file_info(tiff)}
            if record["tiff"]["sha256"] != TIFF_SHA256:
                record["candidate_revision"] = True
                raise TerrainAcquisitionError("TIFF hash mismatch: different-version candidate; not the accepted original")
            record["raster"] = validate_original(tiff)
            # Recheck after inspection, before publication. No source write or conversion.
            if file_info(archive) != {k: record["archive"][k] for k in ("bytes", "sha256")} or file_info(tiff) != {k: record["tiff"][k] for k in ("bytes", "sha256")}:
                raise TerrainAcquisitionError("Staged input changed during validation")
            record["implementation_end"] = identity()
            if record["implementation_start"] != record["implementation_end"]:
                raise TerrainAcquisitionError("Implementation or worktree changed during acquisition")
            record.update(status="COMPLETED", completed_at=now())
            manifest = stage / "acquisition-manifest.json"
            manifest.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            # Same-filesystem no-clobber links, with every handle already closed.
            for source in (archive, tiff, manifest):
                target = raw_dir / source.name
                os.link(source, target)
                published.append(target)
        return record
    except Exception as exc:
        retained = []
        for path in reversed(published):
            try:
                path.unlink()
            except OSError:
                retained.append(str(path))
        record.update(status="FAILED", failed_at=now(), error=f"{type(exc).__name__}: {exc}",
                      retained_final_paths=retained)
        record.pop("completed_at", None)
        try:
            with (raw_dir / "acquisition-failed.json").open("x", encoding="utf-8") as stream:
                json.dump(record, stream, indent=2, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
        except OSError as report_error:
            raise TerrainAcquisitionError(f"{exc}; FAILED record could not be saved: {report_error}; quarantine {raw_dir}") from exc
        raise TerrainAcquisitionError(f"{exc}; FAILED record in {raw_dir}; retained paths: {retained}; do not reuse this run") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True, help="New run directory under data/raw/terrain/tokyo_tama_dem_050m/komae/")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-bytes", type=int, default=10_000_000)
    args = parser.parse_args(argv)
    try:
        record = acquire(args.raw_dir, timeout=args.timeout, max_bytes=args.max_bytes)
    except (TerrainAcquisitionError, OSError) as exc:
        print(f"Terrain acquisition FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"Raw acquisition COMPLETED: {Path(args.raw_dir).absolute()}")
    print(f"Original TIFF SHA-256: {record['tiff']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
