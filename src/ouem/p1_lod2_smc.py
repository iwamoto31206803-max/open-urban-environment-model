"""P1-1b: fixed S/M/C LoD2 triangulation and traced, bounded mesh repair.

Run only in the existing isolated P1 environment. No voxelization, terrain,
downloads or dependency installation. The F runner is imported, never changed.
"""
from collections import Counter
from copy import deepcopy
import importlib.metadata as metadata
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

from ouem import p1_lod2_f as f

IDENTITIES = {
    "S": "bldg_040379e5-dffb-40b6-a392-6396158211f5",
    "M": "bldg_2bd71700-a145-46ff-b14f-ad60394ff253",
    "C": "bldg_2d5a9713-b02f-4903-9164-c5653e03494d",
}
REPO = Path(__file__).resolve().parents[2]
RECORDS = REPO / "docs/experiments/voxcitygml_p1"


def environment_inventory(prefix):
    """Package/config identities, not a claim of full environment byte identity."""
    site = Path(prefix) / "Lib/site-packages"
    packages = {}
    for dist in metadata.distributions(path=[str(site)]):
        import hashlib
        packages[dist.metadata["Name"]] = {
            "version": dist.version,
            "metadata_sha256": hashlib.sha256((dist.read_text("METADATA") or "").encode()).hexdigest(),
        }
    return {"packages": packages, "config_sha256": f.sha(Path(prefix) / "pyvenv.cfg")}


def select_building(member, source_id):
    selected = []
    for _, elem in ET.iterparse(member, events=("end",)):
        if elem.tag == "{" + f.NS["bldg"] + "}Building":
            if elem.get("{" + f.NS["gml"] + "}id") == source_id:
                selected.append(deepcopy(elem))
            elem.clear()
    f.require(len(selected) == 1, "requested Building ID absent or duplicated")
    root = ET.Element("CityModel")
    root.append(selected[0])
    return root, selected[0]


def read_faces(building, sample, archived):
    faces = []
    for bounded in building.findall("bldg:boundedBy", f.NS):
        f.require(len(bounded) == 1, "ambiguous boundedBy")
        surface = bounded[0]
        kind = surface.tag.split("}")[-1]
        f.require(kind in sample["semantic_counts"], "unrecognized surface semantics")
        lod = surface.find("bldg:lod2MultiSurface", f.NS)
        f.require(lod is not None, "explicit LoD2 required; no fallback")
        for polygon in lod.findall(".//gml:Polygon", f.NS):
            rings = []
            for name in ("exterior", "interior"):
                for node in polygon.findall("gml:" + name, f.NS):
                    pos = node.find(".//gml:posList", f.NS)
                    f.require(pos is not None and pos.text, "posList required")
                    values = np.array([float(x) for x in pos.text.split()])
                    f.require(values.size % 3 == 0, "invalid XYZ length")
                    xyz = values.reshape(-1, 3)
                    f.require(len(xyz) >= 4 and np.isfinite(xyz).all(), "invalid/nonfinite ring")
                    f.require(np.array_equal(xyz[0], xyz[-1]), "unclosed ring")
                    rings.append(xyz)
            f.require(len(polygon.findall("gml:exterior", f.NS)) == 1, "one exterior required")
            faces.append({"polygon_id": polygon.get("{" + f.NS["gml"] + "}id"),
                          "semantic": kind, "rings": rings, "element": polygon})
    counts = Counter(face["semantic"] for face in faces)
    f.require(dict(counts) == sample["semantic_counts"], "semantic face counts differ")
    ids = [face["polygon_id"] for face in faces]
    f.require(all(ids) and len(set(ids)) == len(ids), "missing/duplicate polygon ID")
    f.require(set(ids) == {face["polygon_id"] for face in archived["faces"]}, "polygon ID mismatch")
    f.require(all(face["mapping"] == "VERIFIED" for face in archived["faces"]), "nonunique archived mapping")
    return faces


def triangle_support(rings, vertices, triangles):
    """Independent planar-projection coverage test; never generate expected triangles.

    Drop the dominant exterior normal axis, with a local coordinate origin.
    The area error budget is an IEEE arithmetic bound fixed before real runs:
    256 * eps64 * max(1, extent^2) * (ring vertices + triangle count).
    This is a numerical coverage check, not a physical geometry tolerance.
    """
    expected = np.vstack([ring[:-1] for ring in rings])
    f.require(np.array_equal(expected, vertices), "triangulation changes source XYZ/H or rings")
    f.require(triangles.ndim == 2 and triangles.shape[1] == 3 and len(triangles) > 0,
              "missing triangles")
    f.require(np.issubdtype(triangles.dtype, np.integer) and triangles.min() >= 0
              and triangles.max() < len(vertices), "invalid triangle indices")
    metric = f.project(vertices)
    projected_rings = [f.project(ring) for ring in rings]
    exterior = projected_rings[0][:-1] - projected_rings[0][0]
    normal = np.cross(exterior, np.roll(exterior, -1, axis=0)).sum(axis=0)
    f.require(np.linalg.norm(normal) > 0, "degenerate face normal")
    drop = int(np.argmax(np.abs(normal)))
    axes = [axis for axis in range(3) if axis != drop]
    origin = metric[0, axes]
    xy = metric[:, axes] - origin
    projected = [ring[:, axes] - origin for ring in projected_rings]
    polygon = Polygon(projected[0], projected[1:])
    f.require(polygon.is_valid and polygon.area > 0, "invalid source projected polygon; no repair")
    cells = [Polygon(xy[tri]) for tri in triangles]
    f.require(all(cell.is_valid and cell.area > 0 for cell in cells), "degenerate triangle")
    union = unary_union(cells)
    budget = float(256 * np.finfo(float).eps * max(1., np.ptp(xy, axis=0).max() ** 2)
                   * (len(vertices) + len(triangles)))
    uncovered = float(polygon.difference(union).area)
    outside = float(union.difference(polygon).area)
    overlap = float(max(0., sum(cell.area for cell in cells) - union.area))
    metrics = {"dropped_axis": drop, "source_projected_area_m2": float(polygon.area),
               "uncovered_m2": uncovered, "outside_m2": outside, "overlap_m2": overlap,
               "numerical_area_budget_m2": budget, "holes": len(rings) - 1}
    f.require(max(uncovered, outside, overlap) <= budget,
              "triangle support lost/added/overlapped (including holes): " + json.dumps(metrics))
    return metrics


def triangle_keys(vertices, triangles, precision=6):
    values = vertices if precision is None else np.round(vertices, precision)
    return Counter(tuple(sorted(tuple(values[index]) for index in tri))
                   for tri in triangles)


def shape_delta(before, faces, after, newfaces):
    old = triangle_keys(before, faces)
    new = triangle_keys(after, newfaces)
    distances = []
    for start in range(0, len(after), 128):
        distance = np.max(np.abs(after[start:start + 128, None] - before[None]), axis=2)
        distances.extend(distance.min(axis=1).tolist())
    old_z, new_z = np.unique(before[:, 2]), np.unique(after[:, 2])
    return {"triangles_removed_at_merge_precision": sum((old - new).values()),
            "triangles_added_at_merge_precision": sum((new - old).values()),
            "max_nearest_vertex_coordinate_delta_m": max(distances, default=None),
            "new_H_values": np.setdiff1d(new_z, old_z).tolist(),
            "lost_H_values": np.setdiff1d(old_z, new_z).tolist()}


def topology(vertices, triangles):
    stats = f.mesh_stats(vertices, triangles)
    edges = Counter(tuple(sorted((int(tri[i]), int(tri[(i + 1) % 3]))))
                    for tri in triangles for i in range(3))
    stats.update(boundary_edges=sum(n == 1 for n in edges.values()),
                 nonmanifold_edges=sum(n > 2 for n in edges.values()))
    return stats


def traced_watertight(engine, vertices, triangles, method):
    """Observe pinned operations without allowing an automatic repair cascade."""
    f.require(method in ("merge", "repair"), "voxel marching/hull outside scope")
    trace = []
    originals = {name: getattr(engine, name) for name in
                 ("_merge_vertices", "_trimesh_repair", "_validate_watertight")}
    def observe(name):
        def wrapped(v, t, *args, **kwargs):
            before = topology(v, t)
            result = originals[name](v, t, *args, **kwargs)
            out_v, out_t = result[1:] if name == "_validate_watertight" else result
            trace.append({"operation": name, "before": before,
                          "after": topology(out_v, out_t),
                          "vertices_array_changed": not np.array_equal(v, out_v),
                          "faces_array_changed": not np.array_equal(t, out_t)})
            return result
        return wrapped
    try:
        for name in originals:
            setattr(engine, name, observe(name))
        result = engine.make_watertight_mesh(vertices.copy(), triangles.copy(), method=method, precision=6)
    finally:
        for name, original in originals.items():
            setattr(engine, name, original)
    return result, trace


def diagnose(member, standard, archived, sample, output):
    """Independent per-building stop boundary; record failures without continuing it."""
    from voxcitygml.citygml import geometry, extractors
    from voxcitygml import watertight

    output.mkdir(exist_ok=False)
    result = {"label": sample["label"], "source_id": sample["source_id"],
              "ouem_id": sample["ouem_id"], "stages": {}, "faces": [],
              "voxelization": "NOT_EXECUTED_BY_SCOPE", "voxel_ready": "BLOCKED"}
    stage = "SOURCE_IDENTITY"
    try:
        root, building = select_building(member, sample["source_id"])
        records = read_faces(building, sample, archived)
        result["source_counts"] = {
            "semantic_faces": dict(Counter(record["semantic"] for record in records)),
            "polygons": len(records),
            "rings": sum(len(record["rings"]) for record in records),
            "holes": sum(len(record["rings"]) - 1 for record in records),
            "vertices_excluding_closure_with_face_duplicates": sum(
                len(ring) - 1 for record in records for ring in record["rings"]),
        }
        with sqlite3.connect(standard.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            rows = db.execute("SELECT ouem_id,source_lod,geometry FROM building WHERE source_id=?",
                              (sample["source_id"],)).fetchall()
        f.require(len(rows) == 1 and rows[0][:2] == (sample["ouem_id"], 2), "Standard ID/LoD mismatch")
        import hashlib
        f.require(hashlib.sha256(rows[0][2]).hexdigest() == sample["standard_rows"][0]["geometry_blob_sha256"],
                  "Standard geometry BLOB SHA mismatch")
        target_faces = f.polygons(f.decode(rows[0][2]))
        mapping = {face["polygon_id"]: face["standard_face_index"] for face in archived["faces"]}
        result["stages"][stage] = "PASS"
        stage = "TRIANGULATION"
        vertices, triangles, offset = [], [], 0
        for record in records:
            rings = record["rings"]
            entry = {"polygon_id": record["polygon_id"], "semantic": record["semantic"],
                     "ring_vertex_counts_including_closure": [len(ring) for ring in rings],
                     "ring_XYZ_sha256": [f.array_sha(ring) for ring in rings],
                     "holes": len(rings) - 1}
            result["faces"].append(entry)
            targets = target_faces[mapping[record["polygon_id"]]]
            f.require(len(targets) == len(rings), "Standard loses/adds a ring")
            entry["standard_alignment"] = [f.align_ring(f.project(ring), np.array(target))
                                           for ring, target in zip(rings, targets)]
            v, t = geometry.parse_polygon_to_triangles(record["element"], f.NS)
            entry["triangles"] = len(t)
            entry["coverage"] = triangle_support(rings, v, t)
            entry["status"] = "PASS"
            vertices.append(f.project(v))
            triangles.append(t + offset)
            offset += len(v)
        v, t = np.vstack(vertices), np.vstack(triangles).astype(np.int32)
        meshes = extractors.extract_buildings_from_root(root, f.NS, prefer_lod=2, max_lod=2)
        f.require(len(meshes) == 1 and meshes[0].feature_id == sample["source_id"]
                  and meshes[0].attributes["lod"] == 2, "foreign ID/LoD fallback")
        f.require(triangle_keys(f.project(meshes[0].vertices), meshes[0].faces, precision=None)
                  == triangle_keys(v, t, precision=None),
                  "whole-building extraction loses/changes triangles")
        result["stages"][stage] = "PASS"
        result["triangulated"] = topology(v, t)
        np.save(output / "triangulated_vertices.npy", v, allow_pickle=False)
        np.save(output / "triangulated_faces.npy", t, allow_pickle=False)
        before = (f.array_sha(v), f.array_sha(t))
        stage = "MERGE"
        merged, trace = traced_watertight(watertight, v, t, method="merge")
        result["merge"] = {"method": merged.method, "accepted_by_engine": bool(merged.is_watertight),
                           "error": merged.error, "stats": topology(merged.vertices, merged.faces),
                           "delta": shape_delta(v, t, merged.vertices, merged.faces), "trace": trace}
        np.save(output / "merge_vertices.npy", merged.vertices, allow_pickle=False)
        np.save(output / "merge_faces.npy", merged.faces, allow_pickle=False)
        # Preserve the F bound and correspondence test; never calibrate on S/M/C.
        result["merge"]["correspondence"] = f.repair_correspondence(v, t, merged.vertices, merged.faces)
        f.require(before == (f.array_sha(v), f.array_sha(t)), "triangulated input mutated")
        if merged.is_watertight:
            result["stages"][stage] = "PASS"
            result["voxel_ready"] = "CONDITIONAL_REVIEW_REQUIRED"
        else:
            result["stages"][stage] = "NOT_WATERTIGHT"
            stage = "REPAIR_DIAGNOSIS"
            # Explicit next stage only: never auto-escalate to voxel marching or hull.
            repaired, repair_trace = traced_watertight(watertight, merged.vertices, merged.faces, method="repair")
            result["repair_diagnosis"] = {
                "method": repaired.method, "accepted_by_engine": bool(repaired.is_watertight),
                "error": repaired.error, "stats": topology(repaired.vertices, repaired.faces),
                "delta_from_merge": shape_delta(merged.vertices, merged.faces, repaired.vertices, repaired.faces),
                "adopted": False,
                "trace": repair_trace,
                "next_stage": "STOP: voxel marching/hull not authorized in P1-1b",
            }
            np.save(output / "repair_diagnostic_vertices.npy", repaired.vertices, allow_pickle=False)
            np.save(output / "repair_diagnostic_faces.npy", repaired.faces, allow_pickle=False)
            result["stages"][stage] = "DIAGNOSTIC_ONLY_NOT_ACCEPTED"
        result["status"] = "PASS_MERGE_ONLY" if merged.is_watertight else "BLOCKED_REPAIR_REVIEW"
        result["source_H_preserved_through_triangulation"] = True
    except Exception as exc:
        result["stages"][stage] = "BLOCKED"
        result["status"] = "BLOCKED"
        result["error"] = f"{type(exc).__name__}: {exc}"
    f.write(output / "geometry_diagnostics.json", result)
    return result


def run(member, standard, audit_report, output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"profile": "ouem-p1-1b-fixed-smc/v0.1", "status": "BLOCKED",
                "scientific_validation": "NOT_VERIFIED", "formal_acceptance": "NOT_VERIFIED",
                "terrain_integration_ready": False, "voxelization": "NOT_EXECUTED_BY_SCOPE"}
    try:
        f.require(Path(sys.prefix).name == "ouem-voxcitygml-p1" and sys.prefix != sys.base_prefix,
                  "isolated P1 venv required")
        inputs = [member, standard, audit_report]
        pins = json.loads((RECORDS / "p1-1a/manifest.json").read_bytes())["inputs"]
        f.require(all(f.sha(path) == pins[path.name] for path in inputs), "input SHA mismatch")
        evidence = [RECORDS / "evidence/source_identity.json", RECORDS / "evidence/static_compatibility.json",
                    RECORDS / "p1-1a/manifest.json", REPO / "src/ouem/p1_lod2_f.py"]
        all_inputs = {str(path): f.sha(path) for path in inputs + evidence}
        before_env = {"OUEM": environment_inventory(REPO / ".venv"),
                      "P1": environment_inventory(sys.prefix)}
        def verify_preservation():
            f.require(all(f.sha(Path(path)) == digest for path, digest in all_inputs.items()), "input/F runner changed")
            f.require(before_env == {"OUEM": environment_inventory(REPO / ".venv"),
                                     "P1": environment_inventory(sys.prefix)}, "environment inventory changed")
            f.require(not events, "forbidden network/protected-write attempt")
        events = f.guard(output, [member.resolve().parent, standard.resolve().parent,
                                  audit_report.resolve().parent, REPO / ".venv", Path(sys.prefix)])
        import voxcitygml
        from voxcitygml import watertight
        from ouem.komae_integration import voxcity_provenance
        f.require(not watertight._MESHLIB_AVAILABLE and not any(
            dist.metadata["Name"].lower() == "meshlib" for dist in metadata.distributions()), "MeshLib present")
        f.require(metadata.version("voxcitygml") == "0.3.0", "VoxCityGML version mismatch")
        expected = json.loads(evidence[1].read_bytes())["voxcitygml"]
        f.require(expected["commit"] == f.GML_COMMIT, "VoxCityGML commit mismatch")
        root = Path(voxcitygml.__file__).resolve().parent.parent
        f.require(all(f.sha(root / name) == digest for name, digest in expected["source_sha256"].items()),
                  "VoxCityGML source mismatch")
        provenance = voxcity_provenance()
        f.require(provenance["verified"], "VoxCity provenance mismatch")
        manifest["environment"] = {"python": sys.version.split()[0], "voxcitygml_commit": f.GML_COMMIT,
                                    "voxcity": provenance, "meshlib": False,
                                    "voxcitygml_source_files_matched": len(expected["source_sha256"]),
                                    "packages": {name: metadata.version(name) for name in
                                                 ("voxcitygml", "voxcity", "numpy", "trimesh", "pyproj", "shapely", "mapbox-earcut")}}
        samples = json.loads(evidence[0].read_bytes())["samples"]
        audit = json.loads(audit_report.read_bytes())
        results = {}
        for label, source_id in IDENTITIES.items():
            sample = next(s for s in samples if s["label"] == label)
            f.require(sample["source_id"] == source_id, "P1-0 sample ID mismatch")
            archived = next(b for b in audit["buildings"] if b["source_id"] == source_id)
            f.require(sample["ouem_id"] == archived["ouem_id"], "archived ouem_id mismatch")
            results[label] = diagnose(member, standard, archived, sample, output / label)
            # A geometry failure stops that independent building; shared input,
            # environment or side-effect failures stop the whole run immediately.
            verify_preservation()
        manifest.update(status="PASS_MERGE_ONLY" if all(r["status"] == "PASS_MERGE_ONLY" for r in results.values())
                        else "BLOCKED_ONE_OR_MORE_BUILDINGS",
                        buildings={label: {"status": r["status"], "voxel_ready": r["voxel_ready"]}
                                   for label, r in results.items()},
                        inputs={Path(path).name: digest for path, digest in all_inputs.items()},
                        environment_inventory_unchanged=True, input_SHA_unchanged=True,
                        forbidden_attempts=events)
    except Exception as exc:
        manifest["error"] = f"{type(exc).__name__}: {exc}"
    manifest["implementation_sha256"] = f.sha(__file__)
    manifest["outputs"] = {str(path.relative_to(output)).replace("\\", "/"): f.sha(path)
                           for path in sorted(output.rglob("*")) if path.is_file() and "cache" not in path.parts}
    f.write(output / "manifest.json", manifest)
    return manifest


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("member", "standard", "audit-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.member, args.standard, args.audit_report, args.output)
    print(json.dumps({key: result.get(key) for key in ("status", "buildings", "error")}))
    return int(result["status"] != "PASS_MERGE_ONLY")


if __name__ == "__main__":
    raise SystemExit(main())
