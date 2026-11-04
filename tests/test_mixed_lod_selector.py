"""Authored coordinates/selection rules; no production parser builds expectations."""
import copy
import hashlib
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import zipfile

import pytest
from shapely.geometry import box

from ouem import mixed_lod_selector as m
from ouem.native.building.source_h_lod2 import read_lod2

G="{http://www.opengis.net/gml}"
B="{http://www.opengis.net/citygml/building/2.0}"
C="{http://www.opengis.net/citygml/2.0}"
X="{http://www.w3.org/1999/xlink}href"
SRS="http://www.opengis.net/def/crs/EPSG/0/6697"
BOUNDS=(-24000.,-41000.,-22000.,-39000.)


def cube(x=139.58,y=35.64,base=10.25,top=18.25):
    a,b,c,d=(x,y,base),(x+.0001,y,base),(x+.0001,y+.0001,base),(x,y+.0001,base)
    e,f,g,h=(x,y,top),(x+.0001,y,top),(x+.0001,y+.0001,top),(x,y+.0001,top)
    return tuple((ring,) for ring in ((a,b,c,d,a),(e,f,g,h,e),(a,b,f,e,a),(b,c,g,f,b),(c,d,h,g,c),(d,a,e,h,d)))


def add_lod(building,lod,faces,refs=False):
    branch=ET.SubElement(building,B+("lod1Solid" if lod==1 else f"lod{lod}MultiSurface"))
    if lod==1:
        surface=ET.SubElement(ET.SubElement(ET.SubElement(branch,G+"Solid"),G+"exterior"),G+"CompositeSurface")
    else:surface=ET.SubElement(branch,G+"MultiSurface")
    sid=building.get(G+"id")
    polygon_ids=[]
    for i,face in enumerate(faces):
        pid=f"{sid}_l{lod}_p{i}"
        polygon_ids.append(pid)
        polygon=ET.SubElement(ET.SubElement(surface,G+"surfaceMember"),G+"Polygon",{G+"id":pid})
        for n,ring in enumerate(face):
            shell=ET.SubElement(polygon,G+("exterior" if n==0 else "interior"))
            pos=ET.SubElement(ET.SubElement(shell,G+"LinearRing"),G+"posList")
            pos.text=" ".join(str(v) for x,y,h in ring for v in (y,x,h))
    if refs:
        solid=ET.Element(B+"lod2Solid")
        building.insert(0,solid)
        surface=ET.SubElement(ET.SubElement(ET.SubElement(solid,G+"Solid"),G+"exterior"),G+"CompositeSurface")
        for pid in polygon_ids:ET.SubElement(surface,G+"surfaceMember",{X:"#"+pid})
    return branch


def building(sid="authored",one=True,two=True,refs=False):
    node=ET.Element(B+"Building",{G+"id":sid})
    if one:add_lod(node,1,cube())
    if two:add_lod(node,2,cube(top=20.75),refs=refs)
    return node


def xml(nodes):
    root=ET.Element(C+"CityModel")
    ET.SubElement(ET.SubElement(root,G+"boundedBy"),G+"Envelope",dict(srsName=SRS,srsDimension="3"))
    # Dimension is inherited from geometry in real input, not from sibling Envelope.
    for node in nodes:
        for branch in node:
            if branch.tag.startswith(B+"lod") and len(branch):branch[0].attrib.setdefault("srsDimension","3")
        ET.SubElement(root,C+"cityObjectMember").append(node)
    return ET.tostring(root,encoding="utf-8")


def archive(tmp_path,nodes,second=None):
    path=tmp_path/"raw.zip"
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("udx/bldg/a.gml",xml(nodes))
        if second is not None:z.writestr("udx/bldg/b.gml",xml(second))
    return path


def select(path,members=None):
    return m.select_raw(path,members or ["udx/bldg/a.gml"],release="authored-fixture",bounds=BOUNDS)


@pytest.mark.parametrize("one,two,lod,reason",[(True,True,2,"LOD2_PRESENT_VALID"),(True,False,1,"LOD2_ABSENT_USE_LOD1"),(False,True,2,"LOD2_PRESENT_VALID"),(False,False,None,"NO_SUPPORTED_LOD1_OR_LOD2")])
def test_presence_selection_exact_xyz_h_and_identity(tmp_path,one,two,lod,reason):
    path=archive(tmp_path,[building(one=one,two=two)])
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    result,geometries=select(path)
    row=result["records"][0]
    assert row["selected_lod"]==lod and row["selection_reason"]==reason
    assert row["lod1_presence"] is one and row["lod2_presence"] is two
    assert row["lod1_validation_status"]==("VALID" if one else "ABSENT")
    assert row["lod2_validation_status"]==("VALID" if two else "ABSENT")
    assert row["ouem_id"]=="oub-"+str(uuid.uuid5(uuid.NAMESPACE_URL,"ouem-standard-building-v0.1|PLATEAU CityGML|authored"))
    if lod:
        assert geometries["authored"]==cube(top=20.75 if lod==2 else 18.25)
        assert row["aoi_intersects"] is True
        assert len(row["polygons"])==6
        assert row["polygons"][0]["polygon_id"]==f"authored_l{lod}_p0"
        assert row["polygons"][0]["polygon_ordinal"]==1
        assert "lod"+str(lod) in row["geometry_branch_locator"][0]
    else:
        assert row["aoi_intersects"] is None and geometries=={}
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


@pytest.mark.parametrize("case",["empty2","missing_ms2","unclosed2","nan2","dimension2","unsupported2","bad1_with_good2","empty1","solid_interior1","unknown_ref","external_ref","duplicate_ref","missing_ref","mixed_ref"])
def test_invalid_present_geometry_never_falls_back_or_publishes(tmp_path,case):
    node=building(refs=case.endswith("ref"))
    one=node.find(B+"lod1Solid");two=node.find(B+"lod2MultiSurface")
    pos=next(two.iter(G+"posList"))
    if case=="empty2":two[0].clear()
    if case=="missing_ms2":two.clear()
    if case=="unclosed2":pos.text=pos.text.rsplit(" ",3)[0]+" 0 0 0"
    if case=="nan2":pos.text=pos.text.replace("10.25","nan",1)
    if case=="dimension2":two[0].set("srsDimension","2")
    if case=="unsupported2":two.tag=B+"lod2MultiCurve"
    if case=="bad1_with_good2":next(one.iter(G+"posList")).text="0 0 nan "*4
    if case=="empty1":one.clear()
    if case=="solid_interior1":ET.SubElement(one[0],G+"interior")
    if case.endswith("ref"):
        refs=[n for n in node.iter() if X in n.attrib]
        if case=="unknown_ref":refs[0].set(X,"#missing")
        if case=="external_ref":refs[0].set(X,"other.gml#polygon")
        if case=="duplicate_ref":refs[0].set(X,refs[1].get(X))
        if case=="missing_ref":node.find(B+"lod2Solid")[0][0][0].remove(refs[0])
        if case=="mixed_ref":ET.SubElement(refs[0],G+"Polygon")
    path=archive(tmp_path,[node]);out=tmp_path/"failed"
    with pytest.raises(ValueError):m.run(path,["udx/bldg/a.gml"],release="fixture",bounds=BOUNDS,output_dir=out)
    assert not (out/"manifest.json").exists()
    failure=json.loads((out/"failure.json").read_text())
    assert failure["execution_status"]=="FAILED"
    if case=="bad1_with_good2":
        assert failure["code"]=="LOD1_INVALID" and failure["failed_record"]["selected_lod"] is None
    if case=="empty2":
        assert failure["code"]=="LOD2_INVALID"
        assert failure["failed_record"]["lod2_presence"] is True
        assert failure["failed_record"]["lod2_validation_status"]=="INVALID"


def split_lod2_surfaces(node):
    surface = node.find(B+"lod2MultiSurface")[0]
    second_surface = ET.SubElement(ET.SubElement(node, B+"lod2MultiSurface"), G+"MultiSurface")
    member = surface[-1]
    surface.remove(member)
    second_surface.append(member)
    return member[0]


@pytest.mark.parametrize("with_solid", [False, True])
def test_multiple_lod2_branches_preserve_faces_and_provenance(tmp_path, with_solid):
    node = building(refs=with_solid)
    split_lod2_surfaces(node)
    if with_solid:
        members = node.find(B+"lod2Solid")[0][0][0]
        members[:] = list(reversed(members))
    result, geometry = select(archive(tmp_path, [node]))
    row = result["records"][0]
    first, second = "./bldg:lod2MultiSurface[1]", "./bldg:lod2MultiSurface[2]"
    expected = [(first, f"authored_l2_p{i}", i+1) for i in range(5)]
    expected.append((second, "authored_l2_p5", 1))
    expected_faces = cube(top=20.75)
    if with_solid:
        expected.reverse()
        expected_faces = expected_faces[::-1]
    assert row["selected_lod"] == 2
    assert row["geometry_branch_locator"] == [first, second]
    assert [(p["branch_locator"], p["polygon_id"], p["polygon_ordinal"])
            for p in row["polygons"]] == expected
    assert geometry["authored"] == expected_faces


@pytest.mark.parametrize(("case", "error"), [
    ("missing_ref", "missing, duplicate or cross-building target"),
    ("duplicate_ref", "missing, duplicate or cross-building target"),
    ("duplicate_id", "empty/duplicate XML ID"),
])
def test_invalid_multiple_lod2_branches_fail_closed(tmp_path, case, error):
    node = building(refs=True)
    polygon = split_lod2_surfaces(node)
    members = node.find(B+"lod2Solid")[0][0][0]
    if case == "missing_ref":
        members.remove(members[-1])
    elif case == "duplicate_ref":
        members[-1].set(X, members[0].get(X))
    else:
        polygon.set(G+"id", "authored_l2_p0")
    path = archive(tmp_path, [node])
    out = tmp_path/"failed"

    with pytest.raises(ValueError, match=error):
        m.run(path, ["udx/bldg/a.gml"], release="fixture", bounds=BOUNDS, output_dir=out)

    failure = json.loads((out/"failure.json").read_text())
    assert failure["execution_status"] == "FAILED"
    if case != "duplicate_id":
        assert failure["code"] == "LOD2_INVALID"
        assert failure["failed_record"]["selected_lod"] is None
    assert not (out/"manifest.json").exists()
    assert not (out/"geometries.jsonl").exists()


@pytest.mark.parametrize("separate",[False,True])
def test_duplicate_building_ids_fail_across_members(tmp_path,separate):
    node=building()
    path=archive(tmp_path,[node] if separate else [node,copy.deepcopy(node)],second=[copy.deepcopy(node)] if separate else None)
    with pytest.raises(ValueError,match="duplicate Building ID"):
        select(path,["udx/bldg/a.gml","udx/bldg/b.gml"] if separate else None)


def test_lod1_polygon_hole_is_retained(tmp_path):
    node=building(one=False,two=False)
    faces=list(cube())
    hole=((139.58002,35.64002,18.25),(139.58008,35.64002,18.25),(139.58008,35.64008,18.25),(139.58002,35.64002,18.25))
    faces[1]=(faces[1][0],hole)
    add_lod(node,1,faces)
    result,geometry=select(archive(tmp_path,[node]))
    assert geometry["authored"][1][1]==hole
    assert geometry["authored"]==tuple(faces)
    assert result["records"][0]["selected_lod"]==1


@pytest.mark.parametrize("two_inside",[False,True])
def test_selection_precedes_aoi_and_does_not_clip(tmp_path,two_inside):
    node=building(one=False,two=False)
    add_lod(node,1,cube(x=140.58 if two_inside else 139.58))
    faces=cube(x=139.58 if two_inside else 140.58,top=20.75)
    add_lod(node,2,faces)
    result,geometry=select(archive(tmp_path,[node]))
    assert result["records"][0]["selected_lod"]==2
    assert result["records"][0]["aoi_intersects"] is two_inside
    assert geometry["authored"]==faces


@pytest.mark.parametrize("one,two,expected",[(True,True,2),(True,False,1),(False,False,None)])
def test_higher_lods_do_not_change_priority(tmp_path,one,two,expected):
    node=building(one=one,two=two)
    add_lod(node,3,cube(top=90));add_lod(node,4,cube(top=100))
    result,_=select(archive(tmp_path,[node]))
    assert result["records"][0]["selected_lod"]==expected
    assert result["records"][0]["other_lods_present"]==[3,4]


def test_boundary_contact_and_zero_area_wall_projection():
    face=(((1.,.2,10.),(2.,.2,10.),(2.,.8,10.),(1.,.8,10.),(1.,.2,10.)),)
    wall=(((1.,.2,10.),(1.,.8,10.),(1.,.8,20.),(1.,.2,20.),(1.,.2,10.)),)
    assert m._intersects((face,wall),box(0,0,1,1),lambda x,y:(x,y))
    assert not m._intersects((face,),box(-2,-2,0,0),lambda x,y:(x,y))


def test_existing_lod2_reader_and_profile_remain_separate(tmp_path):
    node=building(refs=True)
    path=archive(tmp_path,[node])
    result,geometry=select(path)
    raw=tmp_path/"a.gml"
    with zipfile.ZipFile(path) as z:raw.write_bytes(z.read("udx/bldg/a.gml"))
    legacy,excluded=read_lod2([raw])
    assert geometry==legacy and excluded==[]
    # Legacy LoD2-only intentionally does not become a LoD1 fallback reader.
    raw.write_bytes(xml([building(two=False)]))
    with pytest.raises(ValueError,match="no eligible LoD2"):read_lod2([raw])
    assert result["schema"]=="ouem-raw-mixed-lod-selector-manifest/v0.1"
    assert "raw" in result["profile"]


def test_outputs_provenance_and_safe_rerun(tmp_path):
    path=archive(tmp_path,[building()]);out=tmp_path/"output"
    r=m.run(path,["udx/bldg/a.gml"],release="explicit-release",bounds=BOUNDS,output_dir=out)
    assert r["source"]["release"]=="explicit-release"
    assert r["source"]["zip_sha256"]==hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z:
        assert r["source"]["members"][0]["sha256"]==hashlib.sha256(z.read("udx/bldg/a.gml")).hexdigest()
    geo=json.loads((out/"geometries.jsonl").read_text())
    assert geo["faces"]==json.loads(json.dumps(cube(top=20.75)))
    assert r["records"][0]["geometry_sha256"]==hashlib.sha256(m.canonical(geo["faces"])).hexdigest()
    assert r["crs"]["vertical_operation"]=="identity_H"
    assert r["crs"]["geometry_tuple_order"]==["longitude","latitude","H"]
    original=(out/"manifest.json").read_bytes()
    with pytest.raises(FileExistsError):m.run(path,["udx/bldg/a.gml"],release="other",bounds=BOUNDS,output_dir=out)
    assert (out/"manifest.json").read_bytes()==original


@pytest.mark.parametrize("case",["dtd","wrong_crs","duplicate_polygon_id","building_part","bad_dimension"])
def test_raw_global_fail_closed(tmp_path,case):
    node=building()
    if case=="duplicate_polygon_id":
        polygons=list(node.iter(G+"Polygon"));polygons[1].set(G+"id",polygons[0].get(G+"id"))
    if case=="building_part":ET.SubElement(node,B+"BuildingPart")
    if case=="bad_dimension":node.set("srsDimension","2")
    data=xml([node])
    if case=="dtd":data=b'<!DOCTYPE CityModel [<!ENTITY x "x">]>'+data
    if case=="wrong_crs":data=data.replace(b"/6697",b"/4979")
    path=tmp_path/"raw.zip"
    with zipfile.ZipFile(path,"w") as z:z.writestr("udx/bldg/a.gml",data)
    with pytest.raises(ValueError):select(path)


def test_invalid_geometry_is_checked_even_outside_aoi(tmp_path):
    node=building(one=False,two=False)
    branch=add_lod(node,2,cube(x=140.58))
    next(branch.iter(G+"posList")).text="0 0 nan "*4
    with pytest.raises(m.SelectionError,match="LOD2_INVALID"):
        select(archive(tmp_path,[node]))


def test_city_attributes_are_audit_only(tmp_path):
    node=building(two=False)
    city=ET.SubElement(node,"{https://www.geospatial.jp/iur/uro/3.2}city",dict(codeSpace="../../codelists/city.xml"))
    city.text="13112"
    result,_=select(archive(tmp_path,[node]))
    assert result["records"][0]["selected_lod"]==1
    assert result["records"][0]["aoi_intersects"] is True
    assert result["records"][0]["city_attributes"]==[dict(value="13112",code_space="../../codelists/city.xml")]


@pytest.mark.parametrize("changed_at",[2,3])
def test_input_change_prevents_success_publication(tmp_path,monkeypatch,changed_at):
    path=archive(tmp_path,[building()]);out=tmp_path/"out"
    original=m.digest
    calls=0
    def changed(p):
        nonlocal calls
        value=original(p)
        if Path(p).suffix==".zip":
            calls+=1
            if calls==changed_at:return "0"*64
        return value
    monkeypatch.setattr(m,"digest",changed)
    with pytest.raises(ValueError,match="INPUT_CHANGED"):
        m.run(path,["udx/bldg/a.gml"],release="fixture",bounds=BOUNDS,output_dir=out)
    assert not (out/"manifest.json").exists()
    assert json.loads((out/"failure.json").read_text())["code"]=="INPUT_CHANGED"


def test_explicit_experimental_json_schema(tmp_path):
    schema=json.loads((Path(__file__).parents[1]/"docs/schemas/ouem_raw_mixed_lod_selector_manifest_v0.1.schema.json").read_text(encoding="utf-8"))
    js=pytest.importorskip("jsonschema",reason="optional installed schema validator; no new runtime dependency")
    validator=js.Draft202012Validator
    validator.check_schema(schema)
    path=archive(tmp_path,[building(),building("none",one=False,two=False)])
    r=m.run(path,["udx/bldg/a.gml"],release="fixture",bounds=BOUNDS,output_dir=tmp_path/"ok")
    validator(schema).validate(r)
    geometry_schema={"$schema":schema["$schema"],"$defs":schema["$defs"],"$ref":"#/$defs/geometry_record"}
    for line in (tmp_path/"ok/geometries.jsonl").read_text().splitlines():
        validator(geometry_schema).validate(json.loads(line))
    bad=copy.deepcopy(r);bad["records"][0]["selected_lod"]=1
    with pytest.raises(js.ValidationError):validator(schema).validate(bad)
    invalid=building();invalid.find(B+"lod2MultiSurface").clear()
    path=archive(tmp_path,[invalid])
    with pytest.raises(ValueError):m.run(path,["udx/bldg/a.gml"],release="fixture",bounds=BOUNDS,output_dir=tmp_path/"bad")
    validator(schema).validate(json.loads((tmp_path/"bad/failure.json").read_text()))
