"""Small analytic fixtures; no real-data fixtures or engine execution."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from shapely.geometry import Polygon, box

from ouem import real_roof_distribution as r
from ouem import synthetic_height_distribution as g


def face(name,bounds,z=lambda x,y:0.):
    return g.Face(name,(tuple((x,y,z(x,y)) for x,y in box(*bounds).exterior.coords),))


def fixture(faces=None,footprint=None):
    faces=faces or [face("roof",(0,0,2,1))]
    footprint=box(0,0,2,1) if footprint is None else footprint
    ground_rings=(tuple((x,y,-10.) for x,y in footprint.exterior.coords),
                  *(tuple((x,y,-10.) for x,y in ring.coords) for ring in footprint.interiors))
    building=g.Building("fixture",footprint,tuple(faces),"independent synthetic test fixture")
    identity=dict(source_id="fixture",ouem_id="ouem-fixture",label="fixture",source_ref={"kind":"synthetic test only"},
        faces=[dict(polygon_id=f.face_id,standard_xyz_rings=f.rings,semantic="RoofSurface",mapping="VERIFIED") for f in faces],
        ground_faces=[dict(polygon_id="ground",standard_xyz_rings=ground_rings)])
    return building,identity


def test_shared_kernel_matches_existing_wrapper_without_synthetic_identity():
    building,_=fixture()
    grid=g.GridSpec((0,0,2,1))
    for method in g.METHODS:
        cells,sources,excluded=g.sample_roofs(grid,[building],method=method)
        previous=g.derive(grid,[building],method=method)
        assert cells==previous["cells"] and sources==previous["source_provenance"] and excluded==previous["excluded_faces"]
        assert "vertical_datum" not in json.dumps(cells)


def test_zero_is_known_and_nodata_preserves_unknown_and_absence(tmp_path):
    building,identity=fixture([face("tiny",(0,0,.1,1))],box(0,0,1,1))
    result=r.calculate(building,identity,g.GridSpec((0,0,2,1)))
    assert result["maps"]["centre"]["state"].tolist()==[[2,0]]
    assert np.isnan(result["maps"]["centre"]["top"]).all()
    assert result["maps"]["cell_max"]["state"].tolist()==[[1,0]]
    assert result["maps"]["cell_max"]["top"][0,0]==0
    assert result["qa"]["support_only_gain_cells"]==1
    path=tmp_path/"zero.tif"
    r.raster(path,result["maps"]["cell_max"]["top"],result["grid"],quantity="absolute_H",unit="m",nodata=float("nan"))
    with rasterio.open(path) as ds:
        assert ds.crs.to_epsg()==6677 and ds.shape==(1,2) and ds.dtypes==("float64",)
        assert np.isnan(ds.nodata) and ds.read_masks(1).tolist()==[[255,0]]
        assert ds.read(1)[0,0]==0 and ds.xy(0,0)==(.5,.5)


def test_slope_and_clipped_cell_max_analytic():
    building,identity=fixture([face("slope",(0,0,2,1),lambda x,y:10+2*x+3*y)])
    result=r.calculate(building,identity,g.GridSpec((0,0,2,1)))
    np.testing.assert_allclose(result["maps"]["centre"]["top"],[[12.5,14.5]])
    np.testing.assert_allclose(result["maps"]["cell_max"]["top"],[[15,17]])
    np.testing.assert_allclose(result["delta"],[[2.5,2.5]])
    assert result["qa"]["independent_plane_max_error_m"]<1e-10
    building,identity=fixture([face("partial",(0,0,.75,1),lambda x,y:10+2*x)],box(0,0,1,1))
    result=r.calculate(building,identity,g.GridSpec((0,0,1,1)))
    assert result["maps"]["centre"]["top"][0,0]==11
    assert result["maps"]["cell_max"]["top"][0,0]==11.5  # not full-cell extrapolated 12
    assert result["maps"]["cell_max"]["roof_coverage"][0,0]==.75


def test_hole_boundary_and_lower_contributions_preserved():
    outer=box(0,0,3,3)
    hole=box(1,1,2,2)
    polygon=Polygon(outer.exterior.coords,[hole.exterior.coords])
    roof=g.Face("hole",(tuple((x,y,10.) for x,y in polygon.exterior.coords),
                        tuple((x,y,10.) for x,y in polygon.interiors[0].coords)))
    building,identity=fixture([roof],outer)
    result=r.calculate(building,identity,g.GridSpec((0,0,3,3)))
    assert result["maps"]["cell_max"]["state"][1,1]==2
    assert result["qa"]["uncovered_area_m2"]==1
    building,identity=fixture([face("low",(0,0,.5,1),lambda x,y:4),
                               face("high",(.5,0,1,1),lambda x,y:9)],box(0,0,1,1))
    result=r.calculate(building,identity,g.GridSpec((0,0,1,1)))
    row=result["tables"]["centre"][0]
    assert row["absolute_top_z"]==9 and row["contribution_count"]==2
    assert sorted(c["absolute_top_z"] for c in row["contributions"])==[4,9]
    assert result["maps"]["centre"]["roof_coverage"][0,0]==1


def test_micro_boundary_differences_and_no_repair():
    epsilon=1e-7
    building,identity=fixture([face("roof",(-epsilon,0,1-epsilon,1),lambda x,y:10)],box(0,0,1,1))
    before=r.json_digest(identity)
    result=r.calculate(building,identity,g.GridSpec((-1,0,2,1)))
    assert result["qa"]["outside_footprint_roof_area_m2"]==pytest.approx(epsilon)
    assert result["qa"]["uncovered_area_m2"]==pytest.approx(epsilon)
    assert result["qa"]["used_support_area_m2"]==pytest.approx(1-epsilon)
    assert before==r.json_digest(identity)
    assert result["maps"]["cell_max"]["state"].tolist()==[[0,1,0]]
    assert result["projections"]["roof_faces"][0]["original_projection"]!=result["projections"]["roof_faces"][0]["used_intersection"]


def test_multiple_ground_surfaces_do_not_select_largest():
    def ground(bounds):return dict(standard_xyz_rings=face("g",bounds).rings)
    with pytest.raises(ValueError,match="union"):
        r.ground_footprint([ground((0,0,2,2)),ground((3,0,4,1))])
    assert r.ground_footprint([ground((0,0,1,1)),ground((1,0,2,1))]).area==2


@pytest.mark.parametrize("kind",["semantic","mapping","xyz","footprint","grid"])
def test_invalid_handoff_rejected(kind):
    building,identity=fixture()
    grid=g.GridSpec((0,0,2,1))
    if kind=="semantic":identity["faces"][0]["semantic"]="WallSurface"
    elif kind=="mapping":identity["faces"][0]["mapping"]="AMBIGUOUS_OR_MISSING"
    elif kind=="xyz":identity["faces"][0]["standard_xyz_rings"]=face("changed",(0,0,2,1),lambda x,y:1).rings
    elif kind=="footprint":building=g.Building("fixture",box(0,0,1,1),building.faces,building.provenance)
    else:grid=g.GridSpec((0,0,2,2),2.)
    with pytest.raises(ValueError): r.calculate(building,identity,grid)


def test_global_integer_phase_and_reproducible_input_immutability():
    building,identity=fixture([face("roof",(100.2,-3.8,102.7,-1.2),lambda x,y:10)],box(100.2,-3.8,102.7,-1.2))
    grid=r.building_grid(building)
    assert grid.bounds==(99,-5,104,0)
    before=r.json_digest(identity)
    a,b=r.calculate(building,identity),r.calculate(building,identity)
    assert before==r.json_digest(identity)
    assert r.json_digest(a["tables"])==r.json_digest(b["tables"])
    assert r.grid_metadata(grid)["global_phase_origin_xy"]==[0,0]
    assert not any("synthetic datum" in str(x) for x in (a["vertical"],a["profile"]))


def test_bad_audit_or_missing_input_never_publishes_completion(tmp_path):
    audit_run=tmp_path/"audit"
    audit_run.mkdir()
    (audit_run/"manifest.json").write_text('{}')
    result=r.run(audit_run,tmp_path/"bad",tmp_path)
    assert result["status"]=="BLOCKED" and not (tmp_path/"bad"/"manifest.json").exists()
    with pytest.raises(FileExistsError):r.run(audit_run,tmp_path/"bad",tmp_path)


def test_partial_raster_failure_has_no_completed_manifest(tmp_path,monkeypatch):
    building,identity=fixture()
    class Watch:
        identities={}
        def unchanged(self):pass
    monkeypatch.setattr(r,"load_samples",lambda *args:([(building,identity)],Watch(),{}))
    def fail(*args,**kwargs):raise OSError("injected raster failure")
    monkeypatch.setattr(r,"raster",fail)
    result=r.run(tmp_path/"unused",tmp_path/"out",tmp_path)
    assert result["status"]=="BLOCKED" and not (tmp_path/"out"/"manifest.json").exists()


def test_saved_rasters_tables_and_plot_are_reproducible(tmp_path):
    building,identity=fixture()
    result=r.calculate(building,identity)
    r.save_building(tmp_path/"a",result)
    r.save_building(tmp_path/"b",result)
    files=list((tmp_path/"a").iterdir())
    assert len([p for p in files if p.suffix==".tif"])==9
    assert all(p.read_bytes()==(tmp_path/"b"/p.name).read_bytes() for p in files)
    source=json.loads((tmp_path/"a"/"source_faces.json").read_bytes())
    assert list(source)==["roof"]
    inputs=json.loads((tmp_path/"a"/"inputs.json").read_bytes())
    assert inputs["vertical"]==r.VERTICAL and inputs["policies"]==r.POLICIES
