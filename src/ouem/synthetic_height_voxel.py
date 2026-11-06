"""STEP 3-B experimental 1 m synthetic-only adapter and integer occupancy QA."""
from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform

import numpy as np
from shapely.geometry import shape

from ouem import synthetic_height_distribution as distribution
from ouem.real_komae_voxel import effective_ground
from ouem.komae_integration import voxcity_provenance

PROFILE = "ouem-synthetic-distributed-height-voxel/v0.1"


class Blocked(ValueError):
    """Input, vertical reference, ownership or capacity is unresolved."""


def require(condition, message):
    if not condition:
        raise Blocked(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def array_identity(array):
    return dict(shape=list(array.shape), dtype=array.dtype.str,
                sha256=hashlib.sha256(array.tobytes(order="C")).hexdigest())


def validated_derived(derived):
    """Replay the existing synthetic procedure; do not trust edited state/top/grid."""
    try:
        grid = distribution.GridSpec(tuple(derived["grid"]["bounds"]),
                                     derived["grid"]["resolution"], derived["grid"]["epsg"])
        require(grid.resolution == 1., "initial voxel profile requires 1 m cells")
        sources = [distribution.Building(s["source_id"], shape(s["footprint"]),
                   tuple(distribution.Face(f["face_id"], f["rings"]) for f in s["faces"]),
                   s["provenance"]) for s in derived["source_provenance"]]
        replay = distribution.derive(grid, sources, method=derived["sampling_method"])
        require(digest(replay) == digest(derived), "Derived identity/state/procedure mismatch")
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise Blocked(f"invalid synthetic Derived: {exc}") from exc
    return grid


def prepare(derived, dem, *, method, datum, representative_tops=None, owners=None):
    """Convert known building-cell tops to [0, top-owner_ground].

    Owner rule: unique source, otherwise an explicit cell->source selection.
    Every contributing building gets its own grounded extrusion interval, using
    the selected cell owner's ground as the fixed API does. Faces remain in the
    complete Derived record; they do not imply cavities or separate solids.
    """
    grid = validated_derived(derived)
    require(datum == derived["procedure"]["vertical_datum"], "vertical datum mismatch")
    require(method in ("representative", "centre", "cell_max"), "unknown method")
    require(method == "representative" or method == derived["sampling_method"], "sampling method mismatch")
    require(np.asarray(dem).shape == (grid.height, grid.width), "DEM grid mismatch")
    dem = np.array(dem, dtype=np.float64, copy=True)
    require(np.isfinite(dem).all(), "nonfinite DEM")
    owners = dict(owners or {})
    identifiers = sorted(s["source_id"] for s in derived["source_provenance"])
    mapping = {sid: k+1 for k, sid in enumerate(identifiers)}
    representative_tops = dict(representative_tops or {})
    if method == "representative":
        require(set(representative_tops) == set(identifiers)
                and all(isinstance(z, (int,float)) and not isinstance(z,bool)
                        and math.isfinite(z) for z in representative_tops.values()),
                "explicit finite representative tops required")
    else:
        require(not representative_tops, "representative tops forbidden for distributed method")
    ids = np.zeros(dem.shape, dtype=np.int32)
    choices, unresolved = {}, []
    for cell in derived["cells"]:
        index = tuple(cell["cell_index"])
        candidates = [r["source_id"] for r in cell["buildings"]]
        if not candidates:
            require(index not in owners, "owner assigned to absent building")
            continue
        if index in owners:
            owner = owners[index]
            require(owner in candidates, "owner is not a cell contributor")
        else:
            require(len(candidates) == 1, f"unresolved owner competition at {index}")
            owner = candidates[0]
        choices[index] = owner
        ids[index] = mapping[owner]
        if method != "representative":
            unresolved.extend((index, r["source_id"]) for r in cell["buildings"]
                              if r["state"] != "KNOWN" or not r["valid"])
    require(set(owners) <= set(choices), "unknown owner cell")
    require(not unresolved, f"TOP_UNKNOWN; no implicit fill: {unresolved}")
    effective, d0 = effective_ground(ids, dem)
    segments = np.empty(dem.shape, dtype=object)
    height = np.zeros(dem.shape)
    intervals = []
    for cell in derived["cells"]:
        index = tuple(cell["cell_index"])
        segments[index] = []
        for record in cell["buildings"]:
            top = (representative_tops[record["source_id"]] if method == "representative"
                   else record["absolute_top_z"])
            high = float(top - effective[index])
            require(math.isfinite(high) and high > 0, f"top at/below effective ground at {index}")
            segments[index].append([0., high])
            height[index] = max(height[index], high)
            intervals.append(dict(cell_index=list(index), source_id=record["source_id"],
                                  owner_source_id=choices[index], absolute_top_z=top,
                                  effective_ground_z=float(effective[index]), low=0., high=high))
    return dict(height=height, segments=segments, ids=ids, dem=dem,
                metadata=dict(profile=PROFILE, input_kind="derived", method=method, grid=deepcopy(derived["grid"]),
                              grid_identity=derived["grid_identity"], datum=datum,
                              owner_rule="unique source or explicitly selected contributor per cell",
                              source_owner_mapping=mapping,
                              explicit_owner_choices=[dict(cell_index=list(k), source_id=v)
                                                      for k,v in sorted(owners.items())],
                              derived=deepcopy(derived), derived_sha256=digest(derived),
                              representative_tops=representative_tops, intervals=intervals,
                              expected_effective_ground=effective.tolist(), expected_d0=d0))


def occupancy_oracle(inputs, *, numba, max_levels=512):
    """Independent scalar integer intervals, built before calling Voxelizer.

    Does not call engine rounding/flattening/voxelization. Supports explicit
    disjoint or overlapping intervals; union by assignment, never fill gaps.
    """
    height, segments, ids, dem = (inputs[k] for k in ("height","segments","ids","dem"))
    require(dem.ndim == 2 and dem.size and height.shape == ids.shape == segments.shape == dem.shape,
            "input shapes differ")
    require(dem.dtype == height.dtype == np.dtype("float64") and ids.dtype.kind in "iu"
            and segments.dtype == object, "invalid input dtype")
    require(np.isfinite(dem).all() and np.isfinite(height).all() and (height >= 0).all()
            and (ids >= 0).all(), "nonfinite/invalid input values")
    require(dem.size <= 4096 and np.max(ids) <= 4096, "synthetic profile size exceeded")
    effective, d0 = effective_ground(ids, dem)
    relative = effective-d0
    ground = np.empty(ids.shape, dtype=int)
    intervals, errors = [], []
    capacity = math.ceil(float(np.max(height+relative)))+1
    require(isinstance(max_levels,int) and 0 < capacity <= max_levels, "Z capacity exceeds explicit limit")
    for index in np.ndindex(ids.shape):
        value = float(np.float32(relative[index])) if numba else float(relative[index])
        g = math.floor(value+.5)+1
        ground[index] = g
        require(g <= capacity, "surface outside Z capacity")
        cell = segments[index]
        require(isinstance(cell,list) and bool(cell) == bool(ids[index]), "owner/segment support mismatch")
        highest = 0.
        for pair in cell:
            require(isinstance(pair,(list,tuple)) and len(pair)==2, "invalid segment pair")
            low, high = pair
            require(all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
                        for v in pair) and 0 <= low < high, "invalid interval bounds")
            highest = max(highest,high)
            # For nonnegative values int(x+.5) is floor(x+.5), not ties-to-even.
            start, stop = g+math.floor(low+.5), g+math.floor(high+.5)
            require(start < stop, "interval vanishes after rounding")
            require(stop <= capacity, "segment clipped by Z capacity")
            intervals.append(dict(cell_index=list(index), low=low, high=high, start=start, stop=stop))
            errors.append(d0+stop-(float(effective[index])+high))
        require(height[index] == highest, "height_grid and maximum segment high differ")
    expected = np.zeros((*ids.shape,capacity),dtype=np.int8)
    for index in np.ndindex(ids.shape):
        g = ground[index]
        expected[index][:g-1] = -1
        expected[index][g-1] = 1
    for row in intervals:
        expected[tuple(row["cell_index"])][row["start"]:row["stop"]] = -3
    return expected, dict(d0=float(d0), effective_ground=effective.tolist(),
                          ground_index=(ground-1).tolist(), first_building_anchor=ground.tolist(),
                          capacity=capacity, integer_intervals=intervals,
                          segment_upper_edge_minus_top_z_m=errors,
                          maximum_absolute_upper_edge_error_m=max(map(abs,errors),default=0.))


def execute(inputs, *, max_levels=512):
    """Pinned public API + independent oracle, immutable copied API arguments."""
    from voxcity.generator import voxelizer as engine
    from voxcity.geoprocessor.raster import process_grid
    import numba

    provenance = voxcity_provenance()
    require(provenance["verified"] and engine.NUMBA_AVAILABLE, "pinned Numba engine not established")
    require(inputs["metadata"]["profile"] == PROFILE, "unknown experimental profile")
    metadata = inputs["metadata"]
    if metadata.get("input_kind") == "derived":
        rebuilt = prepare(metadata["derived"], inputs["dem"], method=metadata["method"],
                          datum=metadata["datum"], representative_tops=metadata["representative_tops"],
                          owners={tuple(r["cell_index"]):r["source_id"] for r in metadata["explicit_owner_choices"]})
        require(input_identity(rebuilt) == input_identity(inputs), "Derived-to-engine input identity mismatch")
    else:
        require(metadata.get("input_kind") == "explicit_interval_fixture"
                and metadata.get("provenance"), "unknown input state/provenance")
    expected, qa = occupancy_oracle(inputs, numba=True, max_levels=max_levels)
    before = input_identity(inputs)
    ids, dem = inputs["ids"], inputs["dem"]
    # Verify the owner-ground formula against the pinned helper independently
    # of occupancy; float32 ground must also agree exactly at rounding boundaries.
    actual_ground = process_grid(ids.copy(), dem.copy()-float(dem.min()))
    independent_ground = np.asarray(qa["effective_ground"])-qa["d0"]
    require(np.allclose(actual_ground,independent_ground,rtol=0,atol=1e-10)
            and np.array_equal(actual_ground.astype("float32"),independent_ground.astype("float32")),
            "engine/independent effective ground mismatch")
    previous_threads = numba.get_num_threads()
    args = [deepcopy(inputs[k]) for k in ("height","segments","ids")]
    args += [np.ones(ids.shape,dtype=int),dem.copy(),np.zeros(ids.shape)]
    api_before = [array_identity(a) if a.dtype != object else digest(a.tolist()) for a in args]
    try:
        numba.set_num_threads(2)
        voxels = engine.Voxelizer(1.,"Standard").generate_combined(*args,print_class_info=False)
    finally:
        numba.set_num_threads(previous_threads)
    require(before == input_identity(inputs), "adapter inputs changed during execution")
    require(api_before == [array_identity(a) if a.dtype != object else digest(a.tolist()) for a in args],
            "Voxelizer mutated its input arrays")
    require(voxels.dtype == np.int8 and np.array_equal(voxels,expected), "public Voxelizer/oracle mismatch")
    require((voxels == -3).any(), "no building voxels generated")
    qa.update(status="PASS_SYNTHETIC_ONLY", shape=list(voxels.shape),
              class_counts={str(v):int((voxels==v).sum()) for v in (-3,-1,0,1)},
              input_unchanged=True, public_api_arguments_unchanged=True)
    return dict(voxels=voxels, qa=qa, inputs=inputs, input_identity=before,
                voxels_identity=array_identity(voxels), engine=provenance,
                runtime=dict(python=platform.python_version(), numpy=version("numpy"),
                             numba=version("numba"), shapely=version("shapely"),
                             threads=2, voxel_size_m=1., land_cover_source="Standard",
                             public_api="voxcity.generator.voxelizer.Voxelizer.generate_combined"))


def explicit_intervals(dem, ids, segments, height, *, provenance):
    """Independent authored occupancy fixture, never inferred from top-only data."""
    dem = np.array(dem,dtype=np.float64,copy=True)
    ids = np.array(ids,copy=True)
    packed = np.empty(dem.shape,dtype=object)
    require(len(segments)==dem.shape[0] and all(len(r)==dem.shape[1] for r in segments),
            "explicit segment shape differs")
    for index in np.ndindex(dem.shape):
        packed[index] = deepcopy(segments[index[0]][index[1]])
    return dict(dem=dem,ids=ids,segments=packed,height=np.array(height,dtype=np.float64,copy=True),
                metadata=dict(profile=PROFILE,input_kind="explicit_interval_fixture",provenance=provenance,
                              datum="arbitrary synthetic datum; not T.P.",voxel_size_m=1.))


def input_identity(inputs):
    return dict(arrays={k:array_identity(inputs[k]) for k in ("height","ids","dem")},
                segments_sha256=digest(inputs["segments"].tolist()), metadata_sha256=digest(inputs["metadata"]))


def save_result(path, result):
    """New directory only; manifest is last, after byte/array reread QA."""
    path = Path(path)
    require(result["input_identity"] == input_identity(result["inputs"])
            and result["voxels_identity"] == array_identity(result["voxels"]), "result changed before save")
    path.mkdir(parents=True,exist_ok=False)
    outputs = {}
    arrays = {k:result["inputs"][k] for k in ("height","ids","dem")}
    arrays.update(voxels=result["voxels"],effective_ground=np.array(result["qa"]["effective_ground"]))
    for name,array in arrays.items():
        file = path/(name+".npy")
        np.save(file,array,allow_pickle=False)
        require(np.array_equal(np.load(file,allow_pickle=False),array), "saved array reread differs")
        outputs[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    for name,value in dict(segments=result["inputs"]["segments"].tolist(),
                           metadata=result["inputs"]["metadata"],qa=result["qa"]).items():
        file = path/(name+".json")
        file.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        require(digest(json.loads(file.read_text(encoding="utf-8")))==digest(value), "saved JSON reread differs")
        outputs[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    implementation = {name:hashlib.sha256(Path(file).read_bytes()).hexdigest() for name,file in
                      dict(adapter=__file__, distribution=distribution.__file__,
                           grid=distribution.GridSpec.metadata.__code__.co_filename,
                           effective_ground=effective_ground.__code__.co_filename,
                           engine_provenance=voxcity_provenance.__code__.co_filename).items()}
    manifest = dict(profile=PROFILE,status="COMPLETED_SYNTHETIC_ONLY", input_identity=result["input_identity"],
                    engine=result["engine"], runtime=result["runtime"], outputs=outputs,
                    implementation_sha256=implementation,
                    terrain_integration_ready=False, scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED")
    (path/"manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return manifest


def demonstration_run(path):
    """Reuse STEP 3-A's exact authored cases; independent comparisons, new run."""
    path = Path(path)
    path.mkdir(parents=True,exist_ok=False)
    summary, unexpected = {}, []
    expected_rejections = {("roof_hole","centre"),("roof_hole","cell_max"),("thin_eave","centre")}
    for name,case in distribution.demonstration()["cases"].items():
        results, rows = {}, {}
        for method in ("representative","centre","cell_max"):
            derived = case["derived_cell_max" if method=="cell_max" else "derived_centre"]
            grid = derived["grid"]
            dem = np.full((grid["height"],grid["width"]),2.)
            tops = {s["source_id"]:case["representative_absolute_z"] for s in derived["source_provenance"]}
            try:
                inputs = prepare(derived,dem,method=method,datum=derived["procedure"]["vertical_datum"],
                                 representative_tops=tops if method=="representative" else None)
                result = execute(inputs)
            except Blocked as exc:
                rows[method] = dict(status="BLOCKED",reason=str(exc))
                if (name,method) not in expected_rejections or "TOP_UNKNOWN" not in str(exc):
                    unexpected.append([name,method,str(exc)])
                continue
            require((name,method) not in expected_rejections, "unknown roof unexpectedly accepted")
            manifest = save_result(path/name/method,result)
            rows[method] = dict(status="PASS_SYNTHETIC_ONLY",qa=result["qa"],outputs=manifest["outputs"])
            results[method] = result["voxels"]
        comparisons = {}
        for a,b in (("representative","centre"),("representative","cell_max"),("centre","cell_max")):
            if a not in results or b not in results:
                continue
            va,vb = results[a],results[b]
            depth = max(va.shape[2],vb.shape[2])
            aa=np.pad(va== -3,((0,0),(0,0),(0,depth-va.shape[2])))
            bb=np.pad(vb== -3,((0,0),(0,0),(0,depth-vb.shape[2])))
            comparisons[a+"_vs_"+b] = dict(differing_voxels=int((aa!=bb).sum()),
                                            differing_columns=int(np.any(aa!=bb,axis=2).sum()))
        summary[name] = dict(methods=rows, comparisons=comparisons)
    # These intervals are authored occupancy fixtures, not inferred roof solids.
    fixtures = {
        "owner_ground":explicit_intervals([[10,14,13]],[[1,1,0]],[[[[0,8]],[[0,8]],[]]],[[8,8,0]],
                                          provenance="explicit owner mean ground fixture"),
        "disjoint":explicit_intervals([[10]],[[1]],[[[[0,2],[4,6]]]],[[6]],
                                      provenance="explicit two occupied intervals with AIR gap"),
        "mixed_heights":explicit_intervals([[2,4]],[[1,2]],[[[[0,2]],[[0,20]]]],[[2,20]],
                                           provenance="explicit high/low building and DEM fixture"),
    }
    fixture_results = {}
    for name,inputs in fixtures.items():
        result = execute(inputs)
        manifest = save_result(path/"explicit"/name,result)
        fixture_results[name] = dict(qa=result["qa"],outputs=manifest["outputs"])
    report=dict(profile=PROFILE,status="BLOCKED" if unexpected else "PASS_SYNTHETIC_ONLY",cases=summary,
                explicit_interval_fixtures=fixture_results,unexpected_failures=unexpected,
                expected_input_rejections=[list(v) for v in sorted(expected_rejections)],
                terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED")
    file = path/"comparison.json"
    file.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    if not unexpected:
        manifests = {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(path.rglob("manifest.json"))}
        manifests[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
        (path/"manifest.json").write_text(json.dumps(dict(profile=PROFILE,status="COMPLETED_SYNTHETIC_ONLY",
            outputs=manifests,terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",
            formal_acceptance="NOT_VERIFIED"),sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,required=True)
    args=parser.parse_args()
    demonstration_run(args.run_dir)


if __name__ == "__main__":
    main()
