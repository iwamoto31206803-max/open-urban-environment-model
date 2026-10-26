"""Komae-only local helper: explicit inputs, fresh outputs, corrected Tama evidence.

PROCESSING_COMPLETED_PENDING_REVIEW means only that the Native and Standard
CLIs exited successfully. Their own checks are not independent output
verification by this helper, nor formal acceptance. This helper does not
reopen/independently validate their outputs.

Input checks pin the TIFF hash and raster profile, but do not read PR #66's
acquisition manifest, check its COMPLETED status, or compare its recorded
ZIP/TIFF hashes with files. The next formal re-acceptance must independently
check that acquisition evidence and trace it through Native/Standard manifests
to the actual Standard output before a separate acceptance decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from ouem.acquire.tokyo_tama_dem import TIFF_SHA256, VERTICAL_NAME, VERTICAL_SOURCE, validate_original
from ouem.native.terrain import sha256_file

ROOT = Path(__file__).resolve().parents[2]


def preflight(source, run_dir):
    """Read-only checks and command plan; no registration, conversion or acceptance."""
    if Path(run_dir).is_symlink():
        raise ValueError("Run directory must not be a symlink")
    source, run_dir = Path(source).resolve(), Path(run_dir).resolve()
    if not source.is_file() or sha256_file(source) != TIFF_SHA256:
        raise ValueError("Source must match the frozen A2 original SHA-256 (09LD3451)")
    metadata = validate_original(source)
    if run_dir.exists() or run_dir.is_symlink():
        raise ValueError("Run directory must be new; old manifests/artifacts must not be overwritten")
    if not (ROOT / "config/study_areas/komae_09LD3451.yaml").is_file():
        raise ValueError("Repository Komae study-area configuration is missing")
    native = run_dir / "native.json"
    standard = run_dir / "standard.tif"
    commands = [
        [sys.executable, "-m", "pytest", "-q"],
        [sys.executable, "-m", "ouem.native.terrain", str(source), "--output", str(native),
         "--provider", "Tokyo Metropolitan Government, Bureau of Digital Services",
         "--source-dataset", "Tokyo Digital Twin Tama ground grid 0.50 m / 09LD3451",
         "--vertical-reference-status", "source-declared",
         "--vertical-reference", VERTICAL_NAME,
         "--vertical-reference-source", VERTICAL_SOURCE],
        [sys.executable, "-m", "ouem.standardize.terrain", str(native), "--output", str(standard),
         "--study-area", str(ROOT / "config/study_areas/komae_09LD3451.yaml")],
    ]
    return {"status": "READY_FOR_LOCAL_PROCESSING_NOT_ACCEPTED", "source": str(source),
            "source_sha256": TIFF_SHA256, "raster": metadata, "run_directory": str(run_dir),
            "vertical_reference_status": "source-declared", "vertical_reference": VERTICAL_NAME,
            "vertical_reference_source": VERTICAL_SOURCE, "commands": commands}


def run(source, run_dir, *, check=False):
    """Plan or invoke existing CLIs; successful exits alone set pending-review status.

    No acquisition-manifest validation or independent output verification is
    performed here; see the module description and work README for the boundary.
    """
    report = preflight(source, run_dir)
    if check:
        return report
    subprocess.run(report["commands"][0], cwd=ROOT, check=True)
    # Recheck after tests; refuse an output directory created by another run.
    report = preflight(source, run_dir)
    Path(report["run_directory"]).mkdir(parents=True, exist_ok=False)
    for command in report["commands"][1:]:
        subprocess.run(command, cwd=ROOT, check=True)
    report["status"] = "PROCESSING_COMPLETED_PENDING_REVIEW"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Explicit original TIFF, including a new Tama Raw run path")
    parser.add_argument("--run-dir", type=Path, required=True, help="New directory for Native/Standard outputs")
    parser.add_argument("--check", action="store_true", help="Read-only preflight; no tests, files or processing")
    args = parser.parse_args(argv)
    try:
        report = run(args.source, args.run_dir, check=args.check)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"Terrain local helper FAILED: {exc}; retain failed runs for inspection, do not reuse", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
