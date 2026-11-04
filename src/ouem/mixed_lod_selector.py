"""Experimental Raw CityGML2 selector. No Converter/Native/Standard/engine output."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import platform
import time
import xml.etree.ElementTree as ET
import zipfile

from pyproj import Transformer
from shapely.geometry import box

from ouem.native.building.source_h_geometry import GeometryValidationError, require
from ouem.native.building.source_h_lod2 import _ring, _signature
from ouem.standardize.building import deterministic_ouem_id
from ouem.standardize.building.source_h_geometry import as_shape, map_xy

SCHEMA = "ouem-raw-mixed-lod-selector-manifest/v0.1"
PROFILE = "experimental-raw-citygml2-lod2-else-lod1-source-h/v0.1"
G = "{http://www.opengis.net/gml}"
B = "{http://www.opengis.net/citygml/building/2.0}"
CORE = "{http://www.opengis.net/citygml/2.0}"
URO = "{https://www.geospatial.jp/iur/uro/3.2}"
X = "{http://www.w3.org/1999/xlink}href"
SRS = "http://www.opengis.net/def/crs/EPSG/0/6697"
CRS = dict(source_srs_name=SRS, source_tuple_order=["latitude", "longitude", "H"],
           geometry_tuple_order=["longitude", "latitude", "H"], horizontal_epsg=6668,
           vertical_epsg=6695, quantity="gravity_related_height", unit="metre",
           vertical_operation="identity_H", status="source-declared-not-survey-verified")


def canonical(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
                      allow_nan=False).encode("utf-8")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class SelectionError(GeometryValidationError):
    def __init__(self, code, record, cause):
        self.record = record
        super().__init__(code, record["source_id"], str(cause))


def _locations(building):
    result = {id(building): "."}
    def visit(node):
        counts = Counter()
        for child in node:
            counts[child.tag] += 1
            tag = child.tag.replace(B, "bldg:").replace(G, "gml:")
            result[id(child)] = f"{result[id(node)]}/{tag}[{counts[child.tag]}]"
            visit(child)
    visit(building)
    return result


def _face(polygon):
    require(polygon.tag == G+"Polygon" and len(polygon) > 0
            and polygon[0].tag == G+"exterior"
            and all(r.tag == G+"interior" for r in list(polygon)[1:]),
            "Raw.Polygon", "one exterior then interior rings required")
    rings = []
    for shell in polygon:
        require(not any(X in n.attrib for n in shell.iter()), "Raw.ring", "inline rings required")
        ring = _ring(shell)  # existing bounded finite, 3D, exact-closure primitive
        require(all(-180 <= x <= 180 and -90 <= y <= 90 for x,y,h in ring),
                "Raw.XY", "outside geographic lon/lat domain; check raw axis order")
        require(not list(shell[0][0]), "Raw.posList", "nested posList content unsupported")
        rings.append(ring)
    return tuple(rings)


def _metadata(branch, polygon, ordinal, locations):
    return dict(branch_locator=locations[id(branch)], polygon_id=polygon.get(G+"id"),
                polygon_ordinal=ordinal)


def _lod1(building, locations):
    branches = [n for n in building.iter() if n.tag.startswith(B+"lod1")]
    require(len(branches) == 1 and branches[0].tag == B+"lod1Solid"
            and branches[0] in list(building), "Raw.LoD1", "one direct lod1Solid required")
    branch = branches[0]
    require(len(branch) == 1 and branch[0].tag == G+"Solid", "Raw.LoD1", "inline Solid required")
    solid = branch[0]
    require(len(solid) == 1 and solid[0].tag == G+"exterior"
            and len(solid[0]) == 1 and solid[0][0].tag == G+"CompositeSurface",
            "Raw.LoD1", "only Solid exterior supported; interior shell unsupported")
    members = list(solid[0][0])
    require(members and all(n.tag == G+"surfaceMember" and len(n) == 1
            and n[0].tag == G+"Polygon" for n in members), "Raw.LoD1", "inline polygon members required")
    require(not any(X in n.attrib for n in branch.iter()), "Raw.LoD1", "LoD1 xref unsupported")
    return tuple(_face(n[0]) for n in members), [_metadata(branch,n[0],i+1,locations) for i,n in enumerate(members)]


def _lod2(building, locations):
    branches = [n for n in building.iter() if n.tag == B+"lod2MultiSurface"]
    solids = [n for n in building.iter() if n.tag == B+"lod2Solid"]
    require(branches and all(n.tag in (B+"lod2MultiSurface",B+"lod2Solid")
            for n in building.iter() if n.tag.startswith(B+"lod2")),
            "Raw.LoD2", "LoD2 requires supported MultiSurface; unsupported/empty branch is not absent")
    faces, metadata, polygons = [], [], []
    for branch in branches:
        require(len(branch) == 1 and branch[0].tag == G+"MultiSurface", "Raw.LoD2", "one inline MultiSurface required")
        members = list(branch[0])
        require(members and all(n.tag == G+"surfaceMember" and len(n) == 1
                and n[0].tag == G+"Polygon" for n in members), "Raw.LoD2", "nonempty inline polygon members required")
        require(not any(X in n.attrib for n in branch.iter()), "Raw.LoD2", "MultiSurface xref unsupported")
        for i, member in enumerate(members):
            polygons.append(member[0]); faces.append(_face(member[0]))
            metadata.append(_metadata(branch,member[0],i+1,locations))
    refs = [n for branch in solids for n in branch.iter() if X in n.attrib]
    if solids:
        require(len(solids) == 1 and solids[0] in list(building), "Raw.LoD2", "one direct lod2Solid required")
        solid = solids[0]
        require(len(solid) == 1 and solid[0].tag == G+"Solid" and len(solid[0]) == 1
                and solid[0][0].tag == G+"exterior" and len(solid[0][0]) == 1
                and solid[0][0][0].tag == G+"CompositeSurface", "Raw.LoD2", "only exterior reference Solid supported")
        members = list(solid[0][0][0])
        require(members and all(n.tag == G+"surfaceMember" and not len(n)
                and set(n.attrib) == {X} for n in members) and refs == members,
                "Raw.xlink", "only reference-only Solid members supported")
        targets = {p.get(G+"id"):i for i,p in enumerate(polygons)}
        identifiers = [n.get(X)[1:] for n in members]
        require(None not in targets and len(identifiers) == len(set(identifiers))
                and set(identifiers) == set(targets), "Raw.xlink", "missing, duplicate or cross-building target")
        order = [targets[key] for key in identifiers]
        resolved = [faces[i] for i in order]
        require(_signature(resolved) == _signature(faces), "Raw.xlink", "Solid/boundary correspondence failed")
        faces, metadata = resolved, [metadata[i] for i in order]
    return tuple(faces), metadata


def _intersects(faces, rectangle, transform):
    tree = ("GeometryCollection", tuple(("Polygon", p) for p in faces))
    # Pure XY projection on a temporary copy; untouched lon/lat/H goes to output.
    return bool(as_shape(map_xy(tree, transform)).intersects(rectangle))


def _building(node, member, bounds, project):
    sid = node.get(G+"id")
    presence = {lod:any(n.tag.startswith(B+f"lod{lod}") for n in node.iter()) for lod in (1,2)}
    record = dict(source_id=sid, ouem_id=deterministic_ouem_id(sid),
                  selected_lod=None, selection_reason="NO_SUPPORTED_LOD1_OR_LOD2",
                  lod1_presence=presence[1], lod2_presence=presence[2],
                  lod1_validation_status="ABSENT" if not presence[1] else "NOT_EVALUATED",
                  lod2_validation_status="ABSENT" if not presence[2] else "NOT_EVALUATED",
                  source_member=member, geometry_branch_locator=[], polygons=[],
                  geometry_sha256=None, aoi_intersects=None,
                  other_lods_present=[lod for lod in (3,4) if any(n.tag.startswith(B+f"lod{lod}") for n in node.iter())],
                  city_attributes=[dict(value=(n.text or "").strip(),code_space=n.get("codeSpace"))
                                   for n in node.iter(URO+"city")])
    locations = _locations(node)
    decoded = {}
    for lod, decoder in ((1,_lod1),(2,_lod2)):
        if presence[lod]:
            try:
                decoded[lod] = decoder(node, locations)
                record[f"lod{lod}_validation_status"] = "VALID"
            except (ValueError,IndexError,TypeError) as exc:
                record[f"lod{lod}_validation_status"] = "INVALID"
                raise SelectionError(f"LOD{lod}_INVALID",record,exc) from exc
    if decoded:
        lod = 2 if presence[2] else 1
        faces, metadata = decoded[lod]
        record.update(selected_lod=lod, selection_reason="LOD2_PRESENT_VALID" if lod==2 else "LOD2_ABSENT_USE_LOD1",
                      geometry_branch_locator=list(dict.fromkeys(p["branch_locator"] for p in metadata)),
                      polygons=metadata,geometry_sha256=hashlib.sha256(canonical(faces)).hexdigest(),
                      aoi_intersects=_intersects(faces, box(*bounds), project.transform))
        return record, faces
    return record, None


def _member(archive, name, bounds, project, seen_buildings):
    info = archive.getinfo(name)
    require(info.file_size <= 256*1024*1024, "Raw", "member exceeds 256MiB")
    h, tail = hashlib.sha256(), b""
    with archive.open(info) as stream:
        while chunk := stream.read(1024*1024):
            h.update(chunk); data=tail+chunk
            require(b"\x00" not in data and b"<!DOCTYPE" not in data.upper() and b"<!ENTITY" not in data.upper(),
                    "Raw.XML", "DTD/entities/non-ASCII-compatible XML unsupported")
            tail=data[-16:]
    identity = dict(member=name,sha256=h.hexdigest(),size_bytes=info.file_size)
    root, envelope, inside, dimensions, tags, xml_ids = None, False, False, [], [], set()
    rows, geometry = [], {}
    with archive.open(info) as stream:
        for event,node in ET.iterparse(stream,events=("start","end")):
            if root is None:
                root=node
                require(root.tag==CORE+"CityModel", "Raw.XML", "CityGML2 CityModel required")
            if event=="start":
                tags.append(node.tag)
                require(node.tag!=B+"BuildingPart", "Raw", "BuildingPart unsupported")
                if node.tag==B+"Building":
                    require(not inside and len(tags)>1 and tags[-2]==CORE+"cityObjectMember", "Raw", "direct non-nested Building required")
                    inside=True
                    sid=node.get(G+"id")
                    require(sid and sid.strip() and sid not in seen_buildings, "Raw.Building.id", "missing/duplicate Building ID")
                    seen_buildings.add(sid)
                dimensions.append(node.get("srsDimension",dimensions[-1] if dimensions else None))
                require(dimensions[-1] in (None,"3"), "Raw.dimension", "only 3D supported")
                if node.tag==G+"posList" and dimensions[-1]=="3":node.set("srsDimension","3")
                if G+"id" in node.attrib:
                    identifier=node.get(G+"id")
                    require(identifier.strip() and identifier not in xml_ids, "Raw.XML.id", "empty/duplicate XML ID")
                    xml_ids.add(identifier)
                if "srsName" in node.attrib:require(node.get("srsName")==SRS,"Raw.srsName","explicit 6697 required")
                if node.tag==G+"Envelope":
                    require(node.get("srsName")==SRS and node.get("srsDimension")=="3", "Raw.Envelope", "6697/3D envelope required")
                    envelope=True
                ignored_lod = any(t.startswith((B+"lod3",B+"lod4")) for t in tags)
                for key,value in node.attrib.items():
                    if key.endswith("}href") and not ignored_lod:
                        require(inside and key==X and node.tag==G+"surfaceMember" and value.startswith("#") and len(value)>1,
                                "Raw.xlink","only internal surfaceMember reference supported")
                        require(any(t.startswith((B+"lod1",B+"lod2")) for t in tags), "Raw.xlink", "reference outside selected LoD branches")
                continue
            dimensions.pop(); tags.pop()
            if node.tag==B+"Building":
                row,faces=_building(node,name,bounds,project)
                rows.append(row)
                if faces is not None:geometry[row["source_id"]]=faces
                node.clear(); inside=False
            elif node.tag==CORE+"cityObjectMember":root.clear()
    require(envelope,"Raw.Envelope","missing explicit CRS declaration")
    return identity,rows,geometry


def select_raw(zip_path, members, *, release, bounds):
    """Validate every present LoD1/2 before AOI filtering; return un-clipped 3D faces.

    VALID means supported numerical/structural scope, not XSD/manifold/survey validity.
    LoD3/4 geometry is not interpreted, repaired or used as a fallback.
    """
    require(isinstance(release,str) and release.strip(),"release","explicit source release required")
    require(len(bounds)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in bounds)
            and bounds[0]<bounds[2] and bounds[1]<bounds[3],"AOI","finite increasing EPSG6677 bounds required")
    require(members and len(members)==len(set(members)),"members","nonempty unique members required")
    for name in members:
        p=PurePosixPath(name)
        require(not p.is_absolute() and ".." not in p.parts and "\\" not in name and p.suffix==".gml",
                "members","safe explicit GML ZIP member required")
    zip_path=Path(zip_path).resolve(strict=True)
    before=digest(zip_path)
    seen,identities,records,geometries=set(),[],[],{}
    with zipfile.ZipFile(zip_path) as archive:
        names=archive.namelist()
        for member in members:require(names.count(member)==1,"ZIP","member missing or duplicated")
        project=Transformer.from_crs(6668,6677,always_xy=True)
        for member in members:
            identity,rows,geometry=_member(archive,member,bounds,project,seen)
            identities.append(identity);records.extend(rows);geometries.update(geometry)
    require(digest(zip_path)==before,"ZIP","input changed during selection","INPUT_CHANGED")
    records.sort(key=lambda r:r["source_id"])
    counts=lambda rows:{str(lod):sum(r["selected_lod"]==lod for r in rows) for lod in (1,2)}
    manifest=dict(schema=SCHEMA,profile=PROFILE,status="EXPERIMENTAL",execution_status="COMPLETED",
        formal_acceptance="NOT_VERIFIED",source=dict(zip_path=str(zip_path),zip_sha256=before,release=release,members=identities),
        crs=CRS,aoi=dict(epsg=6677,bounds=list(bounds),predicate="selected full 3D geometry, XY-only intersects; boundary included; no clip"),
        namespaces=dict(bldg=B[1:-1],gml=G[1:-1]),input_unchanged=True,
        counts=dict(raw_buildings=len(records),selected_lods=counts(records),
            aoi_selected_lods=counts([r for r in records if r["aoi_intersects"]]),
            excluded_no_lod=sum(r["selected_lod"] is None for r in records)),records=records)
    return manifest,geometries


def run(zip_path,members,*,release,bounds,output_dir):
    """Fresh output only; no success manifest on any failure."""
    out=Path(output_dir)
    out.mkdir()  # never overwrite/resume, including failed runs
    started=time.perf_counter()
    try:
        manifest,geometries=select_raw(zip_path,members,release=release,bounds=bounds)
        path=out/"geometries.jsonl"
        with path.open("xb") as stream:
            for row in manifest["records"]:
                if row["selected_lod"] is not None:
                    stream.write(canonical(dict(source_id=row["source_id"],selected_lod=row["selected_lod"],
                                                faces=geometries[row["source_id"]]))+b"\n")
        require(digest(zip_path)==manifest["source"]["zip_sha256"],"ZIP","input changed before publication","INPUT_CHANGED")
        manifest.update(geometry_output=dict(path=path.name,sha256=digest(path),encoding="UTF-8 JSONL; ordered faces/rings/longitude,latitude,H"),
            implementation_sha256=digest(__file__),python=platform.python_version(),
            completed_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started)
        pending=out/"manifest.pending.json"
        with pending.open("xb") as stream:stream.write(canonical(manifest)+b"\n")
        pending.rename(out/"manifest.json")
        return manifest
    except Exception as exc:
        failure=dict(schema=SCHEMA,profile=PROFILE,execution_status="FAILED",error=str(exc),
                     code=getattr(exc,"code",type(exc).__name__),failed_record=getattr(exc,"record",None))
        with (out/"failure.json").open("xb") as stream:stream.write(canonical(failure)+b"\n")
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip",type=Path,required=True)
    parser.add_argument("--member",action="append",required=True)
    parser.add_argument("--release",required=True)
    parser.add_argument("--bounds",type=float,nargs=4,required=True,help="xmin ymin xmax ymax in EPSG:6677")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    try:
        result=run(args.zip,args.member,release=args.release,bounds=args.bounds,output_dir=args.output_dir)
    except Exception as exc:
        parser.exit(2,f"Raw selector FAILED: {exc}\n")
    print(json.dumps(result["counts"],sort_keys=True))


if __name__=="__main__":main()
