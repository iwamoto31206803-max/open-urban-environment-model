"""STEP 2-A: saved Candidate B -> pinned CPU binary building shadow -> GeoTIFF."""
import argparse
from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import numpy as np
from pyproj import Geod
import rasterio
from rasterio.transform import from_origin

from ouem.compatibility_probe import load_candidate
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require
from ouem.terrain_candidate_b_preflight import digest

T5_SHA = "1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f"
AOI = [-22575,-39925,-22475,-39825]
DOMAIN = [-22588,-39938,-22461,-39811]
REGISTRATION_TOLERANCE_M = .01


def sun_direction(metadata):
    """Use true sun azimuth and the saved geographic grid bearing."""
    from voxcity.utils.orientation import direction_to_axis_vector

    origin = np.asarray(metadata["origin_lonlat"])
    u,v = (np.asarray(metadata[key]) for key in ("u_step_lonlat","v_step_lonlat"))
    rows,cols = metadata["shape"][:2]
    geod = Geod(ellps="WGS84")
    bearing,_,_ = geod.inv(*origin,*(origin+rows*u))
    east,_,_ = geod.inv(*origin,*(origin+cols*v))
    error = (east-bearing-90+180)%360-180
    require(abs(error)<.01,"shadow.grid.rotation","geographic grid is not orthogonal within .01 degree")
    direction = direction_to_axis_vector(180.,45.,bearing)
    require(direction[0]<0 and direction[2]>0,"shadow.sun","expected sunward south/up ray")
    return tuple(direction),dict(azimuth_true_deg=180.,elevation_deg=45.,axis0_true_azimuth_deg=bearing,
                                 orthogonality_error_deg=error,direction_uv_up=direction.tolist(),
                                 view_point_height_m=0.,hit_values=[0,-1,1],inclusion_mode=False,
                                 include_building_roofs=False)


def calculate(voxels, valid, direction):
    from voxcity.simulator.solar.kernels import compute_direct_solar_irradiance_map_binary

    require(voxels.dtype==np.int8 and voxels.ndim==3 and
            np.isin(voxels,[-3,-1,0,1]).all(),"shadow.classes","building-only int8 voxels required")
    buildings = np.any(voxels==-3,axis=2)
    require(valid.dtype==bool and valid.shape==voxels.shape[:2] and np.array_equal(valid,~buildings),
            "shadow.observers","all and only non-building columns must have valid observers")
    raw = compute_direct_solar_irradiance_map_binary(
        voxels,direction,0.,(0,-1,1),1.,.6,1.,False,False)
    require(raw.shape==valid.shape and np.isfinite(raw[valid]).all()
            and np.isnan(raw[~valid]).all() and np.isin(raw[valid],[0.,1.]).all(),
            "shadow.result","unexpected NaN, roof observer or non-binary value")
    classes = np.full(valid.shape,255,dtype="uint8")
    classes[valid] = raw[valid].astype("uint8")
    return classes


def counts(classes, mask):
    values = classes[mask]
    shadow,sun,excluded = (int((values==code).sum()) for code in (0,1,255))
    require(shadow+sun+excluded==values.size,"shadow.counts","unclassified cell")
    return dict(cells=int(values.size),shadow=shadow,sun=sun,excluded=excluded,
                valid=shadow+sun,shadow_fraction_of_valid=None if not shadow+sun else shadow/(shadow+sun))


def export_raster(path, classes, centres_xy, roi, bounds):
    x0,y0,x1,y1 = bounds
    width,height = int(x1-x0),int(y1-y0)
    require(width==x1-x0 and height==y1-y0 and width>0 and height>0,
            "shadow.export","integer metre bounds required")
    xy = centres_xy[roi]
    require(classes.shape==roi.shape and centres_xy.shape==roi.shape+(2,)
            and np.isfinite(xy).all() and len(xy)==width*height,
            "shadow.export","ROI must cover exactly the target grid")
    col = np.floor(xy[:,0]-x0).astype(int)
    row = np.floor(y1-xy[:,1]).astype(int)
    require(((col>=0)&(col<width)&(row>=0)&(row<height)).all()
            and len(np.unique(row*width+col))==len(xy),
            "shadow.export","out-of-range, duplicate or missing cell registration")
    error = np.linalg.norm(xy-np.column_stack((x0+col+.5,y1-row-.5)),axis=1)
    require(float(error.max())<=REGISTRATION_TOLERANCE_M,"shadow.registration","cell registration exceeds .01 m")
    data = np.full((height,width),255,dtype="uint8")
    data[row,col] = classes[roi]
    affine = from_origin(x0,y1,1.,1.)
    with rasterio.open(path,"w",driver="GTiff",width=width,height=height,count=1,dtype="uint8",
                       crs="EPSG:6677",transform=affine,nodata=255,compress="deflate") as ds:
        ds.write(data,1)
        ds.update_tags(AREA_OR_POINT="Area",metric="experimental building-only binary shadow",
                       classes="0 shadow; 1 sun; 255 excluded",source_mapping="actual centre -> north-up pixel")
    with rasterio.open(path) as ds:
        require(ds.crs.to_epsg()==6677 and ds.transform==affine and ds.shape==data.shape
                and ds.dtypes==("uint8",) and ds.nodata==255
                and tuple(ds.bounds)==tuple(bounds)
                and np.array_equal(ds.read(1),data) and np.array_equal(ds.read_masks(1)>0,data!=255),
                "shadow.TIFF","reopened raster or NoData differs")
        checks = []
        for r,c in ((0,0),(0,width-1),(height-1,0),(height-1,width-1),(height//2,width//2)):
            actual = ds.xy(r,c)
            require(actual==(x0+c+.5,y1-r-.5),"shadow.TIFF.coordinates","corner/centre mismatch")
            source = int(np.flatnonzero((row==r)&(col==c))[0])
            checks.append(dict(row=r,col=c,pixel_centre=list(actual),source_centre=xy[source].tolist(),
                               registration_error_m=float(error[source])))
    return dict(epsg=6677,shape=list(data.shape),affine=list(affine)[:6],nodata=255,
                bounds=list(bounds),extent_centre=[(x0+x1)/2,(y0+y1)/2],
                max_centre_registration_error_m=float(error.max()),coordinate_checks=checks)


def write_json(path, value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write("\n")


def run(source, output, *, report_sha256=T5_SHA):
    source,output = Path(source).resolve(strict=True),Path(output).resolve()
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            "shadow.output","new output directory outside the source run required")
    output.mkdir()
    report = dict(profile="ouem-candidate-b-step2a-shadow/v0.1",status="FAILED",
                  terrain_integration_ready=False,scientific_validation="NOT_VERIFIED",
                  formal_acceptance="NOT_VERIFIED")
    try:
        engine = voxcity_provenance()
        require(engine["verified"],"shadow.engine","pinned engine required")
        arrays,metadata,probe,t5,watch = load_candidate(source,report_sha256,observer_height=0.)
        require(t5["domain"]==DOMAIN and t5["evaluation_aoi"]==AOI
                and metadata["shape"]==[127,127,12]
                and len(t5["grid"]["buildings"])==63
                and Counter(row["source_lod"] for row in t5["grid"]["buildings"])=={1:31,2:32},
                "shadow.scope","expected Candidate B 63-building saved T5 run")
        direction,settings = sun_direction(metadata)
        report.update(engine=engine,settings=settings,probe=probe,grid=metadata,
                      inputs=watch.identities,source_run=str(source),source_report_sha256=report_sha256,
                      vertical_evidence=t5["vertical_evidence"],
                      implementation_sha256=digest(Path(__file__)),
                      probe_implementation_sha256=digest(Path(__file__).with_name("compatibility_probe.py")),
                      environment=dict(host=platform.node(),python=platform.python_version(),os=platform.platform(),
                                       numpy=np.__version__,rasterio=rasterio.__version__,numba=version("numba")))
        voxels,roi,xy = (arrays[key] for key in ("voxels","roi","centres_xy"))
        classes = calculate(voxels,arrays["observer_valid"],direction)
        statistics = {name:counts(classes,mask) for name,mask in
                      dict(domain=np.ones(roi.shape,dtype=bool),evaluation=roi,outside_evaluation=~roi).items()}
        xmid,ymid = (AOI[0]+AOI[2])/2,(AOI[1]+AOI[3])/2
        quadrants = {name:counts(classes,roi & horizontal & vertical)
                     for name,horizontal,vertical in (
                         ("NW",xy[...,0]<xmid,xy[...,1]>=ymid),("NE",xy[...,0]>=xmid,xy[...,1]>=ymid),
                         ("SW",xy[...,0]<xmid,xy[...,1]<ymid),("SE",xy[...,0]>=xmid,xy[...,1]<ymid))}
        with TemporaryDirectory(prefix=".stage-",dir=output) as directory:
            stage = Path(directory)
            for name,array in dict(domain_classes=classes,evaluation_classes=classes[roi],
                                   evaluation_indices=np.argwhere(roi)).items():
                np.save(stage/(name+".npy"),array,allow_pickle=False)
                require(np.array_equal(np.load(stage/(name+".npy"),allow_pickle=False),array),
                        "shadow.readback","saved classification differs")
            spatial = export_raster(stage/"evaluation_shadow.tif",classes,xy,roi,AOI)
            watch.unchanged()
            result = report | dict(status="COMPLETED",statistics=statistics,spatial=spatial,
                                    evaluation_quadrants=quadrants,
                                    input_immutability="PASS",
                                    outputs={p.name:digest(p) for p in sorted(stage.iterdir())})
            write_json(stage/"report.json",result)
            for name in result["outputs"]:
                (stage/name).rename(output/name)
            watch.unchanged()
            (stage/"report.json").rename(output/"report.json")
        return result
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        write_json(output/"failure.json",report)
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--report-sha256",default=T5_SHA)
    args=parser.parse_args()
    report=run(args.source_run,args.output_dir,report_sha256=args.report_sha256)
    print(report["status"],report.get("error",report.get("statistics")))
    return int(report["status"]!="COMPLETED")


if __name__=="__main__":
    raise SystemExit(main())
