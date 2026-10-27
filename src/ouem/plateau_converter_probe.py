"""Experimental preflight/fixture evidence; never converts or accepts Building data.

This prepares a new ignored run and records missing prerequisites. A prepared
matrix is NOT an executed Converter verification suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

CANDIDATE = "ce7766df9788ce391b149c55df16d33082d0bc72"
REPOSITORY = "https://github.com/MIERUNE/plateau-gis-converter"
GML = "http://www.opengis.net/gml"
BLDG = "http://www.opengis.net/citygml/building/2.0"
NS = {"gml": GML, "bldg": BLDG}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_fixture(fixture, expected):
    """Bounded structural checks, explicitly not full XSD/solid validation."""
    fixture, expected = Path(fixture), Path(expected)
    if fixture.stat().st_size > 256_000:
        raise ValueError("fixture exceeds synthetic input limit")
    spec = json.loads(expected.read_text(encoding="utf-8"))
    if sha256(fixture) != spec["fixture_sha256"]:
        raise ValueError("fixture hash mismatch")
    data = fixture.read_bytes()
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("DTD/entities are not permitted")
    root = ET.fromstring(data)
    envelope = root.find(".//gml:Envelope", NS)
    if envelope is None or envelope.get("srsName") != "http://www.opengis.net/def/crs/EPSG/0/6697":
        raise ValueError("explicit EPSG:6697 envelope required")
    ids = [node.get(f"{{{GML}}}id") for node in root.iter() if node.get(f"{{{GML}}}id")]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate XML ID")
    buildings = root.findall(".//bldg:Building", NS)
    if {b.get(f"{{{GML}}}id") for b in buildings} != {b["id"] for b in spec["buildings"]}:
        raise ValueError("building identity mismatch")
    checks = []
    for building in buildings:
        identifier = building.get(f"{{{GML}}}id")
        wanted = next(b for b in spec["buildings"] if b["id"] == identifier)
        for lod, selector in [(1, "bldg:lod1Solid"), (2, "bldg:boundedBy")]:
            polygons = [p for branch in building.findall(selector, NS)
                        for p in branch.findall(".//gml:Polygon", NS)]
            if len(polygons) != wanted[f"lod{lod}_polygons"]:
                raise ValueError("LoD polygon count mismatch")
            heights = []
            for polygon in polygons:
                for positions in polygon.findall(".//gml:posList", NS):
                    values = list(map(float, (positions.text or "").split()))
                    if (len(values) < 12 or len(values) % 3 or
                            not all(map(math.isfinite, values)) or values[:3] != values[-3:]):
                        raise ValueError("nonfinite, unclosed or malformed ring")
                    heights.extend(values[2::3])
            if (min(heights), max(heights)) != (wanted["base_H_m"], wanted[f"lod{lod}_top_H_m"]):
                raise ValueError("fixture height range mismatch")
        interiors = building.findall(".//bldg:boundedBy//gml:interior", NS)
        if len(interiors) != wanted["lod2_interior_rings"]:
            raise ValueError("courtyard ring count mismatch")
        for kind in ("RoofSurface", "GroundSurface", "WallSurface"):
            if not building.findall(f".//bldg:{kind}", NS):
                raise ValueError("missing thematic surface")
        checks.append({"id": identifier, "structural_checks": "PASS"})
    return {"status": "PASS", "scope": "XML/identity/LoD/ring/height structure only",
            "full_xsd_validation": "NOT RUN", "solid_topology": "NOT RUN", "buildings": checks}


def record_command(argv, directory, label, timeout=15):
    """Record exact argv/output/exit without shell evaluation or implied acceptance."""
    directory = Path(directory)
    if not label.replace("_", "").isalnum():
        raise ValueError("unsafe log label")
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = subprocess.run(argv, cwd=directory, capture_output=True, timeout=timeout, check=False)
        stdout, stderr, code, error = result.stdout, result.stderr, result.returncode, None
    except (OSError, subprocess.TimeoutExpired) as exc:
        stdout = getattr(exc, "stdout", None) or b""
        stderr = getattr(exc, "stderr", None) or b""
        code, error = None, str(exc)
    for suffix, content in [("stdout", stdout), ("stderr", stderr)]:
        with (directory / f"{label}.{suffix}.log").open("xb") as stream:
            stream.write(content)
    receipt = {"argv": list(map(str, argv)), "cwd": str(directory.resolve()),
               "started_at_utc": started, "ended_at_utc": datetime.now(timezone.utc).isoformat(),
               "exit_code": code, "error": error,
               "stdout_sha256": sha256(directory / f"{label}.stdout.log"),
               "stderr_sha256": sha256(directory / f"{label}.stderr.log")}
    with (directory / f"{label}.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    return receipt


def prepare(repo, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    allowed = (repo / "data/work/plateau-converter-cli").resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("run must be a new child of data/work/plateau-converter-cli")
    output.mkdir(parents=True, exist_ok=False)
    fixtures = repo / "tests/fixtures/plateau_converter"
    fixture, expected = fixtures / "two_buildings.gml", fixtures / "expected.json"
    fixture_checks = inspect_fixture(fixture, expected)
    commands = {tool: record_command([tool, "--version"], output, tool)
                for tool in ("git", "rustc", "cargo")}
    tools = {tool: shutil.which(tool) for tool in ("rustc", "cargo", "cl", "cmake", "nusamai")}
    home = Path.home()
    known = [home / ".cargo/bin/cargo.exe", home / ".cargo/bin/rustc.exe",
             Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"),
             Path("C:/Program Files/Microsoft Visual Studio"),
             Path("C:/Program Files (x86)/Microsoft Visual Studio")]
    prerequisites = {str(path): path.exists() for path in known} if sys.platform == "win32" else {}
    report = {"record_type": "experimental Converter preflight, not acquisition or acceptance",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "candidate": {"repository": REPOSITORY, "commit": CANDIDATE,
                            "executable": None, "executable_sha256": None,
                            "source_archive_sha256": None, "dependencies_acquired": False,
                            "lockfile_url": f"https://raw.githubusercontent.com/MIERUNE/plateau-gis-converter/{CANDIDATE}/Cargo.lock",
                            "observed_lockfile_sha256": "6523c64b038d3c4bd458953a1deef105b0993edf88c1f94d077524d78d0500ef",
                            "lockfile_status": "dated metadata observation, not locally verified by this probe"},
              "environment": {"platform": platform.platform(), "machine": platform.machine(),
                              "python": sys.version, "python_executable": sys.executable,
                              "tool_paths": tools, "known_tool_paths": prerequisites},
              "commands": commands, "fixture": {"path": str(fixture), "sha256": sha256(fixture),
                                                 "expected_sha256": sha256(expected), "checks": fixture_checks},
              "probe_module_sha256": sha256(__file__),
              "converter_execution": "BLOCKED" if not tools["nusamai"] and not tools["cargo"] else "NOT RUN",
              "reason": "no located Windows CLI or Rust build chain" if not tools["nusamai"] and not tools["cargo"] else
                        "preflight only; candidate binary/build and independent validators require review",
              "matrix": {key: "NOT RUN" for key in ("V1_6697", "V2_4979", "V3_6677", "V4_gpkg",
                         "lod_ids", "invalid_xml", "invalid_coordinates", "unsupported_crs",
                         "existing_output", "partial_failure", "repeat_bytes", "repeat_semantics")}}
    with (output / "preflight.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report = prepare(args.repo, args.output_dir)
    print(json.dumps({"converter_execution": report["converter_execution"], "reason": report["reason"],
                      "fixture": report["fixture"]["checks"]["status"]}))
    return 2 if report["converter_execution"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
