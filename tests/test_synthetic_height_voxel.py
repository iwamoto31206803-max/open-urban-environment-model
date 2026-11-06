"""Small authored fixtures; no Candidate B fixture imports or real datasets."""
from copy import deepcopy
import json

import numpy as np
import pytest
from shapely.geometry import box

from ouem import synthetic_height_distribution as d
from ouem import synthetic_height_voxel as v


def source(sid="a",bounds=(0,0,2,2),plane=lambda x,y:10.,face_bounds=None):
    xy=box(*(face_bounds or bounds)).exterior.coords
    face=d.Face("roof",(tuple((x,y,plane(x,y)) for x,y in xy),))
    return d.Building(sid,box(*bounds),(face,),"authored synthetic fixture")


def prepared(buildings=None,*,method="centre",dem=None,bounds=(0,0,2,2),tops=None,owners=None):
    buildings=buildings or [source()]
    derived=d.derive(d.GridSpec(bounds),buildings,method="cell_max" if method=="cell_max" else "centre")
    return v.prepare(derived,np.full((derived["grid"]["height"],derived["grid"]["width"]),2.) if dem is None else dem,
                     method=method,datum=derived["procedure"]["vertical_datum"],
                     representative_tops=tops,owners=owners)


def explicit(dem,ids,segments,height):
    return v.explicit_intervals(dem,ids,segments,height,provenance="independently authored occupied intervals")


def test_flat_three_methods_identical_and_hand_counted():
    results=[v.execute(prepared(method=m,tops={"a":10.} if m=="representative" else None))
             for m in ("representative","centre","cell_max")]
    for result in results:
        assert result["voxels"].shape==(2,2,9)
        np.testing.assert_array_equal(result["voxels"][:,:,0],1)
        np.testing.assert_array_equal(result["voxels"][:,:,1:],-3)
        assert result["qa"]["class_counts"]=={"-3":32,"-1":0,"0":0,"1":4}
        assert result["qa"]["d0"]==2
        assert result["qa"]["maximum_absolute_upper_edge_error_m"]==1
        np.testing.assert_array_equal(result["voxels"],results[0]["voxels"])


def test_sloped_roof_independent_cell_endpoints_and_differences():
    building=source(plane=lambda x,y:10+2*x+3*y)
    a=v.execute(prepared([building]))
    b=v.execute(prepared([building],method="cell_max"))
    # Top [15.5,17.5,12.5,14.5], ground 2, high rounding -> [14,16,11,13].
    assert [r["stop"] for r in a["qa"]["integer_intervals"]]==[15,17,12,14]
    assert [r["stop"] for r in b["qa"]["integer_intervals"]]==[17,19,14,16]
    assert a["qa"]["class_counts"]["-3"]==54
    assert b["qa"]["class_counts"]["-3"]==62
    assert a["qa"]["maximum_absolute_upper_edge_error_m"]==1.5
    for index,stop in zip(np.ndindex((2,2)),[15,17,12,14]):
        assert np.all(a["voxels"][index][1:stop]==-3)
        assert np.all(a["voxels"][index][stop:]==0)


def test_step_multiple_faces_kept_and_occupancy_changes():
    low=source(bounds=(0,0,.75,1),plane=lambda x,y:4).faces[0]
    low=d.Face("low",low.rings)
    high=source(bounds=(.75,0,2,1),plane=lambda x,y:9).faces[0]
    high=d.Face("high",high.rings)
    building=d.Building("a",box(0,0,2,1),(low,high),"authored step")
    a=prepared([building],bounds=(0,0,2,1))
    b=prepared([building],method="cell_max",bounds=(0,0,2,1))
    assert a["segments"].tolist()==[[[[0.,2.]],[[0.,7.]]]]
    assert b["segments"].tolist()==[[[[0.,7.]],[[0.,7.]]]]
    row=b["metadata"]["derived"]["cells"][0]["buildings"][0]
    assert row["contribution_count"]==2 and len(row["contributions"])==2
    aa,bb=v.execute(a),v.execute(b)
    assert np.count_nonzero(aa["voxels"]!=bb["voxels"])==5


def test_partial_and_unsupported_centre_are_not_filled(monkeypatch):
    building=source(bounds=(0,0,1,1),face_bounds=(0,0,.1,1),plane=lambda x,y:10+2*x)
    with pytest.raises(v.Blocked,match="TOP_UNKNOWN"):
        prepared([building],bounds=(0,0,1,1))
    p=prepared([building],method="cell_max",bounds=(0,0,1,1))
    assert p["height"][0,0]==pytest.approx(8.2)
    assert p["metadata"]["derived"]["cells"][0]["buildings"][0]["coverage_fraction"]==pytest.approx(.1)
    assert v.execute(p)["qa"]["class_counts"]["-3"]==8
    # representative is an independently requested model, never a centre fill.
    r=prepared([building],method="representative",bounds=(0,0,1,1),tops={"a":10.2})
    assert r["metadata"]["method"]=="representative"


def test_competing_buildings_require_explicit_owner_and_retain_both():
    buildings=[source("a",(0,0,2,1),lambda x,y:20),source("b",(1,0,3,1),lambda x,y:24)]
    with pytest.raises(v.Blocked,match="competition"):
        prepared(buildings,bounds=(0,0,3,1),dem=[[10,14,16]])
    p=prepared(buildings,bounds=(0,0,3,1),dem=[[10,14,16]],owners={(0,1):"a"})
    assert p["ids"].tolist()==[[1,1,2]]
    assert p["metadata"]["source_owner_mapping"]=={"a":1,"b":2}
    assert p["metadata"]["expected_effective_ground"]==[[12,12,16]]
    assert p["segments"][0,1]==[[0,8],[0,12]]
    assert len(p["metadata"]["intervals"])==4
    result=v.execute(p)
    assert result["qa"]["d0"]==12
    assert result["qa"]["ground_index"]==[[0,0,4]]
    assert result["qa"]["shape"]==[1,3,13]
    with pytest.raises(v.Blocked,match="not a cell contributor"):
        prepared(buildings,bounds=(0,0,3,1),owners={(0,1):"unknown"})


@pytest.mark.parametrize("segments,occupied", [([[0,2],[4,6]],[1,2,5,6]),
                                               ([[0,4],[2,6]],[1,2,3,4,5,6])])
def test_explicit_disjoint_and_overlapping_intervals(segments,occupied):
    p=explicit([[10]],[[1]],[[segments]],[[6]])
    result=v.execute(p)
    assert np.flatnonzero(result["voxels"][0,0]==-3).tolist()==occupied
    assert result["voxels"][0,0,0]==1
    assert len(result["qa"]["integer_intervals"])==2
    assert p["metadata"]["input_kind"]=="explicit_interval_fixture"


def test_owner_mean_ground_d0_and_surface_independent_of_raw_minimum():
    p=explicit([[10,14,13]],[[1,1,0]],[[[[0,8]],[[0,8]],[]]],[[8,8,0]])
    result=v.execute(p)
    assert result["qa"]["d0"]==12  # not raw minimum 10
    assert result["qa"]["effective_ground"]==[[12,12,13]]
    assert result["qa"]["ground_index"]==[[0,0,1]]
    assert result["qa"]["first_building_anchor"]==[[1,1,2]]
    assert result["voxels"][0,2,:2].tolist()==[-1,1]


@pytest.mark.parametrize("high,count",[(2.999999,3),(3.,3),(3.000001,3),(3.499999,3),(3.5,4),(3.500001,4)])
def test_rounding_boundary_matches_public_api(high,count):
    p=explicit([[2]],[[1]],[[[[0,high]]]],[[high]])
    result=v.execute(p)
    assert result["qa"]["class_counts"]["-3"]==count
    assert result["qa"]["integer_intervals"][0]["stop"]==count+1


def test_float32_ground_rounding_and_mixed_heights():
    p=explicit([[10,10.49999999]],[[1,2]],[[[[0,3]],[[0,3]]]],[[3,3]])
    result=v.execute(p)
    assert result["qa"]["ground_index"]==[[0,1]]  # engine casts relative DEM to float32
    _,double=v.occupancy_oracle(p,numba=False)
    assert double["ground_index"]==[[0,0]]
    p=explicit([[2,4]],[[1,2]],[[[[0,2]],[[0,20]]]],[[2,20]])
    assert v.execute(p)["voxels"].shape==(1,2,23)


def test_capacity_shortfall_not_silently_clipped():
    # ceil(.5+.5)+1 = 2 levels, but ground anchor 2 + rounded high 1 = stop 3.
    p=explicit([[0,.5]],[[0,1]],[[[],[[0,.5]]]],[[0,.5]])
    with pytest.raises(v.Blocked,match="clipped"):
        v.execute(p)
    p=explicit([[0]],[[1]],[[[[0,10]]]],[[10]])
    with pytest.raises(v.Blocked,match="explicit limit"):
        v.execute(p,max_levels=5)
    for changed in (9.,11.):
        p["height"][0,0]=changed
        with pytest.raises(v.Blocked,match="differ|clipped"):
            v.execute(p)


@pytest.mark.parametrize("low,high",[(0,.49),(-1,3),(3,2),(0,np.nan),(0,np.inf),(0,"3")])
def test_invalid_or_vanishing_intervals_rejected(low,high):
    p=explicit([[0]],[[1]],[[[[low,high]]]],[[3]])
    with pytest.raises(v.Blocked):
        v.execute(p)


@pytest.mark.parametrize("corruption",["state","z","grid","sha"])
def test_derived_edits_fail_closed(corruption):
    p=prepared()
    derived=deepcopy(p["metadata"]["derived"])
    if corruption=="state": derived["cells"][0]["buildings"][0]["state"]="UNRECOGNIZED"
    elif corruption=="z": derived["cells"][0]["buildings"][0]["absolute_top_z"]=np.nan
    elif corruption=="grid": derived["grid"]["origin_xy"]=[100,100]
    else: derived["source_identity"]="0"*64
    with pytest.raises(v.Blocked):
        v.prepare(derived,np.full((2,2),2.),method="centre",datum=derived["procedure"]["vertical_datum"])


def test_datum_ground_and_mutated_handoff_rejection():
    p=prepared()
    with pytest.raises(v.Blocked,match="datum"):
        v.prepare(p["metadata"]["derived"],p["dem"],method="centre",datum="T.P.")
    for z in (2.,1.):
        with pytest.raises(v.Blocked,match="below"):
            prepared([source(plane=lambda x,y:z)])
    with pytest.raises(v.Blocked,match="DEM"):
        prepared(dem=[[np.nan]*2]*2)
    for key in ("dem","height","ids"):
        changed=deepcopy(p)
        changed[key][0,0]+=1
        with pytest.raises(v.Blocked,match="identity"):
            v.execute(changed)


def test_inputs_reproducible_and_save_reread(tmp_path,monkeypatch):
    p=prepared()
    before=v.input_identity(p)
    a,b=v.execute(p),v.execute(p)
    assert before==v.input_identity(p)
    np.testing.assert_array_equal(a["voxels"],b["voxels"])
    ma=v.save_result(tmp_path/"a",a)
    mb=v.save_result(tmp_path/"b",b)
    assert ma==mb
    assert ma["status"]=="COMPLETED_SYNTHETIC_ONLY"
    assert ma["terrain_integration_ready"] is False
    with pytest.raises(FileExistsError):
        v.save_result(tmp_path/"a",a)
    def fail(*args,**kwargs): raise OSError("injected write failure")
    monkeypatch.setattr(np,"save",fail)
    with pytest.raises(OSError): v.save_result(tmp_path/"partial",a)
    assert not (tmp_path/"partial"/"manifest.json").exists()


def test_save_rejects_changed_result(tmp_path):
    result=v.execute(prepared())
    result["voxels"][0,0,1]=0
    with pytest.raises(v.Blocked,match="changed"):
        v.save_result(tmp_path/"changed",result)
    assert not (tmp_path/"changed").exists()


def test_demonstration_expected_rejections_and_no_false_completion(tmp_path,monkeypatch):
    report=v.demonstration_run(tmp_path/"valid")
    assert report["status"]=="PASS_SYNTHETIC_ONLY"
    assert report["cases"]["flat"]["comparisons"]["centre_vs_cell_max"]["differing_voxels"]==0
    assert report["cases"]["slope"]["comparisons"]["centre_vs_cell_max"]["differing_voxels"]==8
    assert report["cases"]["thin_eave"]["methods"]["centre"]["status"]=="BLOCKED"
    assert report["cases"]["roof_hole"]["methods"]["cell_max"]["status"]=="BLOCKED"
    assert (tmp_path/"valid"/"manifest.json").exists()
    real=v.prepare
    def fail(*args,**kwargs):
        if args[0]["source_provenance"][0]["source_id"]=="synthetic-flat":
            raise v.Blocked("injected unresolved condition")
        return real(*args,**kwargs)
    monkeypatch.setattr(v,"prepare",fail)
    failed=v.demonstration_run(tmp_path/"blocked")
    assert failed["status"]=="BLOCKED"
    assert not (tmp_path/"blocked"/"manifest.json").exists()


def test_oracle_does_not_accept_public_api_corruption(monkeypatch):
    from voxcity.generator.voxelizer import Voxelizer
    real=Voxelizer.generate_combined
    def corrupt(self,*args,**kwargs):
        result=real(self,*args,**kwargs)
        result[0,0,1]=0
        return result
    monkeypatch.setattr(Voxelizer,"generate_combined",corrupt)
    with pytest.raises(v.Blocked,match="oracle"):
        v.execute(prepared())
