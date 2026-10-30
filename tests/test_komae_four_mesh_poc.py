from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from ouem import komae_four_mesh_poc as p
from ouem import real_komae_source_h as old
from ouem.adapters.voxcity import VoxCityAdapterError


def test_four_mesh_scope_is_separate():
    assert old.MEMBERS == ("53393456_bldg_6697_op.gml", "53393466_bldg_6697_op.gml")
    assert len(p.MEMBERS) == 4 and set(old.MEMBERS) < set(p.MEMBERS)
    assert p.PROFILE.startswith("exploratory-")


def test_effective_ground_uses_owned_cells_and_preserves_inputs():
    buildings = gpd.GeoDataFrame(dict(source_id=["a","b"],ouem_id=["oa","ob"],id=[1,2]),
                                geometry=[box(0,0,1,1),box(1,0,2,1)],crs=6677)
    ids = np.array([[1,1],[0,0]])
    dem = np.array([[10.,12.],[999.,888.]])
    original = dem.copy()
    records, missing = p.update_heights(buildings, {"oa":[10.,20.],"ob":[10.,30.]}, ids, dem)
    assert records[0]["ground_eff_abs"] == 11 and records[0]["height"] == 9
    assert records[0]["min_height"] == 0 and records[0]["z_top_abs"] == 20
    assert missing == [dict(source_id="b",ouem_id="ob",voxcity_id=2,reason="NO_OWNED_ENGINE_CELL")]
    np.testing.assert_array_equal(original,dem)
    assert buildings.id.tolist() == [1,2]
    with pytest.raises(VoxCityAdapterError,match="non-positive"):
        p.update_heights(buildings,{"oa":[1.,2.]},ids,dem)


def test_previous_comparison_checks_xyz_not_just_xy(tmp_path, monkeypatch):
    previous=tmp_path/"previous.gpkg"
    previous.write_bytes(b"placeholder")
    tree=("Polygon",(((0,0,10),(1,0,20),(0,1,20),(0,0,10)),))
    record=(tree,None,None)
    monkeypatch.setattr(p,"read_standard",lambda *a:{"a":record})
    result=p.compare_previous({"a":record,"b":record},previous)
    assert result["changed_records"] == [] and result["additional_ids"] == ["b"]
    assert p.compare_previous({"a":(tree,2,None)},previous)["changed_records"] == ["a"]
    with pytest.raises(ValueError,match="old IDs missing"):
        p.compare_previous({},previous)


def test_invalid_member_scope_fails_before_creating_output(tmp_path):
    with pytest.raises(ValueError,match="members"):
        old.run(SimpleNamespace(),members=("../bad.gml",))


def test_consumer_failure_is_recorded_without_engine_or_overwrite(tmp_path, monkeypatch):
    import json
    run=tmp_path/"new-run"
    run.mkdir()
    paths={key:tmp_path/name for key,name in
           (("terrain","terrain.tif"),("study_area","area.yaml"),("previous_standard","old.gpkg"))}
    for path in paths.values(): path.write_bytes(b"protected")
    paths["terrain"].with_suffix(".tif.manifest.json").write_text("{}")
    args=SimpleNamespace(run_dir=run, artifact_root=tmp_path, **paths)
    monkeypatch.setattr(p,"validate_source_h_standard",lambda *a,**kw:
                        dict(technical_validation="FAIL",issues=["authored failure"]))
    with pytest.raises(ValueError,match="authored failure"):
        p.voxel_phase(args,{"standard":{"manifest":"unused"}})
    report=json.loads((run/"voxcity/report.json").read_text())
    assert report["status"] == "FAILED" and report["input_unchanged"]
    assert report["formal_acceptance"] == "NOT_VERIFIED"
    assert list((run/"voxcity").iterdir()) == [run/"voxcity/report.json"]
    with pytest.raises(FileExistsError):
        p.voxel_phase(args,{})


def test_previous_face_permutation_is_reported_without_losing_xyz_checks(tmp_path, monkeypatch):
    previous=tmp_path/"old.gpkg"
    previous.write_bytes(b"old")
    a=("Polygon",(((0,0,10),(1,0,20),(0,1,20),(0,0,10)),))
    b=("Polygon",(((3,0,11),(4,0,21),(3,1,21),(3,0,11)),))
    old=("MultiPolygon",(a,b))
    new=("MultiPolygon",(b,a))
    monkeypatch.setattr(p,"read_standard",lambda *args:{"a":(old,None,5.)})
    result=p.compare_previous({"a":(new,None,5.)},previous)
    assert result["changed_records"] == [] and result["ordered_record_differences"] == ["a"]
    # Same vertex bag but changed ring connectivity must still fail comparison.
    changed=("Polygon",(((0,0,10),(0,1,20),(1,0,20),(0,0,10)),))
    result=p.compare_previous({"a":(("MultiPolygon",(b,changed)),None,5.)},previous)
    assert result["changed_records"] == ["a"]


def test_prepared_run_is_referenced_and_never_overwritten(tmp_path, monkeypatch):
    import json
    prepared=tmp_path/"prepared"
    prepared.mkdir()
    saved=dict(status="COMPLETED",input_unchanged=True,standard={"manifest":"verified-at-use"})
    (prepared/"report.json").write_text(json.dumps(saved))
    output=tmp_path/"new-output"
    argv=["poc"]
    for name,value in {"artifact-root":tmp_path,"run-dir":output,"zip":"unused.zip",
        "converter":"unused.exe","terrain":"terrain.tif","study-area":"area.yaml",
        "previous-standard":"previous.gpkg","prepared-standard-run":prepared}.items():
        argv += ["--"+name,str(value)]
    monkeypatch.setattr(p.sys,"argv",argv)
    calls=[]
    monkeypatch.setattr(p,"voxel_phase",lambda args,report:calls.append(report))
    monkeypatch.setattr(p.source,"run",lambda *a,**kw:pytest.fail("must not rerun Raw stages"))
    p.main()
    reference=json.loads((output/"source-reference.json").read_text())
    assert reference["report_sha256"] == p.source.digest(prepared/"report.json")
    assert calls == [saved]
    with pytest.raises(FileExistsError): p.main()
    assert json.loads((prepared/"report.json").read_text()) == saved
