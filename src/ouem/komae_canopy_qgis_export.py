"""Read-only export of saved Komae canopy voxels for local QGIS review.

The output is diagnostic evidence, never a formal acceptance decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem.komae_repair_qgis_export import _guard_output, _new_directory


TREE = -2
BUILDING = -3
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10))}


def require(ok, message):
    if not ok:
        raise runner.Blocked(message)


def _array_digest(array):
    require(not array.dtype.hasobject, "object voxel array is forbidden")
    return hashlib.sha256(np.ascontiguousarray(array).tobytes(order="C")).hexdigest()


def _read_array(evidence, report_path, report, name, record):
    filename = name + "-voxels.npy"
    require(filename in report.get("outputs", {}), f"missing {filename} hash")
    path = report_path.parent / filename
    require(evidence.artifact(str(path)) == path and
            runner.sha256_file(path) == report["outputs"][filename],
            f"{filename}: saved file SHA-256 mismatch")
    data = np.load(path, allow_pickle=False, mmap_mode="r")
    require(data.ndim == 3 and data.dtype.kind in "iu" and
            data.dtype.str == record["dtype"] and list(data.shape) == record["shape"] and
            _array_digest(data) == record["sha256"], f"{filename}: array evidence mismatch")
    return data


def _one_repeat(evidence, number):
    a3 = provenance.command(evidence.report, number, "a3")
    require(len(a3) > 3 and a3[1].endswith("voxcity_komae_a3_acceptance.py"),
            "unsupported A3 command")
    terrain = evidence.artifact(a3[3])
    adapter = evidence.artifact(provenance.option(a3, "--adapter-output"))
    a3_report = evidence.artifact(provenance.option(a3, "--report"))
    canopy_path = evidence.artifact(provenance.option(a3, "--canopy-report"))
    arrays_path = evidence.artifact(provenance.option(a3, "--array-evidence"))
    manifest = evidence.manifest(adapter)
    canopy = evidence.document(canopy_path)
    array_evidence = evidence.document(arrays_path)
    require(manifest.get("schema") == "ouem-standard-to-voxcity-building-adapter/v0.1" and
            canopy.get("schema") == "ouem-komae-meta-chm-canopy/v0.1" and
            canopy.get("status") == "AUTOMATED_PASS" and
            canopy.get("acceptance") == "PENDING_LOCAL_REVIEW" and
            canopy.get("repeat_deterministic") is True,
            f"repeat {number}: canopy evidence is not an automated PASS awaiting review")
    require(manifest.get("voxcity") == {"version": runner.VOXCITY_VERSION,
                                        "commit": runner.VOXCITY_COMMIT} and
            manifest["inputs"]["standard_terrain"]["sha256"] == runner.sha256_file(terrain) and
            evidence.artifact(manifest["inputs"]["standard_terrain"]["path"]) == terrain and
            manifest["output"]["sha256"] == runner.sha256_file(adapter),
            f"repeat {number}: Adapter pin or terrain/output lineage differs")
    require(array_evidence.get("first") == array_evidence.get("second") == canopy["component_evidence"],
            f"repeat {number}: A3 component evidence differs")
    require(evidence.document(a3_report).get("building_voxels_produced") is True,
            f"repeat {number}: A3 report did not produce buildings")
    current = _read_array(evidence, canopy_path, canopy, "current", canopy["current"])
    bare = _read_array(evidence, canopy_path, canopy, "no-canopy", canopy["no_canopy"])
    rectangle = manifest["voxcity_grid"]["rectangle_vertices_lonlat"]
    mesh = float(manifest["meshsize"])
    require(math.isfinite(mesh) and mesh > 0, "invalid saved mesh size")
    require(manifest["crs"]["target"] == "EPSG:4326" and
            manifest["crs"]["source"] == "EPSG:6677", "unexpected Adapter CRS")
    require(current.shape[:2] == bare.shape[:2], "scenario horizontal grids differ")
    return dict(number=number, terrain=terrain, adapter=adapter, manifest=manifest,
                canopy=canopy, current=current, bare=bare, rectangle=rectangle,
                mesh=mesh, paths=[str(terrain), str(adapter), str(a3_report),
                                  str(canopy_path), str(arrays_path)])


def _compare_scenarios(one):
    current, bare, report = one["current"], one["bare"], one["canopy"]
    require(current.dtype == bare.dtype, "scenario voxel dtypes differ")
    depth = max(current.shape[2], bare.shape[2])
    padded = np.zeros((*current.shape[:2], depth), dtype=current.dtype)
    padded[:, :, :bare.shape[2]] = bare
    other = np.zeros_like(padded)
    other[:, :, :current.shape[2]] = current
    tree = other == TREE
    building = other == BUILDING
    count = int(np.count_nonzero(tree))
    changed = int(np.count_nonzero(other != padded))
    require(count > 0 and count == report["current"]["tree_voxels"] and
            int(np.count_nonzero(padded == TREE)) == report["no_canopy"]["tree_voxels"] == 0 and
            int(np.count_nonzero(building)) == int(np.count_nonzero(padded == BUILDING)) ==
            report["current"]["building_voxels"] == report["no_canopy"]["building_voxels"] and
            np.array_equal(building, padded == BUILDING) and
            np.array_equal(other != padded, tree) and
            changed == count == report["scenario_difference"]["changed_voxels"] ==
            report["scenario_difference"]["tree_voxels_added"],
            "saved scenario counts, building retention or differences disagree")
    # A positive land-cover class is placed at ground_level-1. Trees occupy
    # higher k, including above a building where building does not overwrite.
    landcover = padded > 0
    surface_k = np.max(np.where(landcover, np.arange(depth), -1), axis=2)
    require(np.all(surface_k >= 0) and
            np.all(np.where(tree)[2] > surface_k[np.where(tree)[0], np.where(tree)[1]]),
            "tree voxel lies at/below saved land-cover surface")
    return {"tree_voxels": count, "tree_cells": int(np.count_nonzero(np.any(tree, axis=2))),
            "building_voxels": int(np.count_nonzero(building)), "changed_voxels": changed,
            "tree_mask": tree}


def _grid(one):
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords
    grid = compute_cell_center_coords(one["rectangle"], one["mesh"])
    require(grid is not None and tuple(grid["grid_size"]) == one["current"].shape[:2],
            "pinned VoxCity grid geometry differs from saved voxel shape")
    require(np.isfinite(grid["lons"]).all() and np.isfinite(grid["lats"]).all(),
            "grid has nonfinite cell centres")
    return grid


def _dem_grid(one):
    # Read-only reconstruction of the actual A3 DEM grid, checked against the
    # saved A3 digest. Never rerun A1/A2, building rasterization or voxelization.
    from voxcity.geoprocessor.raster import create_dem_grid_from_geotiff_polygon
    dem = create_dem_grid_from_geotiff_polygon(one["terrain"], one["mesh"],
                                                one["rectangle"], dem_interpolation=False)
    record = one["canopy"]["component_evidence"]["dem"]
    require(dem.dtype.str == record["dtype"] and list(dem.shape) == record["shape"] and
            _array_digest(dem) == record["sha256"] and np.isfinite(dem).all(),
            "reconstructed VoxCity DEM differs from saved A3 evidence")
    return dem


def _check_vertical_datum(one, dem):
    """Prove the shifted-engine zero using an unbuilt raw-DEM minimum cell."""
    bare = one["bare"]
    building_cells = np.any(bare == BUILDING, axis=2)
    minimum = float(np.min(dem))
    unbuilt_minimum = (dem == minimum) & ~building_cells
    require(np.any(unbuilt_minimum),
            "cannot prove absolute voxel datum: every raw DEM minimum cell has a building")
    surface = np.max(np.where(bare > 0, np.arange(bare.shape[2]), -1), axis=2)
    # Pinned Numba path passes the processed DEM as float32 to its kernel.
    expected = np.floor(np.asarray(dem - minimum, dtype=np.float32) /
                        one["mesh"] + 0.5).astype(int)
    require(np.array_equal(surface[~building_cells], expected[~building_cells]),
            "saved voxel ground levels disagree with reconstructed DEM outside buildings")
    return minimum, int(np.count_nonzero(~building_cells))


def _cell_polygon(grid, i, j):
    from shapely.geometry import Polygon
    origin, u, v = grid["origin"], grid["u_vec"], grid["v_vec"]
    dx, dy = grid["adj_mesh"]
    def corner(a, b):
        xy = origin + a * dx * u + b * dy * v
        return float(xy[0]), float(xy[1])
    polygon = Polygon([corner(i, j), corner(i + 1, j), corner(i + 1, j + 1), corner(i, j + 1)])
    require(polygon.is_valid and polygon.area > 0, "invalid VoxCity cell polygon")
    centre = polygon.centroid
    require(abs(centre.x - grid["lons"][i, j]) < 1e-9 and
            abs(centre.y - grid["lats"][i, j]) < 1e-9,
            "cell polygon disagrees with pinned VoxCity centre/orientation")
    return polygon


def _features(tree, grid, dem_min, mesh):
    from shapely.ops import unary_union
    cells = {}
    spans = {}
    for i, j in np.argwhere(np.any(tree, axis=2)):
        i, j = int(i), int(j)
        polygon = provenance.reproject_xy(_cell_polygon(grid, i, j), 4326, 6677)
        require(polygon.is_valid and polygon.area > 0, "invalid projected VoxCity cell")
        cells[i, j] = polygon
        levels = np.flatnonzero(tree[i, j])
        start = previous = int(levels[0])
        for k in map(int, levels[1:]):
            if k != previous + 1:
                spans.setdefault((start, previous + 1), []).append(polygon)
                start = k
            previous = k
        spans.setdefault((start, previous + 1), []).append(polygon)
    require(sum((end - start) * len(polygons) for (start, end), polygons in spans.items()) ==
            int(np.count_nonzero(tree)), "tree span voxel count differs")
    footprint = unary_union(list(cells.values()))
    require(footprint.is_valid and not footprint.is_empty, "invalid canopy footprint union")
    records = []
    for (start, end), polygons in sorted(spans.items()):
        geometry = unary_union(polygons)
        require(geometry.is_valid and not geometry.is_empty, "invalid canopy span union")
        records.append({"k_start": start, "k_end": end, "cell_count": len(polygons),
                        "voxel_count": (end - start) * len(polygons),
                        "base_m": dem_min + start * mesh, "top_m": dem_min + end * mesh,
                        "height_m": (end - start) * mesh, "geometry": geometry})
    return footprint, records


def _write_layers(directory, identity, footprint, spans, adapter_path, tree_cells):
    import geopandas as gpd
    from shapely import force_3d
    document = runner.read_json(adapter_path)
    require(document.get("crs", {}).get("properties", {}).get("name") ==
            "urn:ogc:def:crs:EPSG::4326", "Adapter GeoJSON CRS differs")
    from shapely.geometry import shape
    buildings = [{"ouem_id": feature["properties"]["ouem_id"],
                  "height_m": float(feature["properties"]["height"]),
                  "geometry": provenance.reproject_xy(shape(feature["geometry"]), 4326, 6677)}
                 for feature in document["features"]]
    require(len(buildings) == len({item["ouem_id"] for item in buildings}) and
            all(b["geometry"].is_valid and b["geometry"].area > 0 for b in buildings),
            "Adapter building footprint is invalid or IDs repeat")
    path = directory / "canopy-qgis.gpkg"
    spans_3d = [{**row, "geometry": force_3d(row["geometry"], z=row["base_m"])}
                for row in spans]
    layers = (("canopy_occupancy", [{"tree_cells": tree_cells,
                                       "geometry": footprint}]),
              ("canopy_3d_spans", spans_3d), ("adapter_buildings", buildings))
    content = {name: [{**{k: v for k, v in row.items() if k != "geometry"},
                       "geometry_wkb": row["geometry"].wkb_hex} for row in rows]
               for name, rows in layers}
    semantic_sha256 = runner.content_hash(content)
    for index, (name, rows) in enumerate(layers):
        _guard_output(directory.parent, directory, identity)
        require(not path.exists() if index == 0 else path.is_file(), "output GeoPackage was substituted")
        if index:
            stat = path.stat()
            require((stat.st_dev, stat.st_ino) == gpkg_identity,
                    "output GeoPackage identity changed")
        frame = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:6677")
        frame.to_file(path, layer=name, driver="GPKG", mode="w" if index == 0 else "a")
        stat = path.stat()
        if index == 0:
            gpkg_identity = (stat.st_dev, stat.st_ino)
        require((stat.st_dev, stat.st_ino) == gpkg_identity,
                "output GeoPackage identity changed during layer write")
        saved = gpd.read_file(path, layer=name)
        require(saved.crs is not None and saved.crs.to_epsg() == 6677 and len(saved) == len(rows) and
                all(a.geometry.equals(b["geometry"]) for a, b in zip(saved.itertuples(), rows)),
                f"{name}: GeoPackage geometry/CRS readback mismatch")
    return path, {name: len(rows) for name, rows in layers}, semantic_sha256


def export_run(root, output_base):
    root = Path(root).absolute()
    evidence = provenance.Evidence(root)
    report = evidence.report
    pinned_engine = runner.voxcity_provenance()
    require(pinned_engine["verified"],
            "installed VoxCity 1.7.0 pinned source cannot be verified: " +
            pinned_engine.get("reason", "unknown reason"))
    require(report.get("status") == "AUTOMATED_PASS" and report.get("quality") ==
            report.get("reproducibility") == "PASS" and
            report.get("acceptance") == "PENDING_LOCAL_REVIEW" and
            len(report.get("repeats", [])) == 2 and all(report.get("comparisons", {}).values()),
            "integration report is not an automated PASS pending local review")
    repeats = [_one_repeat(evidence, n) for n in (1, 2)]
    checks = [_compare_scenarios(one) for one in repeats]
    require(repeats[0]["rectangle"] == repeats[1]["rectangle"] and
            repeats[0]["mesh"] == repeats[1]["mesh"] and
            np.array_equal(repeats[0]["current"], repeats[1]["current"]) and
            np.array_equal(repeats[0]["bare"], repeats[1]["bare"]) and
            repeats[0]["canopy"]["alignment"] == repeats[1]["canopy"]["alignment"],
            "saved repeats differ in grid, voxels or CHM alignment")
    grid = _grid(repeats[0])
    dem = _dem_grid(repeats[0])
    dem_min, checked_ground_cells = _check_vertical_datum(repeats[0], dem)
    require(_array_digest(dem) == _array_digest(_dem_grid(repeats[1])),
            "saved repeat DEM grids differ")
    require(_check_vertical_datum(repeats[1], dem)[0] == dem_min,
            "saved repeat vertical datums differ")
    footprint, spans = _features(checks[0]["tree_mask"], grid, dem_min, repeats[0]["mesh"])
    evidence.finish()
    directory, identity = _new_directory(output_base, root, root.name)
    gpkg, layer_counts, content_sha256 = _write_layers(directory, identity, footprint, spans,
                                                       repeats[0]["adapter"], checks[0]["tree_cells"])
    evidence.finish()
    result = {"schema": "ouem-komae-canopy-qgis-export/v0.1", "source_run": str(root),
              "status": "EXPORT_PASS", "acceptance": "PENDING_LOCAL_REVIEW",
              "crs": "EPSG:6677", "grid_orientation": "pinned VoxCity uv_m, axis 0 first rectangle edge; axis 1 second edge",
              "voxel_z": "base_m = DEM minimum + k_start*meshsize; top_m = DEM minimum + k_end*meshsize; voxel faces, not CHM heights",
              "dem_min_m": dem_min, "meshsize_m": repeats[0]["mesh"],
              "ground_cells_checked": checked_ground_cells,
              "grid_shape": list(repeats[0]["current"].shape[:2]),
              "checks": {k: v for k, v in checks[0].items() if k != "tree_mask"},
              "repeat_arrays_equal": True, "layers": layer_counts,
              "voxcity": pinned_engine,
              "source_file_sha256": {str(Path(path).relative_to(root)): info["sha256"]
                                     for path, info in sorted(evidence.before.items())},
              "source_integrity": evidence.finish(),
              "output": {"path": str(gpkg), "sha256": runner.sha256_file(gpkg),
                         "semantic_sha256": content_sha256}}
    output = directory / "export-report.json"
    _guard_output(directory.parent, directory, identity)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    evidence.finish()
    return result, output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="existing portable integration run ID")
    args = parser.parse_args(argv)
    if not RUN_ID.fullmatch(args.run_id) or args.run_id.upper() in WINDOWS_RESERVED:
        parser.error("run ID must be 1–64 ASCII letters, digits, underscores or hyphens")
    root = runner.REPOSITORY / "data/work/integration" / args.run_id
    try:
        result, report = export_run(root, runner.REPOSITORY / "data/work/canopy-qgis")
    except (OSError, ValueError, KeyError, runner.Blocked) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"EXPORT_PASS: {result['output']['path']}")
    print(f"Report: {report}")
    print(f"Tree cells: {result['checks']['tree_cells']}; tree voxels: {result['checks']['tree_voxels']}")
    print("Formal acceptance: PENDING_LOCAL_REVIEW; inspect in QGIS before a separate review record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
