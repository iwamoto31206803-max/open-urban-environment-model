"""Independent small shadow scenes and map accounting; no old fixture imports."""
import numpy as np
import pytest
import rasterio
from rasterio import Affine

from ouem import real_roof_shadow as s


def sample(flat=True,bounds=(-12,-12,12,12)):
    grid=s.roof.geometry.GridSpec(bounds)
    x,y=grid.centres()
    present=(abs(x)<2)&(abs(y)<2)
    top=np.full(x.shape,np.nan)
    top[present]=8. if flat else 8.-.75*(y[present]+1.5)
    return dict(grid=grid,maps=dict(top=top,state=present.astype(np.uint8),roof_coverage=present.astype(float),
        footprint_fraction=present.astype(float)),dem=np.full(x.shape,2.),vertical=dict(status="CONDITIONAL"),
        source=dict(source_id="authored-shadow",label="F" if flat else "S"),context={})


def test_flat_control_shared_observers_immutability_and_reproducibility():
    scene=sample()
    before=s.voxel.array_identity(scene["maps"]["top"])
    a,b=s.calculate(scene),s.calculate(scene)
    assert before==s.voxel.array_identity(scene["maps"]["top"])
    assert a["metrics"]["changed_cells"]==0 and a["metrics"]["shadow_IoU"]==1
    assert a["metrics"]["representative_shadow_cells"]==20
    np.testing.assert_array_equal(a["difference"],b["difference"])
    assert a["context"]["two_cell_border_unshadowed"]
    assert a["observers"]["requested_height_m"]==0
    np.testing.assert_allclose(a["observers"]["actual_height_above_effective_ground_m"][a["observers"]["valid"]],1.5)


def test_only_roof_expression_changes_and_small_domain_fails_closed():
    scene=sample(flat=False)
    a,b=(s.prepare(scene,m) for m in s.METHODS)
    assert all(np.array_equal(a[k],b[k]) for k in ("ids","dem"))
    assert a["metadata"]["expected_effective_ground"]==b["metadata"]["expected_effective_ground"]
    assert np.all(a["height"]>=b["height"])
    result=s.calculate(scene)
    assert result["metrics"]["shadow_to_sun"]>0 and result["metrics"]["sun_to_shadow"]==0
    with pytest.raises(ValueError,match="reach"):s.calculate(sample(bounds=(-3,-3,3,3)))


def test_zero_net_area_change_still_records_two_way_spatial_changes():
    a=np.array([[0,0,1,1,255]],dtype=np.uint8)
    b=np.array([[0,1,0,1,255]],dtype=np.uint8)
    classes,metrics=s.difference(a,b,a!=255)
    assert classes.tolist()==[[2,3,4,1,0]]
    assert metrics["shadow_cells_delta_B_minus_A"]==0
    assert metrics["changed_cells"]==2 and metrics["shadow_to_sun"]==metrics["sun_to_shadow"]==1
    assert metrics["shadow_IoU"]==pytest.approx(1/3)


def test_real_axis_bearing_and_explicit_north_south_reflection():
    direction,qa=s.axis(s.roof.geometry.GridSpec((-22580,-39850,-22540,-39810)))
    assert -.15<qa["grid_north_true_bearing_deg"]<-.14
    assert direction[0]<0 and direction[1]<0 and direction[2]>0
    a=np.array([[1,2],[3,4]],dtype=np.int8)
    assert s.shared.flip(a).tolist()==[[3,4],[1,2]]


def test_embedding_keeps_original_roofs_and_refuses_uncovered_DEM(tmp_path):
    scene=sample(bounds=(-3,-3,3,3))
    original=s.roof.grid_metadata(scene["grid"])
    item=dict(maps=scene["maps"],inputs=dict(metadata=dict(source=dict(grid=original),vertical=scene["vertical"]),dem=scene["dem"]),source_dir=tmp_path)
    p=tmp_path/"dem.tif"
    with rasterio.open(p,"w",driver="GTiff",height=80,width=80,count=1,dtype="float32",crs="EPSG:6677",
                       transform=Affine(.5,0,-20,0,-.5,20),nodata=-9999) as f:f.write(np.full((80,80),2,dtype=np.float32),1)
    expanded=s.scene(item,p,(-20,-20,20,20))
    assert np.isfinite(expanded["maps"]["top"]).sum()==16
    assert np.nanmax(expanded["maps"]["top"])==8
    assert expanded["grid"].bounds==(-13,-13,13,13)
    assert np.sum(expanded["maps"]["roof_coverage"])==16
    with pytest.raises(ValueError):s.terrain.sample_dem(p,s.roof.geometry.GridSpec((-21,-21,21,21)))
