"""P1-2b: fixed-point A/B control before any real C voxel/shadow operation."""
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import sys

import numpy as np

from ouem import p1_lod2_f as f
from ouem import p1_lod2_smc as b
from ouem import p1_mesh_voxel as mesh

SETTINGS = dict(meshsize=1., hit_values=[0, -1, 1], inclusion_mode=False,
                tree_k=.6, tree_lad=1., numba_threads=2,
                azimuth_true_deg=180., elevation_deg=45.,
                baseline_include_building_roofs=False, baseline_requested_observer_height_m=0.,
                ray_kernel="voxcity.simulator.common.raytracing.trace_ray_generic",
                axis_transform="single axis-0 reflection; integer origin (R-1-r,c,k); kernel adds 0.5",
                observer="saved STEP4C XYZ; no observer regeneration")


def save_array(path, array):
    np.save(path, array, allow_pickle=False)
    f.require(np.array_equal(np.load(path, allow_pickle=False), array, equal_nan=True), "array readback differs")


def origins_for(mask, index, xyz, grid, d0, nz):
    """World-space audit includes the ray kernel's own +0.5 centre offset."""
    rows, cols = np.where(mask)
    f.require(mask.dtype == bool and index.shape == mask.shape and xyz.shape == mask.shape + (3,), "observer shapes differ")
    origins = np.column_stack((mask.shape[0] - 1 - rows, cols, index[mask])).astype(np.float64)
    f.require(np.isfinite(origins).all() and np.array_equal(origins, np.floor(origins))
              and (origins[:, 2] >= 0).all() and (origins[:, 2] < nz).all(), "noninteger/out-of-capacity origin")
    xmin, ymin, xmax, ymax = grid["bounds"]
    f.require(grid["resolution"] == 1. and grid["orientation"] == "north-up"
              and mask.shape == (int(ymax-ymin), int(xmax-xmin)), "unsupported observer grid")
    actual = np.column_stack((xmin + origins[:, 1] + .5,
                              ymin + origins[:, 0] + .5, d0 + origins[:, 2] + .5))
    f.require(np.array_equal(actual, xyz[mask]), "ray origin world XYZ differs from saved observer")
    return rows, cols, origins


def point_map(voxels, mask, index, xyz, grid, d0, direction, trace=None):
    """Only a point loop around VoxCity's existing DDA; no new ray algorithm."""
    if trace is None:
        from voxcity.simulator.common.raytracing import trace_ray_generic
        trace = trace_ray_generic
    f.require(voxels.dtype == np.int8 and voxels.ndim == 3
              and np.isin(voxels, [0, -1, 1, -3]).all(), "unexpected voxel classes/dtype")
    rows, cols, origins = origins_for(mask, index, xyz, grid, d0, voxels.shape[2])
    f.require(voxels.shape[:2] == mask.shape and len(rows) > 0, "empty/unaligned observers")
    # Match compute_direct_solar_irradiance_map_binary's pre-normalization.
    sd = np.array(direction, dtype=np.float64)
    length = math.sqrt(sd[0]*sd[0] + sd[1]*sd[1] + sd[2]*sd[2])
    f.require(np.isfinite(sd).all() and length > 0 and sd[0] < 0 and sd[2] > 0, "saved south/up sun invalid")
    sd /= length
    engine = np.ascontiguousarray(voxels[::-1])
    before = f.array_sha(engine), f.array_sha(voxels)
    result = np.full(mask.shape, 255, dtype=np.uint8)
    for row, col, origin in zip(rows, cols, origins):
        hit, transmission = trace(engine, origin, sd, (0, -1, 1), 1., .6, 1., False)
        f.require(transmission == 1., "unexpected attenuation without TREE")
        result[row, col] = 0 if hit else 1
    f.require(before == (f.array_sha(engine), f.array_sha(voxels)), "ray kernel mutated voxels")
    return result


def control(saved, model, trace=None):
    valid = saved["valid"]
    old = saved[model + "_shadow"]
    f.require(np.array_equal(old != 255, valid), "control cannot shrink saved valid mask")
    actual = point_map(saved[model], valid, saved["index"], saved["xyz"], saved["grid"],
                       saved["d0"], saved["direction"], trace)
    difference = (old != actual) & valid
    return actual, dict(status="PASS" if not difference.any() else "BLOCKED",
        evaluated_saved_valid_points=int(valid.sum()), mismatch_count=int(difference.sum()),
        mismatch_row_col=np.argwhere(difference).tolist(), saved_shadow_cells=int((old[valid] == 0).sum()),
        control_shadow_cells=int((actual[valid] == 0).sum()), origin_XYZ_exact=True,
        mask_policy="full saved M_AB; no C-derived exclusion in control")


def load_baseline(root, watches):
    evidence = json.loads((b.RECORDS / "p1-2a/input_alignment_evidence.json").read_bytes())
    def pin(path, expected):
        f.require(f.sha(path) == expected, "input SHA mismatch: " + path.name)
        watches[str(path.resolve())] = expected
    pin(root / "manifest.json", evidence["STEP4C_manifest_SHA256"])
    manifest = json.loads((root / "manifest.json").read_bytes())
    f.require(manifest["status"] == "COMPLETED_EXPERIMENTAL", "saved STEP4C incomplete")
    for name, digest in manifest["outputs"].items():
        pin(root / name, digest)
    report = json.loads((root / "report.json").read_bytes())
    f.require(report["settings"]["azimuth_true_deg"] == 180. and report["settings"]["elevation_deg"] == 45.
              and report["settings"]["requested_observer_height_m"] == 0., "saved settings differ")
    output = {}
    for label in "FSMC":
        info = report["buildings"][label]
        def array(name):
            return np.load(root / label / (name + ".npy"), allow_pickle=False)
        metadata_a = json.loads((root / label / "representative/metadata.json").read_bytes())
        metadata_b = json.loads((root / label / "distributed/metadata.json").read_bytes())
        valid, index, xyz = (array(name) for name in ("observer_valid", "observer_index", "observer_xyz"))
        a, bb = (array(name + "/shared_voxels") for name in ("representative", "distributed"))
        ids = array("representative/ids")
        f.require(np.array_equal(valid, ids == 0) and np.array_equal(ids, array("distributed/ids"))
                  and np.array_equal(valid, ~np.any(a == -3, axis=2))
                  and np.array_equal(valid, ~np.any(bb == -3, axis=2)), "baseline valid/building support differs")
        f.require(np.isnan(xyz[~valid]).all() and (index[~valid] == -1).all(), "invalid observers lost")
        f.require(metadata_a["expected_d0"] == metadata_b["expected_d0"]
                  and metadata_a["expected_effective_ground"] == metadata_b["expected_effective_ground"]
                  and np.array_equal(a == 1, bb == 1) and np.array_equal(a == -1, bb == -1), "A/B terrain differs")
        surface = np.argmax(a == 1, axis=2)
        f.require(np.array_equal(index[valid], (surface + 1)[valid]), "saved observer index convention differs")
        direction = info["orientation"]["direction_north_east_up"]
        angle = math.radians(180. - info["orientation"]["grid_north_true_bearing_deg"])
        f.require(np.allclose(direction, np.array([math.cos(angle), math.sin(angle), 1.])/math.sqrt(2), atol=1e-12, rtol=0), "saved direction inconsistent")
        output[label] = dict(A=a, B=bb, A_shadow=array("representative/shadow"), B_shadow=array("distributed/shadow"),
            valid=valid, index=index, xyz=xyz, grid=info["grid"], d0=metadata_a["expected_d0"],
            direction=direction, info=info)
    return output


def runtime(watches):
    from ouem.komae_integration import voxcity_provenance
    import voxcity
    provenance = voxcity_provenance()
    f.require(provenance["verified"], "VoxCity provenance mismatch")
    evidence = json.loads((b.RECORDS / "p1-2a/input_alignment_evidence.json").read_bytes())
    site = Path(voxcity.__file__).resolve().parent
    for name, digest in evidence["runtime_static"]["P1"]["source_files"].items():
        path = site / name
        f.require(f.sha(path) == digest, "ray/orientation source differs")
        watches[str(path)] = digest
    static = json.loads((b.RECORDS / "evidence/static_compatibility.json").read_bytes())["voxcitygml"]
    f.require(static["commit"] == f.GML_COMMIT, "GML commit pin mismatch")
    dist = metadata.distribution("voxcitygml")
    for name, digest in static["source_sha256"].items():
        path = Path(dist.locate_file(name)); f.require(f.sha(path) == digest, "GML source differs")
        watches[str(path)] = digest
    f.require(not any(d.metadata["Name"].lower() == "meshlib" for d in metadata.distributions()), "MeshLib prohibited")
    return dict(python=sys.version.split()[0], voxcity=provenance, voxcitygml_commit=f.GML_COMMIT,
                versions={n:metadata.version(n) for n in ("numba", "numpy", "voxcity", "voxcitygml")},
                STEP4C_saved_numba="0.68.0", MeshLib=False)


def common_grid(saved, vertices):
    x0, y0, x1, y1 = saved["grid"]["bounds"]
    d0 = saved["d0"]
    nz = max(saved["A"].shape[2], saved["B"].shape[2],
             math.ceil(max(float(vertices[:, 2].max()), float(saved["xyz"][saved["valid"], 2].max()))-d0)+2)
    f.require(vertices[:, 2].min() >= d0 and (vertices[:, 0] > x0).all()
              and (vertices[:, 0] < x1).all() and (vertices[:, 1] > y0).all()
              and (vertices[:, 1] < y1).all(), "source mesh outside shared context/Zmin; no clipping")
    return dict(n_rows=saved["valid"].shape[0], n_cols=saved["valid"].shape[1], n_z=nz,
                min_x=float(x0), max_x=float(x1), min_y=float(y0), max_y=float(y1),
                min_z=d0, max_z=d0+nz, voxel_size=1.)


def air_pad(voxels, nz):
    f.require(nz >= voxels.shape[2], "cannot truncate original Z")
    result = np.pad(voxels, ((0, 0), (0, 0), (0, nz-voxels.shape[2])), constant_values=0)
    f.require(np.array_equal(result[:, :, :voxels.shape[2]], voxels)
              and not result[:, :, voxels.shape[2]:].any(), "non-AIR padding")
    return result


def context_qa(voxels, saved):
    occupied = np.argwhere(voxels == -3)
    f.require(len(occupied) > 0, "empty C occupancy")
    x0, y0, x1, y1 = saved["grid"]["bounds"]
    west, east = x0+int(occupied[:, 1].min()), x0+int(occupied[:, 1].max())+1
    south, north = y1-int(occupied[:, 0].max())-1, y1-int(occupied[:, 0].min())
    top = saved["d0"] + int(occupied[:, 2].max()) + 1
    reach = max(0., top-float(saved["xyz"][saved["valid"], 2].min()))
    dn, de, du = saved["direction"]
    dx, dy = -de/du*reach, -dn/du*reach
    shadow_box = [west+min(0, dx), south+min(0, dy), east+max(0, dx), north+max(0, dy)]
    f.require(shadow_box[0] > x0+1 and shadow_box[1] > y0+1
              and shadow_box[2] < x1-1 and shadow_box[3] < y1-1, "conservative C shadow reach outside context")
    air = voxels.shape[2]-1-int(occupied[:, 2].max())
    f.require(air >= 1, "no upper AIR margin")
    return dict(conservative_shadow_bbox_XY=shadow_box, maximum_vertical_reach_m=reach,
                highest_occupied_upper_H=top, AIR_layers_above_highest_occupied=air,
                source_H_not_reanchored=True)


def fixed_mask(saved, c_voxels):
    rows, cols, _ = origins_for(saved["valid"], saved["index"], saved["xyz"],
                                saved["grid"], saved["d0"], c_voxels.shape[2])
    f.require(c_voxels.shape[:2] == saved["valid"].shape and np.isin(c_voxels, [0, -3]).all(), "C support/classes differ")
    classes = c_voxels[rows, cols, saved["index"][saved["valid"]]]
    mask = saved["valid"].copy()
    mask[rows[classes == -3], cols[classes == -3]] = False
    f.require(mask.any(), "empty common mask")
    reason = np.zeros(mask.shape, dtype=np.uint8)
    reason[mask] = 1
    occupied = saved["valid"] & ~mask
    reason[occupied] = 2
    return mask, reason, occupied, dict(original_AB_valid=int(saved["valid"].sum()),
        common_valid=int(mask.sum()), original_AB_excluded=int((~saved["valid"]).sum()),
        C_origin_occupied_excluded=int(occupied.sum()), excluded_row_col=np.argwhere(occupied).tolist(),
        reason_codes={"original_AB_excluded": 0, "common_AIR_observer": 1, "C_origin_occupied": 2},
        outside_domain_or_capacity="none; any such case is BLOCKED, never excluded",
        mask_fixed_before_C_shadow=True)


def compare(first, second, mask):
    # Existing accounting helper only; never call its scene regeneration or
    # the A/B-specific monotonic-shadow assertion for C.
    from ouem.real_roof_shadow import difference
    f.require(mask.any(), "empty comparison support")
    classes, old = difference(first, second, mask)
    return classes, dict(valid_cells=old["valid_observers"], first_shadow_cells=old["representative_shadow_cells"],
        second_shadow_cells=old["distributed_shadow_cells"],
        discrete_area_delta_m2_second_minus_first=old["shadow_cells_delta_B_minus_A"],
        changed_cells=old["changed_cells"], first_shadow_to_second_sun=old["shadow_to_sun"],
        first_sun_to_second_shadow=old["sun_to_shadow"], shadow_IoU=old["shadow_IoU"],
        common_sun=int((classes == 1).sum()), common_shadow=int((classes == 2).sum()),
        first_only_shadow=int((classes == 3).sum()), second_only_shadow=int((classes == 4).sum()),
        empty_union=not np.any((first[mask] == 0) | (second[mask] == 0)))


def plot(path, label, saved, maps, differences):
    from matplotlib.figure import Figure
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    fig = Figure(figsize=(12, 7))
    bounds = saved["grid"]["bounds"]
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
    shadow_colors = ["#263c66", "#f4f5ee", "#c8c8c8"]
    colors = ["#c8c8c8", "#f4f5ee", "#263c66", "#ee982e", "#36a9a6"]
    for n, (name, array) in enumerate(list(maps.items()) + list(differences.items())):
        axis = fig.add_subplot(2, 3, n+1)
        values = np.where(array == 255, 2, array) if n < 3 else array
        axis.imshow(values, origin="upper", extent=extent, interpolation="nearest",
                    cmap=ListedColormap(shadow_colors if n < 3 else colors), vmin=0, vmax=2 if n < 3 else 4)
        x = np.arange(array.shape[1]) + bounds[0] + .5
        y = bounds[3] - np.arange(array.shape[0]) - .5
        axis.contour(x, y, (~saved["valid"]).astype(int), levels=[.5], colors="#ad2943", linewidths=.7)
        axis.set_title(name + (" shadow" if n < 3 else " comparison"))
        axis.ticklabel_format(useOffset=False, style="plain")
        axis.xaxis.set_major_locator(MaxNLocator(3)); axis.yaxis.set_major_locator(MaxNLocator(3))
        if n >= 3: axis.set_xlabel("EPSG:6677 X (m)")
        if n % 3 == 0: axis.set_ylabel("EPSG:6677 Y (m)")
    fig.suptitle(label + " | A/B/C same saved observer XYZ | true azimuth 180, elevation 45")
    fig.legend(handles=[Patch(facecolor=color, label=text) for color, text in zip(colors,
               ("excluded", "common sun", "common shadow", "first-only shadow", "second-only shadow"))],
               loc="lower center", ncol=5)
    fig.subplots_adjust(left=.09, right=.98, bottom=.13, top=.89, hspace=.32, wspace=.29)
    fig.savefig(path, dpi=120, metadata={"Software": "OUEM P1-2b"})


def run(baseline, output, *, member=None, standard=None, audit_report=None, archive_a=None, archive_b=None):
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    gates = {"Gate_" + str(n): "NOT_EXECUTED" for n in range(1, 6)}
    report = dict(profile="ouem-p1-2b-common-point-shadow/v0.1", status="BLOCKED", gates=gates,
                  settings=SETTINGS, buildings={}, scientific_validation="NOT_VERIFIED",
                  formal_acceptance="NOT_VERIFIED", terrain_integration_ready=False)
    watches = {}
    active_gate = "Gate_1"
    try:
        gates["Gate_1"] = "BLOCKED"
        f.require(Path(sys.prefix).name == "ouem-voxcitygml-p1" and sys.prefix != sys.base_prefix, "isolated P1 required")
        before_env = {"OUEM": b.environment_inventory(b.REPO / ".venv"), "P1": b.environment_inventory(sys.prefix)}
        events = f.guard(output, [b.REPO / "data/work", baseline.resolve(), b.REPO / ".venv", Path(sys.prefix)])
        for source in (__file__, f.__file__, b.__file__, mesh.__file__,
                       b.RECORDS / "p1-2a/P1-2a_EXPERIMENT_SPEC_DRAFT.md", b.RECORDS / "p1-2a/input_alignment_evidence.json"):
            watches[str(Path(source).resolve())] = f.sha(source)
        report["runtime"] = runtime(watches)
        saved = load_baseline(baseline, watches)
        memory = {label: {key: f.array_sha(value) for key, value in item.items() if isinstance(value, np.ndarray)}
                  for label, item in saved.items()}
        def preserve():
            f.require(not events and all(f.sha(Path(path)) == digest for path, digest in watches.items()), "input changed or forbidden side effect")
            f.require(memory == {label: {key: f.array_sha(value) for key, value in item.items() if isinstance(value, np.ndarray)}
                                     for label, item in saved.items()}, "saved A/B arrays mutated in memory")
            f.require(before_env == {"OUEM": b.environment_inventory(b.REPO / ".venv"), "P1": b.environment_inventory(sys.prefix)}, "environment metadata changed")
        import numba
        threads = numba.get_num_threads(); numba.set_num_threads(2)
        try:
            for label, item in saved.items():
                folder = output / label; folder.mkdir()
                valid = item["valid"]
                diagnostic = dict(controls={}, saved_direction_north_east_up=list(item["direction"]),
                    saved_observer_grid=item["grid"], D0_abs_H=item["d0"],
                    original_saved_valid_count=int(valid.sum()),
                    observer_index_range=[int(item["index"][valid].min()), int(item["index"][valid].max())],
                    observer_abs_H_range=[float(item["xyz"][valid, 2].min()), float(item["xyz"][valid, 2].max())])
                report["buildings"][label] = diagnostic
                for model in ("A", "B"):
                    actual, qa = control(item, model)
                    diagnostic["controls"][model] = qa
                    save_array(folder / (model + "_control.npy"), actual)
                    save_array(folder / (model + "_control_mismatch.npy"), (actual != item[model + "_shadow"]) & item["valid"])
                    f.write(folder / (model + "_control.json"), qa)
                    f.require(qa["status"] == "PASS", "Gate 1 classification mismatch; C not executed")
                    preserve()
            gates["Gate_1"] = "PASS"
            # Global barrier: all eight full-mask controls have passed before
            # any real C source extraction, voxelization or ray evaluation.
            active_gate = "Gate_2"; gates[active_gate] = "BLOCKED"
            member = member or b.REPO / "data/work/mixed-lod-converter-bridge/run-02/extracted/udx/bldg/53393466_bldg_6697_op.gml"
            standard = standard or b.REPO / "data/work/mixed-lod-standard/run-02/standard.gpkg"
            audit_report = audit_report or b.REPO / "data/work/step4-0-roof-audit/audit-final-e/report.json"
            archive_a = archive_a or b.REPO / "data/work/voxcitygml_p1/p1-1a-final-b"
            archive_b = archive_b or b.REPO / "data/work/voxcitygml_p1/p1-1b-final-d"
            public = json.loads((b.RECORDS / "p1-1a/manifest.json").read_bytes())
            for path in (member, standard, audit_report):
                digest = public["inputs"][path.name]
                f.require(f.sha(path) == digest, "C source input SHA differs")
                watches[str(path.resolve())] = digest
            for path in (b.RECORDS / "p1-1a/manifest.json", b.RECORDS / "p1-1b/manifest.json",
                         b.RECORDS / "evidence/source_identity.json", b.RECORDS / "evidence/static_compatibility.json"):
                watches[str(path.resolve())] = f.sha(path)
            from voxcitygml import voxelizer3d, watertight
            f.require(not watertight._MESHLIB_AVAILABLE and not voxelizer3d._MESHLIB_VOXEL_AVAILABLE, "MeshLib prohibited")
            audit = json.loads(audit_report.read_bytes())
            c_models = {}
            for label, item in saved.items():
                folder = output / label; diagnostic = report["buildings"][label]
                _, _, merged_v, merged_t, identity = mesh.verify_mesh(label, member, standard, audit, archive_a, archive_b, watches)
                grid = common_grid(item, merged_v)
                padding_qa = {}
                for model in ("A", "B"):
                    padded = air_pad(item[model], grid["n_z"])
                    replay = point_map(padded, item["valid"], item["index"], item["xyz"], item["grid"], item["d0"], item["direction"])
                    f.require(np.array_equal(replay, item[model+"_shadow"]), "A/B AIR extension changes control")
                    save_array(folder / (model+"_shared_voxels.npy"), padded)
                    padding_qa[model] = dict(original_shape=list(item[model].shape), shared_shape=list(padded.shape),
                        AIR_layers_added=grid["n_z"]-item[model].shape[2], original_layers_identical=True,
                        added_layers_AIR_only=True, full_saved_valid_control_identical=True,
                        highest_occupied_upper_H=item["d0"]+int(np.argwhere(padded == -3)[:, 2].max())+1)
                # Use the archived merge-only arrays as the actual C input.
                cvox, masks, trace = mesh.traced_voxelize(voxelizer3d, merged_v, merged_t, merged_v, merged_t, grid)
                enlarged = dict(grid)
                for axis in "xyz":
                    enlarged["min_"+axis] -= 1; enlarged["max_"+axis] += 1
                for key in ("n_rows", "n_cols", "n_z"): enlarged[key] += 2
                extra, _, _ = mesh.traced_voxelize(voxelizer3d, merged_v, merged_t, merged_v, merged_t, enlarged)
                outside = extra.copy(); outside[1:-1, 1:-1, 1:-1] = 0
                f.require(np.array_equal(extra[1:-1, 1:-1, 1:-1], cvox) and not outside.any(), "C voxel context clipping")
                qa = dict(identity=identity, grid=grid, trace=trace, shape=list(cvox.shape),
                          occupied_cells=int((cvox == -3).sum()), scanline_fill_cells=int(masks["interior"].sum()),
                          contact_shell_cells=int(masks["shell"].sum()), voxel_padding_core_identity=True,
                          extra_domain_occupied_cells=0, geometry_context=context_qa(cvox, item),
                          original_H_unchanged=True, original_C_archives_unchanged=True,
                          GROUND_SURFACE_DEM="NOT_CREATED; D0 is grid origin only")
                qa["A_B_padding_qa"] = padding_qa
                diagnostic["C_derived"] = qa; c_models[label] = cvox
                save_array(folder / "C_voxels.npy", cvox)
                for name, array in masks.items(): save_array(folder / ("C_"+name+".npy"), array)
                f.write(folder / "C_voxel_qa.json", qa)
                preserve()
            gates["Gate_2"] = "PASS"
            active_gate = "Gate_3"; gates[active_gate] = "BLOCKED"
            common_masks = {}
            for label, item in saved.items():
                folder = output / label
                mask, reason, occupied, qa = fixed_mask(item, c_models[label])
                save_array(folder / "common_mask.npy", mask)
                save_array(folder / "observer_exclusion_reason.npy", reason)
                save_array(folder / "C_origin_occupied.npy", occupied)
                save_array(folder / "C_origin_excluded_XYZ.npy", item["xyz"][occupied])
                qa["mask_file_sha256"] = f.sha(folder / "common_mask.npy")
                qa["mask_array_sha256"] = f.array_sha(mask)
                f.write(folder / "common_mask_qa.json", qa)
                report["buildings"][label]["common_mask"] = qa
                mask.setflags(write=False); common_masks[label] = mask
                preserve()
            gates["Gate_3"] = "PASS"
            active_gate = "Gate_4"; gates[active_gate] = "BLOCKED"
            # No C ray call occurs before every geometry-only mask is on disk.
            for label, item in saved.items():
                folder = output / label; mask = common_masks[label]; cvox = c_models[label]
                maps = {model: np.where(mask, item[model+"_shadow"], 255).astype(np.uint8) for model in ("A", "B")}
                maps["C"] = point_map(cvox, mask, item["index"], item["xyz"], item["grid"], item["d0"], item["direction"])
                higher = point_map(air_pad(cvox, cvox.shape[2]+3), mask, item["index"], item["xyz"], item["grid"], item["d0"], item["direction"])
                f.require(np.array_equal(higher, maps["C"]), "C shadow changes with upper AIR capacity")
                border = np.zeros(mask.shape, bool)
                border[:2, :] = border[-2:, :] = border[:, :2] = border[:, -2:] = True
                f.require(not ((maps["C"] == 0) & border).any(), "C shadow on two-cell context border")
                f.require(f.sha(folder / "common_mask.npy") == report["buildings"][label]["common_mask"]["mask_file_sha256"], "fixed mask file changed")
                differences = {}; pairs = {}
                for first, second in (("A", "B"), ("A", "C"), ("B", "C")):
                    name = first+"_"+second
                    differences[name], pairs[name] = compare(maps[first], maps[second], mask)
                    save_array(folder / (name+"_difference.npy"), differences[name])
                statistics = {model: dict(valid_observers=int(mask.sum()), shadow_cells=int((array[mask] == 0).sum()),
                    shadow_area_m2=float((array[mask] == 0).sum()), shadow_fraction=float((array[mask] == 0).mean()))
                    for model, array in maps.items()}
                for model, array in maps.items(): save_array(folder / (model+"_common_shadow.npy"), array)
                result = dict(models_on_common_mask=statistics, pairs_on_common_mask=pairs,
                              original_STEP4C_full_AB_metrics=item["info"]["metrics"],
                              C_plus_three_AIR_identity=True, C_outer_two_cell_shadow_count=0,
                              shared_observer_mask_array_sha256=f.array_sha(mask),
                              shadow_codes={"shadow": 0, "sun": 1, "excluded": 255},
                              difference_codes={"excluded": 0, "common_sun": 1, "common_shadow": 2,
                                                "first_only_shadow": 3, "second_only_shadow": 4})
                report["buildings"][label]["comparison"] = result
                f.write(folder / "comparison_qa.json", result)
                plot(folder / "comparison.png", label, item, maps, differences)
                preserve()
            gates["Gate_4"] = "PASS"
            active_gate = "Gate_5"; gates[active_gate] = "BLOCKED"
            preserve()
            gates["Gate_5"] = "CONDITIONAL"
            report["Gate_5_local_QA"] = "PASS: readback/input preservation; independent-run SHA comparison pending"
            report["status"] = "READY_FOR_INDEPENDENT_REPRODUCIBILITY_CHECK"
        finally:
            numba.set_num_threads(threads)
        report.update(input_SHA_unchanged=True, environment_metadata_unchanged=True, forbidden_attempts=events)
    except Exception as exc:
        report["status"] = "BLOCKED"; gates[active_gate] = "BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
    f.write(output / "report.json", report)
    def locator(path):
        path = Path(path).resolve()
        if path.is_relative_to(b.REPO): return path.relative_to(b.REPO).as_posix()
        if path.is_relative_to(Path(sys.prefix)): return "P1_VENV/"+path.relative_to(Path(sys.prefix)).as_posix()
        return path.name
    manifest = dict(status=report["status"], gates=gates, implementation_sha256=f.sha(__file__),
                    inputs={locator(path): digest for path, digest in watches.items()},
                    outputs={str(p.relative_to(output)).replace("\\", "/"): f.sha(p)
                             for p in sorted(output.rglob("*")) if p.is_file() and "cache" not in p.parts},
                    scientific_validation="NOT_VERIFIED", formal_acceptance="NOT_VERIFIED", terrain_integration_ready=False)
    f.write(output / "manifest.json", manifest)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for name in ("member", "standard", "audit-report", "archive-a", "archive-b"):
        parser.add_argument("--"+name, type=Path)
    args = parser.parse_args(); result = run(args.baseline, args.output, member=args.member,
        standard=args.standard, audit_report=args.audit_report, archive_a=args.archive_a, archive_b=args.archive_b)
    print(json.dumps({key: result.get(key) for key in ("status", "gates", "error")}))
    return int(result["status"] != "READY_FOR_INDEPENDENT_REPRODUCIBILITY_CHECK")


if __name__ == "__main__":
    raise SystemExit(main())
