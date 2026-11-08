"""P1-1c fixed four-building mesh-only voxelization and approximation diagnostics.

No terrain or environmental analysis. The solid-angle sampler is a diagnostic
oracle, not a replacement voxelizer or an exact solid/voxel intersection engine.
"""
from itertools import product
import importlib.metadata as metadata
import json
from pathlib import Path
import sqlite3
import sys
import time

import numpy as np

from ouem import p1_lod2_f as f
from ouem import p1_lod2_smc as b

CONDITIONS = {"1m": (1., 0.), "0.5m": (.5, 0.), "1m_shift_xyz": (1., .5)}
MAX_CELLS = 200_000  # Fixed diagnostic resource guard, not an accuracy gate.


def grid_spec(vertices, size, phase=0.):
    f.require(size in (.5, 1.) and phase in (0., .5), "unsupported limited experiment condition")
    lo = np.floor(vertices.min(axis=0)) - 1 + phase
    hi = np.ceil(vertices.max(axis=0)) + 1 + phase
    counts = np.rint((hi - lo) / size).astype(int)
    f.require(np.all(counts * size == hi - lo), "grid extent is not integral")
    f.require(np.all(lo < vertices.min(axis=0)) and np.all(hi > vertices.max(axis=0)), "mesh outside grid")
    shape = (int(counts[1]), int(counts[0]), int(counts[2]))
    f.require(np.prod(shape) <= MAX_CELLS, "diagnostic resource guard exceeded")
    return dict(n_rows=shape[0], n_cols=shape[1], n_z=shape[2],
                min_x=float(lo[0]), max_x=float(hi[0]), min_y=float(lo[1]), max_y=float(hi[1]),
                min_z=float(lo[2]), max_z=float(hi[2]), voxel_size=size)


def points_at(grid, cells, fractions):
    """row south, column east, Z up; fractions are local cell offsets."""
    size = grid["voxel_size"]
    return np.column_stack((grid["min_x"] + (cells[:, 1] + fractions[:, 0]) * size,
                            grid["max_y"] - (cells[:, 0] + fractions[:, 1]) * size,
                            grid["min_z"] + (cells[:, 2] + fractions[:, 2]) * size))


def solid_angle_classify(vertices, faces, points):
    """Independent oriented solid angle: 1=inside, 0=outside, -1=ambiguous.

    Explicit point-on-triangle detection avoids silently assigning boundary
    samples to either side. All tolerances below derive from float64 arithmetic,
    coordinate ULP and triangle conditioning, never observed real-data errors.
    """
    triangles = vertices[faces]
    u, v = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    normal = np.cross(u, v)
    nlen = np.linalg.norm(normal, axis=1)
    d00, d01, d11 = (np.einsum("ij,ij->i", x, y) for x, y in ((u, u), (u, v), (v, v)))
    denominator = d00 * d11 - d01 ** 2
    f.require(np.all(nlen > 0) and np.all(denominator > 0), "degenerate reference triangle")
    eps = np.finfo(float).eps
    plane_budget = max(8 * np.spacing(np.abs(vertices).max()),
                       1024 * eps * max(1., np.linalg.norm(np.ptp(vertices, axis=0))))
    bary_budget = 256 * eps * np.maximum(1., d00 * d11 / denominator)
    integer_budget = 1024 * eps * len(faces)
    result = np.full(len(points), -1, dtype=np.int8)
    for start in range(0, len(points), 512):
        p = points[start:start + 512]
        a = triangles[None, :, 0] - p[:, None]
        c = triangles[None, :, 2] - p[:, None]
        bb = triangles[None, :, 1] - p[:, None]
        la, lb, lc = (np.linalg.norm(x, axis=2) for x in (a, bb, c))
        numerator = np.einsum("ijk,ijk->ij", a, np.cross(bb, c))
        divisor = (la * lb * lc + np.einsum("ijk,ijk->ij", a, bb) * lc
                   + np.einsum("ijk,ijk->ij", bb, c) * la
                   + np.einsum("ijk,ijk->ij", c, a) * lb)
        winding = np.abs((2 * np.arctan2(numerator, divisor)).sum(axis=1) / (4 * np.pi))
        d20 = -np.einsum("ijk,jk->ij", a, u)
        d21 = -np.einsum("ijk,jk->ij", a, v)
        s = (d11 * d20 - d01 * d21) / denominator
        t = (d00 * d21 - d01 * d20) / denominator
        on_plane = np.abs(np.einsum("ijk,jk->ij", a, normal)) / nlen <= plane_budget
        boundary = (on_plane & (s >= -bary_budget) & (t >= -bary_budget)
                    & (s + t <= 1 + bary_budget)).any(axis=1)
        valid = ~boundary & np.isfinite(winding)
        part = result[start:start + len(p)]
        part[valid & (winding <= integer_budget)] = 0
        part[valid & (np.abs(winding - 1) <= integer_budget)] = 1
    return result


def sample_overlap(vertices, faces, grid, occupied, subdivisions):
    """Full-domain stratified midpoint quadrature, with explicit ambiguity bounds.

    Bounds cover ambiguous sample labels only, NOT unsampled geometry or the
    quadrature error. These are reference estimates, never exact ground truth.
    """
    f.require(subdivisions in (2, 3), "unsupported diagnostic sample density")
    n = subdivisions ** 3
    offsets = np.array(list(product((np.arange(subdivisions) + .5) / subdivisions, repeat=3)))
    cells = np.indices(occupied.shape).reshape(3, -1).T
    counts = dict(tp=0, fp=0, fn=0, tn=0, ambiguous_occupied=0, ambiguous_empty=0)
    categories = dict(occupied_all_samples_inside=0, occupied_mixed_samples=0,
                      occupied_no_inside_samples=0, occupied_with_ambiguous_samples=0)
    for start in range(0, len(cells), 128):
        part = cells[start:start + 128]
        pts = points_at(grid, np.repeat(part, n, axis=0), np.tile(offsets, (len(part), 1)))
        labels = solid_angle_classify(vertices, faces, pts).reshape(-1, n)
        occ = occupied[tuple(part.T)]
        inside, outside, ambiguous = ((labels == k).sum(axis=1) for k in (1, 0, -1))
        for key, mask, values in (("tp", occ, inside), ("fp", occ, outside),
                                  ("fn", ~occ, inside), ("tn", ~occ, outside),
                                  ("ambiguous_occupied", occ, ambiguous), ("ambiguous_empty", ~occ, ambiguous)):
            counts[key] += int(values[mask].sum())
        categories["occupied_all_samples_inside"] += int((occ & (inside == n)).sum())
        categories["occupied_mixed_samples"] += int((occ & (inside > 0) & (outside > 0)).sum())
        categories["occupied_no_inside_samples"] += int((occ & (inside == 0)).sum())
        categories["occupied_with_ambiguous_samples"] += int((occ & (ambiguous > 0)).sum())
    unit = grid["voxel_size"] ** 3 / n
    tp, fp, fn = (counts[k] * unit for k in ("tp", "fp", "fn"))
    ao, ae = (counts[k] * unit for k in ("ambiguous_occupied", "ambiguous_empty"))
    vv = int(occupied.sum()) * grid["voxel_size"] ** 3
    return dict(method="independent oriented solid-angle; full-domain subcell midpoints",
                subdivisions_per_axis=subdivisions, sample_count=len(cells) * n,
                sample_counts=counts, cell_categories=categories,
                sampled_solid_volume_m3=[tp + fn, tp + fn + ao + ae],
                intersection_m3=[tp, tp + ao], excess_m3=[fp, fp + ao], missed_m3=[fn, fn + ae],
                sampled_IoU=[tp / (vv + fn + ae), (tp + ao) / (vv + fn)],
                limitation="intervals cover ambiguous samples only; no bound on quadrature error")


def traced_voxelize(engine, raw_v, raw_t, merged_v, merged_t, grid):
    """Pinned private API; observe interior and contact shell separately."""
    gp = engine.Grid3DParams(**grid)
    shape = (gp.n_rows, gp.n_cols, gp.n_z)
    voxels = np.zeros(shape, dtype=np.int8)
    masks = {name: np.zeros(shape, dtype=bool) for name in ("interior", "shell")}
    trace = []
    names = ("make_watertight_mesh", "_voxelize_by_occupancy", "_voxelize_single_mesh",
             "_z_scanline_fill", "_surface_voxelize_numba")
    original = {name: getattr(engine, name) for name in names}
    def repair(*args, **kwargs):
        kwargs["method"] = "merge"  # Prevent escalation before it can alter shape.
        wt = original["make_watertight_mesh"](*args, **kwargs)
        f.require(wt.method == "merge" and wt.is_watertight, "unexpected repair or open solid")
        f.require(np.array_equal(wt.vertices, merged_v) and np.array_equal(wt.faces, merged_t),
                  "voxel repair differs from SHA-bound archived merge")
        trace.append("repair:merge")
        return wt
    def occupancy(*args, **kwargs):
        ok = original["_voxelize_by_occupancy"](*args, **kwargs)
        trace.append("occupancy:" + str(ok))
        f.require(ok, "occupancy failed; fallback prohibited")
        return ok
    def forbidden(*args, **kwargs):
        raise ValueError("sealed-surface fallback prohibited")
    def capture(name, key):
        def wrapped(*args, **kwargs):
            f.require(b.triangle_keys(args[0], args[1], None) == b.triangle_keys(merged_v, merged_t, None),
                      "internal mesh triangle geometry changed")
            out = original[name](*args, **kwargs)
            r, c, z = args[6:9] if key == "interior" else (args[6], args[8], args[10])
            masks[key][r:r + out.shape[0], c:c + out.shape[1], z:z + out.shape[2]] = out
            return out
        return wrapped
    arrays_before = [f.array_sha(x) for x in (raw_v, raw_t, merged_v, merged_t)]
    try:
        engine.make_watertight_mesh = repair
        engine._voxelize_by_occupancy = occupancy
        engine._voxelize_single_mesh = forbidden
        engine._z_scanline_fill = capture("_z_scanline_fill", "interior")
        engine._surface_voxelize_numba = capture("_surface_voxelize_numba", "shell")
        engine._voxelize_building_solid(raw_v, raw_t, gp, voxels, -3, True)
    finally:
        for name, value in original.items():
            setattr(engine, name, value)
    f.require(arrays_before == [f.array_sha(x) for x in (raw_v, raw_t, merged_v, merged_t)], "mesh input mutated")
    f.require(trace == ["repair:merge", "occupancy:True"], "unexpected voxelization trace")
    f.require((voxels == -3).any() and np.isin(voxels, [0, -3]).all(), "empty/invalid classes")
    f.require(np.array_equal(voxels == -3, masks["interior"] | masks["shell"]), "interior/shell union differs")
    return voxels, masks, trace


def verify_mesh(label, member, standard, audit, archive_a, archive_b, input_shas):
    """Recheck exact source/Standard/rings/triangles, then load SHA-bound old mesh."""
    from voxcitygml.citygml import geometry, extractors
    import hashlib
    samples = json.loads((b.RECORDS / "evidence/source_identity.json").read_bytes())["samples"]
    sample = next(s for s in samples if s["label"] == label)
    expected_id = f.SOURCE_ID if label == "F" else b.IDENTITIES[label]
    f.require(sample["source_id"] == expected_id, "sample ID differs")
    old = next(x for x in audit["buildings"] if x["source_id"] == expected_id)
    f.require(old["ouem_id"] == sample["ouem_id"], "ouem_id mismatch")
    root, building = b.select_building(member, expected_id)
    records = b.read_faces(building, sample, old)
    with sqlite3.connect(standard.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        rows = db.execute("SELECT ouem_id,source_lod,geometry FROM building WHERE source_id=?", (expected_id,)).fetchall()
    f.require(len(rows) == 1 and rows[0][:2] == (sample["ouem_id"], 2), "Standard ID/LoD mismatch")
    f.require(hashlib.sha256(rows[0][2]).hexdigest() == sample["standard_rows"][0]["geometry_blob_sha256"], "Standard BLOB mismatch")
    targets = f.polygons(f.decode(rows[0][2]))
    mapping = {face["polygon_id"]: face["standard_face_index"] for face in old["faces"]}
    vertices, triangles, offset = [], [], 0
    for rec in records:
        target = targets[mapping[rec["polygon_id"]]]
        f.require(len(target) == len(rec["rings"]), "ring count differs")
        for ring, match in zip(rec["rings"], target):
            f.align_ring(f.project(ring), np.array(match))
        v, t = geometry.parse_polygon_to_triangles(rec["element"], f.NS)
        b.triangle_support(rec["rings"], v, t)
        vertices.append(f.project(v)); triangles.append(t + offset); offset += len(v)
    raw_v, raw_t = np.vstack(vertices), np.vstack(triangles).astype(np.int32)
    mesh = extractors.extract_buildings_from_root(root, f.NS, prefer_lod=2, max_lod=2)
    f.require(len(mesh) == 1 and mesh[0].feature_id == expected_id and mesh[0].attributes["lod"] == 2, "ID/LoD fallback")
    f.require(b.triangle_keys(f.project(mesh[0].vertices), mesh[0].faces, None) == b.triangle_keys(raw_v, raw_t, None), "whole-mesh triangles differ")
    public = json.loads((b.RECORDS / ("p1-1a" if label == "F" else "p1-1b") / "manifest.json").read_bytes())
    archive = archive_a if label == "F" else archive_b
    f.require(f.sha(archive / "manifest.json") == public["local_manifest_sha256"], "archived manifest SHA mismatch")
    prefix = "" if label == "F" else label + "/"
    merge_name = "repaired" if label == "F" else "merge"
    needed = ["geometry_diagnostics.json", "triangulated_vertices.npy", "triangulated_faces.npy",
              merge_name + "_vertices.npy", merge_name + "_faces.npy"]
    for name in needed + (["voxels.npy"] if label == "F" else []):
        path = archive / (prefix + name)
        digest = public["archived_local_outputs"][prefix + name]
        f.require(f.sha(path) == digest, "archived geometry/output SHA mismatch")
        input_shas[str(path)] = digest
    input_shas[str(archive / "manifest.json")] = public["local_manifest_sha256"]
    folder = archive / label if label != "F" else archive
    f.require(np.array_equal(raw_v, np.load(folder / "triangulated_vertices.npy", allow_pickle=False))
              and np.array_equal(raw_t, np.load(folder / "triangulated_faces.npy", allow_pickle=False)), "reconstructed source differs from archived triangles")
    merged_v = np.load(folder / (merge_name + "_vertices.npy"), allow_pickle=False)
    merged_t = np.load(folder / (merge_name + "_faces.npy"), allow_pickle=False)
    f.repair_correspondence(raw_v, raw_t, merged_v, merged_t)
    stats = b.topology(merged_v, merged_t)
    f.require(stats["is_volume"] and stats["signed_volume_m3"] > 0, "not a positive watertight reference solid")
    return raw_v, raw_t, merged_v, merged_t, dict(source_id=expected_id, ouem_id=sample["ouem_id"],
        semantic_counts=sample["semantic_counts"], polygon_ids=[r["polygon_id"] for r in records], reference=stats)


def evaluate_case(engine, arrays, grid, output, densities):
    start = time.perf_counter()
    cpu_start = time.process_time()
    voxels, masks, trace = traced_voxelize(engine, *arrays, grid)
    kernel_seconds = time.perf_counter() - start
    # One-cell AIR enlargement: same phase, centres and absolute H in the core.
    padded = dict(grid)
    h = grid["voxel_size"]
    for axis in "xyz":
        padded["min_" + axis] -= h; padded["max_" + axis] += h
    for key in ("n_rows", "n_cols", "n_z"):
        padded[key] += 2
    extended, _, _ = traced_voxelize(engine, *arrays, padded)
    core = extended[1:-1, 1:-1, 1:-1]
    outside = extended.copy(); outside[1:-1, 1:-1, 1:-1] = 0
    f.require(np.array_equal(core, voxels) and not outside.any(), "grid clips occupancy or changes core")
    output.mkdir(exist_ok=False)
    for name, array in {"voxels": voxels, **masks}.items():
        path = output / (name + ".npy")
        np.save(path, array, allow_pickle=False)
        f.require(np.array_equal(np.load(path, allow_pickle=False), array), "output readback differs")
    occupied = voxels == -3
    result = dict(grid=grid, shape=list(voxels.shape), axis_order="row south/col east/z up; metric EPSG:6677 XY + source absolute H",
                  occupied_cells=int(occupied.sum()), voxel_union_volume_m3=float(occupied.sum() * h ** 3),
                  interior_cells=int(masks["interior"].sum()), contact_shell_cells=int(masks["shell"].sum()),
                  shell_only_cells=int((masks["shell"] & ~masks["interior"]).sum()),
                  interior_shell_overlap=int((masks["shell"] & masks["interior"]).sum()),
                  trace=trace, one_cell_padding_check="PASS: core identical; extra occupancy=0",
                  voxel_array_sha256=f.array_sha(voxels), sample_estimates=[])
    for density in densities:
        result["sample_estimates"].append(sample_overlap(arrays[2], arrays[3], grid, occupied, density))
    return result, {"voxel_kernel_seconds": kernel_seconds, "case_total_seconds": time.perf_counter() - start,
                    "case_CPU_seconds": time.process_time() - cpu_start}


def run(member, standard, audit_report, archive_a, archive_b, output, comparisons=False):
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    manifest = dict(profile="ouem-p1-1c-fixed-fsmc/v0.1", status="BLOCKED",
                    scientific_validation="NOT_VERIFIED", formal_acceptance="NOT_VERIFIED", terrain_integration_ready=False)
    timings = {}
    try:
        f.require(Path(sys.prefix).name == "ouem-voxcitygml-p1" and sys.prefix != sys.base_prefix, "isolated P1 required")
        public_a = json.loads((b.RECORDS / "p1-1a/manifest.json").read_bytes())
        inputs = {str(path): f.sha(path) for path in (member, standard, audit_report)}
        f.require(all(digest == public_a["inputs"][Path(path).name] for path, digest in inputs.items()), "raw input SHA mismatch")
        for path in [b.RECORDS / "evidence/source_identity.json", b.RECORDS / "evidence/static_compatibility.json",
                     b.RECORDS / "p1-1a/manifest.json", b.RECORDS / "p1-1b/manifest.json",
                     b.REPO / "src/ouem/p1_lod2_f.py", b.REPO / "src/ouem/p1_lod2_smc.py"]:
            inputs[str(path)] = f.sha(path)
        before_env = {"OUEM": b.environment_inventory(b.REPO / ".venv"), "P1": b.environment_inventory(sys.prefix)}
        events = f.guard(output, [member.resolve().parent, standard.resolve().parent, audit_report.resolve().parent,
                                  archive_a.resolve(), archive_b.resolve(), b.REPO / ".venv", Path(sys.prefix)])
        import voxcitygml
        from voxcitygml import voxelizer3d, watertight
        from ouem.komae_integration import voxcity_provenance
        expected = json.loads((b.RECORDS / "evidence/static_compatibility.json").read_bytes())["voxcitygml"]
        root = Path(voxcitygml.__file__).resolve().parent.parent
        f.require(expected["commit"] == f.GML_COMMIT and all(f.sha(root / n) == h for n, h in expected["source_sha256"].items()), "GML source pin mismatch")
        f.require(not watertight._MESHLIB_AVAILABLE and not voxelizer3d._MESHLIB_VOXEL_AVAILABLE, "MeshLib prohibited")
        provenance = voxcity_provenance(); f.require(provenance["verified"], "VoxCity pin mismatch")
        manifest["environment"] = dict(python=sys.version.split()[0], voxcitygml_commit=f.GML_COMMIT, voxcity=provenance,
                                        meshlib=False, packages={n: metadata.version(n) for n in ("voxcitygml", "voxcity", "numpy", "numba", "trimesh")})
        manifest["settings"] = dict(cpu_numba_threads=2, conditions=list(CONDITIONS) if comparisons else ["1m"],
            occupancy_threshold=0., occupancy_subdivisions=3, forced_repair_method="merge",
            private_API="voxcitygml.voxelizer3d._voxelize_building_solid + _voxelize_by_occupancy + _z_scanline_fill + _surface_voxelize_numba",
            fill_definition="jittered XY parity rays; floor(lower Z)..floor(upper Z), inclusive; not whole-cell interior",
            shell_definition="triangle-box contact; half_extent=h/2+h*1e-6; union with scanline fill",
            sample_definition="independent solid-angle midpoint quadrature; ambiguity intervals exclude quadrature error")
        audit = json.loads(audit_report.read_bytes())
        results = {}
        def preserve():
            f.require(not events, "forbidden side-effect attempt")
            f.require(all(f.sha(Path(path)) == digest for path, digest in inputs.items()), "input/old artifact mutated")
            f.require(before_env == {"OUEM": b.environment_inventory(b.REPO / ".venv"), "P1": b.environment_inventory(sys.prefix)}, "environment metadata changed")
        import numba
        threads = numba.get_num_threads(); numba.set_num_threads(2)
        try:
            for label in "FSMC":
                folder = output / label; folder.mkdir()
                diagnostic = dict(label=label, status="BLOCKED", cases={})
                results[label] = diagnostic
                try:
                    *arrays, identity = verify_mesh(label, member, standard, audit, archive_a, archive_b, inputs)
                    diagnostic.update(identity)
                    conditions = CONDITIONS if comparisons else {"1m": CONDITIONS["1m"]}
                    for name, (size, phase) in conditions.items():
                        grid = grid_spec(arrays[0], size, phase)
                        result, timing = evaluate_case(voxelizer3d, arrays, grid, folder / name,
                                                       densities=(2, 3) if name == "1m" else (2,))
                        result["voxel_to_reference_volume_ratio"] = result["voxel_union_volume_m3"] / identity["reference"]["signed_volume_m3"]
                        for estimate in result["sample_estimates"]:
                            estimate["sampled_solid_minus_reference_m3"] = [
                                value - identity["reference"]["signed_volume_m3"]
                                for value in estimate["sampled_solid_volume_m3"]]
                        diagnostic["cases"][name] = result
                        timings[label + "/" + name] = timing
                        if label == "F" and name == "1m":
                            old_voxels = np.load(archive_a / "voxels.npy", allow_pickle=False)
                            new_voxels = np.load(folder / name / "voxels.npy", allow_pickle=False)
                            f.require(np.array_equal(old_voxels, new_voxels), "F differs from P1-1a")
                            diagnostic["F_P1_1a_voxel_identity"] = "PASS: exact array equality"
                    diagnostic["status"] = "PASS_MESH_ONLY"
                    diagnostic["environment_analysis_ready"] = "CONDITIONAL_REVIEW_REQUIRED"
                except Exception as exc:
                    diagnostic["error"] = f"{type(exc).__name__}: {exc}"
                f.write(folder / "voxel_diagnostics.json", diagnostic)
                preserve()
        finally:
            numba.set_num_threads(threads)
        manifest.update(status="PASS_MESH_ONLY" if all(d["status"] == "PASS_MESH_ONLY" for d in results.values()) else "BLOCKED_ONE_OR_MORE_BUILDINGS",
                        buildings={label: d["status"] for label, d in results.items()},
                        input_SHA_unchanged=True, environment_metadata_unchanged=True, forbidden_attempts=events,
                        inputs={str(Path(path).resolve().relative_to(b.REPO)).replace("\\", "/"): digest for path, digest in inputs.items()})
    except Exception as exc:
        manifest["error"] = f"{type(exc).__name__}: {exc}"
    f.write(output / "timings.json", timings)
    manifest["implementation_sha256"] = f.sha(__file__)
    manifest["outputs"] = {str(path.relative_to(output)).replace("\\", "/"): f.sha(path)
                           for path in sorted(output.rglob("*")) if path.is_file() and "cache" not in path.parts and path.name != "timings.json"}
    f.write(output / "manifest.json", manifest)
    return manifest


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("member", "standard", "audit-report", "archive-a", "archive-b", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--comparisons", action="store_true", help="only after baseline workload review: 0.5m and 1m XYZ phase+0.5m")
    a = parser.parse_args()
    result = run(a.member, a.standard, a.audit_report, a.archive_a, a.archive_b, a.output, a.comparisons)
    print(json.dumps({k: result.get(k) for k in ("status", "buildings", "error")}))
    return int(result["status"] != "PASS_MESH_ONLY")


if __name__ == "__main__":
    raise SystemExit(main())
