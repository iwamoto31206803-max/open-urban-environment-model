"""STEP 4-A: four audited LoD2 samples -> absolute roof H, never HAG/voxels."""
from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform

import numpy as np
import rasterio
from shapely.geometry import Point, box, mapping
from shapely.ops import unary_union

from ouem import lod2_roof_audit as audit
from ouem import synthetic_height_distribution as geometry
from ouem.consumers import mixed_lod as consumer
from ouem.consumers._source_h_geometry import decode
from ouem.consumers.source_h_standard import Watch
from ouem.native.building.source_h_geometry import open_readonly, polygons, require

PROFILE="ouem-real-lod2-absolute-roof-top/four-audited-samples/v0.1"
AUDIT_MANIFEST_SHA="14498ba34826c2b68c2a22c29da6fcbeb8bc696e20b68f799d8a8cca0a41a852"
AUDIT_REPORT_SHA="71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e"
LABELS=dict(F="simple_flat",S="sloped",M="multiple_roof_faces",C="hole_or_complex_outline")
VERTICAL=dict(source_compound_epsg=6697,source_horizontal_epsg=6668,source_vertical_epsg=6695,
              standard_horizontal_epsg=6677,vertical_operation="identity_H in Standard; planar evaluation here",
              quantity="absolute source-declared gravity-related H (m); not HAG",
              realization="NOT_VERIFIED",epoch="NOT_VERIFIED",accuracy="NOT_VERIFIED")
Z_TOLERANCE=1e-8
AREA_TOLERANCE=1e-7
STATES={"NO_BUILDING":0,"KNOWN":1,"TOP_UNKNOWN":2}
POLICIES=dict(footprint="STEP 4-A provisional union of valid explicit GroundSurface XY; Polygon only",
              support="RoofSurface projection intersected with provisional footprint",
              boundary="no snap, buffer, hole filling, interpolation or shape repair",
              height="absolute source H only; no DEM subtraction or representative fill")


def json_digest(value):
    return hashlib.sha256(consumer.canonical(value)).hexdigest()


def ground_footprint(faces):
    require(bool(faces),"ground","GroundSurface required")
    polygons_xy=[audit.projected_polygon(f["standard_xyz_rings"]) for f in faces]
    require(all(p.is_valid and p.area>0 for p in polygons_xy),"ground","invalid GroundSurface projection")
    footprint=unary_union(polygons_xy)
    require(footprint.geom_type=="Polygon" and footprint.is_valid and footprint.area>0,
            "ground","union must be valid Polygon; no largest-part selection")
    return footprint


def grid_metadata(grid):
    return dict(grid.metadata(),origin_xy=[grid.bounds[0],grid.bounds[3]],
        column_axis=[1.,0.],row_axis=[0.,-1.],global_phase_origin_xy=[0.,0.],default_halo_cells=1,
        sampling_location="cell centres locate cells; roof evaluation is method-specific",
        boundary_rule="positive-area presence/support; closed-set centre; affine maximum on polygon closure")


def load_samples(audit_run,artifact_root):
    """Pin historical audit and replay existing read-only chain, without DEM QA."""
    watch=Watch(artifact_root)
    audit_run=Path(audit_run)
    audit._capture(watch,"step4_0_manifest",audit_run/"manifest.json",AUDIT_MANIFEST_SHA)
    audit._capture(watch,"step4_0_report",audit_run/"report.json",AUDIT_REPORT_SHA)
    previous=consumer.load(audit_run/"report.json")
    manifest=consumer.load(audit_run/"manifest.json")
    require(manifest["report_sha256"]==AUDIT_REPORT_SHA and previous["status"]=="AUDIT_COMPLETED"
            and previous["real_data_audit"]=="EXECUTED","audit","executed pinned audit required")
    for name,identity in previous["inputs"].items():
        watch.capture(name,identity["path"],identity["sha256"],identity["size_bytes"])
    selected_ids={label:previous["sample_selection"][category]["source_id"] for label,category in LABELS.items()}
    require(None not in selected_ids.values() and len(set(selected_ids.values()))==4,"samples","fixed four required")
    def path(name): return watch.root/previous["inputs"][name]["path"]
    t5=consumer.load(path("T5_report"))
    bounds=t5["evaluation_aoi"]
    standard,native,bridge,selector,paths,member=consumer.graph(watch,path("standard_manifest"),
        previous["inputs"]["standard_manifest"]["sha256"],bounds)
    raw=audit.city.read_zip(paths["raw_zip"],member["member"],member)
    projection=consumer.zone_ix()
    xy=lambda x,y:projection(x,y,errcheck=True)
    selected,decisions=consumer.raw_selection(raw,selector,paths["selector_geometry"],member["member"],bounds,xy)
    snapshots=consumer.converter_passes(raw,bridge,paths)  # saved outputs only; no Converter execution
    consumer.verify_decisions(decisions,selected,raw,native,bridge,selector)
    native_shapes,attrs=consumer.gpkg_rows(paths,selected,snapshots,bridge,selector["source"]["release"],raw)
    chain=consumer.audit_standard(paths["standard"],native_shapes,attrs,standard,bounds,xy)
    audit.verify_population(t5["grid"]["buildings"],attrs)
    semantics=audit.read_semantics(paths["extracted_member"],set(selected_ids.values()))
    with open_readonly(paths["standard"]) as db:
        shapes={sid:polygons(decode(blob)) for sid,blob in db.execute("SELECT source_id,geometry FROM building")}
    historical={r["source_id"]:r for r in previous["buildings"]}
    source_ref=dict(audit_manifest_sha256=AUDIT_MANIFEST_SHA,audit_report_sha256=AUDIT_REPORT_SHA,
        zip_sha256=standard["raw_source"]["zip_sha256"],member=member,
        standard_gpkg=standard["output"],native_gpkg=standard["inputs"]["native_gpkg"],
        standard_manifest_sha256=previous["inputs"]["standard_manifest"]["sha256"])
    samples=[]
    for label,sid in selected_ids.items():
        require(sid in attrs and attrs[sid][3]==2,"samples","audited LoD2 source missing")
        matches=audit.correspondence(semantics[sid],polygons(native_shapes[sid]))
        for row,old in zip(matches,historical[sid]["faces"],strict=True):
            require(row["mapping"]=="VERIFIED" and row["semantic"] in audit.SEMANTICS
                    and all(row[k]==old[k] for k in row),sid,"historical face correspondence differs")
        ground,roof,refs=[],[],[]
        for row in matches:
            rings=shapes[sid][row["standard_face_index"]]
            if row["semantic"]=="GroundSurface": ground.append((row["polygon_id"],rings))
            if row["semantic"]=="RoofSurface":
                require(geometry._face(geometry.Face(row["polygon_id"],rings)) is not None,sid,"invalid roof support")
                roof.append(geometry.Face(row["polygon_id"],rings))
                refs.append(dict(row,standard_xyz_rings=rings,source_ref="inputs.json#/source_ref"))
        require(ground and roof,sid,"explicit independent ground and roof required")
        ground_records=[dict(polygon_id=fid,standard_xyz_rings=rings) for fid,rings in ground]
        footprint=ground_footprint(ground_records)
        identity=dict(source_id=sid,ouem_id=attrs[sid][1],label=label,source_ref=source_ref,faces=refs,
                      ground_faces=ground_records,
                      historical_audit_classification=historical[sid]["classification"])
        building=geometry.Building(sid,footprint,tuple(roof),"verified PLATEAU source H; see inputs.json")
        samples.append((building,identity))
    for name,file in dict(adapter=__file__,kernel=geometry.__file__,auditor=audit.__file__,consumer=consumer.__file__).items():
        audit._capture(watch,"current_code_"+name,file)
    watch.unchanged()
    return samples,watch,dict(source_ref=source_ref,historical_audit_implementation=previous["implementation"],
                             current_input_qa=chain,sample_ids=selected_ids)


def building_grid(building):
    """Global integer-metre phase, one whole-cell halo; no half-cell shift."""
    extents=[building.footprint.bounds]+[audit.projected_polygon(f.rings).bounds for f in building.faces]
    bounds=(math.floor(min(b[0] for b in extents))-1,math.floor(min(b[1] for b in extents))-1,
            math.ceil(max(b[2] for b in extents))+1,math.ceil(max(b[3] for b in extents))+1)
    grid=geometry.GridSpec(bounds)
    require(grid.width*grid.height<=4096,"grid","sample exceeds bounded profile")
    return grid


def calculate(building,identity,grid=None):
    """Real profile wrapper; use geometry-only kernel, never synthetic Derived."""
    grid=grid or building_grid(building)
    require(grid.epsg==6677 and grid.resolution==1. and grid.width*grid.height<=4096,
            "grid","bounded EPSG:6677 1 m grid required")
    require(box(*grid.bounds).covers(building.footprint),"grid","footprint outside explicit grid")
    require(building.footprint.equals(ground_footprint(identity["ground_faces"])),"source","footprint differs from GroundSurface union")
    refs={f["polygon_id"]:f for f in identity["faces"]}
    require(len(refs)==len(building.faces) and set(refs)=={f.face_id for f in building.faces}
            and all(r["semantic"]=="RoofSurface" and r["mapping"]=="VERIFIED" for r in refs.values()),
            "source","only verified explicit RoofSurface may be sampled")
    require(all(json_digest(refs[f.face_id]["standard_xyz_rings"])==json_digest(f.rings) for f in building.faces),
            "source","face XYZ differs from verified reference")
    before=json_digest(dict(footprint=mapping(building.footprint),faces=[f.rings for f in building.faces]))
    parsed={f.face_id:geometry._face(f) for f in building.faces}
    require(all(v is not None for v in parsed.values()),"source","invalid/vertical roof")
    roof_original=unary_union([v[0] for v in parsed.values()])
    support=roof_original.intersection(building.footprint)
    maps,tables={},{}
    maximum_error=0.
    for method in geometry.METHODS:
        cells,_,excluded=geometry.sample_roofs(grid,[building],method=method)
        require(not excluded,"source","roof excluded by geometric kernel")
        shape=(grid.height,grid.width)
        top=np.full(shape,np.nan,dtype="float64")
        state=np.zeros(shape,dtype="uint8")
        coverage=np.zeros(shape)
        footprint=np.zeros(shape)
        rows=[]
        for cell in cells:
            i,j=cell["cell_index"]
            base=dict(row=i,col=j,centre_xy=cell["centre_xy"],sampling_method=method,
                      source_id=None,ouem_id=None,state="NO_BUILDING",building_present=False,absolute_top_z=None,valid=False,
                      unsupported_reason="NO_BUILDING",footprint_fraction=0.,roof_coverage_fraction=0.,
                      partial_coverage=False,contribution_count=0,contributions=[],source_ref="inputs.json#/source_ref")
            if cell["buildings"]:
                row=cell["buildings"][0]
                known=row["valid"]
                state[i,j]=1 if known else 2
                if known: top[i,j]=row["absolute_top_z"]
                coverage[i,j],footprint[i,j]=row["coverage_fraction"],row["footprint_fraction"]
                base.update(source_id=building.source_id,ouem_id=identity["ouem_id"],state=row["state"],building_present=True,
                    absolute_top_z=row["absolute_top_z"],valid=known,
                    unsupported_reason=None if known else "CENTRE_UNSUPPORTED" if coverage[i,j]>0 else "NO_ROOF_SUPPORT",
                    footprint_fraction=footprint[i,j],roof_coverage_fraction=coverage[i,j],
                    partial_coverage=row["partial_roof_coverage"],contribution_count=row["contribution_count"],
                    contributions=[dict(c,xyz_ref="source_faces.json#/"+c["face_id"]) for c in row["contributions"]])
                # Independent plane fit, centred for numerical conditioning.
                x,y=cell["centre_xy"]
                pixel=box(x-.5,y-.5,x+.5,y+.5)
                for contribution in row["contributions"]:
                    face=refs[contribution["face_id"]]
                    rings=face["standard_xyz_rings"]
                    vertices=np.array([p for r in rings for p in r],dtype=float)
                    origin=vertices[0]
                    offsets=vertices-origin
                    coefficients,_,rank,_=np.linalg.lstsq(np.column_stack((offsets[:,:2],np.ones(len(offsets)))),offsets[:,2],rcond=None)
                    require(rank==3,"plane","independent plane fit is singular")
                    clipped=audit.projected_polygon(rings).intersection(building.footprint).intersection(pixel)
                    require(clipped.area>0,"support","contribution has no positive support")
                    independent_known=method=="cell_max" or clipped.covers(Point(x,y))
                    require(contribution["valid"]==independent_known,"support","centre validity differs")
                    if independent_known:
                        points=[(x,y)] if method=="centre" else list(geometry._vertices(clipped))
                        expected=max(float(origin[2]+coefficients@[px-origin[0],py-origin[1],1.]) for px,py in points)
                        value=contribution["absolute_top_z"]
                        error=abs(expected-value)
                        maximum_error=max(maximum_error,error)
                        require(error<=Z_TOLERANCE and vertices[:,2].min()-Z_TOLERANCE<=value<=vertices[:,2].max()+Z_TOLERANCE,
                                "plane","top outside source mathematical range or independent fit")
            rows.append(base)
        require(np.array_equal(np.isfinite(top),state==1),"state","known/top mask differs")
        require(((coverage>=0)&(coverage<=1+1e-12)&(footprint>=0)&(footprint<=1+1e-12)).all(),"coverage","fraction outside range")
        require(abs(float(coverage.sum())-support.area)<=AREA_TOLERANCE
                and abs(float(footprint.sum())-building.footprint.area)<=AREA_TOLERANCE,
                "coverage","cell union area does not conserve source area")
        maps[method]=dict(top=top,state=state,roof_coverage=coverage,footprint_fraction=footprint)
        tables[method]=rows
    require(before==json_digest(dict(footprint=mapping(building.footprint),faces=[f.rings for f in building.faces])),
            "source","geometry changed during evaluation")
    a,b=maps["centre"],maps["cell_max"]
    mutual=(a["state"]==1)&(b["state"]==1)
    delta=np.where(mutual,b["top"]-a["top"],np.nan)
    require(np.all(delta[mutual]>=-Z_TOLERANCE),"maximum","cell_max below supported centre")
    qa=dict(independent_plane_max_error_m=maximum_error,source_xyz_unchanged=True,
        footprint_area_m2=float(building.footprint.area),original_roof_union_area_m2=float(roof_original.area),
        used_support_area_m2=float(support.area),uncovered_area_m2=float(building.footprint.difference(roof_original).area),
        outside_footprint_roof_area_m2=float(roof_original.difference(building.footprint).area),
        support_only_gain_cells=int(((a["state"]==2)&(b["state"]==1)).sum()),
        numeric_difference_cells=int((abs(delta[mutual])>Z_TOLERANCE).sum()),
        maximum_difference_m=float(np.max(delta[mutual])) if mutual.any() else None,methods={})
    for method,m in maps.items():
        present=m["state"]!=0
        known=m["state"]==1
        qa["methods"][method]=dict(cells=int(present.size),no_building=int((~present).sum()),
            building_present=int(present.sum()),known=int(known.sum()),unknown=int((m["state"]==2).sum()),
            unknown_fraction_of_building=float((m["state"]==2).sum()/present.sum()),
            footprint_boundary_cells=int(((m["footprint_fraction"]>0)&(m["footprint_fraction"]<1)).sum()),
            partial_roof_cells=int(((m["roof_coverage"]>0)&(m["roof_coverage"]<1)).sum()),
            z_range=[float(m["top"][known].min()),float(m["top"][known].max())] if known.any() else None)
    projections=dict(horizontal_crs="EPSG:6677",ground_faces=[dict(polygon_id=f["polygon_id"],
        geometry=mapping(audit.projected_polygon(f["standard_xyz_rings"]))) for f in identity["ground_faces"]],
        roof_faces=[dict(polygon_id=fid,original_projection=mapping(p[0]),
                        used_intersection=mapping(p[0].intersection(building.footprint))) for fid,p in parsed.items()],
        original_ground_union=mapping(building.footprint),original_roof_union=mapping(roof_original),
        used_support_union=mapping(support))
    return dict(grid=grid,maps=maps,tables=tables,delta=delta,qa=qa,projections=projections,
                identity=deepcopy(identity),profile=PROFILE,vertical=VERTICAL)


def raster(path,array,grid,*,quantity,unit,nodata):
    with rasterio.open(path,"w",driver="GTiff",width=grid.width,height=grid.height,count=1,
        dtype=array.dtype,crs=6677,transform=grid.transform,nodata=nodata,compress="deflate") as ds:
        ds.write(array,1)
        ds.set_band_unit(1,unit)
        ds.update_tags(OUEM_PROFILE=PROFILE,quantity=quantity,vertical_reference=json.dumps(VERTICAL,sort_keys=True))
        if quantity=="state": ds.update_tags(state_encoding=json.dumps(STATES,sort_keys=True))
    with rasterio.open(path) as ds:
        nodata_ok=ds.nodata==nodata if not isinstance(nodata,float) or not math.isnan(nodata) else math.isnan(ds.nodata)
        require(ds.crs.to_epsg()==6677 and ds.transform==grid.transform and ds.shape==array.shape
                and ds.dtypes==(str(array.dtype),) and nodata_ok and ds.units==(unit,)
                and ds.tags().get("OUEM_PROFILE")==PROFILE and ds.tags().get("quantity")==quantity
                and json.loads(ds.tags()["vertical_reference"])==VERTICAL
                and np.array_equal(ds.read(1),array,equal_nan=True),"raster","reopened grid/value/metadata differs")
        valid=np.isfinite(array) if isinstance(nodata,float) and math.isnan(nodata) else array!=nodata if nodata is not None else np.ones(array.shape,bool)
        require(np.array_equal(ds.read_masks(1)>0,valid),"raster","reopened mask differs")
        for row,col in ((0,0),(0,grid.width-1),(grid.height-1,0),(grid.height-1,grid.width-1)):
            require(ds.xy(row,col)==(grid.bounds[0]+col+.5,grid.bounds[3]-row-.5),"raster","corner registration differs")


def plot(path,result):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.ticker import MaxNLocator
    from shapely.geometry import shape
    figure=Figure(figsize=(12,4),layout="constrained")
    FigureCanvasAgg(figure)
    grid=result["grid"]
    extent=(grid.bounds[0],grid.bounds[2],grid.bounds[1],grid.bounds[3])
    source_z=[p[2] for f in result["identity"]["faces"] for ring in f["standard_xyz_rings"] for p in ring]
    zmin,zmax=min(source_z),max(source_z)
    if zmin==zmax: zmin,zmax=zmin-.5,zmax+.5
    for axis,key in zip(figure.subplots(1,3),("centre","cell_max","difference")):
        data=result["delta"] if key=="difference" else result["maps"][key]["top"]
        image=axis.imshow(np.ma.masked_invalid(data),origin="upper",extent=extent,cmap="viridis",
                          **({} if key=="difference" else dict(vmin=zmin,vmax=zmax)))
        for name,color in (("original_ground_union","black"),("original_roof_union","red")):
            geometry_shape=shape(result["projections"][name])
            for polygon in ([geometry_shape] if geometry_shape.geom_type=="Polygon" else geometry_shape.geoms):
                x,y=polygon.exterior.xy
                axis.plot(x,y,color=color,linewidth=.7)
        axis.set_title(key+" (m)")
        axis.set_xlabel("EPSG:6677 X")
        axis.set_ylabel("Y")
        axis.xaxis.set_major_locator(MaxNLocator(nbins=3,integer=True))
        axis.yaxis.set_major_locator(MaxNLocator(nbins=4,integer=True))
        figure.colorbar(image,ax=axis,shrink=.7)
    figure.suptitle(result["identity"]["label"]+": "+result["identity"]["source_id"],fontsize=9)
    figure.savefig(path,dpi=130,metadata={"Software":"OUEM STEP 4-A"})


def save_building(path,result):
    path.mkdir()
    grid=result["grid"]
    audit.write(path/"inputs.json",dict(result["identity"],profile=PROFILE,vertical=VERTICAL,
                                      grid=grid_metadata(grid),states=STATES,policies=POLICIES))
    audit.write(path/"source_faces.json",{f["polygon_id"]:f for f in result["identity"]["faces"]})
    audit.write(path/"projections.json",result["projections"])
    for method,maps in result["maps"].items():
        for name,array in maps.items():
            is_top=name=="top"
            raster(path/(method+"_"+name+".tif"),array,grid,quantity="absolute_H" if is_top else name,
                   unit="m" if is_top else "1",nodata=float("nan") if is_top else 255 if name=="state" else None)
        audit.write(path/(method+"_contributions.json"),result["tables"][method])
    raster(path/"cell_max_minus_centre.tif",result["delta"],grid,quantity="absolute_H_difference",unit="m",nodata=float("nan"))
    audit.write(path/"qa.json",result["qa"])
    plot(path/"diagnostic.png",result)


def run(audit_run,output,artifact_root):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    try:
        samples,watch,source=load_samples(audit_run,artifact_root)
        summaries={}
        for building,identity in samples:
            result=calculate(building,identity)
            save_building(output/identity["label"],result)
            summaries[identity["label"]]=dict(source_id=building.source_id,ouem_id=identity["ouem_id"],
                grid=grid_metadata(result["grid"]),qa=result["qa"])
        watch.unchanged()
        report=dict(profile=PROFILE,status="COMPLETED_EXPERIMENTAL",input_eligibility="PASS_LIMITED_FOUR_SAMPLE_PROFILE",
            baseline_main="171f2afcef50405597465dfe2a91cf2c731b5ff1",policies=POLICIES,
            geometric_numerical_qa="PASS",HAG="NOT_CALCULATED",voxelizer_connection="NOT_VERIFIED",
            terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED",
            vertical=VERTICAL,source=source,inputs=watch.identities,buildings=summaries,
            environment=dict(python=platform.python_version(),**{p:version(p) for p in ("numpy","shapely","rasterio","pyproj","matplotlib")}),
            implementation={Path(f).name:consumer.digest(f) for f in (__file__,geometry.__file__,audit.__file__)})
        audit.write(output/"report.json",report)
        outputs={p.relative_to(output).as_posix():consumer.digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
        watch.unchanged()
        audit.write(output/"manifest.json",dict(profile=PROFILE,status=report["status"],outputs=outputs,
            terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED"))
        return report
    except Exception as exc:
        failure=dict(profile=PROFILE,status="BLOCKED",error=f"{type(exc).__name__}: {exc}",
            terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",formal_acceptance="NOT_VERIFIED")
        audit.write(output/"failure.json",failure)
        return failure


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-run",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--artifact-root",type=Path,required=True)
    args=parser.parse_args()
    report=run(args.audit_run,args.output_dir,args.artifact_root)
    print(report["status"],report.get("error","geometric QA PASS; HAG not calculated"))
    return int(report["status"]!="COMPLETED_EXPERIMENTAL")


if __name__=="__main__":
    raise SystemExit(main())
