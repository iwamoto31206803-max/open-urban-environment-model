"""Small authored references with independent expected inline faces."""
import xml.etree.ElementTree as ET
import pytest
from ouem.native.building.source_h_lod2 import read_lod2, G, B, X
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_source_h_ingestion import FIXTURE


def referenced(tmp_path):
    tree = ET.parse(FIXTURE)
    for b in tree.getroot().iter(f"{{{B}}}Building"):
        solid = ET.Element(f"{{{B}}}lod2Solid")
        b.insert(0, solid)  # Actual Komae references precede boundary definitions.
        shell = ET.SubElement(ET.SubElement(ET.SubElement(solid, f"{{{G}}}Solid"), f"{{{G}}}exterior"), f"{{{G}}}CompositeSurface")
        polygons = [p for branch in b.iter(f"{{{B}}}lod2MultiSurface") for p in branch.iter(f"{{{G}}}Polygon")]
        for i, p in enumerate(polygons):
            identifier = b.get(f"{{{G}}}id") + str(i)
            p.set(f"{{{G}}}id", identifier)
            ET.SubElement(shell, f"{{{G}}}surfaceMember", {X: "#" + identifier})
        for ms in b.iter(f"{{{G}}}MultiSurface"):
            ms.set("srsDimension", "3")
            for pos in ms.iter(f"{{{G}}}posList"):
                pos.attrib.pop("srsDimension", None)
    path = tmp_path / "references.gml"
    tree.write(path)
    return tree, path


def test_internal_forward_references_keep_every_face_and_h(tmp_path):
    tree, path = referenced(tmp_path)
    actual, excluded = read_lod2([path])
    expected, expected_excluded = read_lod2([FIXTURE])
    assert actual == expected and excluded == expected_excluded


@pytest.mark.parametrize("case", ["unknown", "duplicate", "missing", "external", "wrong_target", "duplicate_id", "mixed", "dimension"])
def test_references_fail_explicitly(tmp_path, case):
    tree, path = referenced(tmp_path)
    refs = [e for e in tree.getroot().iter() if X in e.attrib]
    if case == "unknown": refs[0].set(X, "#unknown")
    if case == "duplicate": refs[0].set(X, refs[1].get(X))
    if case == "missing":
        parent = next(e for e in tree.getroot().iter() if refs[0] in list(e))
        parent.remove(refs[0])
    if case == "external": refs[0].set(X, "other.gml#polygon")
    if case == "wrong_target": refs[0].set(X, "#synthetic_tokyo")
    if case == "duplicate_id":
        polys = list(tree.getroot().iter(f"{{{G}}}Polygon"))
        polys[0].set(f"{{{G}}}id", polys[1].get(f"{{{G}}}id"))
    if case == "mixed": ET.SubElement(refs[0], f"{{{G}}}Polygon")
    if case == "dimension": next(tree.getroot().iter(f"{{{G}}}MultiSurface")).set("srsDimension", "2")
    tree.write(path)
    with pytest.raises(GeometryValidationError): read_lod2([path])
