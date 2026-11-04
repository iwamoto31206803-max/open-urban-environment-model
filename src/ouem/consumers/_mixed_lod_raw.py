"""Independent bounded CityGML 2.0 reader for the Mixed-LoD Consumer."""
from collections import Counter
from hashlib import sha256
import math
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from shapely.geometry import Polygon

from ouem.native.building.source_h_geometry import require

G = "{http://www.opengis.net/gml}"
B = "{http://www.opengis.net/citygml/building/2.0}"
CORE = "{http://www.opengis.net/citygml/2.0}"
X = "{http://www.w3.org/1999/xlink}href"
SRS = "http://www.opengis.net/def/crs/EPSG/0/6697"


def child(node, tag):
    require(len(node) == 1 and node[0].tag == tag, node.tag, f"expected one inline {tag}")
    return node[0]


def face(polygon, dimension):
    require(len(polygon) and polygon[0].tag == G+"exterior"
            and all(r.tag == G+"interior" for r in list(polygon)[1:]), "Raw.Polygon", "invalid rings")
    rings = []
    for shell in polygon:
        pos = child(child(shell, G+"LinearRing"), G+"posList")
        require(dimension[pos] == "3" and not len(pos), "Raw.posList", "expected 3D ordinates")
        values = tuple(map(float, (pos.text or "").split()))
        require(12 <= len(values) <= 3_000_000 and len(values) % 3 == 0 and all(map(math.isfinite, values)),
                "Raw.posList", "invalid coordinates")
        ring = tuple((lon, lat, h) for lat, lon, h in zip(values[::3], values[1::3], values[2::3]))
        require(ring[0] == ring[-1] and all(abs(x) <= 180 and abs(y) <= 90 for x, y, _ in ring),
                "Raw.ring", "unclosed ring or invalid XY axes")
        rings.append(ring)
    return tuple(rings)


def faces(branch, surface, dimension, locator):
    require(len(surface), branch.tag, "empty geometry")
    result = []
    for ordinal, member in enumerate(surface, 1):
        require(member.tag == G+"surfaceMember", branch.tag, "unsupported surface member")
        polygon = child(member, G+"Polygon")
        require(not any(X in n.attrib for n in member.iter()), branch.tag, "inline polygons required")
        result.append((face(polygon, dimension), dict(branch_locator=locator,
                      polygon_id=polygon.get(G+"id"), polygon_ordinal=ordinal)))
    return result


def solid_surface(branch):
    return child(child(child(branch, G+"Solid"), G+"exterior"), G+"CompositeSurface")


def building(node, dimension):
    # Traverse XML in source order and construct locators independently of the selector.
    locations = {node: "."}
    for parent in node.iter():
        siblings = Counter()
        for element in parent:
            siblings[element.tag] += 1
            name = element.tag.replace(B, "bldg:").replace(G, "gml:")
            locations[element] = f"{locations[parent]}/{name}[{siblings[element.tag]}]"
    decoded, provenance = {}, {}
    one, two = ([el for el in node.iter() if el.tag.startswith(B+f"lod{lod}")] for lod in (1, 2))
    if one:
        require(len(one) == 1 and one[0].tag == B+"lod1Solid" and one[0] in list(node),
                "Raw.LoD1", "expected one direct lod1Solid")
        branch = one[0]
        require(not any(X in el.attrib for el in branch.iter()), "Raw.LoD1", "references unsupported")
        items = faces(branch, solid_surface(branch), dimension, locations[branch])
        decoded[1], provenance[1] = tuple(f for f, _ in items), ([locations[branch]], [p for _, p in items])
    if two:
        surfaces = [el for el in two if el.tag == B+"lod2MultiSurface"]
        solids = [el for el in two if el.tag == B+"lod2Solid"]
        require(surfaces and len(surfaces)+len(solids) == len(two) and len(solids) <= 1,
                "Raw.LoD2", "unsupported LoD2 branch")
        items = []
        for branch in surfaces:
            require(not any(X in el.attrib for el in branch.iter()), "Raw.LoD2", "MultiSurface references unsupported")
            items.extend(faces(branch, child(branch, G+"MultiSurface"), dimension, locations[branch]))
        if solids:
            require(solids[0] in list(node), "Raw.LoD2", "Solid must be direct")
            members = list(solid_surface(solids[0]))
            by_id = {p["polygon_id"]: (f, p) for f, p in items}
            refs = []
            for el in members:
                href = el.get(X, "")
                require(el.tag == G+"surfaceMember" and not len(el) and set(el.attrib) == {X}
                        and href.startswith("#"), "Raw.LoD2", "invalid Solid reference")
                refs.append(href[1:])
            require(len(refs) == len(items) == len(by_id) and None not in by_id and set(refs) == by_id.keys(),
                    "Raw.LoD2", "missing, duplicate or external Solid target")
            items = [by_id[key] for key in refs]
        decoded[2], provenance[2] = tuple(f for f, _ in items), ([locations[x] for x in surfaces], [p for _, p in items])
    require(decoded, "Raw.LoD", "Building has neither supported LoD")
    heights = [(el.text, el.get("uom"), len(el)) for el in node.findall(B+"measuredHeight")]
    return decoded, provenance[max(decoded)], heights


def read_zip(path, member, expected):
    name = PurePosixPath(member)
    require(not name.is_absolute() and ".." not in name.parts and "\\" not in member
            and name.suffix == ".gml", "Raw.member", "unsafe member")
    with ZipFile(path) as archive:
        require(archive.namelist().count(member) == 1, "Raw.member", "missing or duplicate ZIP member")
        info = archive.getinfo(member)
        require(info.file_size <= 256*1024*1024, "Raw.member", "member exceeds resource limit")
        content = archive.read(info)
    require(expected == dict(member=member, size_bytes=len(content), sha256=sha256(content).hexdigest()),
            "Raw.member", "member identity mismatch")
    require(b"\x00" not in content and b"<!DOCTYPE" not in content.upper() and b"<!ENTITY" not in content.upper(),
            "Raw.XML", "DTD/entities/non-ASCII-compatible XML unsupported")
    root = ET.fromstring(content)
    require(root.tag == CORE+"CityModel", "Raw.XML", "CityGML2 CityModel required")
    direct = {el[0] for el in root.findall(CORE+"cityObjectMember")
              if len(el) == 1 and el[0].tag == B+"Building"}
    require(direct, "Raw", "no parent buildings")
    dimension, ids, envelope = {root: root.get("srsDimension")}, set(), False
    scope = {root: None}
    for el in root.iter():
        require(el.tag != B+"BuildingPart" and (el.tag != B+"Building" or el in direct),
                "Raw", "BuildingPart or nested Building unsupported")
        for c in el:
            dimension[c] = c.get("srsDimension", dimension[el])
            scope[c] = next((lod for lod in (1,2,3,4) if c.tag.startswith(B+f"lod{lod}")), scope[el])
        require(dimension[el] in (None, "3") and el.get("srsName", SRS) == SRS, "Raw.CRS", "invalid CRS/dimension")
        if el.tag == G+"Envelope":
            require(el.get("srsName") == SRS and el.get("srsDimension") == "3", "Raw.CRS", "explicit 6697/3D required")
            envelope = True
        if G+"id" in el.attrib:
            identifier = el.get(G+"id")
            require(identifier.strip() and identifier not in ids, "Raw.XML", f"duplicate/blank XML ID: {identifier}")
            ids.add(identifier)
        for key, value in el.attrib.items():
            if key.endswith("}href") and scope[el] not in (3,4):
                require(scope[el] in (1,2) and key == X and el.tag == G+"surfaceMember"
                        and value.startswith("#") and len(value)>1,
                        "Raw.xlink", "unsupported reference outside supported Solid members")
    require(envelope, "Raw.CRS", "missing Envelope")
    result = {}
    for node in direct:
        sid = node.get(G+"id")
        require(sid, "Raw", "missing Building ID")
        try:
            result[sid] = building(node, dimension)
        except ValueError as exc:
            raise ValueError(f"{sid}: {exc}") from exc
    return result


def intersects(polygons, rectangle, xy):
    return any(Polygon([xy(*p[:2]) for p in face[0]],
                       [[xy(*p[:2]) for p in ring] for ring in face[1:]]).intersects(rectangle)
               for face in polygons)
