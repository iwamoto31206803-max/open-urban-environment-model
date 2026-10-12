"""Read-only prerequisite checks; no integration stages or acceptance decisions."""
from __future__ import annotations

import codecs
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from ouem import komae_integration as runner


def validate_interpreter():
    venv = runner.REPOSITORY / ".venv"
    expected = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    runner.validate_ouem_runtime(expected)
    # Resolving the executable alone cannot distinguish POSIX venv symlinks
    # from the base interpreter or another venv sharing the same binary.
    if Path(sys.prefix).resolve() != venv.resolve():
        raise runner.Blocked("active Python prefix is not the repository .venv")


def gis_probe(path):
    """Inspect a snapshot and launch only an import/version probe in its runtime.

    Never disclose the captured environment or child stderr (which may contain
    secrets). The snapshot is executable configuration and must be user-trusted.
    """
    from ouem.native.building.plateau import load_gis_runtime
    value = runner.read_json(path)
    if value.get("schema") != "ouem-gis-runtime/v0.1":
        raise runner.Blocked("GIS snapshot schema must be ouem-gis-runtime/v0.1")
    runtime = load_gis_runtime(path)
    if (not isinstance(runtime.environment, dict) or not runtime.environment
            or any(not isinstance(k, str) or not isinstance(v, str)
                   or "\0" in k + v or "=" in k for k, v in runtime.environment.items())):
        raise runner.Blocked("GIS snapshot requires a nonempty string environment mapping")
    codecs.lookup(runtime.output_encoding or "utf-8")
    for name in ("python", "ogr2ogr", "ogrinfo"):
        executable = Path(getattr(runtime, name))
        if not executable.is_absolute() or not executable.is_file():
            raise runner.Blocked(f"GIS {name} must identify an existing absolute executable path")
    if Path(runtime.python).resolve() == Path(sys.executable).resolve():
        raise runner.Blocked("GIS Python must be separate from OUEM Python")
    code = ("import json,sys; from osgeo import gdal,ogr,osr; "
            "print(json.dumps({'python':sys.executable,'version':sys.version,"
            "'gdal':gdal.VersionInfo('--version')}))")
    result = subprocess.run([runtime.python, "-B", "-c", code], env=runtime.environment,
                            capture_output=True, timeout=30, check=False)
    if result.returncode:
        raise runner.Blocked(f"GIS import/version probe exited {result.returncode}; check snapshot in GIS shell")
    try:
        observed = json.loads(result.stdout.decode("utf-8"))
        matches = Path(observed["python"]).resolve() == Path(runtime.python).resolve()
        valid = bool(observed["version"] and observed["gdal"])
    except (ValueError, KeyError, TypeError):
        raise runner.Blocked("GIS probe did not return the expected version/identity record") from None
    if not matches or not valid:
        raise runner.Blocked("GIS probe interpreter identity/version differs from the snapshot")
    return {"python": observed["python"], "version": observed["version"], "gdal": observed["gdal"],
            "ogr2ogr": runtime.ogr2ogr, "ogrinfo": runtime.ogrinfo,
            "scope": "Python identity and osgeo import/version only; no conversion"}


def inspect_native_building(path, expected):
    import geopandas as gpd
    import numpy as np
    from shapely import get_coordinates
    frame = gpd.read_file(path, layer="building")
    if frame.crs is None or frame.crs.to_epsg() != 4979:
        raise runner.Blocked("Native Building must use EPSG:4979")
    if len(frame) != expected or "id" not in frame:
        raise runner.Blocked("Native Building count or required id field differs from the requested baseline")
    if frame["id"].isna().any() or frame["id"].astype(str).str.strip().eq("").any() or frame["id"].duplicated().any():
        raise runner.Blocked("Native Building IDs must be nonempty and unique")
    for geometry in frame.geometry:
        if geometry is None or geometry.is_empty or not geometry.has_z:
            raise runner.Blocked("Native Building requires nonempty XYZ geometry")
        if not np.isfinite(get_coordinates(geometry, include_z=True)).all():
            raise runner.Blocked("Native Building contains nonfinite coordinates")
    return {"count": len(frame), "crs": "EPSG:4979", "xyz": True}


def preflight(args):
    """Return independent check results, recording failed dependencies as unchecked."""
    report = {"schema": "ouem-komae-preflight/v0.1", "started_at": runner.now(),
              "status": "BLOCKED", "checks": {}, "inputs": {},
              "scope": "Read-only prerequisites; PASS is not processing success or formal acceptance",
              "settings": {key: getattr(args, key) for key in
                           ("meshsize", "expected_buildings", "expected_native_buildings", "run_dir")}}
    checks = report["checks"]
    values = {}

    def check(name, function, action, requires=()):
        if any(checks[key]["status"] != "PASS" for key in requires):
            checks[name] = {"status": "NOT_CHECKED", "reason": "Prerequisite check did not pass",
                            "requires": list(requires), "action": action}
            return
        try:
            values[name] = function()
            checks[name] = {"status": "PASS"}
        except Exception as exc:
            # Snapshot environment and arbitrary child output must not enter the report.
            message = str(exc) if name != "gis_runtime" or isinstance(exc, runner.Blocked) else type(exc).__name__
            checks[name] = {"status": "BLOCKED", "reason": message, "action": action}

    if not math.isfinite(args.meshsize):
        report["settings"]["meshsize"] = str(args.meshsize)
    check("settings", lambda: runner.validate_settings(args),
          "Use finite positive meshsize and positive expected counts.")
    check("output_path", lambda: runner.validate_run_path(args.run_dir),
          "Choose a new direct child of repository data/work/integration; remove no existing evidence.")

    def dependencies():
        validate_interpreter()
        for module in ("numpy", "rasterio", "geopandas", "shapely", "pyproj", "scipy"):
            importlib.import_module(module)
        dependency_check = subprocess.run(
            [sys.executable, "-B", "-m", "pip", "--disable-pip-version-check", "check"],
            capture_output=True, timeout=30, check=False)
        if dependency_check.returncode:
            raise runner.Blocked("dependency consistency check failed; run OUEM Python -m pip check for details")
        info = runner.environment()
        info["python_prefix"] = sys.prefix
        report["environment"] = info
        if not info["voxcity"]["verified"]:
            raise runner.Blocked("VoxCity version/commit/installed RECORD integrity is unverified")
    check("ouem_environment", dependencies,
          "Use repository .venv in an ordinary terminal; restore dependencies from unchanged pyproject.toml and pinned VoxCity.")

    def inputs():
        paths = runner.input_paths(args)
        for key, path in paths.items():
            report["inputs"][key] = runner.fingerprint(path)
        root = Path(args.run_dir).absolute().resolve()
        if any(Path(item["resolved_path"]).is_relative_to(root) for item in report["inputs"].values()):
            raise runner.Blocked("input and output paths overlap")
        # Refuse live SQLite sidecars before opening either accepted GeoPackage.
        for key in ("native_building", "reference_standard_building"):
            resolved = paths[key].resolve()
            if any(os.path.lexists(str(resolved) + suffix) for suffix in ("-wal", "-shm", "-journal")):
                raise runner.Blocked("GeoPackage has active/recovery sidecars; close its writer and review it before preflight")
        return paths
    check("input_inventory", inputs,
          "Supply existing inputs, adjacent manifests, referenced RAW DEM, snapshot and repository files; do not rewrite acceptance evidence.")
    paths = values.get("input_inventory", {})
    prerequisite = ("input_inventory",)

    def area():
        value = runner.load_study_area(paths["study_area"])
        if value.epsg != 6677 or not all(math.isfinite(v) for v in value.extent):
            raise runner.Blocked("Study Area requires EPSG:6677 and finite ordered extent")
        report["study_area"] = {"id": value.id, "epsg": value.epsg, "extent": list(value.extent)}
        return value
    check("study_area", area, "Supply the intended EPSG:6677 Study Area configuration.", prerequisite)

    def terrain():
        native = runner.load_native_manifest(paths["native_terrain"])
        from ouem.standardize.terrain import validate_terrain_input
        validate_terrain_input(native, values["study_area"])
        return native
    check("native_terrain", terrain,
          "Check RAW path/hash and registered raster metadata against the Native manifest; use compliant accepted inputs.", ("input_inventory", "study_area"))

    def native_building():
        runner.native_building_manifest(paths["native_building_manifest"])
        report["native_building"] = inspect_native_building(paths["native_building"], args.expected_native_buildings)
    check("native_building", native_building, "Review Native Building schema, count, CRS, IDs and XYZ geometry.", prerequisite)

    def reference():
        semantics, manifest = runner.reference_building(
            paths["reference_standard_building"], paths["reference_building_manifest"], args.expected_buildings)
        report["reference_building"] = semantics
        return manifest
    check("reference_building", reference, "Review the accepted Standard Building and adjacent manifest.", prerequisite)

    def vertical():
        from ouem.adapters.voxcity import check_vertical_compatibility
        native = values["native_terrain"]
        return check_vertical_compatibility(values["reference_building"].get("z_reference", ""),
                   {"status": native.vertical_reference_status, "name": native.vertical_reference})
    check("vertical_reference", vertical, "Resolve Building/Terrain vertical-reference evidence without changing historical records.",
          ("native_terrain", "reference_building"))
    def coverage():
        report["reference_dem_coverage"] = runner.coverage(paths["reference_standard_building"], paths["raw_terrain"])
    check("reference_dem_coverage", coverage,
          "Provide DEM with complete finite valid coverage of the reference footprint calculation rectangle.",
          ("native_terrain", "reference_building"))
    def gis():
        report["gis"] = gis_probe(paths["gis_runtime"])
    check("gis_runtime", gis, "Verify trusted snapshot or capture a new snapshot separately in the GIS shell; do not overwrite accepted evidence.", prerequisite)

    def unchanged():
        integrity = runner.verify_inputs(report["inputs"])
        report["input_integrity"] = integrity
        if not integrity or not all(integrity.values()):
            raise runner.Blocked("input/configuration/manifest changed or became unavailable during preflight")
    check("inputs_unchanged", unchanged, "Stop concurrent writers and investigate changed input hashes before retrying.", prerequisite)
    # Recheck safety after probes without creating a directory or testing writes.
    check("output_path_final", lambda: runner.validate_run_path(args.run_dir),
          "Choose an unused safe output path; the runner rechecks it at execution.")
    for name, reason in {
        "historical_building_identity": "Building manifests do not certify current GPKG bytes; current SHA-256 is only a new observation, not historical acceptance verification.",
        "output_writability": "No write probe is performed; ACLs, disk space, locks and future path races are not certified.",
        "engine_runtime": "VoxCity provenance and dependency imports are checked, but engine initialization and optional engine modules are not exercised.",
        "gis_tools": "ogr2ogr/ogrinfo paths exist; their operations and compatibility with actual data are not exercised.",
        "a1_gis_conversion": "No transformation/selection: generated count, reference ID retention and Z preservation are untested.",
        "a2_preservation": "No generated Standard Terrain: grid/mask/elevation preservation is untested.",
        "a3_actual_bounds_and_quality": "Reference DEM coverage is preliminary, not the Study Area or newly generated VoxCity calculation bounds; voxel generation, roof error, overlap and vertical invariants require execution.",
        "repeat_reproducibility": "No repeated execution or generated array/content comparisons.",
        "formal_acceptance": "No QGIS visual inspection, integrated real-data acceptance, nationwide applicability or Phase B validation.",
    }.items():
        checks[name] = {"status": "NOT_CHECKED", "reason": reason}
    report["status"] = "BLOCKED" if any(c["status"] == "BLOCKED" for c in checks.values()) else "PASS"
    report["finished_at"] = runner.now()
    return report
