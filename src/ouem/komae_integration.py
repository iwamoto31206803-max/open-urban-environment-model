"""Isolated, two-repeat Komae demonstration; never declares formal acceptance."""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

from ouem.adapters.voxcity import VOXCITY_COMMIT, VOXCITY_VERSION
from ouem.native.terrain import load_native_manifest, sha256_file
from ouem.komae_contained import PocBlocked
from ouem.runtime import validate_ouem_runtime
from ouem.study_area import load_study_area

REPOSITORY = Path(__file__).resolve().parents[2]
A3_SCRIPT = "scripts/work/voxcity_komae_a3_acceptance.py"


class Blocked(RuntimeError):
    """A prerequisite is not established; processing must not proceed."""


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def content_hash(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def adjacent(path):
    return Path(str(path) + ".manifest.json")


def fingerprint(path):
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise Blocked(f"not a regular input file: {path}")
    return {"path": str(path), "resolved_path": str(resolved),
            "bytes": resolved.stat().st_size, "sha256": sha256_file(resolved)}


def check_links(path):
    """Reject symlinks, junctions/reparse points, and multiply linked files."""
    if not os.path.lexists(path):
        return
    info = Path(path).lstat()
    reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(info.st_mode) or reparse:
        raise Blocked(f"linked output path is forbidden: {path}")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise Blocked(f"hardlinked output file is forbidden: {path}")


def validate_run_path(run_dir):
    """Only a new direct child of repository data/work/integration is allowed."""
    base = REPOSITORY / "data" / "work" / "integration"
    supplied = Path(run_dir).absolute()
    if ".." in supplied.parts or supplied.parent != base or supplied.name in ("", "."):
        raise Blocked(f"run-dir must be a new direct child of {base}")
    for path in (REPOSITORY, REPOSITORY / "data", REPOSITORY / "data/work", base, supplied):
        check_links(path)
    if base.resolve() != base or os.path.lexists(supplied):
        raise Blocked(f"run directory already exists or has a linked ancestor: {supplied}")
    for path in (REPOSITORY, REPOSITORY / "data", REPOSITORY / "data/work", base):
        if path.exists() and not path.is_dir():
            raise Blocked(f"output ancestor is not a directory: {path}")
    return supplied


def safe_run_path(run_dir):
    supplied = validate_run_path(run_dir)
    supplied.parent.mkdir(parents=True, exist_ok=True)
    supplied.mkdir(exist_ok=False)
    return supplied


def guard_tree(root, identity):
    for path in (REPOSITORY, REPOSITORY / "data", REPOSITORY / "data/work", root.parent, root):
        check_links(path)
    info = root.stat()
    if (info.st_dev, info.st_ino) != identity or root.resolve() != root:
        raise Blocked("run directory identity changed")
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            check_links(Path(directory) / name)


def checkpoint(root, identity, report):
    # Serialize first: invalid JSON must not create an empty, blocking temp file.
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    guard_tree(root, identity)
    descriptor, name = tempfile.mkstemp(prefix="integration-report-", suffix=".json.tmp", dir=root)
    temporary = Path(name)
    # Close the Windows handle before replacement; retain this candidate on failure.
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        created = os.fstat(stream.fileno())
        stream.write(payload)
    for attempt in range(5):
        guard_tree(root, identity)
        current = temporary.lstat()
        if (not stat.S_ISREG(current.st_mode)
                or (current.st_dev, current.st_ino) != (created.st_dev, created.st_ino)):
            raise Blocked("report temporary file identity changed")
        try:
            temporary.replace(root / "integration-report.json")
            return
        except OSError as exc:
            # Windows access/sharing/lock violations can be transient (e.g. a reader).
            # Other errors and exhausted retries remain failures, never a successful save.
            if getattr(exc, "winerror", None) not in (5, 32, 33) or attempt == 4:
                raise
            time.sleep(0.05 * 2 ** attempt)


def voxcity_provenance():
    """Verify PEP 610 installation provenance and RECORD integrity, not upstream bytes."""
    result = {"expected_version": VOXCITY_VERSION, "expected_commit": VOXCITY_COMMIT,
              "verified": False, "method": "PEP 610 VCS origin + installed source RECORD hashes",
              "limitation": "Not an independent comparison with the upstream Git tree."}
    try:
        dist = metadata.distribution("voxcity")
        origin = json.loads(dist.read_text("direct_url.json") or "{}")
        vcs = origin.get("vcs_info", {})
        result.update(version=dist.version, commit=vcs.get("commit_id"), url=origin.get("url"))
        if (dist.version != VOXCITY_VERSION or vcs.get("vcs") != "git"
                or vcs.get("commit_id") != VOXCITY_COMMIT
                or origin.get("url", "").lower().removesuffix(".git")
                != "https://github.com/kunifujiwara/voxcity"
                or origin.get("dir_info", {}).get("editable")):
            raise Blocked("VoxCity pinned non-editable VCS installation is not established")
        package = Path(dist.locate_file("voxcity")).resolve()
        spec = importlib.util.find_spec("voxcity")
        if spec is None or Path(spec.origin).resolve() != package / "__init__.py":
            raise Blocked("VoxCity import is shadowed or cannot be located")
        sources = {p.relative_to(package.parent).as_posix(): p for p in package.rglob("*.py")}
        records = {str(p): p for p in (dist.files or [])}
        if not sources:
            raise Blocked("VoxCity installed sources are unavailable")
        for name, path in sources.items():
            entry = records.get(name)
            if entry is None or entry.hash is None or entry.hash.mode != "sha256":
                raise Blocked(f"VoxCity source lacks a SHA-256 RECORD entry: {name}")
            actual = base64.urlsafe_b64encode(bytes.fromhex(sha256_file(path))).decode().rstrip("=")
            if actual != entry.hash.value:
                raise Blocked(f"VoxCity installed source differs from RECORD: {name}")
        result.update(verified=True, checked_source_files=len(sources),
                      source_content_sha256=content_hash({name: sha256_file(path) for name, path in sources.items()}))
    except (OSError, ValueError, TypeError, metadata.PackageNotFoundError, Blocked) as exc:
        result["reason"] = str(exc)
    return result


def environment():
    git = lambda *args: subprocess.check_output(
        ["git", "--no-optional-locks", *args], cwd=REPOSITORY, text=True).strip()
    return {"python": sys.executable, "python_version": platform.python_version(),
            "platform": platform.platform(), "ouem_commit": git("rev-parse", "HEAD"),
            "working_tree": git("status", "--short"),
            "packages": {name: metadata.version(name) for name in
                         ("numpy", "rasterio", "geopandas", "shapely", "pyproj", "voxcity")},
            "voxcity": voxcity_provenance()}


def input_paths(args):
    paths = {key: Path(getattr(args, key)).absolute() for key in
             ("native_building", "native_terrain", "reference_standard_building", "study_area", "gis_runtime")}
    paths["native_building_manifest"] = adjacent(paths["native_building"])
    paths["reference_building_manifest"] = adjacent(paths["reference_standard_building"])
    paths["raw_terrain"] = Path(read_json(paths["native_terrain"])["terrain"]["source_path"])
    receipt = Path(str(paths["native_building"]) + ".receipt.json")
    if receipt.exists():
        paths["native_building_receipt"] = receipt
    paths["pyproject"] = REPOSITORY / "pyproject.toml"
    paths["a3_runner"] = REPOSITORY / A3_SCRIPT
    for source in sorted((REPOSITORY / "src/ouem").rglob("*.py")):
        paths["code:" + str(source.relative_to(REPOSITORY))] = source
    return paths


def verify_inputs(before):
    checks = {}
    for key, recorded in before.items():
        try:
            checks[key] = fingerprint(recorded["path"]) == recorded
        except (OSError, Blocked):
            checks[key] = False
    return checks


def execute(command, log, *, cwd, env=None):
    """Stream logs; stop the process group on Ctrl+C/SIGTERM before returning."""
    options = {"start_new_session": True} if os.name != "nt" else {
        "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    with Path(log).open("xb") as stream:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, **options)
        try:
            return child.wait()
        except BaseException:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                               stdout=stream, stderr=subprocess.STDOUT, check=False)
            else:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.wait()
            raise


def building_semantics(path):
    import geopandas as gpd
    return building_frame_semantics(gpd.read_file(path, layer="building"))


def building_frame_semantics(frame):
    import pandas as pd
    import numpy as np
    from shapely import get_coordinates, normalize, to_wkb
    fields = ["ouem_id", "source_id", "source_dataset", "source_lod", "measured_height"]
    if frame.crs is None or frame.crs.to_epsg() != 6677 or frame.empty:
        raise Blocked("Standard Building must be nonempty EPSG:6677")
    if frame.ouem_id.isna().any() or frame.ouem_id.duplicated().any():
        raise Blocked("Standard Building IDs must be non-null and unique")
    rows = []
    for _, feature in frame.sort_values("ouem_id").iterrows():
        row = {}
        for field in fields:
            value = feature[field]
            row[field] = None if pd.isna(value) else value.item() if hasattr(value, "item") else value
        geometry = feature.geometry
        if (geometry is None or geometry.is_empty or not geometry.has_z
                or not np.isfinite(get_coordinates(geometry, include_z=True)).all()):
            raise Blocked("Standard Building requires nonempty XYZ geometry")
        row["xyz_wkb"] = to_wkb(normalize(geometry), hex=True, byte_order=1, output_dimension=3)
        rows.append(row)
    return {"crs": "EPSG:6677", "ids": sorted(frame.ouem_id.tolist()),
            "content_sha256": content_hash(rows)}


def raster_semantics(path):
    import numpy as np
    import rasterio
    with rasterio.open(path) as src:
        values = src.read(1, masked=True)
        mask = np.ma.getmaskarray(values)
        return {"crs": str(src.crs), "shape": list(values.shape), "dtype": str(values.dtype),
                "transform": list(src.transform)[:6], "nodata": src.nodata,
                "mask_sha256": hashlib.sha256(mask.tobytes(order="C")).hexdigest(),
                "valid_values_sha256": hashlib.sha256(values.data[~mask].tobytes(order="C")).hexdigest()}


def coverage(building, terrain):
    """Conservatively require valid DEM over the actual engine rectangle envelope."""
    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import Window, from_bounds
    from ouem.adapters.voxcity import build_normalized_footprint, _set_normalized_footprints, _to_voxcity_building_crs
    frame = gpd.read_file(building, layer="building")
    shapes = {r.ouem_id: build_normalized_footprint(r.geometry, r.ouem_id) for r in frame.itertuples()}
    normalized = _set_normalized_footprints(frame, shapes)
    lonlat = _to_voxcity_building_crs(normalized)
    xmin, ymin, xmax, ymax = map(float, lonlat.total_bounds)
    rectangle = [[xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin]]
    with rasterio.open(terrain) as src:
        if src.crs is None or src.crs.to_epsg() != 6677 or src.count != 1:
            raise Blocked("coverage requires single-band EPSG:6677 Terrain")
        bounds = transform_bounds("EPSG:4326", src.crs, xmin, ymin, xmax, ymax, densify_pts=101)
        window = from_bounds(*bounds, transform=src.transform)
        left, top = math.floor(window.col_off), math.floor(window.row_off)
        right, bottom = math.ceil(window.col_off + window.width), math.ceil(window.row_off + window.height)
        if left < 0 or top < 0 or right > src.width or bottom > src.height:
            raise Blocked("DEM does not cover the conservative VoxCity rectangle envelope; no clipping/filling allowed")
        values = src.read(1, window=Window(left, top, right-left, bottom-top), masked=True)
        if values.size == 0 or np.ma.getmaskarray(values).any() or not np.isfinite(values.data).all():
            raise Blocked("DEM contains NoData/non-finite cells in the VoxCity calculation envelope")
    return {"rectangle_vertices_lonlat": rectangle, "dem_envelope_epsg6677": list(bounds),
            "policy": "conservative densified rectangle envelope; every intersecting DEM cell valid"}


def a3_checks(report, expected, meshsize):
    def finite_le(key, limit):
        value = report.get(key)
        return isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= limit
    quality = {key: report.get(key) is True for key in
               ("building_id_grid_produced", "building_voxels_produced", "no_unexplained_loss", "vertical_geometry_consistent")}
    quality.update(count=report.get("input_buildings") == expected,
                   ids=report.get("ids_present") == report.get("ids_expected") == list(range(1, expected+1)),
                   invariant=finite_le("building_specific_absolute_invariant_max_error_m", 1e-7),
                   roof=finite_le("max_absolute_roof_error_m", 2*meshsize),
                   tolerance=report.get("vertical_tolerance_m") == 2*meshsize)
    deterministic = {key: report.get(key) is True for key in
                     ("adapter_serialization_deterministic", "grid_and_voxel_deterministic")}
    return quality, deterministic


def checked_arrays(path):
    import numpy as np
    import re
    evidence = read_json(path)
    if evidence.get("schema") != "ouem-voxcity-array-evidence/v0.1":
        raise RuntimeError("invalid array evidence schema")
    for attempt in ("first", "second"):
        arrays = evidence[attempt]
        if set(arrays) != {"dem", "heights", "segments", "ids", "voxels"}:
            raise RuntimeError("array evidence is incomplete")
        for name, value in arrays.items():
            shape = value["shape"]
            if len(shape) != (3 if name == "voxels" else 2) or any(type(n) is not int or n <= 0 for n in shape):
                raise RuntimeError("invalid array evidence dimensions")
            if not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
                raise RuntimeError("invalid array evidence hash")
            if name != "segments" and np.dtype(value["dtype"]).hasobject:
                raise RuntimeError("numeric evidence cannot contain object pointers")
            encoding = "row-major cell segment JSON" if name == "segments" else "C-order bytes"
            if value["encoding"] != encoding:
                raise RuntimeError("invalid array evidence encoding")
            if shape[:2] != arrays["dem"]["shape"]:
                raise RuntimeError("inconsistent array evidence grids")
    return evidence


def adapter_quality(path, expected_ids):
    from shapely.geometry import shape
    document = read_json(path)
    features = document["features"]
    properties = [f["properties"] for f in features]
    ids = [p["ouem_id"] for p in properties]
    return all((
        document.get("crs", {}).get("properties", {}).get("name") == "urn:ogc:def:crs:EPSG::4326",
        ids == expected_ids,
        all(p["id"] == p["voxcity_id"] == i for i, p in enumerate(properties, 1)),
        all(math.isfinite(p["height"]) and p["height"] > 0 and p["min_height"] == 0 for p in properties),
        all(shape(f["geometry"]).is_valid and not shape(f["geometry"]).is_empty
            and not shape(f["geometry"]).has_z and shape(f["geometry"]).area > 0 for f in features),
    ))


def validate_settings(args):
    if not math.isfinite(args.meshsize) or args.meshsize <= 0 or args.expected_buildings <= 0 or args.expected_native_buildings <= 0:
        raise Blocked("meshsize and expected counts must be positive")


def native_building_manifest(path):
    manifest = read_json(path)
    if manifest.get("schema") != "ouem-plateau-native-ingest/v0.1" or manifest.get("errors"):
        raise Blocked("Native Building acceptance manifest is missing/invalid")
    return manifest


def reference_building(path, manifest_path, expected):
    reference = building_semantics(path)
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "ouem-standard-building-manifest/v0.1":
        raise Blocked("reference Standard Building manifest has an invalid schema")
    if len(reference["ids"]) != expected:
        raise Blocked("reference Standard Building count differs from the expected baseline")
    return reference, manifest


def run(args):
    root = safe_run_path(args.run_dir)
    info = root.stat()
    identity = (info.st_dev, info.st_ino)
    report = {"schema": "ouem-komae-integration/v0.1", "run_id": root.name,
              "started_at": now(), "status": "RUNNING", "quality": "NOT_COMPLETED",
              "reproducibility": "NOT_COMPLETED", "acceptance": "PENDING_LOCAL_REVIEW",
              "not_performed": ["QGIS visual acceptance", "formal integrated real-data acceptance", "nationwide/Phase B validation"],
              "settings": {"meshsize": args.meshsize, "expected_buildings": args.expected_buildings,
                           "expected_native_buildings": args.expected_native_buildings, "repeats": 2},
              "inputs": {}, "stages": [], "repeats": [], "comparisons": {}}
    checkpoint(root, identity, report)
    before = {}
    environment_before = None
    exit_code = 2

    def save():
        checkpoint(root, identity, report)

    def unchanged():
        checks = verify_inputs(before)
        report.setdefault("input_integrity", {}).update(checks)
        if not all(checks.values()):
            raise RuntimeError("input/configuration/manifest changed during the run")
        if environment_before is not None:
            current = environment()
            fields = ("python", "python_version", "platform", "ouem_commit", "packages", "voxcity")
            report["environment_integrity"] = {
                key: current.get(key) == environment_before.get(key) for key in fields}
            if not all(report["environment_integrity"].values()):
                raise RuntimeError("execution environment changed during the run")

    def stage(name, command, *, env=None):
        guard_tree(root, identity)
        unchanged()
        item = {"name": name, "command": command, "started_at": now(), "status": "RUNNING",
                "log": str(root / "logs" / (name + ".log"))}
        report["stages"].append(item)
        save()
        try:
            rc = execute(command, item["log"], cwd=REPOSITORY, env=env)
            item.update(exit_code=rc, status="PASS" if rc == 0 else "FAIL")
            return rc
        except BaseException:
            item["status"] = "INTERRUPTED_OR_ERROR"
            raise
        finally:
            item["finished_at"] = now()
            unchanged()
            save()

    try:
        (root / "logs").mkdir()
        validate_settings(args)
        poc = getattr(args, "contained_poc", False)
        baseline_count = args.expected_buildings
        if poc:
            from ouem import komae_contained as contained
            if args.expected_buildings != contained.SELECTED:
                raise Blocked(f"contained PoC requires --expected-buildings {contained.SELECTED}")
            baseline_count = contained.SELECTED + contained.EXCLUDED
            report["settings"]["selection_policy"] = "contained-building-poc"
            report["settings"]["a1_baseline_count"] = baseline_count
        paths = input_paths(args)
        for key, path in paths.items():
            before[key] = fingerprint(path)
            report["inputs"] = before.copy()
        if any(Path(v["resolved_path"]).is_relative_to(root) for v in before.values()):
            raise Blocked("input and run output paths overlap")
        save()
        env_info = environment()
        environment_before = env_info.copy()
        report["environment"] = env_info
        expected_python = REPOSITORY / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        validate_ouem_runtime(expected_python)
        if not env_info["voxcity"]["verified"]:
            raise Blocked("installed VoxCity commit/integrity could not be verified; see environment.voxcity")
        native = load_native_manifest(paths["native_terrain"])
        area = load_study_area(paths["study_area"])
        report["settings"]["study_area"] = {"id": area.id, "epsg": area.epsg, "extent": list(area.extent)}
        native_building_manifest(paths["native_building_manifest"])
        reference, reference_manifest = reference_building(
            paths["reference_standard_building"], paths["reference_building_manifest"], baseline_count)
        from ouem.adapters.voxcity import check_vertical_compatibility
        check_vertical_compatibility(reference_manifest.get("z_reference", ""), {
            "status": native.vertical_reference_status, "name": native.vertical_reference})
        full_reference = reference
        if poc:
            import geopandas as gpd
            subset, selection = contained.select(gpd.read_file(paths["reference_standard_building"], layer="building"), area)
            report["poc_selection"] = selection
            save()
            contained.validate_selection(selection)
            guard = lambda: guard_tree(root, identity)
            poc_reference = root / "poc-reference.gpkg"
            reference = contained.write_subset(subset, poc_reference, paths["reference_standard_building"], selection, guard=guard)
            report["poc_coverage"] = {"status": "NOT_CHECKED"}
            save()
            try:
                report["poc_coverage"] = {"status": "PASS", **coverage(poc_reference, Path(native.source_path))}
            except Blocked as exc:
                report["poc_coverage"] = {"status": "BLOCKED", "reason": str(exc)}
                raise
            before["poc_reference"] = fingerprint(poc_reference)
            before["poc_reference_manifest"] = fingerprint(adjacent(poc_reference))
            report["inputs"] = before.copy()
            save()
        from ouem.native.building.plateau import load_gis_runtime
        runtime = load_gis_runtime(paths["gis_runtime"])
        report["environment"]["gis"] = {"python": runtime.python, "ogr2ogr": runtime.ogr2ogr,
                                           "ogrinfo": runtime.ogrinfo, "output_encoding": runtime.output_encoding}
        if stage("gis-runtime", [runtime.python, "-c",
                 "import sys; from osgeo import gdal; print(sys.version); print(gdal.VersionInfo('--version'))"], env=runtime.environment):
            raise Blocked("GIS child runtime check failed")
        for number in (1, 2):
            folder = root / f"repeat-{number}"
            folder.mkdir()
            building, terrain = folder / "building.gpkg", folder / "terrain.tif"
            adapter, a3_report, arrays = folder / "adapter.geojson", folder / "a3-report.json", folder / "arrays.json"
            prefix = f"repeat-{number}"
            result = {"repeat": number, "quality": {}, "determinism": {}}
            report["repeats"].append(result)
            if stage(prefix + "-a1", [sys.executable, "-m", "ouem.standardize.building",
                     str(paths["native_building"]), "--output", str(building), "--study-area", str(paths["study_area"]),
                     "--gis-runtime", str(paths["gis_runtime"])]):
                raise RuntimeError("A1 process failed")
            b = read_json(adjacent(building))
            bv = b["validation"]
            sem_b = building_semantics(building)
            result["quality"]["a1"] = all((bv["input_features"] == args.expected_native_buildings,
                bv["output_features"] == baseline_count, bv["z_geometries"] == baseline_count,
                bv["output_crs"] == "EPSG:6677", bv["required_metadata"] is True,
                bv["z_preserved"] is True, 0 <= bv["max_z_delta"] <= 1e-9,
                bv["deterministic_ids"] is True, sem_b["ids"] == full_reference["ids"]))
            if not result["quality"]["a1"]:
                raise RuntimeError("A1 quality criteria failed")
            full_sem_b = sem_b
            full_a1 = {str(p): fingerprint(p) for p in (building, adjacent(building))}
            if poc:
                subset, selected = contained.select(gpd.read_file(building, layer="building"), area)
                result["poc_selection"] = selected
                save()
                contained.validate_selection(selected)
                if selected != selection:
                    raise Blocked("A1 PoC selection differs from the reference selection")
                selected_building = folder / "building-contained.gpkg"
                sem_b = contained.write_subset(subset, selected_building, building, selected, guard=guard)
                building = selected_building
                b = read_json(adjacent(building))
                if sem_b["ids"] != reference["ids"]:
                    raise Blocked("A1 PoC selected IDs differ from reference")
                result["full_a1_fingerprints"] = full_a1
            if stage(prefix + "-a2", [sys.executable, "-m", "ouem.standardize.terrain",
                     str(paths["native_terrain"]), "--output", str(terrain), "--study-area", str(paths["study_area"])]):
                raise RuntimeError("A2 process failed")
            t = read_json(adjacent(terrain))
            tv = t["validation"]
            result["quality"]["a2"] = all((tv["grid_preserved"] is True, tv["elevations_preserved"] is True,
                tv["dtype"] == "float32", tv["standard_nodata"] == -9999.0,
                t["source"]["sha256"] == before["raw_terrain"]["sha256"],
                t["standard"]["sha256"] == sha256_file(terrain)))
            if not result["quality"]["a2"]:
                raise RuntimeError("A2 quality/provenance criteria failed")
            check_vertical_compatibility(b["z_reference"], t["vertical_reference"])
            result["coverage"] = coverage(building, Path(native.source_path))
            if coverage(building, terrain) != result["coverage"]:
                raise Blocked("RAW and Standard coverage differ")
            protected = {str(p): fingerprint(p) for p in (building, adjacent(building), terrain, adjacent(terrain))}
            if poc:
                protected.update(full_a1)
            result["a3_input_fingerprints"] = protected
            a3_exit = stage(prefix + "-a3", [sys.executable, str(REPOSITORY / A3_SCRIPT), str(building), str(terrain),
                         "--adapter-output", str(adapter), "--meshsize", str(args.meshsize),
                         "--expected", str(args.expected_buildings), "--report", str(a3_report),
                         "--array-evidence", str(arrays)])
            if not all(verify_inputs(protected).values()):
                raise RuntimeError("A3 changed a Standard input or manifest")
            a = read_json(adjacent(adapter))
            ar = read_json(a3_report)
            quality, determinism = a3_checks(ar, args.expected_buildings, args.meshsize)
            result["quality"].update(quality)
            result["quality"]["adapter_content"] = adapter_quality(adapter, reference["ids"])
            result["determinism"].update(determinism)
            result["quality"]["lineage"] = all(
                a["inputs"][key]["sha256"] == protected[str(path)]["sha256"]
                for key, path in (("standard_building", building), ("standard_terrain", terrain)))
            result["quality"]["adapter_contract"] = all((
                a["schema"] == "ouem-standard-to-voxcity-building-adapter/v0.1",
                a["voxcity"] == {"version": VOXCITY_VERSION, "commit": VOXCITY_COMMIT},
                a["meshsize"] == args.meshsize,
                a["crs"]["source"] == "EPSG:6677", a["crs"]["target"] == "EPSG:4326",
                a["voxcity_grid"]["building_rasterization"] == "precise geometry intersection",
                a["output"]["sha256"] == sha256_file(adapter)))
            result["quality"]["actual_rectangle"] = a["voxcity_grid"]["rectangle_vertices_lonlat"] == result["coverage"]["rectangle_vertices_lonlat"]
            evidence = checked_arrays(arrays)
            result["determinism"]["array_evidence"] = evidence["first"] == evidence["second"]
            if a3_exit and all(quality.values()) and all(determinism.values()):
                raise RuntimeError("A3 exited unsuccessfully despite passing report")
            # Paths, file-container hashes and timestamps remain in raw evidence, not semantic equality.
            semantic_a = {key: a[key] for key in ("schema", "adapter_version", "voxcity", "runtime", "aoi", "meshsize", "crs",
                "vertical_compatibility", "height_derivation", "ground_derivation", "min_height_derivation",
                "id_derivation", "voxcity_grid", "buildings", "warnings")}
            result["comparison_evidence"] = {"building": sem_b, "terrain": raster_semantics(terrain),
                "terrain_sha256": sha256_file(terrain), "adapter_sha256": sha256_file(adapter),
                "adapter_semantics_sha256": content_hash(semantic_a), "arrays": evidence["first"]}
            if poc:
                result["comparison_evidence"]["full_a1_building"] = full_sem_b
                result["comparison_evidence"]["poc_selection_sha256"] = content_hash(selected)
            save()
        left, right = (r["comparison_evidence"] for r in report["repeats"])
        report["comparisons"] = {key: left[key] == right[key] for key in left}
        quality_pass = all(all(r["quality"].values()) for r in report["repeats"])
        repeat_pass = all(report["comparisons"].values()) and all(all(r["determinism"].values()) for r in report["repeats"])
        report["quality"] = "PASS" if quality_pass else "FAIL"
        report["reproducibility"] = "PASS" if repeat_pass else "FAIL"
        report["status"] = "AUTOMATED_PASS" if quality_pass and repeat_pass else "FAILED"
        exit_code = 0 if report["status"] == "AUTOMATED_PASS" else 1
    except (KeyboardInterrupt, InterruptedError) as exc:
        report.update(status="INTERRUPTED", error=type(exc).__name__)
        exit_code = 130
    except Exception as exc:
        report.update(status="BLOCKED" if isinstance(exc, (Blocked, PocBlocked)) else "FAILED",
                      error=f"{type(exc).__name__}: {exc}")
        exit_code = 2 if isinstance(exc, (Blocked, PocBlocked)) else 1
        if any(False in r["quality"].values() for r in report["repeats"]):
            report["quality"] = "FAIL"
    finally:
        report["input_integrity"] = verify_inputs(before)
        for result in report["repeats"]:
            checks = verify_inputs(result.get("a3_input_fingerprints", {}))
            result["a3_input_integrity"] = checks
            report["input_integrity"].update({f"repeat-{result['repeat']}:{key}": value for key, value in checks.items()})
        if not all(report["input_integrity"].values()):
            report["status"] = "FAILED"
            report["integrity_error"] = "input/configuration/manifest changed or became unavailable"
            exit_code = 1
        if environment_before is not None:
            try:
                unchanged()
            except Exception as exc:
                report["status"] = "FAILED"
                report["integrity_error"] = str(exc)
                exit_code = 1
        attempted = {item["name"] for item in report["stages"]}
        report["not_performed"].extend(
            f"repeat-{number}-{step} execution" for number in (1, 2) for step in ("a1", "a2", "a3")
            if f"repeat-{number}-{step}" not in attempted)
        report["finished_at"] = now()
        finalized = False
        try:
            guard_tree(root, identity)
            report["artifacts"] = {p.relative_to(root).as_posix(): fingerprint(p) for p in sorted(root.rglob("*"))
                                   if p.is_file() and p.name != "integration-report.json"}
            save()
            finalized = True
        except (OSError, Blocked) as exc:
            # Never follow a substituted output link just to finish a report.
            print(f"Cannot safely finalize report; last checkpoint retained: {exc}", file=sys.stderr)
            exit_code = 1
    print(f"{report['status'] if finalized else 'REPORT_SAVE_FAILED'}: {root / 'integration-report.json'}")
    return exit_code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "preflight"])
    for option in ("native-building", "native-terrain", "reference-standard-building", "study-area", "gis-runtime", "run-dir"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--contained-poc", action="store_true", help="Run-only 92/19 contained-building PoC; preserves full A1 validation")
    parser.add_argument("--meshsize", type=float, default=1.0)
    parser.add_argument("--expected-buildings", type=int, default=111)
    parser.add_argument("--expected-native-buildings", type=int, default=3637)
    args = parser.parse_args(argv)
    if args.contained_poc and args.action != "run":
        parser.error("--contained-poc applies only to run; ordinary preflight checks the full reference")
    def interrupted(signum, frame):
        raise InterruptedError(f"signal {signum}")
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.action == "preflight":
            from ouem.komae_preflight import preflight
            report = preflight(args)
            print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
            return 2 if report["status"] == "BLOCKED" else 0
        return run(args)
    except (OSError, Blocked) as exc:
        print(f"BLOCKED before execution: {exc}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(main())
