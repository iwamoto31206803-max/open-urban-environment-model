"""Read-only independent verification of the experimental Mixed-LoD chain."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import json
import math
import os
from pathlib import Path
import platform
import struct
from uuid import uuid5, NAMESPACE_URL

from pyproj import CRS, Proj, __version__ as pyproj_version, proj_version_str
from shapely import from_wkb
from shapely.geometry import box

from ouem.native.building.source_h_geometry import inspect_geopackage, open_readonly, polygons, quoted, require
from ._source_h_geometry import decode
from . import _mixed_lod_raw as city
from .source_h_standard import Watch, strict_json, same_json

PROFILE = "ouem-standard-building/plateau-mixed-lod-source-h/v0.1"
NATIVE = "ouem-native-building/plateau-mixed-lod-source-h/v0.1"
SCHEMA = "ouem-mixed-lod-consumer-receipt/v0.1"
LAYER = "bldg:Building"
TOLERANCE = 1e-7
BINARY_SHA = "0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b"
COMMIT = "ce7766df9788ce391b149c55df16d33082d0bc72"
PREDICATE = "selected full 3D geometry, XY-only intersects; boundary included; no clip"
CRS_RAW = dict(source_srs_name=city.SRS, source_tuple_order=["latitude","longitude","H"],
               geometry_tuple_order=["longitude","latitude","H"], horizontal_epsg=6668,
               vertical_epsg=6695, quantity="gravity_related_height", unit="metre",
               vertical_operation="identity_H", status="source-declared-not-survey-verified")
LIMITS = ["XY tolerance is a numerical comparison budget, not survey or datum accuracy.",
          "Checks are point-in-time; hashes do not authenticate historical process claims or prevent concurrent mutation.",
          "Bounded CityGML 2.0/ISO WKB Z subset; solid topology and XSD conformance unverified.",
          "Terrain, VoxCity, GUI, eligibility and formal acceptance unverified."]
ARTIFACTS = {"native_manifest", "native_gpkg", "bridge_receipt", "selector_manifest", "selector_geometry",
             "raw_zip", "bridge_implementation", "converter_binary", "extracted_member",
             "lod1_gpkg", "lod2_gpkg", "lod1_stdout", "lod1_stderr", "lod2_stdout", "lod2_stderr"}
ATTRS = ("source_id", "ouem_id", "source_dataset", "source_lod", "selection_reason", "source_member",
         "source_release", "converter_pass", "measured_height", "measured_height_raw")


def zone_ix():
    # Explicit GRS80 transverse Mercator, independent of the producer Transformer/CRS pipeline.
    return Proj(proj="tmerc", lat_0=36, lon_0=139+50/60, k=.9999, x_0=0, y_0=0, ellps="GRS80", units="m")


def digest(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def indexed(rows, field):
    result = {row["source_id"]: row for row in rows}
    require(len(result) == len(rows), field, "duplicate ID")
    return result


def load(path):
    require(path.stat().st_size <= 64*1024*1024, str(path), "JSON exceeds budget")
    return strict_json(path.read_bytes())


def track(watch, key, ref):
    path = Path(ref["path"])
    require(path.is_absolute() and path == path.resolve(strict=True) and path.is_relative_to(watch.root),
            key, "expected canonical absolute path within artifact root")
    return watch.capture(key, path.relative_to(watch.root).as_posix(), ref["sha256"], ref["size_bytes"])


def declaration(doc, schema, profile=None):
    require(doc.get("schema") == schema and doc.get("execution_status") == "COMPLETED"
            and doc.get("status") == "EXPERIMENTAL" and "error" not in doc
            and (profile is None or doc.get("profile") == profile),
            "manifest", f"incompatible or incomplete {schema}")


def graph(watch, manifest_path, pinned, bounds):
    loc = manifest_path.relative_to(watch.root).as_posix()
    require(isinstance(pinned, str) and len(pinned) == 64, "Standard", "explicit SHA required")
    standard = watch.capture("standard_manifest", loc, pinned, json_data=True)
    declaration(standard, "ouem-mixed-lod-standard-manifest/v0.1", PROFILE)
    require(standard["native_profile"] == NATIVE and standard["formal_acceptance"] == "NOT_VERIFIED",
            "Standard", "incompatible Native profile or acceptance")
    refs = standard["inputs"]
    require(set(refs) == ARTIFACTS, "Standard.inputs", "incomplete or unexpected provenance graph")
    paths = {key: track(watch, key, ref) for key, ref in refs.items()}
    paths["standard"] = track(watch, "standard_gpkg", standard["output"])
    require(paths["standard"] == manifest_path.with_name("standard.gpkg") and standard["output"]["layer"] == "building",
            "Standard.output", "expected adjacent building GeoPackage")
    native, bridge, selector = (load(paths[k]) for k in ("native_manifest", "bridge_receipt", "selector_manifest"))
    declaration(native, "ouem-mixed-lod-native-manifest/v0.1", NATIVE)
    declaration(bridge, "ouem-mixed-lod-converter-bridge/v0.1")
    declaration(selector, "ouem-raw-mixed-lod-selector-manifest/v0.1", "experimental-raw-citygml2-lod2-else-lod1-source-h/v0.1")
    require(native["formal_acceptance"] == selector["formal_acceptance"] == "NOT_VERIFIED"
            and bridge["mixed_native_handoff"] == "ELIGIBLE" and selector["input_unchanged"] is True,
            "chain", "ineligible or incompatible records")
    same_json(native["artifacts"], {k:v for k,v in refs.items() if k not in ("native_manifest","native_gpkg")}, "Native.artifacts")
    same_json(native["native"], refs["native_gpkg"] | {"layer": LAYER}, "Native.output")
    require(paths["native_gpkg"] == paths["native_manifest"].with_name("native.gpkg"), "Native.output", "nonadjacent GeoPackage")
    for key in ("selector_manifest","selector_geometry","extracted_member"):
        same_json(bridge[key], refs[key], "Bridge."+key)
    require(paths["selector_geometry"] == paths["selector_manifest"].with_name("geometries.jsonl")
            and selector["geometry_output"]["path"] == paths["selector_geometry"].name
            and selector["geometry_output"]["sha256"] == refs["selector_geometry"]["sha256"],
            "selector", "geometry reference differs")
    source = selector["source"]
    for doc in (standard, native, bridge):
        same_json(doc["raw_source"], source, "Raw.source")
    require(source["zip_path"] == str(paths["raw_zip"]) and source["zip_sha256"] == refs["raw_zip"]["sha256"]
            and isinstance(source["release"], str) and source["release"].strip() and len(source["members"]) == 1,
            "Raw.source", "ZIP/release/member identity differs")
    member = source["members"][0]
    require((member["sha256"], member["size_bytes"]) == (refs["extracted_member"]["sha256"], refs["extracted_member"]["size_bytes"])
            and paths["extracted_member"] == paths["bridge_receipt"].parent/"extracted"/member["member"],
            "Bridge.member", "extracted member does not bind Raw ZIP")
    aoi = dict(epsg=6677, bounds=list(bounds), predicate=PREDICATE)
    for doc in (standard, native, bridge, selector):
        # Bounds supplied as floats, older JSON may express integral values as integers.
        require(doc["aoi"] == aoi, "AOI", "bounds or predicate differs")
    for doc in (native, bridge, selector):
        same_json(doc["crs"], CRS_RAW, "Raw.CRS")
    same_json(standard["crs"], dict(input=CRS_RAW, output_horizontal_epsg=6677,
              output_axes=["X","Y","H"], vertical_epsg=6695, vertical_operation="identity_H"), "Standard.CRS")
    operation = standard["operation"]
    settings = dict(always_xy=True, allow_ballpark=False, only_best=True, source_epsg=6668,
                    target_epsg=6677, arguments=["longitude","latitude"])
    same_json({k:operation[k] for k in settings}, settings, "Standard.operation")
    require(isinstance(operation["definition"], str) and operation["definition"].strip(), "Standard.operation", "missing operation identity")
    binary = refs["converter_binary"]
    same_json(bridge["converter"], dict(binary=binary, commit=COMMIT, version="nusamai 0.1.19"), "Converter")
    same_json(native["converter"], bridge["converter"], "Native.converter")
    require(binary["sha256"] == BINARY_SHA, "Converter", "unexpected binary")
    require(set(native["branches"]) == set(bridge["branches"]) == {"1","2"}, "Converter", "expected exactly two passes")
    for lod in (1,2):
        branch = bridge["branches"][str(lod)]
        argv = [binary["path"], refs["extracted_member"]["path"], "--sink", "gpkg", "--output", refs[f"lod{lod}_gpkg"]["path"],
                "--epsg", "6697", "-t", f"use_lod=lod{lod}", "-t", "split_components=false"]
        require(branch["argv"] == argv and type(branch["exit_code"]) is int and branch["exit_code"] == 0 and "error" not in branch,
                f"LoD{lod}", "invalid recorded Converter execution")
        start, end = (datetime.fromisoformat(branch[k]) for k in ("started_at","ended_at"))
        require(start.tzinfo is not None and end >= start, f"LoD{lod}", "invalid execution times")
        keys = ("argv","exit_code","started_at","ended_at","gpkg","stdout","stderr")
        same_json(native["branches"][str(lod)], {k:branch[k] for k in keys}, f"Native.LoD{lod}")
        for kind, suffix in (("gpkg",".gpkg"),("stdout",".stdout.log"),("stderr",".stderr.log")):
            key = f"lod{lod}_{kind}"
            same_json(branch[kind], refs[key], f"Bridge.{key}")
            require(paths[key] == paths["bridge_receipt"].parent/f"lod{lod}{suffix}", key, "unexpected branch path")
    package = Path(__file__).resolve().parents[1]
    for key, impl, file in (("selector_impl", {"sha256":selector["implementation_sha256"]}, package/"mixed_lod_selector.py"),
                            ("bridge_impl", bridge["implementation"], package/"mixed_lod_converter_bridge.py"),
                            ("native_impl", native["implementation"], package/"native/building/mixed_lod.py"),
                            ("standard_impl", standard["implementation"], package/"standardize/building/mixed_lod.py")):
        require("path" not in impl or impl["path"] == str(file), key, "implementation path differs")
        watch.capture(key, file.relative_to(watch.root).as_posix(), impl["sha256"], impl.get("size_bytes"))
    same_json(bridge["implementation"], refs["bridge_implementation"], "Bridge.implementation")
    return standard, native, bridge, selector, paths, member


def bits(point):
    return struct.pack("<ddd", *point)


def ring_key(ring):
    coords = tuple(map(bits, ring[:-1]))
    require(bits(ring[0]) == bits(ring[-1]) and len(coords) <= 4096, "ring", "closure or comparison budget")
    first = min(coords)
    return min(seq[i:]+seq[:i] for seq in (coords, coords[::-1]) for i, value in enumerate(seq) if value == first)


def face_keys(faces):
    return Counter((ring_key(face[0]), tuple(sorted(ring_key(r) for r in face[1:]))) for face in faces)


def cross_decode(blob, tree, sid):
    """Cross-check the shared structural decoder with GEOS, including signed H bits."""
    offset = 8 + 8 * (0, 4, 6)[(blob[3] >> 1) & 7]
    shape = from_wkb(blob[offset:])
    require(shape.geom_type == tree[0] == "MultiPolygon" and shape.has_z,
            sid, "GEOS geometry type or dimension differs")
    faces = tuple(tuple(tuple(map(bits, ring.coords)) for ring in (p.exterior, *p.interiors))
                  for p in shape.geoms)
    expected = tuple(tuple(tuple(map(bits, ring)) for ring in p) for p in polygons(tree))
    require(faces == expected, sid, "GEOS and ISO WKB decoders differ")


def oid(sid):
    return "oub-"+str(uuid5(NAMESPACE_URL, "ouem-standard-building-v0.1|PLATEAU CityGML|"+sid))


def raw_selection(raw, selector, geometry, member, bounds, xy):
    rows = indexed(selector["records"], "Selector")
    require(raw.keys() == rows.keys(), "Selector.IDs", "Raw and selector ID sets differ")
    rectangle = box(*bounds)
    selected, decisions = {}, {}
    with geometry.open("rb") as stream:
        for sid, (lods, (branches, polygons_meta), _) in sorted(raw.items()):
            lod = max(lods)
            faces = lods[lod]
            reason = "LOD2_PRESENT_VALID" if lod == 2 else "LOD2_ABSENT_USE_LOD1"
            hit = city.intersects(faces, rectangle, xy)
            row = dict(source_id=sid, ouem_id=oid(sid), selected_lod=lod, selection_reason=reason,
                       source_member=member, aoi_intersects=hit)
            for key, value in (row | dict(
                    lod1_presence=1 in lods, lod2_presence=2 in lods,
                    lod1_validation_status="VALID" if 1 in lods else "ABSENT",
                    lod2_validation_status="VALID" if 2 in lods else "ABSENT",
                    geometry_branch_locator=branches, polygons=polygons_meta,
                    geometry_sha256=sha256(canonical(faces)).hexdigest())).items():
                same_json(rows[sid][key], value, f"{sid}.Selector.{key}")
            require(stream.readline() == canonical(dict(source_id=sid, selected_lod=lod, faces=faces))+b"\n",
                    sid, "Selector geometry differs from Raw")
            decisions[sid] = row
            if hit:
                selected[sid] = row
        require(not stream.read(1), "Selector", "extra geometry records")
    require(selected, "AOI", "no selected buildings")
    return selected, decisions


def converter_passes(raw, bridge, paths):
    snapshots = {}
    for lod in (1,2):
        snapshot = inspect_geopackage(paths[f"lod{lod}_gpkg"], LAYER)
        branch = bridge["branches"][str(lod)]
        expected = {sid:lods[lod] for sid, (lods, _, _) in raw.items() if lod in lods}
        require(snapshot.features.keys() == expected.keys() == branch["features"].keys(),
                f"Converter.LoD{lod}", "ID sets differ")
        results = Counter()
        for sid, tree in snapshot.features.items():
            source, actual = expected[sid], polygons(tree)
            require(face_keys(source) == face_keys(actual), sid, f"Converter LoD{lod} Raw face/ring/XYZ differs")
            result = "EXACT" if source == actual else "ORDER_ONLY"
            results[result] += 1
            evidence = dict(result=result, layer=LAYER, id=sid, blob_sha256=snapshot.geometry_hashes[sid],
                            raw_faces=len(source), converter_faces=len(actual),
                            raw_interiors=sum(len(p)-1 for p in source), converter_interiors=sum(len(p)-1 for p in actual),
                            geometry_type=tree[0])
            same_json(branch["features"][sid], evidence, f"{sid}.Bridge.LoD{lod}")
        require((branch["expected_features"],branch["converter_features"]) == (len(expected),len(expected))
                and branch["results"] == dict(results), f"Converter.LoD{lod}", "summary differs")
        snapshots[lod] = snapshot
    return snapshots


def verify_decisions(all_rows, selected, raw, native, bridge, selector):
    native_rows = indexed(native["decisions"], "Native")
    bridge_rows = indexed(bridge["selection"], "Bridge")
    require(native_rows.keys() == bridge_rows.keys() == all_rows.keys(), "decisions", "incomplete ID sets")
    for sid, row in all_rows.items():
        lod = row["selected_lod"]
        feature = bridge["branches"][str(lod)]["features"][sid]
        bridge_row = {k:row[k] for k in ("source_id","selected_lod","selection_reason","aoi_intersects")}
        same_json(bridge_rows[sid], bridge_row | dict(feature=feature, feature_eligible=True), sid+".Bridge.selection")
        decision = row | dict(disposition="OUTSIDE_AOI")
        if sid in selected:
            branches, polys = raw[sid][1]
            decision.update(disposition="INCLUDED", converter_pass=f"lod{lod}", feature=feature,
                            raw_branches=branches, raw_polygons=polys,
                            raw_geometry_sha256=sha256(canonical(raw[sid][0][lod])).hexdigest())
        same_json(native_rows[sid], decision, sid+".Native.decision")
    count = lambda rows: {str(lod):sum(r["selected_lod"]==lod for r in rows.values()) for lod in (1,2)}
    expected = dict(raw_buildings=len(all_rows), selected_lods=count(all_rows),
                    aoi_selected_lods=count(selected), excluded_no_lod=0)
    same_json(selector["counts"], expected, "Selector.counts")
    same_json(bridge["raw_counts"], expected, "Bridge.counts")
    same_json(bridge["candidate"], dict(selected=len(selected),feature_eligible=len(selected)), "Bridge.candidate")
    same_json(native["counts"], dict(included=len(selected),excluded=len(all_rows)-len(selected),
              by_lod={k:v for k,v in count(selected).items() if v}), "Native.counts")


def gpkg_rows(paths, selected, snapshots, bridge, release, raw):
    actual = inspect_geopackage(paths["native_gpkg"], LAYER)
    require(actual.features.keys() == selected.keys(), "Native.IDs", "unexpected or missing selected ID")
    converter_attrs = {}
    for lod, snapshot in snapshots.items():
        with open_readonly(paths[f"lod{lod}_gpkg"]) as db:
            converter_attrs[lod] = {sid:(blob,height) for sid,blob,height in db.execute(
                f'SELECT id,{quoted(snapshot.geometry_column)},measuredHeight FROM "bldg:Building"')
                if sid in selected and selected[sid]["selected_lod"] == lod}
    expected = {}
    with open_readonly(paths["native_gpkg"]) as db:
        require(db.execute("SELECT * FROM gpkg_geometry_columns").fetchall()
                == [(LAYER,"geometry","MULTIPOLYGON",6697,1,0)], "Native.CRS", "unexpected Native declaration")
        rows = db.execute('SELECT id,geometry,ouem_id,selected_lod,selection_reason,source_member,source_release,'
                          'converter_pass,source_feature_id,geometry_blob_sha256,measured_height_raw,measuredHeight FROM "bldg:Building"')
        for sid, blob, ouem, lod, reason, member, rel, branch, feature_id, sha, original, usable in rows:
            row = selected[sid]
            require(type(lod) is int and lod == row["selected_lod"] and branch == f"lod{lod}", sid, "Native LoD/pass differs")
            require((ouem,reason,member,rel,feature_id) == (row["ouem_id"],row["selection_reason"],row["source_member"],release,sid),
                    sid, "Native identity/provenance differs")
            source_blob, source_height = converter_attrs[lod][sid]
            require(blob == source_blob and sha == sha256(blob).hexdigest()
                    == bridge["branches"][str(lod)]["features"][sid]["blob_sha256"], sid, "Native BLOB mismatch")
            cross_decode(blob, actual.features[sid], sid)
            require(source_height is None or type(source_height) in (float,int) and math.isfinite(source_height),
                    sid, "invalid Converter height")
            declarations = raw[sid][2]
            if declarations:
                require(len(declarations) == 1 and declarations[0][1:] == ("m", 0)
                        and declarations[0][0] is not None, sid, "unsupported Raw measuredHeight declaration")
                raw_height = float(declarations[0][0])
            else:
                raw_height = None
            require(source_height == raw_height, sid, "Converter height differs from Raw")
            require(original == source_height and usable == (None if original == -9999 else original),
                    sid, "Native height/NULL mismatch")
            expected[sid] = (sid,ouem,"PLATEAU CityGML",lod,reason,member,rel,branch,usable,original)
    return actual.features, expected


def audit_standard(path, native, expected, standard, bounds, xy):
    maximum, stats, seen, outside = 0., {}, set(), []
    records = indexed(standard["buildings"], "Standard.manifest")
    require(records.keys() == expected.keys(), "Standard.manifest", "building ID set differs")
    rectangle = box(*bounds)
    with open_readonly(path) as db:
        require(db.execute("PRAGMA application_id").fetchone() == (0x47504B47,)
                and db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
                and not db.execute("PRAGMA foreign_key_check").fetchall(), "Standard", "invalid GeoPackage")
        require(db.execute("SELECT table_name,data_type,srs_id FROM gpkg_contents").fetchall() == [("building","features",6677)]
                and db.execute("SELECT * FROM gpkg_geometry_columns").fetchall() == [("building","geometry","MULTIPOLYGON",6677,1,0)]
                and db.execute("SELECT organization,organization_coordsys_id,definition FROM gpkg_spatial_ref_sys WHERE srs_id=6677").fetchall()
                == [("EPSG",6677,CRS.from_epsg(6677).to_wkt("WKT1_GDAL"))], "Standard.CRS", "wrong geometry or CRS declaration")
        for blob, *attrs in db.execute("SELECT geometry,"+",".join(ATTRS)+" FROM building"):
            sid = attrs[0]
            require(sid in expected and sid not in seen, sid, "Standard duplicate or unexpected ID")
            require(tuple(attrs) == expected[sid] and type(attrs[3]) is int, sid, "Standard attributes or LoD differ")
            same_json(records[sid], dict(zip(ATTRS,attrs)), sid+".Standard.manifest")
            seen.add(sid)
            tree = decode(blob)
            cross_decode(blob, tree, sid)
            require(tree[0] == native[sid][0] == "MultiPolygon", sid, "geometry type differs")
            faces = polygons(tree)
            totals = stats.setdefault(str(attrs[3]), Counter())
            totals.update(features=1, faces=len(faces), exterior_rings=len(faces),
                          interior_rings=sum(len(face)-1 for face in faces),
                          vertices=sum(len(ring) for face in faces for ring in face))
            try:
                for face1, face2 in zip(polygons(native[sid]), faces, strict=True):
                    for ring1, ring2 in zip(face1, face2, strict=True):
                        for (lon,lat,h0),(x,y,h1) in zip(ring1, ring2, strict=True):
                            require(struct.pack("<d",h0) == struct.pack("<d",h1), sid, "H bits differ")
                            px,py = xy(lon,lat)
                            delta = max(abs(x-px),abs(y-py))
                            require(math.isfinite(delta) and delta <= TOLERANCE, sid, "XY tolerance exceeded")
                            maximum = max(maximum,delta)
            except ValueError as exc:
                raise ValueError(f"{sid}: ordered XYZ comparison failed: {exc}") from exc
            if not city.intersects(faces, rectangle, lambda x,y:(x,y)):
                outside.append(sid)
    require(seen == expected.keys(), "Standard.IDs", f"missing IDs: {sorted(expected.keys()-seen)}")
    require(not outside, "Standard.AOI", f"Raw/Standard intersection differs: {outside}")
    return dict(by_lod=stats, max_xy_error_m=maximum, xy_tolerance_m=TOLERANCE, h_exact=True,
                matched_ids=sorted(seen), mismatches=dict(ids=0,lod=0,xyz_h=0,attributes=0,aoi=0))


def run(manifest, pinned, artifact_root, output, *, bounds):
    output = Path(output).resolve()
    output.mkdir()
    try:
        require(len(bounds)==4 and all(map(math.isfinite,bounds)) and bounds[0]<bounds[2] and bounds[1]<bounds[3],
                "AOI", "finite ordered bounds required")
        watch = Watch(artifact_root)
        manifest = Path(manifest).resolve()
        standard,native,bridge,selector,paths,member = graph(watch,manifest,pinned,bounds)
        projection = zone_ix()
        xy = lambda lon,lat: projection(lon,lat,errcheck=True)
        raw = city.read_zip(paths["raw_zip"],member["member"],member)
        selected, all_rows = raw_selection(raw,selector,paths["selector_geometry"],member["member"],bounds,xy)
        snapshots = converter_passes(raw,bridge,paths)
        verify_decisions(all_rows,selected,raw,native,bridge,selector)
        native_geometry, attrs = gpkg_rows(paths,selected,snapshots,bridge,selector["source"]["release"],raw)
        qa = audit_standard(paths["standard"],native_geometry,attrs,standard,bounds,xy)
        receipt = dict(schema=SCHEMA, profile=PROFILE, status="EXPERIMENTAL", execution_status="COMPLETED",
                       consumer_validation="PASS", formal_acceptance="NOT_VERIFIED",
                       completed_at=datetime.now(timezone.utc).isoformat(), artifacts=watch.identities,
                       raw_source=selector["source"], aoi=standard["aoi"], crs=standard["crs"], converter=bridge["converter"],
                       validation=qa | dict(provenance="PASS", ordered_structure="PASS", raw_buildings=len(raw),
                                            excluded=len(raw)-len(selected)),
                       environment=dict(python=platform.python_version(), platform=platform.platform(),
                                        pyproj=pyproj_version, proj=proj_version_str),
                       implementation={Path(p).name:digest(p) for p in (__file__,city.__file__)},
                       xy_reference=projection.srs, unverified=LIMITS)
        pending = output/"receipt.pending.json"
        write(pending,receipt)
        watch.unchanged()
        # The directory is exclusively claimed. Publish only the complete receipt.
        os.replace(pending,output/"receipt.json")
        return receipt
    except BaseException as exc:
        (output/"receipt.pending.json").unlink(missing_ok=True)
        write(output/"failure.json",dict(schema=SCHEMA,profile=PROFILE,execution_status="FAILED",
             consumer_validation="FAIL",formal_acceptance="NOT_VERIFIED",error=str(exc) or type(exc).__name__))
        raise


def write(path, value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("standard-manifest","artifact-root","output-dir"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--standard-sha256",required=True)
    parser.add_argument("--bounds",required=True,nargs=4,type=float)
    args = parser.parse_args()
    result = run(args.standard_manifest,args.standard_sha256,args.artifact_root,args.output_dir,bounds=args.bounds)
    print(json.dumps(result["validation"]["by_lod"],sort_keys=True))


if __name__ == "__main__":
    main()
