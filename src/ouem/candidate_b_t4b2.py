"""Experimental Candidate B T4-B2 voxel integration using pinned T4-B1 grids."""
import argparse
from collections import Counter
from importlib.metadata import distribution, version
import json
import math
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import geopandas as gpd
import numpy as np

from ouem import candidate_b_t4a as t4a
from ouem import candidate_b_t4b1 as b1
from ouem.terrain_candidate_b_preflight import digest, require

PROFILE = "ouem-candidate-b-t4b2-voxel/v0.1"
B1_SHA = "f8e0e72ac4aa2b39b090a4b1f0e54fe5b6b796b1a079661c044eb9d9dedc013f"
ROOF_TOLERANCE_M = 2.0
GROUND_QUANTIZATION_M = 0.500001


def stats(values):
    values = np.asarray(values)
    return dict(min=float(values.min()), max=float(values.max()),
                max_abs=float(np.abs(values).max()))


def audit_voxels(voxels, dem, ids, segments, rows, conflicts):
    """Check each vertical column and attribute only unambiguous roof cells."""
    require(voxels.ndim == 3 and voxels.shape[:2] == dem.shape, "voxel shape differs")
    effective = dem.astype(float, copy=True)
    for row in rows:
        owned = ids == row["id"]
        require(owned.any(), "missing owner")
        ground = math.fsum(dem[owned])/int(owned.sum())
        require(ground == row["g_eff_abs"] and row["z_top_abs"] - ground == row["height"],
                "B1 building height invariant differs")
        effective[owned] = ground
    origin = float(effective.min())
    ground_k = np.floor((effective-origin).astype("float32").astype(float)+0.5).astype(int)
    levels = np.arange(voxels.shape[2])
    require((ground_k < len(levels)).all(), "missing ground surface")
    require(np.array_equal(voxels == -1, levels < ground_k[..., None])
            and np.array_equal(voxels == 1, levels == ground_k[..., None]),
            "ground or land-cover voxel differs")
    expected = np.zeros(voxels.shape, dtype=bool)
    conflict_indices = {tuple(c["index"]) for c in conflicts}
    per_id = {row["id"]: [] for row in rows}
    envelope, conflict_result = [], []
    for i, j in np.ndindex(ids.shape):
        cell = segments[i, j]
        if not cell:
            require(ids[i, j] == 0, "owner has no segment")
            continue
        require(ids[i, j] != 0, "segments without owner")
        spans = []
        for low, high in cell:
            require(math.isfinite(low) and math.isfinite(high) and 0 <= low < high,
                    "invalid segment bounds")
            start = ground_k[i, j]+1+math.floor(low+0.5)
            stop = ground_k[i, j]+1+math.floor(high+0.5)
            require(start < stop <= len(levels), "empty or clipped voxel segment")
            expected[i, j, start:stop] = True
            spans.append([int(start), int(stop)])
        occupied = np.flatnonzero(voxels[i, j] == -3)
        require(occupied.size and occupied[0] == ground_k[i, j]+1
                and np.all(np.diff(occupied) == 1), "floating or discontinuous building")
        roof_abs = origin+int(occupied[-1])
        envelope.append(roof_abs-(effective[i, j]+max(high for _, high in cell)))
        if (i, j) in conflict_indices:
            conflict_result.append(dict(index=[i,j], owner=int(ids[i,j]), segments=cell,
                                        spans_k=spans, occupied_k=occupied.tolist(),
                                        roof_abs=roof_abs, effective_ground_abs=float(effective[i,j])))
        else:
            require(len(cell) == 1, "unaccounted multiple segments")
            per_id[int(ids[i,j])].append((roof_abs, int(occupied.size)))
    require(np.array_equal(voxels == -3, expected) and np.isin(voxels, [-3,-1,0,1]).all(),
            "actual class occupancy differs from ground and segment model")
    require(len(conflict_result) == len(conflicts), "competition missing from voxel audit")
    buildings = []
    for row in rows:
        samples = per_id[row["id"]]
        require(samples, "no unambiguous voxels for building")
        error = np.asarray([z-row["z_top_abs"] for z,_ in samples])
        buildings.append(row | dict(unambiguous_columns=len(samples),
                                    unambiguous_voxels=sum(n for _,n in samples),
                                    roof_error_m=stats(error), a3_upper_face_roof_error_m=stats(error+1)))
    surface = origin+ground_k
    ground_error = stats(surface-effective)
    roof_error = stats(envelope)
    require(ground_error["max_abs"] <= GROUND_QUANTIZATION_M
            and roof_error["max_abs"] <= 1.000001
            and all(r["a3_upper_face_roof_error_m"]["max_abs"] <= ROOF_TOLERANCE_M
                    for r in buildings), "vertical reconstruction exceeds tolerance")
    return effective, dict(z_reference_abs_m=origin, raw_dem_min_abs_m=float(dem.min()),
                           effective_ground_error_m=ground_error, raw_dem_ground_error_m=stats(surface-dem),
                           owner_ground_adjustment_m=stats(effective-dem), segment_envelope_error_m=roof_error,
                           buildings=buildings, conflicts=conflict_result,
                           class_counts={int(k):int(n) for k,n in zip(*np.unique(voxels, return_counts=True))})


def run(building_run, consumer_receipt, terrain_run, b1_run, out):
    out.mkdir()
    report = dict(profile=PROFILE, status="BLOCKED", terrain_integration_ready=False,
                  formal_acceptance="NOT_VERIFIED")
    try:
        receipt = b1_run/"report.json"
        t4a.verify(receipt, B1_SHA)
        preflight = json.loads(receipt.read_bytes())
        require(preflight["profile"] == b1.PROFILE and preflight["status"] == "COMPLETED"
                and preflight["t4b2_candidate"] is True, "unexpected B1 receipt")
        checked, expected, *_ = t4a.load_inputs(building_run, consumer_receipt, terrain_run)
        t4a_path = Path(preflight["inputs"]["t4a_report"]["path"])
        selected, excluded = b1.selection(t4a_path, expected)
        checked["t4a_report"] = (t4a_path, b1.T4A_SHA)
        require({k: sha for k, (_,sha) in checked.items()} ==
                {k: ref["sha256"] for k,ref in preflight["inputs"].items()},
                "B1 input binding differs")
        checked["b1_report"] = (receipt, B1_SHA)
        grids = {}
        for name, sha in preflight["outputs"].items():
            path = b1_run/name
            t4a.verify(path, sha)
            grids[path.stem] = np.load(path, allow_pickle=False)
            checked[name] = (path, sha)
        dem, ids, height = (grids[k] for k in ("dem", "building_ids", "building_height"))
        rows = preflight["buildings"]
        require(sorted(selected) == sorted(row["source_id"] for row in rows)
                and excluded == preflight["excluded"], "B1 building selection differs")
        direct = json.loads(distribution("voxcity").read_text("direct_url.json"))
        require(version("voxcity") == "1.7.0" and direct["vcs_info"]["commit_id"] == b1.PIN,
                "VoxCity pin mismatch")
        from voxcity.generator.voxelizer import NUMBA_AVAILABLE, Voxelizer
        from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon

        frame = gpd.read_file(checked["building_gpkg"][0], layer="building")
        require(frame.crs.to_epsg() == 6677 and frame.source_id.is_unique
                and {r.source_id:(r.ouem_id,r.source_lod) for r in frame.itertuples()} == expected,
                "Standard Building CRS or IDs differ")
        frame = frame[frame.source_id.isin(selected)].sort_values("ouem_id").reset_index(drop=True)
        attributes = {r["ouem_id"]:r for r in rows}
        footprints = {}
        for row in frame.itertuples():
            require(max(b1.adapter._z_values(row.geometry)) == attributes[row.ouem_id]["z_top_abs"],
                    "Standard Building top differs")
            footprints[row.ouem_id] = b1.adapter.build_normalized_footprint(row.geometry,row.ouem_id)
        buildings = b1.adapter._set_normalized_footprints(frame, footprints)
        for key in ("id","height","min_height"):
            buildings[key] = buildings.ouem_id.map({k:r[key] for k,r in attributes.items()})
        buildings, repairs = b1.adapter._repair_post_crs(
            b1.adapter._to_voxcity_building_crs(buildings), footprints)
        require(repairs == preflight["post_crs_repairs"], "footprint repair differs from B1")
        rectangle = preflight["rectangle_lonlat"]

        def raster(frame):
            return create_building_height_grid_from_gdf_polygon(
                frame, b1.MESH, rectangle, overlapping_footprint=True)

        reraster_height, segments, reraster_ids, _ = raster(buildings)
        require(np.array_equal(ids, reraster_ids) and np.array_equal(height, reraster_height),
                "rerasterized heights or ownership differ from B1")
        conflicts = preflight["grid"]["competitions"]
        claims = {}
        for conflict in conflicts:
            index = tuple(conflict["index"])
            inputs = []
            for building_id in conflict["candidates"]:
                _, single_segments, single_ids, _ = raster(buildings[buildings.id == building_id])
                require(single_ids[index] == building_id, "isolated claim differs from B1")
                inputs.extend(dict(id=building_id, bounds=list(pair)) for pair in single_segments[index])
            require(Counter(tuple(r["bounds"]) for r in inputs) ==
                    Counter(map(tuple, segments[index])), "grouped segments differ from isolated claims")
            claims[index] = inputs
        cover, trees = np.ones(ids.shape, dtype=int), np.zeros(ids.shape)
        voxels = Voxelizer(b1.MESH, "Standard").generate_combined(
            height.copy(), segments.copy(), ids.copy(), cover, dem.copy(), trees, print_class_info=False)
        effective, diagnostics = audit_voxels(voxels, dem, ids, segments, rows, conflicts)
        for result in diagnostics["conflicts"]:
            result["isolated_segments"] = claims[tuple(result["index"])]
            result["centre_xy"] = grids["centres_xy"][tuple(result["index"])].tolist()
        with TemporaryDirectory(prefix=".stage-", dir=out) as directory:
            stage = Path(directory)
            for name,array in dict(voxels=voxels, effective_dem_abs=effective).items():
                np.save(stage/(name+".npy"), array, allow_pickle=False)
            t4a.write(stage/"segments.json", segments.tolist())
            for path,sha in checked.values():
                t4a.verify(path, sha)
            result = report | dict(status="COMPLETED", voxel_shape=list(voxels.shape),
                orientation=preflight["orientation"]+"; axis 2 up", mesh_m=b1.MESH,
                projected_aoi=preflight["projected_aoi"], excluded=excluded,
                engine=dict(version="1.7.0", commit=b1.PIN, numba=NUMBA_AVAILABLE),
                vertical_reference=dict(previous="CONDITIONAL", candidate_b_eligibility="PASS_PROPOSED",
                                        ward_tp="INFERRED_FROM_SOURCE_LINEAGE",
                                        accuracy="NOT_VERIFIED", epoch="NOT_VERIFIED",
                                        datum_realization="NOT_VERIFIED"),
                tolerances_m=dict(ground=GROUND_QUANTIZATION_M, a3_upper_face_roof=ROOF_TOLERANCE_M),
                z_reconstruction="reference + k * mesh; A3 upper-face metric adds one mesh",
                environment=dict(host=platform.node(), os=platform.platform(), python=platform.python_version()),
                implementation_sha256=digest(Path(__file__)), diagnostics=diagnostics,
                inputs={k:dict(path=str(path),sha256=sha) for k,(path,sha) in checked.items()},
                outputs={p.name:digest(p) for p in sorted(stage.iterdir())})
            t4a.write(stage/"report.json",result)
            for name in (*result["outputs"], "report.json"):
                (stage/name).rename(out/name)
        return result
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        t4a.write(out/"failure.json",report)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("building-run","consumer-receipt","terrain-run","b1-run","output-dir"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.building_run,args.consumer_receipt,args.terrain_run,args.b1_run,args.output_dir)
    print(result["status"], result.get("error", result.get("voxel_shape")))
    return int(result["status"] != "COMPLETED")


if __name__ == "__main__":
    raise SystemExit(main())
