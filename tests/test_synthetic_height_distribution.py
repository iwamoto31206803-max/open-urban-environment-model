"""Self-contained authored geometry and independent analytic expectations."""
from copy import deepcopy
import json

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from ouem.synthetic_height_distribution import (
    Building, Face, GridSpec, compare, demonstration, derive, relative_to_ground,
)


def roof(name, xy, z=lambda x, y: 10., holes=()):
    return Face(name, tuple(tuple((x, y, z(x, y)) for x, y in ring)
                            for ring in (xy, *holes)))


def rectangle(x0, y0, x1, y1):
    return ((x0,y0), (x1,y0), (x1,y1), (x0,y1), (x0,y0))


def building(faces, footprint=None, sid="a"):
    return Building(sid, box(0,0,2,2) if footprint is None else footprint,
                    tuple(faces), "hand-authored synthetic XYZ; arbitrary datum")


def both(buildings, grid=None):
    grid = grid or GridSpec((0,0,2,2))
    return tuple(derive(grid, buildings, method=m) for m in ("centre", "cell_max"))


def tops(result):
    return [c["buildings"][0]["absolute_top_z"] if c["buildings"] else None
            for c in result["cells"]]


@pytest.mark.parametrize("z", [0., 10., -3.])
def test_flat_representative_and_zero_are_valid(z):
    a,b = both([building([roof("flat", rectangle(0,0,2,2), lambda x,y:z)])])
    assert tops(a) == tops(b) == [z]*4
    assert all(c["buildings"][0]["valid"] for c in a["cells"])
    assert compare(a,b)["differing_cell_count"] == 0


def test_slope_analytic_and_explicit_ground():
    # z=10+2x+3y; north row centres y=1.5, south y=.5.
    a,b = both([building([roof("slope", rectangle(0,0,2,2), lambda x,y:10+2*x+3*y)])])
    assert tops(a) == pytest.approx([15.5,17.5,12.5,14.5])
    assert tops(b) == pytest.approx([18,20,15,17])
    report = compare(a,b)
    assert report["differing_cell_count"] == 4
    assert report["maximum_absolute_difference_m"] == pytest.approx(2.5)
    assert report["partial_coverage_height_differences"] == []
    # These relative values use ground at cell centres, including for cell-max
    # roof Z. They are not maxima of local roof-ground differences.
    np.testing.assert_allclose(relative_to_ground(tops(a), [2]*4), [13.5,15.5,10.5,12.5])
    # ground=2+x, explicitly at the same centres, no owner averaging or D0.
    np.testing.assert_allclose(relative_to_ground(tops(a), [2.5,3.5,2.5,3.5]), [13,14,10,11])
    np.testing.assert_allclose(relative_to_ground(tops(b), [2.5,3.5,2.5,3.5]), [15.5,16.5,12.5,13.5])
    result = relative_to_ground([0,np.nan], [2,2])
    assert result[0] == -2 and np.isnan(result[1])
    with pytest.raises(ValueError):
        relative_to_ground([1], [np.nan])


def test_step_boundary_keeps_both_faces_instead_of_only_highest():
    faces = [roof("low",rectangle(0,0,.75,1),lambda x,y:4),
             roof("high",rectangle(.75,0,2,1),lambda x,y:9)]
    a,b = both([building(faces,box(0,0,2,1))],GridSpec((0,0,2,1)))
    assert tops(a) == [4,9] and tops(b) == [9,9]
    first = b["cells"][0]["buildings"][0]
    assert first["contribution_count"] == 2
    assert {c["face_id"]:c["absolute_top_z"] for c in first["contributions"]} == {"low":4,"high":9}
    assert first["coverage_fraction"] == 1  # union, not sum
    assert compare(a,b)["maximum_absolute_difference_m"] == 5


def test_seam_centre_closed_boundary_and_line_touch_exclusion():
    faces = [roof("left",rectangle(0,0,.5,1),lambda x,y:4),
             roof("right",rectangle(.5,0,1,1),lambda x,y:9)]
    a,_ = both([building(faces,box(0,0,1,1))],GridSpec((0,0,2,1)))
    assert [c["absolute_top_z"] for c in a["cells"][0]["buildings"][0]["contributions"]] == [4,9]
    assert a["cells"][1]["state"] == "NO_BUILDING"


def test_roof_hole_building_unknown_versus_footprint_hole_absent():
    outer, hole = rectangle(0,0,3,3), rectangle(1,1,2,2)
    face = roof("hole",outer, holes=(hole,))
    a,b = both([building([face],box(0,0,3,3))], GridSpec((0,0,3,3)))
    for result in (a,b):
        centre = result["cells"][4]
        assert centre["state"] == "BUILDING_PRESENT"
        assert centre["buildings"][0]["state"] == "TOP_UNKNOWN"
        assert centre["buildings"][0]["absolute_top_z"] is None
        assert centre["contribution_count"] == 0
    fp = Polygon(outer,[hole])
    c,_ = both([building([face],fp)],GridSpec((0,0,3,3)))
    assert c["cells"][4]["state"] == "NO_BUILDING"


def test_partial_thin_eave_and_clipped_maximum():
    # Roof covers only x=[0,.1]. Max must be z(.1)=10.2, not z(1)=12.
    face = roof("eave",rectangle(0,0,.1,1),lambda x,y:10+2*x)
    a,b = both([building([face],box(0,0,1,1))],GridSpec((0,0,1,1)))
    assert tops(a) == [None] and tops(b) == pytest.approx([10.2])
    row = b["cells"][0]["buildings"][0]
    assert row["coverage_fraction"] == pytest.approx(.1)
    assert row["partial_roof_coverage"] and row["footprint_fraction"] == 1
    assert len(compare(a,b)["support_differences"]) == 1
    # A partially covered centre can also have a numerical height difference.
    face = roof("partial",rectangle(0,0,.75,1),lambda x,y:10+2*x)
    a,b = both([building([face],box(0,0,1,1))],GridSpec((0,0,1,1)))
    assert tops(a)==[11] and tops(b)==[11.5]
    assert len(compare(a,b)["partial_coverage_height_differences"]) == 1
    # Roof outside independently authored building extent is clipped explicitly.
    a,b = both([building([roof("over",rectangle(0,0,2,1),lambda x,y:x)],box(0,0,.75,1))],
               GridSpec((0,0,1,1)))
    assert tops(b)==[.75]
    assert b["cells"][0]["buildings"][0]["footprint_fraction"]==.75


def test_vertical_wall_and_unknown_missing_roof():
    wall = Face("wall", (((0,0,0),(0,1,0),(0,1,10),(0,0,10),(0,0,0)),))
    for faces in ([wall], []):
        a,b = both([building(faces)])
        assert tops(a) == tops(b) == [None]*4
    assert a["excluded_faces"] == []
    a,_ = both([building([wall])])
    assert a["excluded_faces"][0]["reason"] == "VERTICAL_FACE_NOT_ROOF_SUPPORT"


def test_multiple_buildings_overlaps_preserve_lower_and_union_coverage():
    a,b = both([building([roof("one",rectangle(0,0,2,2),lambda x,y:3),
                          roof("two",rectangle(0,0,2,2),lambda x,y:7)]),
                building([roof("other",rectangle(0,0,2,2),lambda x,y:12)],sid="b")])
    for result in (a,b):
        cell=result["cells"][0]
        assert cell["building_count"]==2 and cell["contribution_count"]==3
        assert [r["absolute_top_z"] for r in cell["buildings"]] == [7,12]
        assert cell["buildings"][0]["coverage_fraction"]==1
        assert [c["absolute_top_z"] for c in cell["buildings"][0]["contributions"]] == [3,7]


@pytest.mark.parametrize("rings", [(), (((0,0,0),(1,0,0),(1,1,np.nan),(0,0,0)),),
    (((0,0,0),(1,0,0),(1,1,np.inf),(0,0,0)),),
    (((0,0,0),(1,0,0),(1,1,"2"),(0,0,0)),),
    (((0,0,0),(1,0,0),(1,1,True),(0,0,0)),),
    ((None, None, None, None),),
    (((0,0),(1,0),(1,1),(0,0)),),
    (((0,0,0),(1,0,0),(1,1,1),(0,1,0),(0,0,0)),),
    (((0,0,0),(1,1,0),(1,0,0),(0,1,0),(0,0,0)),),
    (((0,0,0),(1,0,0),(2,0,0),(0,0,0)),),
    (((0,0,0),(1,0,0),(1,1,0),(0,1,0)),)])
def test_bad_z_nonplanar_degenerate_invalid_and_unclosed_rejected(rings):
    with pytest.raises(ValueError):
        both([building([Face("bad",rings)])])


def test_invalid_footprints_ids_holes_and_method():
    face=roof("flat",rectangle(0,0,2,2))
    for fp in (Polygon(),Polygon([(0,0),(1,1),(1,0),(0,1)]),
               Polygon([(0,0,0),(1,0,0),(1,1,0),(0,0,0)])):
        with pytest.raises(ValueError):
            both([building([face],fp)])
    with pytest.raises(ValueError,match="duplicate source"):
        both([building([face]),building([face])])
    with pytest.raises(ValueError,match="duplicate face"):
        both([building([face,face])])
    with pytest.raises(ValueError,match="invalid face shape"):
        both([building([roof("bad-hole",rectangle(0,0,1,1),holes=(rectangle(2,2,3,3),))])])
    with pytest.raises(ValueError,match="unsupported"):
        derive(GridSpec((0,0,1,1)),[],method="nearest")


def test_grid_origin_axes_size_identity_and_reproducibility():
    grid=GridSpec((100,-4,104,0),2.)
    sources=[building([roof("slope",rectangle(100,-4,104,0),lambda x,y:20+(x-100)+y)],
                      box(100,-4,104,0))]
    before=deepcopy(sources)
    a,b=both(sources,grid)
    assert tops(a)==[20,22,18,20]
    assert tops(b)==[22,24,20,22]
    assert a["grid"]["origin_xy"]==[100,0]
    assert a["grid"]["column_axis"]==[2,0] and a["grid"]["row_axis"]==[0,-2]
    assert [c["centre_xy"] for c in a["cells"]]==[[101,-1],[103,-1],[101,-3],[103,-3]]
    assert sources==before
    assert json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(both(sources,grid)[0],sort_keys=True,allow_nan=False)
    assert a["grid_identity"]==b["grid_identity"] and a["source_identity"]==b["source_identity"]
    with pytest.raises(ValueError,match="identities"):
        compare(a,both([],grid)[1])
    for bounds,resolution in (((0,0,1,1),0),((0,0,1,1),.3),((1,0,0,1),1)):
        with pytest.raises(ValueError):
            GridSpec(bounds,resolution)


def test_disconnected_clipping_negative_slope_and_input_order():
    # U-shaped roof, clipped to one cell across its separated upper arms.
    xy=((0,-2),(3,-2),(3,1),(2,1),(2,-1),(1,-1),(1,1),(0,1),(0,-2))
    source=building([roof("u",xy,lambda x,y:20-x-y)],Polygon(xy))
    a,b=both([source],GridSpec((0,0,3,3),3))
    assert tops(a)==[None] and tops(b)==[20]
    assert b["cells"][0]["buildings"][0]["coverage_fraction"]==pytest.approx(2/9)
    other=building([roof("flat",rectangle(0,0,2,2))],sid="b")
    first=derive(GridSpec((0,0,3,3)),[source,other],method="cell_max")
    second=derive(GridSpec((0,0,3,3)),[other,source],method="cell_max")
    assert first==second


def test_demonstration_reproducible_analytic_summary():
    report=demonstration()
    assert report==demonstration()
    assert report["cases"]["slope"]["comparison"]["differing_cell_count"]==4
    assert report["cases"]["slope"]["centre"]["representative_minus_top_range_m"]==[2.5,7.5]
    assert report["cases"]["slope"]["cell_max"]["representative_minus_top_range_m"]==[0,5]
    assert report["cases"]["thin_eave"]["centre"]["unknown"]==1
    assert report["cases"]["roof_hole"]["cell_max"]["unknown"]==1
