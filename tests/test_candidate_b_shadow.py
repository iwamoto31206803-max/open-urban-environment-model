import json

import numpy as np
import pytest
import rasterio

from ouem import candidate_b_shadow as shadow
from ouem.compatibility_probe import load_candidate
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_compatibility_probe import snapshot
from test_candidate_b_e0_shadow import model


@pytest.fixture(scope="module",autouse=True)
def pin():
    assert voxcity_provenance()["verified"]


def test_true_south_axis_and_building_classification():
    metadata=dict(shape=[19,23,12],origin_lonlat=[139.6,35.65],
                  u_step_lonlat=[0,1e-5],v_step_lonlat=[1e-5,0])
    direction,settings=shadow.sun_direction(metadata)
    np.testing.assert_allclose(direction,[-2**-.5,0,2**-.5],atol=1e-14)
    voxels=model()
    before=voxels.copy()
    voxels.flags.writeable=False
    valid=~np.any(voxels==-3,axis=2)
    expected=np.ones((19,23),dtype="uint8")
    expected[7:10,11:15]=255
    expected[10:13,11:15]=0
    first=shadow.calculate(voxels,valid,direction)
    np.testing.assert_array_equal(first,expected)
    np.testing.assert_array_equal(shadow.calculate(voxels,valid,direction),first)
    np.testing.assert_array_equal(voxels,before)
    assert settings["view_point_height_m"]==0
    assert (shadow.calculate(model(False),np.ones((19,23),dtype=bool),direction)==1).all()
    assert shadow.counts(first,np.ones(valid.shape,bool))["shadow"]==12


def test_rotated_grid_changes_sun_vector():
    # Grid north points 45 degrees NE, with an orthogonal SE axis 1.
    from pyproj import Geod
    geod=Geod(ellps="WGS84")
    origin=np.array([139.6,35.65])
    north=np.array(geod.fwd(*origin,45.,1.)[:2])
    east=np.array(geod.fwd(*origin,135.,1.)[:2])
    direction,settings=shadow.sun_direction(dict(shape=[1,1,4],origin_lonlat=origin,
                                               u_step_lonlat=north-origin,v_step_lonlat=east-origin))
    np.testing.assert_allclose(direction,[-.5,.5,2**-.5],atol=1e-8)
    assert abs(settings["axis0_true_azimuth_deg"]-45)<1e-6


@pytest.mark.parametrize("fault",["class","observer"])
def test_reject_bad_classes_or_observers(fault):
    voxels=model()
    valid=~np.any(voxels==-3,axis=2)
    if fault=="class":
        voxels[0,0,3]=-2
    else:
        valid[7,11]=True
    with pytest.raises(GeometryValidationError):
        shadow.calculate(voxels,valid,(-2**-.5,0,2**-.5))


def test_roi_is_extracted_after_full_domain_rays():
    voxels=model()
    valid=~np.any(voxels==-3,axis=2)
    full=shadow.calculate(voxels,valid,(-2**-.5,0,2**-.5))
    assert (full[10:13,11:15]==0).all()
    # Demonstrate the boundary bias a premature crop would introduce.
    crop=voxels[10:13,11:15].copy()
    assert (shadow.calculate(crop,np.ones((3,4),dtype=bool),(-2**-.5,0,2**-.5))==1).all()


def test_non_square_coordinate_export_and_roi(tmp_path):
    i,j=np.indices((5,7))
    xy=np.stack((j+.5,i+.5),axis=-1)
    roi=(i>=1)&(i<4)&(j>=1)&(j<6)
    classes=np.ones((5,7),dtype="uint8")
    classes[1,1]=classes[3,5]=0
    classes[2,3]=classes[3,1]=classes[1,5]=255
    classes[0,:]=0  # Outside ROI must not enter the export.
    path=tmp_path/"shadow.tif"
    report=shadow.export_raster(path,classes,xy,roi,[1,1,6,4])
    with rasterio.open(path) as ds:
        np.testing.assert_array_equal(ds.read(1),[[255,1,1,1,0],[1,1,255,1,1],[0,1,1,1,255]])
        assert ds.crs.to_epsg()==6677 and ds.nodata==255
        assert ds.xy(0,0)==(1.5,3.5) and ds.xy(2,4)==(5.5,1.5)
    assert report["max_centre_registration_error_m"]==0
    assert shadow.counts(classes,roi)==dict(cells=15,shadow=2,sun=10,excluded=3,
                                           valid=12,shadow_fraction_of_valid=2/12)
    xy[1,1,0]+=.02
    with pytest.raises(GeometryValidationError,match="registration"):
        shadow.export_raster(tmp_path/"bad.tif",classes,xy,roi,[1,1,6,4])


def authored_t5(tmp_path):
    source=tmp_path/"source"
    source.mkdir()
    data=snapshot()
    voxels,ids,dem,ground,xy,roi,meta,*_=data
    arrays={"t5-3/voxels":voxels,"t5-2/building_ids":ids,"t5-2/dem":dem,
            "t5-3/effective_dem_abs":ground,"t5-2/centres_xy":xy,"t5-2/evaluation_mask":roi}
    for name,array in arrays.items():
        path=source/(name+".npy")
        path.parent.mkdir(exist_ok=True)
        np.save(path,array,allow_pickle=False)
    report=dict(profile="ouem-candidate-b-t5-23/v0.1",gate1="PASS",gate2="PASS",
                domain=meta["domain_bounds"],evaluation_aoi=meta["evaluation_bounds"],voxel_shape=list(voxels.shape),
                grid=dict(engine_grid=dict(origin=meta["origin_lonlat"],u_vec=meta["u_step_lonlat"],
                                           v_vec=meta["v_step_lonlat"],adj_mesh=[1,1],meshsize_m=1,
                                           grid_size=list(voxels.shape[:2])),
                          buildings=[dict(id=17,source_id="authored-building",source_lod=1)]),
                voxels=dict(z_reference_abs_m=25.,numba=True),
                outputs={name+".npy":shadow.digest(source/(name+".npy")) for name in arrays})
    (source/"report.json").write_text(json.dumps(report),encoding="utf-8")
    return source,shadow.digest(source/"report.json")


def test_bound_readonly_loader_and_hash_rejection(tmp_path):
    source,sha=authored_t5(tmp_path)
    arrays,meta,probe,_,watch=load_candidate(source,sha,observer_height=0.)
    assert not arrays["voxels"].flags.writeable
    assert meta["observer_height_m"]==0 and probe["valid_observers"]==23
    before={p:shadow.digest(p) for p in source.rglob("*") if p.is_file()}
    watch.unchanged()
    assert before=={p:shadow.digest(p) for p in before}
    with (source/"t5-3/voxels.npy").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(GeometryValidationError):
        load_candidate(source,sha)


def test_failed_input_has_no_completion_and_refuses_reuse(tmp_path):
    source,_=authored_t5(tmp_path)
    out=tmp_path/"output"
    report=shadow.run(source,out,report_sha256="0"*64)
    assert report["status"]=="FAILED" and (out/"failure.json").exists()
    assert not (out/"report.json").exists()
    with pytest.raises(FileExistsError):
        shadow.run(source,out)


def test_bad_start_is_rejected_by_probe(tmp_path):
    source,sha=authored_t5(tmp_path)
    with pytest.raises(GeometryValidationError,match="outside Z"):
        load_candidate(source,sha,observer_height=100.)


def test_write_failure_keeps_run_incomplete(tmp_path,monkeypatch):
    source,sha=authored_t5(tmp_path)
    arrays,meta,probe,report,watch=load_candidate(source,sha,observer_height=0.)
    # Isolate publication failure after a hand-authored successful load.
    report.update(domain=shadow.DOMAIN,evaluation_aoi=shadow.AOI,
                  vertical_evidence={"accuracy":"NOT_VERIFIED"})
    report["grid"]["buildings"]=[dict(source_lod=1)]*31+[dict(source_lod=2)]*32
    meta["shape"]=[127,127,12]
    monkeypatch.setattr(shadow,"load_candidate",lambda *a,**k:(arrays,meta,probe,report,watch))
    monkeypatch.setattr(shadow,"sun_direction",lambda *a:((-2**-.5,0,2**-.5),{}))
    def fail(*args):
        raise OSError("synthetic write failure")
    monkeypatch.setattr(shadow,"export_raster",fail)
    out=tmp_path/"failed-output"
    result=shadow.run(source,out,report_sha256=sha)
    assert result["status"]=="FAILED" and "synthetic write failure" in result["error"]
    assert (out/"failure.json").exists() and not (out/"report.json").exists()
