from copy import deepcopy
from hashlib import sha256

import numpy as np
import pytest

from ouem import candidate_b_canopy as canopy
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_compatibility_probe import snapshot


DEM_SHA = "d"*64


def authored():
    voxels,ids,raw,ground,xy,roi,meta,index,valid,xyz=snapshot()
    arrays=dict(voxels=voxels,ids=ids,raw_dem=raw,ground_abs=ground,centres_xy=xy,roi=roi,
                observer_index=index,observer_valid=valid,observer_xyz=xyz)
    segments=np.empty(ids.shape,object)
    for ij in np.ndindex(ids.shape):
        segments[ij]=[[0.,3.]] if ids[ij] else []
    height=np.where(ids>0,3.,0.)
    sampled=dict(top=ground+5.,bottom=ground+2.,state=np.ones(ids.shape,dtype="uint8"),
                 missing=np.zeros(ids.shape,bool),outside=np.zeros(ids.shape,bool),
                 valid=np.ones(ids.shape,bool),candidate=np.ones(ids.shape,bool))
    envelope=dict(quantity="absolute_elevation_m",vertical_reference="T.P.",source_dem_sha256=DEM_SHA)
    return arrays,meta,segments,sampled,envelope,height


def integrate(data):
    arrays,metadata,segments,sampled,envelope,height=data
    return canopy.integrate(arrays,metadata,segments,sampled,envelope,
                            source_dem_sha256=DEM_SHA,building_height_grid=height)


def test_public_b1_integration_preserves_authored_base_and_pair(tmp_path):
    data=authored()
    arrays,_,segments,sampled,_,height=data
    before=deepcopy(data)
    for array in (*arrays.values(),*sampled.values(),height):
        array.flags.writeable=False
    current,absent,tree,high,low,qa=integrate(data)
    expected=np.zeros((4,6,8),bool)
    expected[:,:,3:6]=True
    expected[1,2,3]=False  # Building occupies k=1,2,3 and wins over TREE.
    np.testing.assert_array_equal(tree,expected)
    np.testing.assert_array_equal(np.where(tree,0,current),arrays["voxels"])
    np.testing.assert_array_equal(absent,arrays["voxels"])
    assert qa["tree_voxels"]==71 and qa["tree_columns"]==24
    assert qa["building_candidate_columns"]==1
    assert qa["building_priority_removed_tree_voxels"]==1
    assert qa["top_edge_minus_envelope_H_m"]["min"]==1.
    assert qa["bottom_edge_minus_envelope_H_m"]["max"]==1.
    assert qa["vertical_domain"]["added_upper_air_layers"]==0
    second=integrate(data)
    np.testing.assert_array_equal(current,second[0])
    assert qa==second[-1]
    for key,array in arrays.items():
        np.testing.assert_array_equal(array,before[0][key])
    for key,array in sampled.items():
        np.testing.assert_array_equal(array,before[3][key])
    for ij in np.ndindex(segments.shape):
        assert segments[ij]==before[2][ij]
    np.save(tmp_path/"current.npy",current,allow_pickle=False)
    np.testing.assert_array_equal(np.load(tmp_path/"current.npy",mmap_mode="r"),current)
    print("synthetic TREE=71 columns=24 current_bytes_sha256="+sha256(current.tobytes()).hexdigest())


def test_only_required_upper_z_added_and_existing_occupancy_fixed():
    data=authored()
    data[3]["top"][:]=37.  # Ground=25; relative upper=12.
    data[3]["bottom"][:]=34.  # Relative lower=9; first air k=1.
    current,absent,tree,*_,qa=integrate(data)
    assert current.shape==absent.shape==(4,6,13)
    expected=np.zeros((4,6,13),bool)
    expected[:,:,10:13]=True
    np.testing.assert_array_equal(tree,expected)
    np.testing.assert_array_equal(absent[:,:,:8],data[0]["voxels"])
    assert not absent[:,:,8:].any()
    assert qa["vertical_domain"]["D0_H_m"]==25.
    assert qa["vertical_domain"]["added_upper_air_layers"]==5


def test_missing_outside_state_below_and_zero_depth_are_distinct():
    data=authored()
    sampled=data[3]
    sampled["missing"][0,0]=True
    sampled["top"][0,0]=-9999.
    sampled["outside"][0,1]=True
    sampled["missing"][0,1]=True
    sampled["state"][0,2]=2
    sampled["valid"][0,:3]=False
    sampled["candidate"][0,:3]=False
    sampled["bottom"][0,3]=24.  # Below effective ground; exclude whole crown.
    sampled["top"][0,4]=sampled["bottom"][0,4]=25.
    sampled["candidate"][0,4]=False
    *_,tree,high,low,qa=integrate(data)
    assert not tree[0,:5].any()
    assert qa["missing_inside_columns"]==qa["outside_columns"]==qa["invalid_state_inside_columns"]==1
    assert qa["below_effective_ground_excluded_columns"]==qa["zero_depth_valid_columns"]==1


@pytest.mark.parametrize("fault",["vertical","quantity","terrain","D0","inverted","valid_nan","state","base"])
def test_invalid_inputs_rejected_without_correction(fault):
    data=authored()
    if fault=="vertical":
        data[4]["vertical_reference"]="UNRESOLVED"
    elif fault=="quantity":
        data[4]["quantity"]="height_above_ground_m"
    elif fault=="terrain":
        data[4]["source_dem_sha256"]="e"*64
    elif fault=="D0":
        data[1]["d0_effective_abs_m"]=24.
    elif fault=="inverted":
        data[3]["bottom"][0,0]=31.
    elif fault=="valid_nan":
        data[3]["top"][0,0]=np.nan
    elif fault=="state":
        data[3]["state"][0,0]=2
    else:
        data[0]["voxels"][0,0,0]=0
    with pytest.raises(GeometryValidationError):
        integrate(data)


def test_all_missing_does_not_manufacture_successful_tree():
    data=authored()
    data[3]["missing"][:]=True
    data[3]["valid"][:]=False
    data[3]["candidate"][:]=False
    with pytest.raises(GeometryValidationError,match="no candidate"):
        integrate(data)


def test_incomplete_audit_is_not_real_integration(tmp_path):
    source=tmp_path/"source"
    source.mkdir()
    folder=tmp_path/"envelope"
    folder.mkdir()
    envelope=folder/"manifest.json"
    envelope.write_text("{}",encoding="utf-8")
    out=tmp_path/"audit"
    result=canopy.audit(source,envelope,out)
    assert result["status"]=="BLOCKED"
    assert result["real_canopy_integration"]=="NOT_VERIFIED"
    assert not list(out.glob("*.npy"))
    with pytest.raises(FileExistsError):
        canopy.audit(source,envelope,out)
    with pytest.raises(GeometryValidationError,match="outside"):
        canopy.audit(source,envelope,source/"audit")
