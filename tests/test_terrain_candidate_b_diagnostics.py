import json

import numpy as np
import pytest
import rasterio

from ouem import terrain_candidate_b_diagnostics as d


def test_distribution_and_masks():
    tama = np.array([[10.,10.,np.nan],[10.,10.,np.nan],[10.,10.,np.nan]])
    ward = np.array([[np.nan,10.125,10.25],[np.nan,10.,10.],[np.nan,9.75,10.]])
    summary, delta, mask, distance = d.overlap_diagnostics(tama,ward)
    np.testing.assert_array_equal(mask,[[1,3,2],[1,3,2],[1,3,2]])
    np.testing.assert_allclose(delta[:,1],[.125,0,-.25])
    assert np.isnan(delta[:,[0,2]]).all()
    assert summary["total"]["quantiles"]["p50"]==0
    assert summary["total"]["abs_exceeds_m"]=={"0.05":2,"0.1":2,"0.2":1,"0.5":0}
    assert summary["extremes"][0]["xy"]==(-22574.25,-39826.25)
    assert summary["outliers"]["0.2"]["n"]==1
    for data in distance:
        np.testing.assert_array_equal(data[:,1],[.5,.5,.5])


def test_policy_switches_and_mesh_edges():
    tama = np.array([[10.,11.,np.nan],[10.,11.,np.nan]])
    ward = np.array([[np.nan,20.,22.],[np.nan,20.,22.]])
    mesh = np.array([[3423]*3,[3433]*3])
    t,tr = d.policy(tama,ward,mesh,mesh,"TAMA")
    w,wr = d.policy(ward,tama,mesh,mesh,"WARD")
    assert t["chosen"]=={"TAMA":4,"WARD":2}
    assert w["chosen"]=={"WARD":4,"TAMA":2}
    assert t["switch_edges"]==w["switch_edges"]==2
    assert t["largest_switch"]["jump_m"]==11
    assert w["largest_switch"]["jump_m"]==10
    assert [x["x0"] for x in tr if x["source_switch"]]==[-22574.25]*2
    assert [x["x0"] for x in wr if x["source_switch"]]==[-22574.75]*2
    assert t["directions"]["south"]["within_source_mesh_edge"]["n"]==3


def test_diagnostic_georeference_and_nodata(tmp_path):
    path = tmp_path/"difference.tif"
    d.diagnostic_map(path,[np.array([[.25,np.nan]])],"float64",np.nan,["difference"])
    with rasterio.open(path) as ds:
        assert ds.crs.to_epsg()==6677 and ds.transform==d.AFFINE
        assert ds.read(1,masked=True).mask.tolist()==[[False,True]]
        assert ds.read(1)[0,0]==.25
    assert d.raw_geotags(path)["tiepoint"][:5]==(0,0,0,d.AOI[0],d.AOI[3])


def test_hash_failure_retains_only_blocked_report(tmp_path):
    inputs = tmp_path/"inputs"
    (inputs/"tama").mkdir(parents=True)
    (inputs/"tama/09LD3423.tif").write_bytes(b"not the pinned TIFF")
    out = tmp_path/"out"
    result = d.run(inputs,out)
    assert result["status"]=="BLOCKED" and "SHA-256 mismatch" in result["error"]
    assert result["terrain_integration_ready"] is False
    assert [p.name for p in out.iterdir()]==["diagnostic_report.json"]
    assert json.loads((out/"diagnostic_report.json").read_bytes())["status"]=="BLOCKED"
    with pytest.raises(FileExistsError):
        d.run(inputs,out)
