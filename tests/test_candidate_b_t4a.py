import json

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from ouem import candidate_b_t4a as t4


def face(x0,y0,x1,y1,z):
    return (((x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z),(x0,y0,z)),)


@pytest.mark.parametrize(("east", "north"), [(0., 0.), (-22575., -39925.)])
def test_lower_envelope_of_flat_and_sloped_planes(east, north):
    flat = face(east, north, east+1, north+1, 25.)
    # z = 24 + 2*x_local + y_local, crossing the horizontal plane.
    slope = (((east,north,24.),(east+1,north,26.),(east+1,north+1,27.),
              (east,north+1,25.),(east,north,24.)),)
    shape = box(east,north,east+1,north+1)
    low, skipped = t4.lower_envelope(
        [(shape,flat),(shape,slope)],
        east+np.array([.125,.875,1.5]),north+np.array([.125,.875,.5]))
    np.testing.assert_allclose(low,[24.375,25.,np.inf],rtol=0,atol=1e-10)
    assert skipped == 0


def test_nonplanar_face_is_counted_without_contributing():
    flat = face(-22575.,-39925.,-22574.,-39924.,25.)
    a,b,c,d,_ = flat[0]
    twisted = (((*a[:2],20.),(*b[:2],20.),(*c[:2],21.),(*d[:2],20.),(*a[:2],20.)),)
    shape = Polygon([point[:2] for point in flat[0]])
    x,y = np.array([-22574.75]),np.array([-39924.75])
    low, skipped = t4.lower_envelope([(shape,twisted),(shape,flat)],x,y)
    assert skipped == 1
    np.testing.assert_allclose(low,[25.],rtol=0,atol=1e-10)
    low, skipped = t4.lower_envelope([(shape,twisted)],x,y)
    assert skipped == 1 and np.isposinf(low).all()


def fixture(lod, faces, ground=None):
    x,y = np.meshgrid([.25,.75],[.25,.75])
    if ground is None:
        ground = np.ma.array([[10.,11.],[12.,13.]])
    return t4.diagnose("raw","ouem",lod,faces,ground,np.array([[1,2],[3,4]]),x,y,box(0,0,1,1))


@pytest.mark.parametrize("lod",[1,2])
def test_planes_provenance_and_ground(lod):
    faces = [face(0,0,1,1,9),face(0,0,1,1,18)]
    # A vertical face extends below the usable lower shell.
    faces.append((((0,0,2),(0,1,2),(0,1,18),(0,0,18),(0,0,2)),))
    result = fixture(lod,faces)
    assert result["source_lod"]==lod and result["z_abs"]["min"]==2
    assert result["projected_faces"]=={"positive":2,"invalid_positive":0,"zero":1}
    assert result["lower_shell_proxy"]["minus_ground_m"]["mean"]==pytest.approx(-2.5)
    assert result["ground_m"]["mean"]==11.5
    assert result["terrain_sources"]=={"tama":2,"ward":2}
    assert result["screen"]=="NO_SCREENING_FLAGS"


def test_boundary_and_missing_ground():
    boundary = fixture(1,[face(.99,0,1.1,1,18)])
    assert boundary["footprint"]["inside_m2"]==pytest.approx(.01)
    assert boundary["footprint"]["outside_m2"]==pytest.approx(.1)
    assert boundary["flags"]==["FOOTPRINT_EXTENDS_OUTSIDE_AOI","NO_VALID_GROUND_CENTRES"]
    masked = fixture(2,[face(0,0,1,1,18)],np.ma.masked_all((2,2)))
    assert masked["ground_m"] is None and "MISSING_GROUND_CENTRES" in masked["flags"]


def test_unusual_height_relationship():
    below = fixture(2,[face(0,0,1,1,8)])
    assert below["z_top_minus_ground_m"]["max"]<0
    assert "TOP_NOT_ABOVE_ALL_SAMPLED_GROUND" in below["flags"]
    above = fixture(1,[face(0,0,1,1,15)])
    assert "LOWER_SHELL_PROXY_ABOVE_ALL_SAMPLED_GROUND" in above["flags"]


def test_vertical_inferred_conflicting_and_unresolved():
    crs = dict(vertical_epsg=6695,vertical_operation="identity_H",
               input=dict(vertical_epsg=6695,quantity="gravity_related_height",unit="metre"))
    ward = "T.P. inferred for ward; DEM datum realization and epoch unverified; identity height"
    assert t4.vertical_state(crs,ward)=="CONDITIONAL"
    assert t4.vertical_state(crs,None)=="UNRESOLVED"
    assert t4.vertical_state(crs,"other datum")=="MISMATCH"
    assert t4.vertical_state(crs|{"vertical_epsg":5773},ward)=="MISMATCH"


@pytest.mark.parametrize("missing",[False,True])
def test_missing_or_tampered_manifest_blocks(tmp_path,missing):
    if not missing:
        (tmp_path/"manifest.json").write_text("{}")
    out = tmp_path/"report"
    result = t4.run(tmp_path,tmp_path/"receipt.json",tmp_path,out)
    assert result["status"]=="BLOCKED" and result["terrain_integration_ready"] is False
    assert ("FileNotFoundError" if missing else "SHA-256 mismatch") in result["error"]
    assert json.loads((out/"report.json").read_bytes())==result
    with pytest.raises(FileExistsError):
        t4.run(tmp_path,tmp_path/"receipt.json",tmp_path,out)


def test_repeatable_diagnostic_report(tmp_path,monkeypatch):
    rows = {"z":("id2",2,[face(-22575,-39925,-22475,-39825,18)]),
            "a":("id1",1,[face(-22575,-39925,-22475,-39825,18)])}
    monkeypatch.setattr(t4,"load_inputs",lambda *args:(
        {"building_gpkg":(tmp_path/"unused","unused")},{},np.ma.array(np.full((200,200),10.)),
        np.ones((200,200),dtype=np.uint8),"CONDITIONAL"))
    monkeypatch.setattr(t4,"read_buildings",lambda *args:rows)
    monkeypatch.setattr(t4,"verify",lambda *args:None)
    for i in ("first","second"):
        result = t4.run(tmp_path,tmp_path/"receipt.json",tmp_path,tmp_path/i)
        assert result["status"]=="COMPLETED"
        assert [b["source_id"] for b in result["buildings"]]==["a","z"]
    assert (tmp_path/"first/report.json").read_bytes()==(tmp_path/"second/report.json").read_bytes()
