"""STEP 4-C: max-roof representative versus distributed real roofs, binary shadow only."""
from copy import deepcopy
import math
from pathlib import Path

import numpy as np
from pyproj import Geod, Transformer

from ouem import real_roof_terrain_voxel as terrain
from ouem import synthetic_height_solar as shared

roof, voxel, consumer = terrain.roof, terrain.voxel, terrain.consumer
require = voxel.require
PROFILE = "ouem-real-lod2-representative-distributed-shadow/v0.1"
BASELINE = "69d7cd286da76dc1e3f6f9c780d4407525ca23d9"
B2_SHA = "9f564e7d2e06c74301fdcf3670d6f60e2a531e628cfb36de882d8dec6f286817"
B2_REPORT_SHA = "20cf80af2f915a8eea3aca2432ffa23f938fc9c2485be5c276adcce4739cea7b"
METHODS = ("representative", "distributed")
SETTINGS = dict(azimuth_true_deg=180., elevation_deg=45., requested_observer_height_m=0.,
                occluders="BUILDING only", omitted_context="all surrounding buildings omitted", tree="none")
DIFFERENCE_CODES = dict(excluded=0,common_sun=1,common_shadow=2,representative_only_shadow=3,distributed_only_shadow=4)


def axis(grid):
    """Candidate B true-bearing convention applied to this projected north-up scene."""
    from voxcity.utils.orientation import direction_to_axis_vector
    tx, geod = Transformer.from_crs(6677,4326,always_xy=True), Geod(ellps="WGS84")
    x0,y0,x1,y1 = grid.bounds
    x,y = (x0+x1)/2,(y0+y1)/2
    origin = tx.transform(x,y)
    bearing = geod.inv(*origin,*tx.transform(x,y+10))[0]
    east = geod.inv(*origin,*tx.transform(x+10,y))[0]
    require(abs((east-bearing-90+180)%360-180)<.01, "nonorthogonal projected axes")
    corners = [geod.inv(*tx.transform(a,b),*tx.transform(a,b+10))[0] for a,b in ((x0,y0),(x0,y1),(x1,y0),(x1,y1))]
    angle = math.radians(180-bearing)
    expected = np.array([math.cos(angle),math.sin(angle),1.])/math.sqrt(2)
    direction = np.asarray(direction_to_axis_vector(180.,45.,bearing),dtype=float)
    require(np.allclose(direction,expected,rtol=0,atol=1e-12) and direction[0]<0, "true-azimuth mapping differs")
    return tuple(direction), dict(grid_north_true_bearing_deg=bearing, corner_bearing_range_deg=terrain.span(corners),
        projection="EPSG:6677", input_axes=["south","east","up"], kernel_axes=["north","east","up"],
        conversion="axis-0 reflection on inputs and outputs; true azimuth unchanged; subtract recorded grid bearing",
        direction_north_east_up=direction.tolist(), approximation="one local grid bearing per small scene; no per-cell correction")


def scene(item, dem_path, bounds):
    import rasterio
    source = item["inputs"]["metadata"]["source"]
    original = roof.geometry.GridSpec(tuple(source["grid"]["bounds"]))
    with rasterio.open(dem_path) as src:
        minimum = float(src.read(1,masked=True).min())
    top = item["maps"]["top"]
    maximum = float(np.nanmax(top))
    # Conservative 45-degree reach: roof minus lowest available DEM, plus
    # discretization allowance and two whole cells of clear context.
    margin = math.ceil(maximum-minimum+2)+2
    x0,y0,x1,y1 = original.bounds
    extended = (max(bounds[0],x0-margin),max(bounds[1],y0-margin),min(bounds[2],x1+margin),min(bounds[3],y1+margin))
    grid = roof.geometry.GridSpec(extended)
    require(grid.width*grid.height<=4096, "bounded scene too large")
    r,c = int(extended[3]-y1),int(x0-extended[0])
    window = (slice(r,r+original.height),slice(c,c+original.width))
    maps = {}
    for name,array in item["maps"].items():
        target = np.full((grid.height,grid.width),np.nan if name=="top" else 0,dtype=array.dtype)
        target[window] = array
        require(np.array_equal(target[window],array,equal_nan=True), "embedding changed saved roof/coverage")
        maps[name] = target
    dem,indices,sampling = terrain.sample_dem(dem_path,grid)
    require(np.array_equal(dem[window],item["inputs"]["dem"]), "context sampling changed original DEM")
    return dict(grid=grid,maps=maps,dem=dem,source_row_col=indices,sampling=sampling,source=source,
                vertical=item["inputs"]["metadata"]["vertical"],source_dir=item["source_dir"],
                context=dict(requested_margin_m=margin,original_bounds=list(original.bounds),bounds=list(extended),
                             surrounding_buildings="omitted; isolated single-building sensitivity experiment"))


def prepare(sample, method):
    require(method in METHODS, "unknown comparison model")
    ids = (sample["maps"]["state"]==1).astype(np.int32)
    present = ids>0
    require(present.any() and not (sample["maps"]["state"]==2).any(), "unknown or missing building tops")
    effective,d0 = voxel.effective_ground(ids,sample["dem"])
    top = sample["maps"]["top"]
    representative = float(np.nanmax(top))
    chosen = np.full(int(present.sum()),representative) if method=="representative" else top[present]
    high = chosen-effective[present]
    require(np.isfinite(high).all() and (high>0).all(), "nonpositive roof-ground height")
    height = np.zeros(ids.shape,dtype=float)
    height[present] = high
    segments = np.empty(ids.shape,dtype=object)
    for index in np.ndindex(ids.shape):segments[index] = [[0.,float(height[index])]] if present[index] else []
    return dict(height=height,segments=segments,ids=ids,dem=sample["dem"].copy(),metadata=dict(
        profile=PROFILE,method=method,grid=roof.grid_metadata(sample["grid"]),source=deepcopy(sample["source"]),
        vertical=deepcopy(sample["vertical"]),representative_absolute_H=representative,
        representative_rule="maximum saved cell_max absolute roof H; experiment-only",
        source_owner_mapping={sample["source"]["source_id"]:1},expected_d0=d0,
        expected_effective_ground=effective.tolist(),tree="none"))


def difference(a,b,valid):
    require(a.shape==b.shape==valid.shape and np.array_equal(a!=255,valid) and np.array_equal(b!=255,valid)
            and np.isin(a[valid],[0,1]).all() and np.isin(b[valid],[0,1]).all(), "invalid comparison maps/mask")
    ashadow,bshadow = (a==0)&valid,(b==0)&valid
    # 0 excluded, 1 common sun, 2 common shadow, 3 A-only shadow, 4 B-only shadow.
    classes = np.zeros(valid.shape,dtype=np.uint8)
    classes[valid] = 1
    classes[ashadow&bshadow] = 2
    classes[ashadow&~bshadow] = 3
    classes[~ashadow&bshadow] = 4
    union = int((ashadow|bshadow).sum())
    delta = int(bshadow.sum()-ashadow.sum())
    metrics = dict(valid_observers=int(valid.sum()),representative_shadow_cells=int(ashadow.sum()),
        distributed_shadow_cells=int(bshadow.sum()),shadow_cells_delta_B_minus_A=delta,shadow_area_delta_m2=delta,
        changed_cells=int(((a!=b)&valid).sum()),shadow_to_sun=int((classes==3).sum()),
        sun_to_shadow=int((classes==4).sum()),shadow_IoU=1. if not union else float((ashadow&bshadow).sum()/union))
    require(metrics["changed_cells"]==metrics["shadow_to_sun"]+metrics["sun_to_shadow"]
            and delta==metrics["sun_to_shadow"]-metrics["shadow_to_sun"], "difference accounting mismatch")
    return classes,metrics


def calculate(sample):
    results = {m:voxel.execute_arrays(prepare(sample,m)) for m in METHODS}
    a,b = (results[m] for m in METHODS)
    require(all(np.array_equal(a["inputs"][k],b["inputs"][k]) for k in ("dem","ids"))
            and a["qa"]["d0"]==b["qa"]["d0"] and a["qa"]["effective_ground"]==b["qa"]["effective_ground"], "A/B ground/owner differs")
    nz = max(r["voxels"].shape[2] for r in results.values())
    models,capacity = {},{}
    for m,r in results.items():
        original = r["voxels"]
        padded = np.pad(original,((0,0),(0,0),(0,nz-original.shape[2])),constant_values=0)
        require(np.array_equal(padded[:,:,:original.shape[2]],original) and not padded[:,:,original.shape[2]:].any(), "non-AIR padding")
        models[m] = padded
        capacity[m] = dict(original_shape=list(original.shape),shared_shape=list(padded.shape),air_layers_added=nz-original.shape[2])
    require(all(np.array_equal(models["representative"]==code,models["distributed"]==code) for code in (-1,1)), "ground/surface classes differ")
    obs = shared.common_observers(models,sample["grid"],a["qa"]["d0"],np.array(a["qa"]["effective_ground"]),experiments=(("binary",0.),))["binary"]
    direction,orientation = axis(sample["grid"])
    maximum_z = max(r["qa"]["d0"]+max(s["stop"] for s in r["qa"]["integer_intervals"]) for r in results.values())
    reach = max(0.,maximum_z-float(np.min(obs["xyz"][obs["valid"],2])))
    indices = np.argwhere(a["inputs"]["ids"]>0)
    x0,y0,x1,y1 = sample["grid"].bounds
    west,east = x0+indices[:,1].min(),x0+indices[:,1].max()+1
    north,south = y1-indices[:,0].min(),y1-indices[:,0].max()-1
    dx,dy = -direction[1]/direction[2]*reach,-direction[0]/direction[2]*reach
    require(west+min(0,dx)>x0+1 and east+max(0,dx)<x1-1 and south+min(0,dy)>y0+1 and north+max(0,dy)<y1-1,
            "DEM/domain cannot contain conservative shadow reach")
    maps = {}
    for m in METHODS:
        maps[m] = shared.evaluate(models[m],results[m]["inputs"],sample["grid"],binary_only=True,binary_direction=direction)["binary"]
        original = shared.evaluate(results[m]["voxels"],results[m]["inputs"],sample["grid"],binary_only=True,binary_direction=direction)["binary"]
        extra = shared.evaluate(np.pad(models[m],((0,0),(0,0),(0,3))),results[m]["inputs"],sample["grid"],binary_only=True,binary_direction=direction)["binary"]
        require(np.array_equal(original,maps[m]) and np.array_equal(extra,maps[m]), "AIR capacity changes shadow")
        border = np.zeros(obs["valid"].shape,dtype=bool)
        border[:2,:]=border[-2:,:]=border[:,:2]=border[:,-2:]=True
        require(not ((maps[m]==0)&border).any(), "shadow reaches scene boundary")
    classes,metrics = difference(maps["representative"],maps["distributed"],obs["valid"])
    require(not metrics["sun_to_shadow"], "lower roofs unexpectedly enlarge shadow")
    if sample["source"]["label"]=="F":require(not metrics["changed_cells"] and np.array_equal(models["representative"],models["distributed"]), "flat control differs")
    return dict(results=results,models=models,capacity=capacity,observers=obs,maps=maps,difference=classes,metrics=metrics,
                orientation=orientation,context=dict(sample["context"],maximum_45deg_reach_m=reach,shadow_bbox_clear=True,two_cell_border_unshadowed=True))


def plot(path,sample,result):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.colors import ListedColormap,BoundaryNorm
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    from shapely.geometry import shape
    figure = Figure(figsize=(12,9),layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots(2,2).flat
    x0,y0,x1,y1 = sample["grid"].bounds
    footprint = shape(consumer.load(sample["source_dir"]/"projections.json")["original_ground_union"])
    for axis,data,title in zip(axes,[result["maps"][m] for m in METHODS]+[result["difference"],sample["maps"]["top"]],
                               ("Representative shadow","Distributed shadow","Shadow comparison","Original cell_max roof H (m)")):
        if title=="Shadow comparison":
            colors=["lightgray","white","#35364a","#ed9b40","#1976d2"]
            axis.imshow(data,extent=(x0,x1,y0,y1),origin="upper",cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(6)-.5,5))
            axis.legend(handles=[Patch(facecolor=c,label=s) for c,s in zip(colors,("excluded","common sun","common shadow","A-only shadow","B-only shadow"))],fontsize=7)
        elif "roof" in title:
            lo,hi=float(np.nanmin(data)),float(np.nanmax(data))
            if lo==hi:lo,hi=lo-.5,hi+.5
            image=axis.imshow(np.ma.masked_invalid(data),extent=(x0,x1,y0,y1),origin="upper",vmin=lo,vmax=hi)
            figure.colorbar(image,ax=axis,shrink=.7)
        else:
            axis.imshow(np.where(data==255,2,data),extent=(x0,x1,y0,y1),origin="upper",cmap=ListedColormap(["#35364a","white","lightgray"]),vmin=0,vmax=2)
        x,y=footprint.exterior.xy
        axis.plot(x,y,color="crimson",linewidth=.8)
        axis.set(title=title,xlabel="EPSG:6677 X (east)",ylabel="Y (north)")
        axis.ticklabel_format(useOffset=False,style="plain")
        axis.xaxis.set_major_locator(MaxNLocator(nbins=4,integer=True))
        axis.yaxis.set_major_locator(MaxNLocator(nbins=5,integer=True))
    figure.suptitle(sample["source"]["label"]+": isolated real LoD2 / true sun 180°, 45° / delta B−A")
    figure.savefig(path,dpi=130,metadata={"Software":"OUEM STEP 4-C"})


def run(distribution_run,audit_run,b1_run,t5_run,b2_run,output,artifact_root):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    started = False
    try:
        items,watch,_ = terrain.load_inputs(distribution_run,audit_run,b1_run,t5_run,artifact_root)
        b2 = Path(b2_run).resolve(strict=True)
        roof.audit._capture(watch,"4C_B2_manifest",b2/"manifest.json",B2_SHA)
        roof.audit._capture(watch,"4C_B2_report",b2/"report.json",B2_REPORT_SHA)
        saved = consumer.load(b2/"report.json")
        for name,sha in consumer.load(b2/"manifest.json")["outputs"].items():
            path=b2/name
            require(path.resolve().is_relative_to(b2),"unconfined B2 output")
            roof.audit._capture(watch,"4C_B2_output_"+name,path,sha)
        for name,file in dict(adapter=__file__,shadow=shared.shadow.__file__,shared=shared.__file__,observer=shared.observers.__code__.co_filename).items():
            roof.audit._capture(watch,"4C_code_"+name,file)
        geometric = shared.cardinal_geometry_check(shared.scene("flat")["grid"],binary_only=True)
        summaries = {}
        for label,item in items.items():
            require(saved["buildings"][label]["input_identity"]==voxel.input_identity(item["inputs"]),"B2 source identity differs")
            expected,_=voxel.occupancy_oracle(item["inputs"],numba=True)
            require(np.array_equal(np.load(b2/label/"voxels.npy",allow_pickle=False),expected),"B2 saved occupancy differs")
            sample=scene(item,Path(t5_run)/"t5-2/terrain.tif",(-22588,-39938,-22461,-39811))
            started = True
            result=calculate(sample)
            path=output/label
            path.mkdir()
            for method in METHODS:
                sub=path/method
                sub.mkdir()
                r=result["results"][method]
                for name,array in dict(height=r["inputs"]["height"],ids=r["inputs"]["ids"],dem=r["inputs"]["dem"],voxels=r["voxels"],
                                        shared_voxels=result["models"][method],shadow=result["maps"][method]).items():shared.save_array(sub/(name+".npy"),array)
                for name,value in dict(metadata=r["inputs"]["metadata"],segments=r["inputs"]["segments"].tolist(),qa=r["qa"],engine=r["engine"],runtime=r["runtime"]).items():roof.audit.write(sub/(name+".json"),value)
            for name,array in dict(difference=result["difference"],source_top_H=sample["maps"]["top"],roof_coverage=sample["maps"]["roof_coverage"],
                footprint_fraction=sample["maps"]["footprint_fraction"],source_row_col=sample["source_row_col"],
                observer_index=result["observers"]["index"],observer_valid=result["observers"]["valid"],observer_xyz=result["observers"]["xyz"]).items():shared.save_array(path/(name+".npy"),array)
            plot(path/"comparison.png",sample,result)
            summaries[label]=dict(source_id=sample["source"]["source_id"],ouem_id=sample["source"]["ouem_id"],metrics=result["metrics"],context=result["context"],
                grid=roof.grid_metadata(sample["grid"]),orientation=result["orientation"],capacity=result["capacity"],sampling=sample["sampling"],
                actual_binary_observer_height_above_effective_ground_m=terrain.span(result["observers"]["actual_height_above_effective_ground_m"][result["observers"]["valid"]]))
        watch.unchanged()
        report=dict(profile=PROFILE,baseline_main=BASELINE,technical_execution="PASS",binary_shadow="PASS",settings=SETTINGS,
                    shadow_encoding=dict(shadow=0,sun=1,excluded=255),difference_encoding=DIFFERENCE_CODES,
                    geometry_qa=geometric,buildings=summaries,inputs=watch.identities,vertical_status="CONDITIONAL",**terrain.base.FLAGS)
        roof.audit.write(output/"report.json",report)
        outputs={p.relative_to(output).as_posix():consumer.digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
        watch.unchanged()
        roof.audit.write(output/"manifest.json",dict(profile=PROFILE,status="COMPLETED_EXPERIMENTAL",outputs=outputs,**terrain.base.FLAGS))
        return report
    except Exception as exc:
        failure=dict(profile=PROFILE,technical_execution="NOT_EXECUTED" if isinstance(exc,FileNotFoundError) and not started else "BLOCKED",
                     error=f"{type(exc).__name__}: {exc}",**terrain.base.FLAGS)
        roof.audit.write(output/"failure.json",failure)
        return failure


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("distribution-run","audit-run","b1-run","t5-run","b2-run","output-dir","artifact-root"):parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    result=run(args.distribution_run,args.audit_run,args.b1_run,args.t5_run,args.b2_run,args.output_dir,args.artifact_root)
    print(result["technical_execution"],result.get("error","four real-roof binary shadow comparisons PASS"))
    return int(result["technical_execution"]!="PASS")


if __name__=="__main__":main()
