"""Independent small XML/XYZ fixtures, no real-data or old fixture dependencies."""
from copy import deepcopy
import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from ouem import lod2_roof_audit as a


def rectangle(z=10):
    return (((0.,0.,z),(2.,0.,z),(2.,2.,z),(0.,2.,z),(0.,0.,z)),)


def xml(kind="RoofSurface",identifier="face"):
    polygon=f'<g:Polygon g:id="{identifier}"><g:exterior><g:LinearRing><g:posList>0 0 10 0 2 10 2 2 10 2 0 10 0 0 10</g:posList></g:LinearRing></g:exterior></g:Polygon>'
    geometry=f'<b:lod2MultiSurface><g:MultiSurface><g:surfaceMember>{polygon}</g:surfaceMember></g:MultiSurface></b:lod2MultiSurface>'
    branch=f'<b:boundedBy><b:{kind} g:id="surface">{geometry}</b:{kind}></b:boundedBy>' if kind else geometry
    return f'<c:CityModel xmlns:c="http://www.opengis.net/citygml/2.0" xmlns:b="http://www.opengis.net/citygml/building/2.0" xmlns:g="http://www.opengis.net/gml" srsDimension="3"><c:cityObjectMember><b:Building g:id="building">{branch}</b:Building></c:cityObjectMember></c:CityModel>'


@pytest.mark.parametrize("kind",["RoofSurface","WallSurface","GroundSurface","ClosureSurface",None])
def test_explicit_semantics_only_and_inherited_dimensions(tmp_path,kind):
    path=tmp_path/"tiny.gml"
    path.write_text(xml(kind),encoding="utf-8")
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    result=a.read_semantics(path,{"building"})["building"]
    assert len(result)==1 and result[0]["semantic"]==(kind or "UNDETERMINED")
    assert result[0]["polygon_id"]=="face"
    assert result[0]["rings"]==rectangle()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def raw(face=None,semantic="RoofSurface",identifier="face"):
    return dict(rings=rectangle() if face is None else face,semantic=semantic,
                polygon_id=identifier,semantic_surface_id="surface")


def test_unique_correspondence_rotation_reversal_and_native_reorder():
    first,second=rectangle(10),rectangle(0)
    ring=first[0][:-1]
    rotated=tuple(reversed(ring[1:]+ring[:1]))
    rotated=rotated+(rotated[0],)
    result=a.correspondence([raw(first),raw(second,"GroundSurface","ground")],[second,(rotated,)])
    assert [r["mapping"] for r in result]==["VERIFIED"]*2
    assert [r["polygon_id"] for r in result]==["ground","face"]
    assert [r["semantic"] for r in result]==["GroundSurface","RoofSurface"]


@pytest.mark.parametrize("variant",["raw_duplicate","native_duplicate","missing_id","duplicate_id","no_match"])
def test_nonunique_or_missing_mapping_is_not_verified(variant):
    source=[raw()]
    native=[rectangle()]
    if variant=="raw_duplicate": source.append(raw(identifier="other"))
    elif variant=="native_duplicate": native.append(rectangle())
    elif variant=="missing_id": source[0]["polygon_id"]=None
    elif variant=="duplicate_id": source.append(raw(rectangle(0)))
    else: native=[rectangle(20)]
    result=a.correspondence(source,native)
    assert all(r["mapping"]!="VERIFIED" and r["semantic"]=="UNDETERMINED" for r in result)


def test_planar_hole_vertical_nonplanar_and_invalid_qa():
    outer=rectangle()[0]
    hole=((.5,.5,10),(1.5,.5,10),(1.5,1.5,10),(.5,1.5,10),(.5,.5,10))
    qa=a.geometry_qa((outer,hole))
    assert qa["projected_area_m2"]==3 and qa["interior_rings"]==1
    assert qa["step3a_planar_polygon_compatible"] and qa["max_plane_residual_m"]==0
    wall=(((0,0,0),(0,2,0),(0,2,10),(0,0,10),(0,0,0)),)
    assert a.geometry_qa(wall)["near_vertical"] and not a.geometry_qa(wall)["step3a_planar_polygon_compatible"]
    bad=(((0,0,0),(2,0,0),(2,2,1),(0,2,0),(0,0,0)),)
    assert not a.geometry_qa(bad)["step3a_planar_polygon_compatible"]
    assert a.geometry_qa(bad)["max_plane_residual_m"]>0
    for rings in ((((0,0,float("nan")),(1,0,0),(1,1,0),(0,0,float("nan"))),),
                  (((0,0,0),(1,0,0),(1,1,0),(0,1,0)),)):
        with pytest.raises(ValueError): a.geometry_qa(rings)


def building(roof_semantic="RoofSurface"):
    roof,ground=rectangle(10),rectangle(0)
    attrs=("building","ouem-building","dataset",2,"LOD2_PRESENT_VALID","member.gml","release","lod2",10.,10.)
    return a.building_audit("building",attrs,[raw(roof,roof_semantic),raw(ground,"GroundSurface","ground")],
                            [roof,ground],[roof,ground])[0]


def test_eligibility_is_conditional_and_nonvertical_is_not_a_roof():
    row=building()
    assert row["classification"]=="CONDITIONAL"
    assert row["vertical"]["HAG_validity"]=="NOT_VERIFIED"
    assert row["footprint_candidate"]["area_m2"]==4
    assert row["vertical"]["span_minus_measured"]==0
    unknown=building("UNDETERMINED")
    assert unknown["classification"]=="BLOCKED" and unknown["roof_faces"]==0
    assert unknown["faces"][0]["geometric_candidate_only"]
    wall=building("WallSurface")
    assert wall["roof_faces"]==0 and wall["classification"]=="BLOCKED"


def test_sample_selection_deterministic_and_not_found():
    first=building()
    second=deepcopy(first)
    first["source_id"],second["source_id"]="a","b"
    assert a.select_samples([first,second])==a.select_samples([second,first])
    result=a.select_samples([first,second])
    assert result["simple_flat"]["source_id"]=="a"
    assert result["sloped"]["status"]==result["missing_duplicate_or_ambiguous"]["status"]=="NOT_FOUND"


def test_raw_face_missing_in_native_is_not_accepted():
    roof,ground=rectangle(10),rectangle(0)
    attrs=("building","ouem-building","dataset",2,"reason","member","release","lod2",10.,10.)
    row,_,_=a.building_audit("building",attrs,[raw(roof),raw(ground,"GroundSurface","ground"),raw(rectangle(20),identifier="lost")],
                           [roof,ground],[roof,ground])
    assert row["classification"]=="BLOCKED" and "RAW_FACE_SET_NOT_FULLY_ACCOUNTED" in row["reasons"]


def test_xml_dtd_and_missing_building_rejected(tmp_path):
    path=tmp_path/"bad.gml"
    path.write_text('<!DOCTYPE CityModel [<!ENTITY x "bad">]>'+xml())
    with pytest.raises(ValueError,match="DTD"):
        a.read_semantics(path,{"building"})
    path.write_text(xml())
    with pytest.raises(ValueError,match="missing"):
        a.read_semantics(path,{"absent"})


def test_missing_files_wrong_sha_and_new_output_only(tmp_path):
    source=tmp_path/"t5.json"
    source.write_text("{}")
    result=a.run(source,tmp_path/"wrong",t5_sha="0"*64,artifact_root=tmp_path)
    assert result["status"]=="BLOCKED" and result["real_data_audit"]=="NOT_COMPLETED"
    assert not (tmp_path/"wrong"/"manifest.json").exists()
    assert source.read_text()=="{}"
    with pytest.raises(FileExistsError): a.run(source,tmp_path/"wrong",artifact_root=tmp_path)
    result=a.run(tmp_path/"missing",tmp_path/"missing-output",artifact_root=tmp_path)
    assert result["step4a_transition"]=="BLOCKED"


def test_publication_failure_has_no_completed_manifest(tmp_path,monkeypatch):
    monkeypatch.setattr(a,"audit",lambda *args,**kwargs:dict(status="AUDIT_COMPLETED",synthetic_stub=True))
    real=Path.rename
    def fail(self,target):
        if target.name=="manifest.json": raise OSError("injected publication failure")
        return real(self,target)
    monkeypatch.setattr(Path,"rename",fail)
    result=a.run(tmp_path/"unused",tmp_path/"out")
    assert result["status"]=="BLOCKED"
    assert not (tmp_path/"out"/"manifest.json").exists()


def test_population_uses_actual_ids_and_rejects_duplicate_report_rows():
    attrs={"a":("a","ouem-a","dataset",2)}
    rows=[dict(source_id="a",ouem_id="ouem-a",id=1,source_lod=2)]
    a.verify_population(rows,attrs)
    with pytest.raises(ValueError,match="bijection"):
        a.verify_population(rows*2,attrs)
    rows[0]["source_lod"]=1
    with pytest.raises(ValueError,match="bijection"):
        a.verify_population(rows,attrs)
