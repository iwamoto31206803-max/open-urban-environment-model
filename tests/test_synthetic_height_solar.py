"""Authored geometric expectations, independent of the Solar/DDA implementation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

from ouem import synthetic_height_solar as s
from ouem import synthetic_height_distribution as d
from ouem import synthetic_height_voxel as v


@pytest.mark.parametrize("name,limits",[
    ("flat",{"representative":(7.5,6.5),"centre":(7.5,6.5),"cell_max":(7.5,6.5)}),
    ("slope",{"representative":(8.5,7.5),"centre":(5.5,4.5),"cell_max":(6.5,5.5)}),
    ("step",{"representative":(8.5,7.5),"centre":(6.5,5.5),"cell_max":(7.5,6.5)}),
])
def test_all_maps_against_manual_shadow_intercepts(name,limits):
    # For each roof column: northern face Y + upper voxel edge Z - observer Z.
    # At 45 deg, rays at the limiting Y only touch a corner and are not blocked.
    # Flat edge=9; slope per-row edges centre=[7,8,9,10], max=[8,9,9,10].
    # Step boundary y=.25: centre high row starts at y=0, max high row at y=1.
    sample=s.scene(name)
    before=v.array_identity(sample["dem"]),[b.footprint.wkb for b in sample["buildings"]]
    result=s.calculate_scene(sample)
    x,y=sample["grid"].centres()
    building=(abs(x)<2)&(abs(y)<2)
    assert result["valid"].sum()==560 and sample["roi"].sum()==96
    ceiling=800/np.sqrt(2)
    for method,(binary_limit,solar_limit) in limits.items():
        binary_shadow=(abs(x)<2)&(y>2)&(y<binary_limit-1e-9)
        solar_shadow=(abs(x)<2)&(y>2)&(y<solar_limit-1e-9)
        expected=np.where(building,255,np.where(binary_shadow,0,1)).astype("uint8")
        np.testing.assert_array_equal(result["maps"][method]["binary"],expected)
        irradiance=np.where(building,np.nan,np.where(solar_shadow,0.,ceiling))
        np.testing.assert_allclose(result["maps"][method]["solar"],irradiance,rtol=0,atol=1e-9,equal_nan=True)
        assert np.all(result["observation"]["binary"]["index"][~building]==1)
        assert np.all(result["observation"]["solar"]["index"][~building]==2)
        assert np.all(result["observation"]["binary"]["xyz"][...,2][~building]==3.5)
        assert np.all(result["observation"]["solar"]["xyz"][...,2][~building]==4.5)
        assert result["statistics"][method]["roi"]["binary"]["shadow"]==int(binary_shadow.sum())
        assert result["statistics"][method]["domain"]["binary"]["excluded"]==16
    assert before==(v.array_identity(sample["dem"]),[b.footprint.wkb for b in sample["buildings"]])
    if name=="flat":
        assert all(c["roi"]["binary_changed"]==c["roi"]["solar_changed"]==0 for c in result["comparisons"].values())
    else:
        change=result["comparisons"]["centre_to_cell_max"]["roi"]
        assert change["sun_to_shadow"]==change["solar_decreased"]==4
        assert change["shadow_to_sun"]==change["solar_increased"]==0
        assert change["mean_delta_W_m2"]==pytest.approx(-ceiling/24)
        # Lowering representative tops can legitimately increase direct irradiance.
        assert result["comparisons"]["representative_to_centre"]["roi"]["solar_increased"]>0


def test_axis_origin_true_north_cardinal_geometry_and_explicit_reflection():
    grid=s.scene("flat")["grid"]
    audit=s.axis_audit(grid)
    assert audit["axis0_api_reference_true_bearing_deg"]==0
    assert max(map(abs,audit["corner_meridian_convergence_deg"]))<.00008
    a=np.arange(24).reshape(4,6)
    np.testing.assert_array_equal(s.flip(a),a[::-1])
    np.testing.assert_array_equal(s.flip(s.flip(a)),a)
    checks=s.cardinal_geometry_check(grid)
    assert len(checks)==8
    assert [r["shadow_cells"] for r in checks]==[20,16]*4
    # Direct direction components independently use north/east/up coordinates.
    np.testing.assert_allclose(s.solar_direction(180),[-1/np.sqrt(2),0,1/np.sqrt(2)],atol=1e-12)
    np.testing.assert_allclose(s.solar_direction(90),[0,1/np.sqrt(2),1/np.sqrt(2)],atol=1e-12)


def test_missing_axis_reflection_is_detected(monkeypatch):
    monkeypatch.setattr(s,"flip",lambda a:np.ascontiguousarray(a))
    with pytest.raises(v.Blocked,match="cardinal"):
        s.cardinal_geometry_check(s.scene("flat")["grid"],binary_only=True)


def test_wrong_frame_is_not_automatically_rotated():
    with pytest.raises(v.Blocked,match="frame"):
        s.axis_audit(d.GridSpec((100,100,124,124)))


def test_common_air_capacity_and_unchanged_layers():
    result=s.calculate_scene(s.scene("slope"))
    assert {m:result["models"][m].shape for m in s.METHODS}=={
        "representative":(24,24,9),"centre":(24,24,9),"cell_max":(24,24,9)}
    assert result["capacity"]["centre"]["air_layers_added"]==1
    assert result["results"]["centre"]["voxels"].shape==(24,24,8)
    for method in s.METHODS:
        raw=result["results"][method]["voxels"]
        common=result["models"][method]
        np.testing.assert_array_equal(common[:,:,:raw.shape[2]],raw)
        assert not common[:,:,raw.shape[2]:].any()
        assert result["capacity"][method]["original_vs_shared_evaluation"]=="PASS"
    assert not result["models"]["centre"][:,:,8:].any()


@pytest.mark.parametrize("change",["DEM","ID","grid","D0","voxels"])
def test_mismatched_models_fail_closed(change):
    result=s.calculate_scene(s.scene("flat"),binary_only=True)
    models=deepcopy(result["results"])
    row=models["centre"]
    if change=="DEM": row["inputs"]["dem"][0,0]+=1
    elif change=="ID": row["inputs"]["ids"][0,0]=1
    elif change=="grid": row["inputs"]["metadata"]["grid_identity"]="wrong"
    elif change=="D0": row["qa"]["d0"]+=1
    else: row["voxels"][0,0,0]=0
    with pytest.raises(v.Blocked): s.shared_models(models)


def test_observer_motion_is_rejected():
    result=s.calculate_scene(s.scene("flat"),binary_only=True)
    models=deepcopy(result["models"])
    models["centre"][0,0,0]=-1
    models["centre"][0,0,1]=1
    with pytest.raises(ValueError,match="observer"):
        s.common_observers(models,result["grid"],2.,np.full((24,24),2.))


def test_no_roof_support_is_not_filled():
    sample=s.scene("flat")
    b=sample["buildings"][0]
    sample["buildings"]=[d.Building(b.source_id,b.footprint,(),b.provenance)]
    with pytest.raises(v.Blocked,match="TOP_UNKNOWN"):
        s.calculate_scene(sample)


def test_no_observers_or_overlapping_owners_are_blocked():
    sample=s.scene("flat")
    polygon=box(*sample["grid"].bounds)
    face=d.Face("all",(tuple((x,y,8.) for x,y in polygon.exterior.coords),))
    sample["buildings"]=[d.Building("all",polygon,(face,),"all-building rejection fixture")]
    with pytest.raises(ValueError,match="observer"):
        s.calculate_scene(sample)
    sample=s.scene("flat")
    b=sample["buildings"][0]
    sample["buildings"].append(d.Building("other",b.footprint,b.faces,b.provenance))
    with pytest.raises(v.Blocked,match="competition"):
        s.calculate_scene(sample)


def test_public_solar_receives_projected_metadata_and_reflected_grids(monkeypatch):
    from voxcity.simulator.solar import radiation
    result=s.calculate_scene(s.scene("slope"),binary_only=True)
    real=radiation.get_direct_solar_irradiance_map
    calls=[]
    def checked(scene,azimuth,elevation,dni,**kwargs):
        assert scene.voxels.meta.crs=="EPSG:6677" and scene.voxels.meta.meshsize==1
        assert scene.voxels.meta.bounds==(-12,-12,12,12)
        assert scene.extras=={"rotation_angle":0.}
        assert (azimuth,elevation,dni)==(180.,45.,800.)
        assert kwargs["view_point_height"]==1.5 and kwargs["include_building_roofs"] is False
        np.testing.assert_array_equal(scene.buildings.heights,result["results"]["centre"]["inputs"]["height"][::-1])
        calls.append(True)
        return real(scene,azimuth,elevation,dni,**kwargs)
    monkeypatch.setattr(radiation,"get_direct_solar_irradiance_map",checked)
    s.evaluate(result["models"]["centre"],result["results"]["centre"]["inputs"],result["grid"])
    assert len(calls)==1


@pytest.mark.parametrize("bad",["negative","mask","nonfinite","mutation"])
def test_solar_invalid_values_or_mutation_rejected(monkeypatch,bad):
    from voxcity.simulator.solar import radiation
    result=s.calculate_scene(s.scene("flat"),binary_only=True)
    real=radiation.get_direct_solar_irradiance_map
    def corrupt(scene,*args,**kwargs):
        values=real(scene,*args,**kwargs)
        if bad=="negative": values[0,0]=-1
        elif bad=="mask": values[11,11]=0
        elif bad=="nonfinite": values[0,0]=np.nan
        else: scene.tree_canopy.top[0,0]=1
        return values
    monkeypatch.setattr(radiation,"get_direct_solar_irradiance_map",corrupt)
    with pytest.raises(v.Blocked):
        s.evaluate(result["models"]["centre"],result["results"]["centre"]["inputs"],result["grid"])


def test_run_reproducible_new_only_and_binary_survives_solar_failure(tmp_path,monkeypatch):
    a=s.run(tmp_path/"a")
    b=s.run(tmp_path/"b")
    assert a["status"]==b["status"]=="COMPLETED_SYNTHETIC_ONLY"
    assert a["binary_shadow"]==a["direct_solar"]=="PASS"
    def inventory(root):
        return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}
    assert inventory(tmp_path/"a")==inventory(tmp_path/"b")
    with pytest.raises(FileExistsError): s.run(tmp_path/"a")
    def fail(*args,**kwargs): raise v.Blocked("injected Solar API failure")
    monkeypatch.setattr(s,"direct_solar",fail)
    failed=s.run(tmp_path/"partial")
    assert failed["status"]=="BLOCKED" and failed["binary_shadow"]=="PASS" and failed["direct_solar"]=="BLOCKED"
    assert not (tmp_path/"partial"/"manifest.json").exists()
    for scene in ("flat","slope","step"):
        assert (tmp_path/"partial"/scene/"centre"/"binary.npy").exists()
    assert json.loads((tmp_path/"partial"/"binary_report.json").read_text())["binary_shadow"]=="PASS"


def test_partial_save_never_reports_completed(tmp_path,monkeypatch):
    def fail(*args,**kwargs): raise OSError("injected write failure")
    monkeypatch.setattr(np,"save",fail)
    result=s.run(tmp_path/"bad")
    assert result["status"]=="BLOCKED"
    assert not (tmp_path/"bad"/"manifest.json").exists()


def test_failed_root_manifest_publication_is_not_completed(tmp_path,monkeypatch):
    real=Path.rename
    target=tmp_path/"bad"/"manifest.json"
    def fail(self,destination):
        if destination==target: raise OSError("injected root manifest publication failure")
        return real(self,destination)
    monkeypatch.setattr(Path,"rename",fail)
    result=s.run(tmp_path/"bad")
    assert result["status"]=="BLOCKED"
    assert result["binary_shadow"]==result["direct_solar"]=="PASS"
    assert not target.exists()
