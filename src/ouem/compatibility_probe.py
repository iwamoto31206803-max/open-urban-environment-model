"""Read-only numerical handoff probe, not an analysis runner or Standard schema."""
from pathlib import Path

import numpy as np
from pyproj import Transformer

from ouem.b2_gvi import observers
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_voxel import effective_ground
from ouem.consumers.source_h_standard import Watch


def load_candidate(root, report_sha256, *, observer_height=1.5):
    """Bind a saved T5 snapshot and map it to the STEP 1 numerical probe."""
    watch = Watch(Path(root).resolve())
    report = watch.capture("report","report.json",report_sha256,json_data=True)
    require(report["profile"]=="ouem-candidate-b-t5-23/v0.1" and report["gate1"]==report["gate2"]=="PASS",
            "candidate","completed T5-2/T5-3 required")
    for key,sha in report["outputs"].items():
        watch.capture(key,key,sha)

    def array(name):
        require(name+".npy" in report["outputs"],"candidate.array","unbound input array")
        return np.load(watch.resolve(name+".npy"),allow_pickle=False,mmap_mode="r")

    voxels = array("t5-3/voxels")
    xy = array("t5-2/centres_xy")
    grid = report["grid"]["engine_grid"]
    require(list(voxels.shape[:2])==grid["grid_size"],"candidate.shape","engine grid differs")
    metadata = dict(shape=report["voxel_shape"],axes=["north","east","up"],mesh_m=grid["meshsize_m"],xy_epsg=6677,
                    canopy="NONE",d0_effective_abs_m=report["voxels"]["z_reference_abs_m"],
                    numba=report["voxels"]["numba"],origin_lonlat=grid["origin"],
                    u_step_lonlat=(np.array(grid["u_vec"])*grid["adj_mesh"][0]).tolist(),
                    v_step_lonlat=(np.array(grid["v_vec"])*grid["adj_mesh"][1]).tolist(),
                    domain_bounds=report["domain"],evaluation_bounds=report["evaluation_aoi"],
                    observer_height_m=observer_height,
                    source_id_by_numeric_id={str(r["id"]):r["source_id"] for r in report["grid"]["buildings"]})
    index,valid,_ = observers(voxels,height=observer_height)
    xyz = np.concatenate((xy,(metadata["d0_effective_abs_m"]+index+.5)[...,None]),axis=-1)
    arrays = dict(voxels=voxels,ids=array("t5-2/building_ids"),raw_dem=array("t5-2/dem"),
                  ground_abs=array("t5-3/effective_dem_abs"),centres_xy=xy,roi=array("t5-2/evaluation_mask"),
                  observer_index=index,observer_valid=valid,observer_xyz=xyz)
    result = inspect(**arrays,metadata=metadata)
    result["saved_observer_contract"] = "NOT_VERIFIED; recomputed using B2 observer definition"
    watch.unchanged()
    return arrays,metadata,result,report,watch


def inspect(voxels, ids, raw_dem, ground_abs, centres_xy, roi, metadata,
            observer_index, observer_valid, observer_xyz):
    """Check an explicitly mapped snapshot against existing 1 m downstream rules.

    Callers bind source files/hashes with their existing family-specific reader.
    This function performs no file I/O, calculation of shadows/GVI, or mutation.
    """
    shape = voxels.shape
    require(voxels.dtype == np.int8 and voxels.ndim == 3 and min(shape)>0,
            "probe.voxels", "positive 3D int8 array required")
    require(metadata["shape"] == list(shape) and metadata["axes"] == ["north","east","up"]
            and metadata["mesh_m"] == 1. and metadata["xy_epsg"] == 6677,
            "probe.grid", "explicit 1 m north/east/up EPSG:6677 mapping required")
    require(set(map(int,np.unique(voxels))) <= {-3,-2,-1,0,1},
            "probe.classes", "unsupported class or NoData")
    require(metadata["canopy"] in ("NONE","ESTIMATED"),
            "probe.canopy", "canopy provenance must be explicit")
    has_tree = bool(np.any(voxels == -2))
    require(metadata["canopy"] != "NONE" or not has_tree,
            "probe.canopy", "TREE present in a no-canopy snapshot")
    horizontal = shape[:2]
    require(ids.shape == raw_dem.shape == ground_abs.shape == roi.shape == horizontal
            and ids.dtype.kind in "iu" and (ids>=0).all()
            and roi.dtype == bool and roi.any(), "probe.shape", "inconsistent grids or ROI")
    require(np.isfinite(raw_dem).all() and np.isfinite(ground_abs).all()
            and centres_xy.shape == horizontal+(2,) and np.isfinite(centres_xy).all(),
            "probe.values", "finite ground and cell coordinates required")
    d0 = metadata["d0_effective_abs_m"]
    require(np.isfinite(d0) and d0 == float(ground_abs.min()),
            "probe.D0", "D0 must equal the minimum conditioned absolute ground")
    conditioned, _ = effective_ground(ids,raw_dem)
    require(np.allclose(conditioned,ground_abs,atol=1e-10,rtol=0),
            "probe.ground", "owner-conditioned ground differs from raw DEM")
    require(np.array_equal(np.any(voxels == -3,axis=2),ids>0),
            "probe.ownership", "owner/anonymous building column support differs")
    mapping = metadata["source_id_by_numeric_id"]
    require(set(mapping)==set(map(str,np.unique(ids[ids>0])))
            and all(type(value) is str and value for value in mapping.values())
            and len(set(mapping.values()))==len(mapping),
            "probe.identity","positive owner IDs must map uniquely to source IDs")
    # The installed CPU engine's ground cast depends on the recorded path.
    require(type(metadata["numba"]) is bool,"probe.kernel","record numba path explicitly")
    kernel_ground = (ground_abs-d0).astype("float32" if metadata["numba"] else "float64").astype(float)
    surface = np.floor(kernel_ground+.5).astype(int)
    k = np.arange(shape[2])
    require((surface>=0).all() and (surface<shape[2]).all()
            and np.array_equal(voxels==-1,k<surface[...,None])
            and np.array_equal(voxels==1,k==surface[...,None]),
            "probe.vertical", "ground layer or D0/index convention differs")
    origin,u,v = (np.asarray(metadata[key],dtype=float) for key in
                  ("origin_lonlat","u_step_lonlat","v_step_lonlat"))
    require(origin.shape==u.shape==v.shape==(2,) and np.isfinite([origin,u,v]).all()
            and np.linalg.det([u,v])!=0,"probe.basis","invalid geographic cell basis")
    i,j = np.indices(horizontal)
    lonlat = origin+(i[...,None]+.5)*u+(j[...,None]+.5)*v
    x,y = Transformer.from_crs(4326,6677,always_xy=True).transform(lonlat[...,0],lonlat[...,1],errcheck=True)
    require(np.allclose(centres_xy,np.stack((x,y),axis=-1),atol=1e-6,rtol=0)
            and (np.diff(centres_xy[...,1],axis=0)>0).all()
            and (np.diff(centres_xy[...,0],axis=1)>0).all(),
            "probe.coordinates", "axes or projected centres differ from geographic basis")
    domain = metadata["domain_bounds"]
    bounds = metadata["evaluation_bounds"]
    require(len(domain)==len(bounds)==4 and np.isfinite([domain,bounds]).all()
            and domain[0]<=bounds[0]<bounds[2]<=domain[2]
            and domain[1]<=bounds[1]<bounds[3]<=domain[3],
            "probe.extents", "evaluation must be inside the declared processing domain")
    require(((x>=domain[0])&(x<domain[2])&(y>=domain[1])&(y<domain[3])).all(),
            "probe.domain","cell centre outside processing domain")
    expected_roi=(x>=bounds[0])&(x<bounds[2])&(y>=bounds[1])&(y<bounds[3])
    require(np.array_equal(roi,expected_roi),"probe.ROI","ROI disagrees with actual centres")
    height=metadata["observer_height_m"]
    require(np.isfinite(height) and height>=0,"probe.observer","invalid observer height")
    index,valid,_=observers(voxels,height=height,mesh=1.)
    require(observer_index.shape==observer_valid.shape==horizontal
            and observer_valid.dtype==bool and observer_index.dtype.kind in "iu"
            and np.array_equal(valid,observer_valid)
            and np.array_equal(index,observer_index),
            "probe.observer","surface or observer index differs")
    require(observer_xyz.shape==horizontal+(3,) and
            np.allclose(observer_xyz[valid,:2],centres_xy[valid],atol=1e-6,rtol=0)
            and np.array_equal(observer_xyz[valid,2],d0+index[valid]+.5),
            "probe.observer.coordinates","observer geography or absolute Z differs")
    return dict(status="NUMERICAL_HANDOFF_PASS",shape=list(shape),tree_voxels=int((voxels==-2).sum()),
                canopy=metadata["canopy"],valid_observers=int(valid.sum()),roi_cells=int(roi.sum()),
                observer_centre_convention="D0 + k*1m + 0.5m",
                gvi_interpretation="TREE target available" if has_tree else "NO_TREE; zero is not observed absence",
                solar_compatibility="SMALL_ADAPTER",gvi_kernel_compatibility="REUSE_AS_IS",
                provenance_eligibility="NOT_VERIFIED",scientific_validation="NOT_VERIFIED",
                terrain_integration_ready=False)
