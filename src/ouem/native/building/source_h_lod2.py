"""Bounded CityGML2 LoD2 correspondence, not a general CityGML reader."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from .source_h_geometry import polygons, require

G = "http://www.opengis.net/gml"
B = "http://www.opengis.net/citygml/building/2.0"
X = "{http://www.w3.org/1999/xlink}href"
NS = {"gml": G, "bldg": B}
SRS = "http://www.opengis.net/def/crs/EPSG/0/6697"


def _ring(element):
    require(len(element) == 1 and element[0].tag == f"{{{G}}}LinearRing", "Raw.ring", "only inline LinearRing supported")
    ring = element[0]
    require(len(ring) == 1 and ring[0].tag == f"{{{G}}}posList", "Raw.ring", "only one posList supported")
    pos = ring[0]
    require(pos.get("srsDimension") == "3", "Raw.posList", "explicit 3D posList required")
    values = list(map(float, (pos.text or "").split()))
    require(12 <= len(values) <= 3_000_000 and len(values) % 3 == 0 and all(map(math.isfinite, values)),
            "Raw.posList", "finite 3D closed rings within resource bound required")
    points = tuple((values[i+1], values[i], values[i+2]) for i in range(0, len(values), 3))
    require(points[0] == points[-1], "Raw.ring", "unclosed ring")
    return points


def read_lod2(paths):
    """Return eligible/excluded IDs; reject unsupported constructs, never repair."""
    features, excluded, seen_ids = {}, [], set()
    for path in paths:
        path = Path(path)
        require(path.stat().st_size <= 256*1024*1024, "Raw", "member exceeds 256 MiB parsing budget")
        with path.open("rb") as stream:
            tail = b""
            while chunk := stream.read(1024*1024):
                data = tail+chunk
                require(b"\x00" not in data and b"<!DOCTYPE" not in data.upper() and b"<!ENTITY" not in data.upper(),
                        "Raw.XML", "DTD/entities and non-ASCII-compatible encodings unsupported")
                tail = data[-16:]
        root, envelope = None, False
        dimensions, xml_ids = [], set()
        inside_building = False
        for event, node in ET.iterparse(path, events=("start", "end")):
            if root is None:
                root = node
                require(root.tag == "{http://www.opengis.net/citygml/2.0}CityModel", "Raw.XML", "CityGML2 CityModel required")
            if event == "start":
                require(node.tag != f"{{{B}}}BuildingPart", "Raw", "BuildingPart not supported")
                if node.tag == f"{{{B}}}Building":
                    require(not inside_building, "Raw", "nested Building unsupported")
                    inside_building = True
                dimensions.append(node.get("srsDimension", dimensions[-1] if dimensions else None))
                require(dimensions[-1] in (None, "3"), "Raw.dimension", "only 3D supported")
                if node.tag == f"{{{G}}}posList" and dimensions[-1] == "3":
                    node.set("srsDimension", "3")
                xml_id = node.get(f"{{{G}}}id")
                if xml_id is not None:
                    require(xml_id.strip() and xml_id not in xml_ids, "Raw.id", "missing/duplicate XML ID")
                    xml_ids.add(xml_id)
                for key in node.attrib:
                    if key.endswith("}href"):
                        require(inside_building and key == X and node.tag == f"{{{G}}}surfaceMember"
                                and node.get(key).startswith("#") and len(node.get(key)) > 1,
                                "Raw.xlink", "only internal surfaceMember xlink supported")
                if "srsName" in node.attrib:
                    require(node.get("srsName") == SRS, "Raw.srsName", "explicit 6697 required", "CRS_INCONSISTENT")
                if node.tag == f"{{{G}}}Envelope":
                    require(node.get("srsName") == SRS and node.get("srsDimension") == "3", "Raw.Envelope", "6697/3D envelope required")
                    envelope = True
                continue
            dimensions.pop()
            if node.tag == f"{{{B}}}Building":
                identifier = node.get(f"{{{G}}}id")
                require(identifier and identifier.strip() and identifier not in seen_ids,
                        "Raw.id", "missing/duplicate Building ID", "IDENTITY_MISMATCH")
                seen_ids.add(identifier)
                selected = node.findall(".//bldg:lod2MultiSurface", NS)
                require(all(n.tag == f"{{{B}}}lod2MultiSurface" for n in node.iter()
                            if n.tag.startswith(f"{{{B}}}lod2") and n.tag != f"{{{B}}}lod2Solid"), "Raw.LoD2", "unsupported selected LoD2 representation")
                faces = []
                for branch in selected:
                    # No uninspected selected geometry representation is skipped.
                    allowed = {f"{{{G}}}{n}" for n in ("MultiSurface", "surfaceMember", "Polygon", "exterior", "interior", "LinearRing", "posList")}
                    require(all(n is branch or n.tag in allowed for n in branch.iter()), "Raw.LoD2", "unsupported LoD2 geometry construct")
                    require(len(branch) == 1 and branch[0].tag == f"{{{G}}}MultiSurface",
                            "Raw.LoD2", "one inline MultiSurface required")
                    members = list(branch[0])
                    require(all(m.tag == f"{{{G}}}surfaceMember" for m in members), "Raw.LoD2", "only surfaceMember children supported")
                    require(members and all(len(m) == 1 and m[0].tag == f"{{{G}}}Polygon" for m in members),
                            "Raw.LoD2", "inline polygon surfaceMembers required")
                    for member in members:
                        polygon = member[0]
                        require(len(polygon) > 0 and polygon[0].tag == f"{{{G}}}exterior"
                                and all(r.tag == f"{{{G}}}interior" for r in list(polygon)[1:]), "Raw.Polygon", "one exterior then interiors required")
                        faces.append(tuple(_ring(r) for r in polygon))
                solids = node.findall(".//bldg:lod2Solid", NS)
                references = [n for n in node.iter() if X in n.attrib]
                if solids:
                    require(len(solids) == 1 and solids[0] in list(node), "Raw.LoD2", "one direct lod2Solid supported")
                    solid = solids[0]
                    require(len(solid) == 1 and solid[0].tag == f"{{{G}}}Solid"
                            and len(solid[0]) == 1 and solid[0][0].tag == f"{{{G}}}exterior"
                            and len(solid[0][0]) == 1 and solid[0][0][0].tag == f"{{{G}}}CompositeSurface",
                            "Raw.LoD2", "only Solid/exterior/CompositeSurface references supported")
                    members = list(solid[0][0][0])
                    require(members and all(m.tag == f"{{{G}}}surfaceMember" and len(m) == 0
                            and set(m.attrib) == {X} for m in members),
                            "Raw.xlink", "only reference-only Solid members supported")
                    require(set(references) == set(members), "Raw.xlink", "references outside LoD2 Solid unsupported")
                    targets = {p.get(f"{{{G}}}id"): p for branch in selected
                               for p in branch.iter(f"{{{G}}}Polygon")}
                    ids = [m.get(X)[1:] for m in members]
                    require(len(ids) == len(set(ids)), "Raw.xlink", "duplicate Solid reference")
                    require(None not in targets and set(ids) == set(targets),
                            "Raw.xlink", "unknown, cross-building or missing LoD2 Polygon reference")
                    resolved = [tuple(_ring(r) for r in targets[i]) for i in ids]
                    require(_signature(resolved) == _signature(faces), "Raw.xlink", "Solid/boundary faces differ")
                    faces = resolved
                else:
                    require(not references, "Raw.xlink", "references require supported LoD2 Solid")
                if faces:
                    features[identifier] = tuple(faces)
                else:
                    excluded.append(identifier)
                node.clear()
                inside_building = False
            elif node.tag.endswith("}cityObjectMember"):
                root.clear()
        require(envelope, "Raw.Envelope", "missing CRS declaration")
    require(features, "Raw.LoD2", "no eligible LoD2 buildings")
    return features, excluded


def _canonical_ring(ring):
    # Retain every XYZ/multiplicity; ignore only cyclic start and direction.
    values = tuple(ring[:-1])
    require(len(values) <= 4096, "Raw.ring", "canonical matching budget exceeded")
    return min(seq[i:]+seq[:i] for seq in (values, values[::-1]) for i in range(len(seq)))


def _signature(faces):
    return sorted((_canonical_ring(p[0]), tuple(sorted(_canonical_ring(r) for r in p[1:]))) for p in faces)


def compare_lod2(snapshot, raw):
    require(snapshot.features.keys() == raw.keys(), "LoD2.ids", "Raw/Converter eligible ID sets differ", "IDENTITY_MISMATCH")
    for identifier, tree in snapshot.features.items():
        require(_signature(polygons(tree)) == _signature(raw[identifier]), identifier,
                "LoD2 faces, rings or exact source lon/lat/H differ", "LOD2_MISMATCH")
    return {"lod2_correspondence": "PASS", "source_storage_axis_correspondence": "PASS",
            "scope": "supported LoD2 numerical geometry only; not H datum accuracy"}
