"""STEP 3-C: bounded synthetic three-height Solar/Shadow comparison, no trees."""
from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform

import numpy as np
from pyproj import Geod, Proj, Transformer
from shapely.geometry import box

from ouem import synthetic_height_distribution as d
from ouem import synthetic_height_voxel as v
from ouem import candidate_b_shadow as shadow
from ouem.b2_gvi import observers, roi_window  # geometry only; no GVI execution

PROFILE = "ouem-synthetic-distributed-height-solar-shadow/v0.1"
METHODS = ("representative", "centre", "cell_max")
SETTINGS = dict(azimuth_true_deg=180., elevation_deg=45., dni_W_m2=800.,
                binary_requested_height_m=0., solar_requested_height_m=1.5,
                tree_k=.6, tree_lad=1., include_building_roofs=False,
                irradiance_tolerance_W_m2=1e-9, threads=2)


def flip(array):
    """Explicit north-up <-> engine south-up I/O boundary; never change azimuth."""
    from voxcity.utils.orientation import ensure_orientation
    return np.ascontiguousarray(ensure_orientation(array, "north_up", "south_up"))


def scene(name):
    """Three authored roofs with 10 m clear margin around one 4x4 m building."""
    grid = d.GridSpec((-12.,-12.,12.,12.))
    def face(identifier, bounds, z):
        return d.Face(identifier,(tuple((x,y,z(x,y)) for x,y in box(*bounds).exterior.coords),))
    if name == "flat":
        faces, top = [face("flat",(-2,-2,2,2),lambda x,y:8.)], 8.
    elif name == "slope":
        # .05 makes the public allocation genuinely differ from centre without
        # changing the hand-audited integer roof endpoints of this small scene.
        faces, top = [face("slope",(-2,-2,2,2),lambda x,y:9.05-.75*(y+2))], 9.05
    elif name == "step":
        faces = [face("north-low",(-2,.25,2,2),lambda x,y:6.),
                 face("south-high",(-2,-2,2,.25),lambda x,y:9.)]
        top = 9.
    else:
        raise v.Blocked("unknown authored scene")
    building = d.Building("synthetic-building",box(-2,-2,2,2),tuple(faces),"STEP 3-C authored synthetic roof")
    xy = np.stack(grid.centres(),axis=-1)
    roi = (xy[...,0]>=-6)&(xy[...,0]<6)&(xy[...,1]>=2)&(xy[...,1]<10)
    return dict(grid=grid, buildings=[building], dem=np.full((24,24),2.), top=top, roi=roi)


def axis_audit(grid):
    """Declared local true-north frame at EPSG:6677 natural origin, no correction.

    Geographic bearing/convergence are diagnostics, not an automatic rotation.
    Only the small symmetric origin-centred synthetic grid is authorized here.
    """
    v.require(tuple(grid.bounds)==(-12.,-12.,12.,12.) and grid.resolution==1., "unsupported synthetic frame")
    transform = Transformer.from_crs(6677,4326,always_xy=True)
    geod = Geod(ellps="WGS84")
    south, north = transform.transform(0,-12), transform.transform(0,12)
    bearing = geod.inv(*south,*north)[0]
    corners = [transform.transform(x,y) for x,y in ((-12,-12),(-12,12),(12,-12),(12,12))]
    convergence = [float(Proj(6677).get_factors(lon,lat).meridian_convergence) for lon,lat in corners]
    v.require(abs(bearing)<1e-9 and max(map(abs,convergence))<.001, "true/grid north frame not verified")
    return dict(input_axes=["south","east","up"], api_axes=["north","east","up"],
                conversion="explicit axis-0 reflection of all grids/voxels; inverse reflection of outputs",
                grid_metadata_crs="EPSG:6677", bounds=list(grid.bounds), meshsize_m=1.,
                reference_xy=[0.,0.], reference_lonlat=list(transform.transform(0,0)),
                axis0_api_reference_true_bearing_deg=bearing, api_rotation_angle_deg=0.,
                corner_meridian_convergence_deg=convergence, maximum_convergence_tolerance_deg=.001,
                limitation="fixed synthetic tangent-frame sun at natural origin; no per-cell geographic correction")


def solar_direction(azimuth=180.,elevation=45.):
    from voxcity.utils.orientation import direction_to_axis_vector
    direction = np.asarray(direction_to_axis_vector(azimuth,elevation,0.),dtype=float)
    az,el=math.radians(azimuth),math.radians(elevation)
    independent=np.array([math.cos(el)*math.cos(az),math.cos(el)*math.sin(az),math.sin(el)])
    v.require(np.allclose(direction,independent,rtol=0,atol=1e-12), "sun direction mismatch")
    return tuple(direction)


def shared_models(results):
    """Only extend audited public-Voxelizer outputs with AIR, never repair inputs."""
    v.require(set(results)==set(METHODS), "three methods required")
    base=results["representative"]
    identity=base["inputs"]["metadata"]
    nz=max(r["voxels"].shape[2] for r in results.values())
    models,qa={},{}
    for method,result in results.items():
        a,b=result["inputs"],base["inputs"]
        meta=a["metadata"]
        v.require(result["qa"]["status"]=="PASS_SYNTHETIC_ONLY"
                  and v.input_identity(a)==result["input_identity"]
                  and v.array_identity(result["voxels"])==result["voxels_identity"], "unaudited or changed voxel result")
        v.require(meta["grid_identity"]==identity["grid_identity"]
                  and meta["derived"]["source_identity"]==identity["derived"]["source_identity"]
                  and meta["source_owner_mapping"]==identity["source_owner_mapping"]
                  and meta["explicit_owner_choices"]==identity["explicit_owner_choices"]
                  and result["qa"]["d0"]==base["qa"]["d0"]
                  and result["qa"]["effective_ground"]==base["qa"]["effective_ground"]
                  and np.array_equal(a["dem"],b["dem"]) and np.array_equal(a["ids"],b["ids"]),
                  "scene/grid/source/DEM/owner/D0 mismatch")
        vox=result["voxels"]
        v.require(not np.any(vox==-2) and np.array_equal(np.any(vox==-3,axis=2),a["ids"]>0), "TREE or footprint mismatch")
        padded=np.pad(vox,((0,0),(0,0),(0,nz-vox.shape[2])),constant_values=0)
        v.require(np.array_equal(padded[:,:,:vox.shape[2]],vox) and not padded[:,:,vox.shape[2]:].any(), "AIR extension changed base")
        models[method]=padded
        qa[method]=dict(original_shape=list(vox.shape),shared_shape=list(padded.shape),
                        air_layers_added=nz-vox.shape[2], original_layers_unchanged=True,
                        original_identity=v.array_identity(vox),shared_identity=v.array_identity(padded))
    for vox in models.values():
        v.require(np.array_equal(vox==-1,models["representative"]==-1)
                  and np.array_equal(vox==1,models["representative"]==1), "ground/surface changed")
    return models,qa


def common_observers(models, grid, d0, effective_ground, *, experiments=(("binary",0.),("solar",1.5))):
    xy=np.stack(grid.centres(),axis=-1)
    output={}
    for experiment,height in experiments:
        common=None
        for vox in models.values():
            index,valid,origin=observers(vox,height=height)
            surface=np.argmax(vox==1,axis=2)
            building=np.any(vox==-3,axis=2)
            v.require(np.array_equal(valid,~building) and valid.any()
                      and np.array_equal(index[valid],(surface+1+int(height))[valid])
                      and np.all(origin[valid]==0), "observer moved, excluded or inside building")
            # Invalid coordinates are explicitly NaN; index=-1 from B2 diagnostic.
            xyz=np.concatenate((xy,(d0+index+.5)[...,None]),axis=-1)
            xyz[~valid]=np.nan
            now=dict(index=index,valid=valid,xyz=xyz,surface=surface)
            if common is not None:
                v.require(all(np.array_equal(now[k],common[k],equal_nan=True) for k in now), "model observers differ")
            common=now
        common["requested_height_m"]=height
        common["actual_height_above_effective_ground_m"]=(common["xyz"][...,2]-effective_ground)
        output[experiment]=common
    return output


def direct_solar(voxels, inputs, grid, *, azimuth=180., elevation=45.):
    """Minimal projected-grid boundary to the same B1 public API, no new engine."""
    from voxcity.models import VoxCity, VoxelGrid, GridMetadata, BuildingGrid, LandCoverGrid, DemGrid, CanopyGrid
    from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
    meta=GridMetadata("EPSG:6677",tuple(grid.bounds),1.)
    engine_vox=flip(voxels)
    empty=np.zeros(voxels.shape[:2])
    args=VoxCity(VoxelGrid(engine_vox,meta),
        BuildingGrid(flip(inputs["height"]),deepcopy(flip(inputs["segments"])),flip(inputs["ids"]),meta),
        LandCoverGrid(np.ones(empty.shape,dtype=int),meta),DemGrid(flip(inputs["dem"]),meta),
        CanopyGrid(empty.copy(),meta,bottom=empty.copy()),extras={"rotation_angle":0.})
    def identity():
        arrays=dict(voxels=engine_vox,height=args.buildings.heights,ids=args.buildings.ids,
                    dem=args.dem.elevation,land_cover=args.land_cover.classes,
                    canopy_top=args.tree_canopy.top,canopy_bottom=args.tree_canopy.bottom)
        return dict(arrays={k:v.array_identity(a) for k,a in arrays.items()},
                    segments=v.digest(args.buildings.min_heights.tolist()),
                    grid=[meta.crs,list(meta.bounds),meta.meshsize],extras=deepcopy(args.extras))
    before=identity()
    values=get_direct_solar_irradiance_map(args,azimuth,elevation,SETTINGS["dni_W_m2"],show_plot=False,
        view_point_height=1.5,include_building_roofs=False,tree_k=.6,tree_lad=1.)
    v.require(before==identity(),"public Solar API changed inputs")
    return flip(values)


def evaluate(voxels,inputs,grid,*,azimuth=180.,binary_only=False,binary_direction=None):
    import numba
    before=v.array_identity(voxels),v.input_identity(inputs)
    v.require(binary_direction is None or binary_only, "explicit binary direction requires binary-only evaluation")
    valid=inputs["ids"]==0
    prior=numba.get_num_threads()
    try:
        numba.set_num_threads(2)
        direction=solar_direction(azimuth) if binary_direction is None else binary_direction
        binary=flip(shadow.calculate(flip(voxels),flip(valid),direction))
        solar=None if binary_only else direct_solar(voxels,inputs,grid,azimuth=azimuth)
    finally:
        numba.set_num_threads(prior)
    v.require(before==(v.array_identity(voxels),v.input_identity(inputs)),"calculation changed original inputs")
    if binary_only:
        return dict(binary=binary)
    ceiling=SETTINGS["dni_W_m2"]*math.sin(math.radians(45.))
    v.require(binary.shape==solar.shape==valid.shape and solar.dtype==np.float64
              and np.array_equal(np.isfinite(solar),valid) and np.isnan(solar[~valid]).all()
              and (solar[valid]>=0).all() and (solar[valid]<=ceiling+1e-9).all()
              and np.all(np.isclose(solar[valid],0,rtol=0,atol=1e-9)|np.isclose(solar[valid],ceiling,rtol=0,atol=1e-9)),
              "invalid horizontal direct irradiance/mask/range")
    return dict(binary=binary,solar=solar)


def cardinal_geometry_check(grid,*,binary_only=False):
    """Independent hand geometry for ONE flat prism, four cardinal sun positions.

    At 45 degrees the tangent north shadow limit is y=2+(roof_edge-observer_Z).
    Touch-only rays at that limit do not traverse positive building volume.
    This diagnostic is not an alternative ray tracer or scene engine.
    """
    sample=scene("flat")
    derived=d.derive(grid,sample["buildings"],method="centre")
    inputs=v.prepare(derived,sample["dem"],method="centre",datum=derived["procedure"]["vertical_datum"])
    result=v.execute(inputs)
    x,y=grid.centres()
    checks=[]
    for azimuth,downwind,across in ((180.,y,x),(0.,-y,x),(90.,-x,y),(270.,x,y)):
        maps=evaluate(result["voxels"],inputs,grid,azimuth=azimuth,binary_only=binary_only)
        for key,limit,expected_count in (("binary",7.5,20),("solar",6.5,16)):
            if key not in maps:
                continue
            expected=(abs(across)<2)&(downwind>2)&(downwind<limit-1e-9)
            actual=(maps[key]==0)&(inputs["ids"]==0)
            v.require(expected.sum()==expected_count and np.array_equal(actual,expected), "cardinal geometric shadow mismatch")
            checks.append(dict(azimuth_true_deg=azimuth,experiment=key,shadow_cells=int(actual.sum()),
                               tangent_limit_m=limit,independent_geometry="PASS"))
    return checks


def statistics(maps,valid,region):
    use=valid&region
    v.require(use.any(),"ROI has no non-building observers")
    result=dict(observers=int(use.sum()),binary=shadow.counts(maps["binary"],region))
    if "solar" in maps:
        values=maps["solar"][use]
        result["solar"]=dict(mean_W_m2=float(values.mean()),minimum_W_m2=float(values.min()),
                              maximum_W_m2=float(values.max()),zero_cells=int((values==0).sum()))
    return result


def compare_maps(a,b,valid,region):
    use=valid&region
    x,y=a["binary"][use],b["binary"][use]
    result=dict(binary_changed=int((x!=y).sum()),shadow_to_sun=int(((x==0)&(y==1)).sum()),
                sun_to_shadow=int(((x==1)&(y==0)).sum()))
    if "solar" in a and "solar" in b:
        delta=b["solar"][use]-a["solar"][use]
        result.update(solar_changed=int((abs(delta)>1e-9).sum()),solar_increased=int((delta>1e-9).sum()),
                      solar_decreased=int((delta< -1e-9).sum()),mean_delta_W_m2=float(delta.mean()),
                      minimum_delta_W_m2=float(delta.min()),maximum_delta_W_m2=float(delta.max()))
    return result


def calculate_scene(sample,*,binary_only=False):
    grid=sample["grid"]
    axis=axis_audit(grid)
    v.require(all(box(*grid.bounds).covers(b.footprint) for b in sample["buildings"]),"building outside domain")
    results={}
    for method in METHODS:
        derived=d.derive(grid,sample["buildings"],method="cell_max" if method=="cell_max" else "centre")
        inputs=v.prepare(derived,sample["dem"],method=method,datum=derived["procedure"]["vertical_datum"],
                         representative_tops={b.source_id:sample["top"] for b in sample["buildings"]}
                         if method=="representative" else None)
        # This comparison profile rejects competing sources, even explicit choices.
        v.require(all(c["building_count"]<=1 for c in derived["cells"]),"overlapping scene is unsupported")
        results[method]=v.execute(inputs)
    models,capacity=shared_models(results)
    base=results["representative"]
    observation=common_observers(models,grid,base["qa"]["d0"],np.array(base["qa"]["effective_ground"]))
    valid=observation["solar"]["valid"]
    v.require(np.array_equal(valid,observation["binary"]["valid"])
              and not (sample["roi"]&~valid).any(),"ROI/observer mismatch")
    maps={}
    for method in METHODS:
        maps[method]=evaluate(models[method],results[method]["inputs"],grid,binary_only=binary_only)
        original=results[method]["voxels"]
        if original.shape!=models[method].shape:
            control=evaluate(original,results[method]["inputs"],grid,binary_only=binary_only)
            v.require(all(np.array_equal(control[k],maps[method][k],equal_nan=True) for k in control),
                      "original/common Z capacity changed evaluation")
        capacity[method]["original_vs_shared_evaluation"]="PASS"
    extra=evaluate(np.pad(models["representative"],((0,0),(0,0),(0,3))),base["inputs"],grid,binary_only=binary_only)
    v.require(all(np.array_equal(extra[k],maps["representative"][k],equal_nan=True) for k in extra),
              "extra AIR changed evaluation")
    regions=dict(domain=np.ones(valid.shape,dtype=bool),roi=sample["roi"])
    stats={m:{name:statistics(maps[m],valid,r) for name,r in regions.items()} for m in METHODS}
    comparisons={a+"_to_"+b:{name:compare_maps(maps[a],maps[b],valid,r) for name,r in regions.items()}
                 for a,b in (("representative","centre"),("representative","cell_max"),("centre","cell_max"))}
    edge=max(r["qa"]["d0"]+max(s["stop"] for s in r["qa"]["integer_intervals"]) for r in results.values())
    lowest=float(observation["binary"]["xyz"][...,2][valid].min())
    return dict(results=results,models=models,maps=maps,observation=observation,axis=axis,
                capacity=capacity,statistics=stats,comparisons=comparisons,
                valid=valid,roi=sample["roi"],grid=grid,
                context=dict(domain_bounds=list(grid.bounds),roi_bounds=[-6.,2.,6.,10.],
                             building_to_domain_margin_m=10.,highest_occluder_edge_z=edge,
                             lowest_observer_z=lowest,maximum_45deg_reach_m=max(0.,edge-lowest),
                             outside_domain="synthetic open space; unknown external occluders not modelled",
                             calculation_order="full domain rays, then ROI extraction"))


def run(output):
    """New run; preserve binary artifacts if direct API later fails, no false PASS."""
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    report=dict(profile=PROFILE,status="BLOCKED",binary_shadow="NOT_VERIFIED",direct_solar="NOT_VERIFIED",
                terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED")
    try:
        geometry=cardinal_geometry_check(scene("flat")["grid"],binary_only=True)
        cached={}
        for name in ("flat","slope","step"):
            sample=scene(name)
            result=calculate_scene(sample,binary_only=True)
            if name=="flat":
                v.require(all(not c[r]["binary_changed"]
                              for c in result["comparisons"].values() for r in ("domain","roi")),"flat models differ")
            root=output/name
            root.mkdir()
            for method in METHODS:
                v.save_result(root/method/"voxelizer",result["results"][method])
                for metric,array in dict(shared_voxels=result["models"][method],**result["maps"][method]).items():
                    save_array(root/method/(metric+".npy"),array)
                r0,r1,c0,c1=roi_window(result["roi"])
                save_array(root/method/"roi_binary.npy",result["maps"][method]["binary"][r0:r1,c0:c1])
            for experiment,obs in result["observation"].items():
                for key in ("index","valid","xyz","surface","actual_height_above_effective_ground_m"):
                    save_array(root/(experiment+"_observer_"+key+".npy"),obs[key])
            save_array(root/"roi.npy",result["roi"])
            save_array(root/"centres_xy.npy",np.stack(result["grid"].centres(),axis=-1))
            cached[name]=result
        report.update(binary_shadow="PASS",direct_solar="BLOCKED",settings=SETTINGS,geometry_qa=geometry)
        binary_report=dict(report,scenes={name:dict(statistics=r["statistics"],comparisons=r["comparisons"],
            axis=r["axis"],capacity=r["capacity"],context=r["context"]) for name,r in cached.items()})
        binary_report.update(status="BINARY_PASS_DIRECT_NOT_VERIFIED",direct_solar="NOT_VERIFIED")
        write_json(output/"binary_report.json",binary_report)
        # Binary artifacts for every scene are now durable, independently of Solar.
        geometry=cardinal_geometry_check(scene("flat")["grid"])
        summaries={}
        for name,result in cached.items():
            root=output/name
            for method in METHODS:
                pair=evaluate(result["models"][method],result["results"][method]["inputs"],result["grid"])
                v.require(np.array_equal(pair["binary"],result["maps"][method]["binary"]),"binary changed during Solar phase")
                result["maps"][method]["solar"]=pair["solar"]
                original=result["results"][method]["voxels"]
                if original.shape!=result["models"][method].shape:
                    check=evaluate(original,result["results"][method]["inputs"],result["grid"])
                    v.require(np.array_equal(check["solar"],pair["solar"],equal_nan=True),"Solar changed with Z padding")
                save_array(root/method/"solar.npy",pair["solar"])
                r0,r1,c0,c1=roi_window(result["roi"])
                save_array(root/method/"roi_solar.npy",pair["solar"][r0:r1,c0:c1])
            base=result["results"]["representative"]
            extra=evaluate(np.pad(result["models"]["representative"],((0,0),(0,0),(0,3))),
                           base["inputs"],result["grid"])
            v.require(np.array_equal(extra["solar"],result["maps"]["representative"]["solar"],equal_nan=True),
                      "extra AIR changed Solar")
            regions=dict(domain=np.ones(result["valid"].shape,dtype=bool),roi=result["roi"])
            stats={m:{k:statistics(result["maps"][m],result["valid"],r) for k,r in regions.items()} for m in METHODS}
            comparisons={a+"_to_"+b:{k:compare_maps(result["maps"][a],result["maps"][b],result["valid"],r)
                         for k,r in regions.items()} for a,b in
                         (("representative","centre"),("representative","cell_max"),("centre","cell_max"))}
            if name=="flat":
                v.require(all(not c[r]["solar_changed"] for c in comparisons.values() for r in regions),"flat Solar models differ")
            for a,b in (("representative","centre"),("representative","cell_max"),("centre","cell_max")):
                save_array(root/(a+"_to_"+b+"_solar_delta.npy"),result["maps"][b]["solar"]-result["maps"][a]["solar"])
            summaries[name]=dict(axis=result["axis"],capacity=result["capacity"],statistics=stats,
                                 comparisons=comparisons,context=result["context"],binary_shadow="PASS",direct_solar="PASS",
                                 invariants=dict(grid_DEM_owner_footprint_ground_surface_D0="PASS",no_TREE="PASS",
                                     common_observer_indices_mask_XYZ="PASS",input_and_api_array_immutability="PASS",
                                     common_and_additional_AIR_capacity="PASS",
                                     D0=result["results"]["representative"]["qa"]["d0"],
                                     original_and_shared_after={m:dict(
                                         original=v.array_identity(result["results"][m]["voxels"]),
                                         shared=v.array_identity(result["models"][m])) for m in METHODS}))
        report.update(status="COMPLETED_SYNTHETIC_ONLY",binary_shadow="PASS",direct_solar="PASS",
                      settings=SETTINGS,geometry_qa=geometry,scenes=summaries,
                      runtime=dict(python=platform.python_version(),**{k:version(k) for k in ("numpy","numba","pyproj","voxcity")}),
                      implementations={Path(f).name:hashlib.sha256(Path(f).read_bytes()).hexdigest()
                          for f in (__file__,d.__file__,v.__file__,shadow.__file__,observers.__code__.co_filename)})
        write_json(output/"report.json",report)
        outputs={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(output.rglob("*")) if p.is_file()}
        write_json(output/"manifest.json",dict(profile=PROFILE,status=report["status"],outputs=outputs,
            terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED"))
    except Exception as exc:
        report.update(status="BLOCKED",error=f"{type(exc).__name__}: {exc}")
        write_json(output/"failure.json",report)
    return report


def save_array(path,array):
    np.save(path,array,allow_pickle=False)
    v.require(np.array_equal(np.load(path,allow_pickle=False),array,equal_nan=True),"saved array reread differs")


def write_json(path,value):
    v.require(not path.exists(),"output JSON already exists")
    temporary=path.with_name("."+path.name+".tmp")
    with temporary.open("x",encoding="utf-8") as stream:
        stream.write(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
    readback=json.loads(temporary.read_text(encoding="utf-8"))
    v.require(v.digest(readback)==v.digest(value),"saved JSON differs")
    temporary.rename(path)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,required=True)
    report=run(parser.parse_args().run_dir)
    print(report["status"],report.get("error","binary PASS / direct PASS"))
    return int(report["status"]!="COMPLETED_SYNTHETIC_ONLY")


if __name__=="__main__":
    raise SystemExit(main())
