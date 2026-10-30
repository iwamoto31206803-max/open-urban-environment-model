"""Opt-in four-mesh LoD2 / representative-height experiment; never Acceptance."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import distribution, version
import json
import platform
import sys
from pathlib import Path
import time

import geopandas as gpd
import numpy as np
from pyproj import Transformer

from ouem import real_komae_source_h as source
from ouem.adapters import voxcity as adapter
from ouem.adapters.source_h_synthetic_voxel import PIN
from ouem.consumers.source_h_standard import Watch, validate_source_h_standard
from ouem.consumers._source_h_geometry import read_standard
from ouem.native.building.provenance import SOURCE_H_PROFILE
from ouem.native.building.source_h_geometry import require, polygons
from ouem.standardize.building.source_h_geometry import points
from ouem.study_area import load_study_area

MEMBERS = tuple(f"533934{n}_bldg_6697_op.gml" for n in (55, 56, 65, 66))
PROFILE = "exploratory-komae-four-mesh-representative-height/v0.1"


def update_heights(buildings, z_values, ids, dem):
    """Use actual owner cells only; report zero owners without inventing ground."""
    records, missing = [], []
    for row in buildings.itertuples():
        if not np.any(ids == row.id):
            missing.append(dict(source_id=row.source_id, ouem_id=row.ouem_id,
                                voxcity_id=int(row.id), reason="NO_OWNED_ENGINE_CELL"))
            continue
        derived = adapter.derive_attributes(z_values[row.ouem_id],
            adapter.grid_ground_samples(ids, dem, row.id))
        records.append(dict(source_id=row.source_id, ouem_id=row.ouem_id,
                            voxcity_id=int(row.id), **derived))
    return records, missing


def compare_previous(current, previous):
    old = read_standard(previous, "building")
    require(old.keys() <= current.keys(), "previous", "old IDs missing from new Standard")
    # Separate cross-run face permutation from any ring/XYZ/attribute change.
    # Within-run Native/Standard order preservation remains independently strict.
    ordered_changed = [key for key in old if old[key] != current[key]]
    changed = [key for key in old if old[key][1:] != current[key][1:]
               or old[key][0][0] != current[key][0][0]
               or Counter(polygons(old[key][0])) != Counter(polygons(current[key][0]))]
    return dict(old_count=len(old), common_ids=len(old.keys() & current.keys()),
                additional_ids=sorted(current.keys()-old.keys()), changed_records=changed,
                ordered_record_differences=ordered_changed,
                previous_sha256=source.digest(previous))


def voxel_phase(args, standard_report):
    out = args.run_dir / "voxcity"
    out.mkdir()
    report = dict(profile=PROFILE, status="RUNNING", formal_acceptance="NOT_VERIFIED",
                  source_h_eligibility="NOT_ESTABLISHED", started_at=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, platform=platform.platform(),
                  implementation_sha256={str(Path(__file__)):source.digest(Path(__file__))})
    protected = [args.terrain, args.terrain.with_suffix(".tif.manifest.json"), args.study_area,
                 args.previous_standard]
    before = {str(p): source.digest(p) for p in protected}
    started = time.perf_counter()
    try:
        manifest = standard_report["standard"]["manifest"]
        consumer = validate_source_h_standard(manifest, args.artifact_root, SOURCE_H_PROFILE,
                                             study_area_config=args.study_area.resolve())
        require(consumer["technical_validation"] == "PASS", "consumer", str(consumer["issues"]))
        report["consumer"] = consumer
        watch = Watch(args.artifact_root)
        for key, identity in consumer["artifacts"].items():
            watch.capture(key, identity["path"], identity["sha256"], identity["size_bytes"])
        standard = watch.resolve(consumer["artifacts"]["standard"]["path"])
        require(standard == Path(standard_report["standard"]["output"]).resolve(),
                "Standard.binding", "runner output differs from Consumer-bound artifact")
        features = read_standard(standard, "building")
        require(len(features) == 373, "Standard", "this bounded PoC expects 373 Raw-selected IDs")
        report["previous173"] = compare_previous(features, args.previous_standard)
        require(not report["previous173"]["changed_records"], "previous", "existing records changed")
        area = load_study_area(args.study_area)
        require(area.epsg == 6677 and area.extent == (-23600., -40800., -23200., -40500.),
                "AOI", "bounded Komae 400x300m configuration required")
        tm = json.loads(args.terrain.with_suffix(".tif.manifest.json").read_text())
        require(tm["standard"]["sha256"] == source.digest(args.terrain), "Terrain", "hash mismatch")
        require(tm["schema"] == "ouem-standard-terrain-manifest/v0.1", "Terrain", "unsupported schema")
        adapter.check_vertical_compatibility("T.P.", tm["vertical_reference"])
        direct = json.loads(distribution("voxcity").read_text("direct_url.json"))
        require(version("voxcity") == "1.7.0" and direct.get("vcs_info", {}).get("commit_id") == PIN,
                "VoxCity", "fixed version/commit required")
        from voxcity.geoprocessor.raster import (create_building_height_grid_from_gdf_polygon as raster,
            create_dem_grid_from_geotiff_polygon as raster_dem, process_grid)
        from voxcity.geoprocessor.raster.core import compute_cell_center_coords
        from voxcity.generator.voxelizer import Voxelizer
        b = gpd.read_file(standard, layer="building")
        require(b.crs.to_epsg() == 6677 and b.ouem_id.is_unique, "Standard", "CRS/ID mismatch")
        z = {r.ouem_id: adapter._z_values(r.geometry) for r in b.itertuples()}
        fps = {r.ouem_id: adapter.build_normalized_footprint(r.geometry, r.ouem_id) for r in b.itertuples()}
        b = adapter._set_normalized_footprints(b, fps)
        mapping = adapter.numeric_id_mapping(b.ouem_id)
        b["id"] = b.ouem_id.map(mapping)
        b["voxcity_id"] = b.id
        b["height"], b["min_height"] = 1., 0.
        b = adapter._to_voxcity_building_crs(b)
        b, repair = adapter._repair_post_crs(b, fps)
        transform = Transformer.from_crs(6677, 4326, always_xy=True)
        xmin, ymin, xmax, ymax = area.extent
        rectangle = [transform.transform(x, y) for x, y in
                     ((xmin,ymin),(xmin,ymax),(xmax,ymax),(xmax,ymin))]
        dem = raster_dem(str(args.terrain), 1., rectangle, dem_interpolation=False)
        require(np.isfinite(dem).all(), "DEM", "nonfinite engine samples")
        report.update(voxcity=dict(version=version("voxcity"), commit=PIN),
            rectangle_vertices_lonlat=rectangle, projected_aoi=list(area.extent),
            meshsize_m=1., grid_geometry={k: np.asarray(v).tolist() for k,v in compute_cell_center_coords(rectangle,1.).items() if k not in ("lons", "lats")},
            post_crs_repair=repair, iterations=[], missing=[])
        previous_ids = None
        for iteration in range(8):
            heights, segments, ids, _ = raster(b, 1., rectangle, overlapping_footprint=True)
            require(ids.shape == dem.shape, "grid", "building/DEM shape mismatch")
            records, missing = update_heights(b, z, ids, dem)
            report["missing"].extend(missing)
            report["iterations"].append(dict(iteration=iteration, owners=len(records), missing=len(missing)))
            require(records, "ownership", "no buildings own cells")
            # Explicit exploratory handling: zero-owner features have no G_eff and
            # are omitted from the next engine pass, never from canonical Standard.
            b = b[b.id.isin([r["voxcity_id"] for r in records])].copy()
            b["height"] = b.ouem_id.map({r["ouem_id"]:r["height"] for r in records})
            if not missing and previous_ids is not None and np.array_equal(previous_ids, ids):
                break
            previous_ids = ids.copy()
        else:
            raise ValueError("owner-grid assignment did not converge in eight passes")
        # Re-rasterize final heights; convergence must hold at actual voxel inputs.
        heights, segments, final_ids, _ = raster(b, 1., rectangle, overlapping_footprint=True)
        require(np.array_equal(ids, final_ids), "convergence", "final heights changed ownership")
        effective = process_grid(ids, dem.copy())
        d0 = float(dem.min())
        for r in records:
            require(np.allclose(effective[ids == r["voxcity_id"]] + d0,
                                r["ground_eff_abs"], atol=1e-9, rtol=0),
                    "ground", "process_grid disagrees with owner-cell mean")
        b.to_file(out/"buildings.geojson", driver="GeoJSON")
        cover, trees = np.ones(ids.shape, dtype=int), np.zeros(ids.shape)
        voxels = Voxelizer(1., "Standard").generate_combined(heights.copy(), segments.copy(),
            ids.copy(), cover, dem.copy(), trees, print_class_info=False)
        require(voxels.shape[:2] == ids.shape, "voxel", "shape mismatch")
        for name, array in dict(building_ids=ids, heights=heights, terrain_H=dem,
                                effective_dem=effective, voxels=voxels).items():
            np.save(out/(name+".npy"), array, allow_pickle=False)
        source.write(out/"segments.json", [[cell for cell in row] for row in segments])
        counts = []
        for r in records:
            mask = ids == r["voxcity_id"]
            counts.append(dict(**r, owner_cells=int(mask.sum()), building_voxels=int((voxels[mask]==-3).sum())))
        require(all(r["building_voxels"] > 0 for r in counts), "voxel", "owner has no Building voxels")
        multi = [(int(i),int(j),segments[i,j]) for i,j in np.argwhere(ids>0) if len(segments[i,j])>1]
        errors = []
        for i,j in np.argwhere(ids>0):
            ks = np.flatnonzero(voxels[i,j] == -3)
            expected = d0 + effective[i,j] + max(high for low,high in segments[i,j])
            errors.append(abs(d0+int(ks[-1])+1-expected) if ks.size else float("inf"))
        require(np.isfinite(errors).all(), "roof", "no voxel roof at occupied cell")
        report.update(status="COMPLETED", buildings=counts, input_buildings=len(features),
            grid_owners=len(records), grid_shape=list(ids.shape), voxel_shape=list(voxels.shape),
            height=source.distribution([r["height"] for r in records]), terrain_H=source.distribution(dem.ravel()),
            multi_segment_cells=len(multi), roof_envelope_error_m=source.distribution(errors),
            class_counts={str(int(k)):int(v) for k,v in zip(*np.unique(voxels,return_counts=True))},
            footprint_diagnostics={k:v[1] for k,v in fps.items()},
            output_hashes={p.name:source.digest(p) for p in out.iterdir() if p.is_file()})
        source.write(out/"multi-segment-cells.json", multi)
        watch.unchanged()
    except Exception as exc:
        report.update(status="FAILED", error=str(exc))
        raise
    finally:
        report["input_unchanged"] = before == {str(p):source.digest(p) for p in protected}
        if not report["input_unchanged"]: report["status"]="FAILED"
        report.update(input_sha256=before, elapsed_seconds=time.perf_counter()-started,
                      completed_at=datetime.now(timezone.utc).isoformat())
        source.write(out/"report.json", report)
    require(report["status"]=="COMPLETED", "integrity", "input changed")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("artifact-root","run-dir","zip","converter","terrain","study-area","previous-standard"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--prepared-standard-run", type=Path,
                        help="Read-only completed Raw/Standard run; fresh output directory still required")
    args=parser.parse_args()
    if args.prepared_standard_run:
        root=args.artifact_root.resolve(strict=True)
        require(args.run_dir.resolve().is_relative_to(root), "run_dir", "outside artifact root")
        saved=args.prepared_standard_run/"report.json"
        result=json.loads(saved.read_text(encoding="utf-8"))
        require(result["status"]=="COMPLETED" and result["input_unchanged"],
                "prepared_standard_run", "completed immutable source run required")
        args.run_dir.mkdir()
        source.write(args.run_dir/"source-reference.json", dict(
            report_path=str(saved.resolve()), report_sha256=source.digest(saved)))
    else:
        result=source.run(args, members=MEMBERS)
    voxel_phase(args, result)


if __name__ == "__main__":
    main()
