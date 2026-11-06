"""Self-contained numerical-anchor fixtures; no Candidate B fixture imports."""
from copy import deepcopy
import json

import numpy as np
import pytest

from ouem import real_roof_voxel as r


def fixture(top=(12.49, 13.5), ground=(10., 10.2)):
    grid = r.roof.geometry.GridSpec((0, 0, 3, 1))
    ring = [[0,0,ground[0]], [2,0,ground[1]], [2,1,ground[1]], [0,1,ground[0]], [0,0,ground[0]]]
    identity = dict(profile=r.roof.PROFILE, vertical=deepcopy(r.roof.VERTICAL), grid=r.roof.grid_metadata(grid),
        ground_faces=[dict(polygon_id="ground", standard_xyz_rings=[ring])], label="F", source_id="fixture-real-profile",
        ouem_id="fixture-id", faces=[])
    maps = dict(top=np.array([[*top, np.nan]]), state=np.array([[1,1,0]], dtype=np.uint8),
                roof_coverage=np.array([[1.,.01,0.]]), footprint_fraction=np.array([[1.,.25,0.]]))
    inputs, qa = r.prepare(identity, maps)
    return dict(inputs=inputs, qa=qa, maps=maps)


def test_minimum_ground_vertex_anchor_and_positive_relative_heights():
    item=fixture()
    assert item["qa"]["anchor_H"] == 10.
    assert item["qa"]["ground_vertex_H_range"] == [10.,10.2]
    np.testing.assert_allclose(item["inputs"]["height"], [[2.49,3.5,0.]])
    assert item["inputs"]["segments"].tolist() == [[[[0.,2.49]],[[0.,3.5]],[]]]
    assert item["inputs"]["metadata"]["profile"] == r.PROFILE
    assert "synthetic" not in str(item["inputs"]["metadata"])
    assert item["qa"]["expansion_vs_support_m2"] == pytest.approx(.99)
    reloaded=json.loads(json.dumps(item["inputs"]["metadata"]["source"]))
    rebuilt,_=r.prepare(reloaded,item["maps"])
    assert r.voxel.input_identity(rebuilt)==r.voxel.input_identity(item["inputs"])


@pytest.mark.parametrize("kind", ["nonpositive", "nonfinite", "unknown", "grid", "ground", "fraction"])
def test_invalid_b0_inputs_fail_closed(kind):
    item=fixture()
    identity=deepcopy(item["inputs"]["metadata"]["source"])
    maps=deepcopy(item["maps"])
    if kind=="nonpositive": maps["top"][0,0]=10.
    elif kind=="nonfinite": maps["top"][0,0]=np.inf
    elif kind=="unknown": maps["state"][0,0]=2
    elif kind=="grid": identity["grid"]["origin_xy"][0]=.5
    elif kind=="ground": identity["ground_faces"][0]["standard_xyz_rings"][0][0][2]=np.nan
    else: maps["roof_coverage"][0,0]=0
    with pytest.raises(ValueError): r.prepare(identity,maps)


def test_public_voxelizer_hand_counted_occupancy_rounding_and_reproducibility():
    item=fixture()
    before=r.voxel.input_identity(item["inputs"])
    a,b=r.execute(item),r.execute(item)
    expected=np.zeros((1,3,5),dtype=np.int8)
    expected[:,:,0]=1
    expected[0,0,1:3]=-3
    expected[0,1,1:5]=-3
    np.testing.assert_array_equal(a["voxels"],expected)
    np.testing.assert_array_equal(a["voxels"],b["voxels"])
    assert before==r.voxel.input_identity(item["inputs"])
    assert a["qa"]["d0"]==10.
    assert a["qa"]["distinct_building_column_heights_m"]==[2,4]
    np.testing.assert_allclose(a["upper"][0,:2],[13,15])
    np.testing.assert_allclose(a["lower"][0,:2],[12,14])
    item["inputs"]["height"][0,0]+=1
    with pytest.raises(ValueError,match="handoff"):r.execute(item)


def test_quantized_empty_interval_and_capacity_are_rejected():
    with pytest.raises(ValueError,match="vanishes"):r.execute(fixture(top=(10.1,13.5)))
    item=fixture()
    item["inputs"]["height"][0,1]=1
    with pytest.raises(ValueError):r.voxel.occupancy_oracle(item["inputs"],numba=True)


def test_decimal_constant_dem_keeps_exact_anchor_without_ulp_relief():
    anchor=24.888792
    shape=(1,40)
    ids=np.ones(shape,dtype=np.int32)
    ids[0,-1]=0
    segments=np.empty(shape,dtype=object)
    for index in np.ndindex(shape):segments[index]=[[0.,2.]] if ids[index] else []
    inputs=dict(ids=ids,dem=np.full(shape,anchor),segments=segments,height=(ids*2.).astype(float),metadata={})
    expected,qa=r.voxel.occupancy_oracle(inputs,numba=True)
    assert qa["d0"]==anchor and np.all(np.array(qa["effective_ground"])==anchor)
    result=r.voxel.execute_arrays(inputs)
    np.testing.assert_array_equal(result["voxels"],expected)


def test_missing_real_data_is_not_executed_and_bad_sha_is_blocked(tmp_path):
    a=r.run(tmp_path/"missing",tmp_path/"absent",tmp_path/"a",tmp_path)
    assert a["technical_execution"]=="NOT_EXECUTED"
    assert not (tmp_path/"a/manifest.json").exists()
    audit=tmp_path/"audit"
    audit.mkdir()
    (audit/"manifest.json").write_text('{}')
    b=r.run(tmp_path/"missing",audit,tmp_path/"b",tmp_path)
    assert b["technical_execution"]=="BLOCKED" and b["stopped_at"]=="B0"
    with pytest.raises(FileExistsError):r.run(tmp_path/"missing",audit,tmp_path/"b",tmp_path)


def test_partial_b1_write_failure_never_completes(tmp_path,monkeypatch):
    class Watch:
        identities={}
        def unchanged(self):pass
    monkeypatch.setattr(r,"load_inputs",lambda *args:({"F":fixture()},Watch(),{}))
    def fail(*args):raise OSError("injected save failure")
    monkeypatch.setattr(r,"save_building",fail)
    result=r.run(tmp_path,tmp_path,tmp_path/"failed",tmp_path)
    assert result["technical_execution"]=="BLOCKED" and result["stopped_at"]=="B1"
    assert json.loads((tmp_path/"failed/gate_b0.json").read_bytes())["status"]=="PASS"
    assert not (tmp_path/"failed/manifest.json").exists()
