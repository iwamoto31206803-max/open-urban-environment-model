"""Authored Raw and WKB controls plus adversarial Mixed chain fixtures."""
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from ouem.consumers import mixed_lod as consumer
from ouem.consumers import _mixed_lod_raw as city
from test_mixed_lod_native import inputs
import test_mixed_lod_native as native_fixture
from test_mixed_lod_standard import ready
from test_mixed_lod_selector import B, G, X, add_lod, building, cube, split_lod2_surfaces, xml
from test_source_h_ingestion import db


@pytest.fixture(autouse=True)
def without_unselected_lod_fixture(monkeypatch):
    # This Consumer rejects a parent with neither supported LoD; the writer can
    # retain a reason-coded exclusion. Test the stricter rule separately below.
    archive = native_fixture.archive

    def authored_archive(tmp, nodes):
        one = next(n for n in nodes if n.get(G+"id") == "one")
        ET.SubElement(one, B+"measuredHeight", {"uom": "m"}).text = "-9999"
        return archive(tmp, [n for n in nodes if n.get(G+"id") != "none"])

    monkeypatch.setattr(native_fixture, "archive", authored_archive)


def read(tmp_path, nodes):
    member = "udx/bldg/synthetic.gml"
    data = xml(nodes)
    path = tmp_path/"test.zip"
    with ZipFile(path,"w") as z:
        z.writestr(member,data)
    return city.read_zip(path,member,dict(member=member,size_bytes=len(data),sha256=sha256(data).hexdigest()))


def test_authored_raw(tmp_path):
    one, two, both = building("one",two=False), building("two",one=False), building("both",refs=True)
    split_lod2_surfaces(both)
    base = cube()
    hole = ((139.58002,35.64002,10.25),(139.58004,35.64002,10.25),
            (139.58004,35.64004,10.25),(139.58002,35.64002,10.25))
    with_hole = ((base[0][0],hole),*base[1:])
    one.remove(one.find(B+"lod1Solid"))
    add_lod(one,1,with_hole)
    members = both.find(B+"lod2Solid")[0][0][0]
    members[:] = list(reversed(members))
    rows = read(tmp_path,[one,two,both])
    assert rows["one"][0] == {1:with_hole}
    assert rows["two"][0] == {2:cube(top=20.75)}
    assert rows["both"][0] == {1:base,2:cube(top=20.75)[::-1]}
    assert len(rows["both"][1][0]) == 2


@pytest.mark.parametrize(("kind","error"),[("empty","one inline"),("ref","external Solid target"),
    ("duplicate_polygon","duplicate/blank XML ID"),("duplicate_building","duplicate/blank XML ID"),
    ("no_lod","neither supported LoD")])
def test_raw_rejection(tmp_path,kind,error):
    node = building(refs=True)
    polygon = split_lod2_surfaces(node)
    nodes = [node]
    if kind == "empty":
        node.find(B+"lod2MultiSurface").clear()
    elif kind == "ref":
        node.find(B+"lod2Solid")[0][0][0][0].set(X,"#unknown")
    elif kind == "duplicate_polygon":
        polygon.set(G+"id","authored_l2_p0")
    elif kind == "duplicate_building":
        nodes.append(building(two=False))
    else:
        nodes = [building(one=False,two=False)]
    with pytest.raises(ValueError,match=error):
        read(tmp_path,nodes)


def test_projection_control_and_independent_wkb():
    ref = consumer.zone_ix()
    assert max(map(abs,ref(139+50/60,36))) < 1e-7
    assert ref(139.84,36)[0] > 0
    # An authored binary MULTIPOLYGON Z containing a vertical face, one closure,
    # and signed zero. The two decoders must agree without a writer round-trip.
    pts = ((0.,0.,-0.),(1.,0.,1.),(0.,0.,1.),(0.,0.,-0.))
    wkb = struct.pack("<BII",1,1006,1)+struct.pack("<BIII",1,1003,1,4)
    blob = b"GP\x00\x01"+struct.pack("<i",6677)+wkb+b"".join(struct.pack("<ddd",*p) for p in pts)
    tree = ("MultiPolygon",(("Polygon",(pts,)),))
    assert consumer.decode(blob) == tree
    consumer.cross_decode(blob,tree,"hand-authored")
    changed = (pts[0],pts[1],(0.,0.,2.),pts[3])
    with pytest.raises(ValueError,match="decoders differ"):
        consumer.cross_decode(blob,("MultiPolygon",(("Polygon",(changed,)),)),"tampered")


@pytest.fixture
def chain(ready, monkeypatch, tmp_path):
    from test_mixed_lod_standard import run
    run(ready)
    _, bounds, out = ready
    manifest = out/"manifest.json"
    data = json.loads(manifest.read_bytes())
    monkeypatch.setattr(consumer,"BINARY_SHA",data["inputs"]["converter_binary"]["sha256"])
    root = Path(os.path.commonpath([tmp_path,Path(consumer.__file__).resolve()]))
    return manifest, bounds, root, tmp_path/"consumer"


def verify(chain, pinned=None):
    path,bounds,root,out = chain
    return consumer.run(path,pinned or consumer.digest(path),root,out,bounds=bounds)


def record(path):
    return dict(path=str(path),sha256=consumer.digest(path),size_bytes=path.stat().st_size)


def test_full_chain_ignores_saved_validation(chain):
    path,_,_,out = chain
    data = json.loads(path.read_bytes())
    data["validation"] = dict(h_exact=False,max_xy_error_m=999,by_lod={})
    path.write_text(json.dumps(data),encoding="utf-8")
    report = verify(chain)
    assert report["validation"]["matched_ids"] == ["boundary","dual","one","two"]
    assert report["validation"]["by_lod"]["1"]["interior_rings"] == 1
    assert report["validation"]["excluded"] == 1
    assert report["consumer_validation"] == "PASS"
    assert (out/"receipt.json").exists()
    with pytest.raises(FileExistsError):
        verify(chain)


@pytest.mark.parametrize(("case","error"),[
    ("pinned","SHA-256 mismatch"),("stale","incompatible or incomplete"),
    ("xy","XY tolerance exceeded"),("h","H bits differ"),
    ("original","attributes or LoD differ"),("nullable","attributes or LoD differ"),
    ("pass","attributes or LoD differ"),("lod","attributes or LoD differ"),
    ("missing","missing IDs"),("duplicate","duplicate or unexpected ID"),
    ("crs","wrong geometry or CRS declaration"),("replace","SHA-256 mismatch"),
    ("native_lod","Native LoD/pass differs"),("native_geometry","Native BLOB mismatch"),
    ("converter_height","Converter height differs from Raw"),
])
def test_chain_rejects_tampering(chain,case,error):
    path,_,_,out = chain
    data = json.loads(path.read_bytes())
    pinned = consumer.digest(path)
    gpkg = path.with_name("standard.gpkg")
    if case == "stale":
        data["profile"] = "obsolete"
    elif case in ("native_lod","native_geometry","converter_height"):
        native_manifest = Path(data["inputs"]["native_manifest"]["path"])
        native = json.loads(native_manifest.read_bytes())
        target = Path(native["native"]["path"])
        with db(target) as conn:
            statements = {
                "native_lod": 'UPDATE "bldg:Building" SET selected_lod=1,converter_pass=\'lod1\' WHERE id=\'dual\'',
                "native_geometry": 'UPDATE "bldg:Building" SET geometry=(SELECT geometry FROM "bldg:Building" WHERE id=\'one\') WHERE id=\'dual\'',
                "converter_height": 'UPDATE "bldg:Building" SET measured_height_raw=42,measuredHeight=42 WHERE id=\'one\'',
            }
            conn.execute(statements[case])
            conn.commit()
        if case == "converter_height":
            bridge_path = Path(data["inputs"]["bridge_receipt"]["path"])
            bridge = json.loads(bridge_path.read_bytes())
            converter = Path(data["inputs"]["lod1_gpkg"]["path"])
            with db(converter) as conn:
                conn.execute('UPDATE "bldg:Building" SET measuredHeight=42 WHERE id=\'one\'')
                conn.commit()
            for branch in (bridge["branches"]["1"],native["branches"]["1"]):
                branch["gpkg"] = record(converter)
            bridge_path.write_text(json.dumps(bridge),encoding="utf-8")
            for key,value in (("lod1_gpkg",record(converter)),("bridge_receipt",record(bridge_path))):
                native["artifacts"][key] = data["inputs"][key] = value
        data["inputs"]["native_gpkg"] = record(target)
        native["native"] = record(target) | {"layer":"bldg:Building"}
        native_manifest.write_text(json.dumps(native),encoding="utf-8")
        data["inputs"]["native_manifest"] = record(native_manifest)
    elif case not in ("pinned",):
        with db(gpkg) as conn:
            if case in ("xy","h"):
                blob = bytearray(conn.execute("SELECT geometry FROM building WHERE source_id='one'").fetchone()[0])
                # Header + MultiPolygon header + Polygon header + ring count. Offset
                # both occurrences of the first point to keep the ring closed.
                base = 8+9+9+4
                count = struct.unpack_from("<I",blob,base-4)[0]
                for i in (0,count-1):
                    offset = base+24*i+(16 if case=="h" else 0)
                    struct.pack_into("<d",blob,offset,struct.unpack_from("<d",blob,offset)[0]+.01)
                conn.execute("UPDATE building SET geometry=? WHERE source_id='one'",(blob,))
            elif case == "original":
                conn.execute("UPDATE building SET measured_height_raw=1 WHERE source_id='one'")
            elif case == "nullable":
                conn.execute("UPDATE building SET measured_height=0 WHERE source_id='one'")
            elif case == "pass":
                conn.execute("UPDATE building SET converter_pass='lod1' WHERE source_id='dual'")
            elif case == "lod":
                conn.execute("UPDATE building SET source_lod=1 WHERE source_id='dual'")
            elif case == "missing":
                conn.execute("DELETE FROM building WHERE source_id='one'")
            elif case == "duplicate":
                conn.executescript("CREATE TABLE dup AS SELECT * FROM building; "
                                   "INSERT INTO dup SELECT * FROM building WHERE source_id='one'; "
                                   "DROP TABLE building; ALTER TABLE dup RENAME TO building;")
            elif case == "crs":
                conn.execute("UPDATE gpkg_geometry_columns SET z=0")
            elif case == "replace":
                conn.execute("UPDATE building SET measured_height_raw=42")
            conn.commit()
        if case != "replace":
            data["output"] = record(gpkg) | {"layer":"building"}
    if case == "pinned":
        data["status"] = "modified"
    path.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match=error):
        verify(chain,pinned if case=="pinned" else None)
    assert (out/"failure.json").exists()
    assert not (out/"receipt.json").exists()


@pytest.mark.parametrize("interrupt",[False,True])
def test_no_success_on_late_replacement_or_interruption(chain,monkeypatch,interrupt):
    original = consumer.Watch.unchanged
    path,_,_,out = chain

    def changed(watch):
        if interrupt:
            raise KeyboardInterrupt()
        path.write_bytes(path.read_bytes()+b" ")
        original(watch)

    monkeypatch.setattr(consumer.Watch,"unchanged",changed)
    with pytest.raises(KeyboardInterrupt if interrupt else ValueError):
        verify(chain)
    assert (out/"failure.json").exists()
    assert not (out/"receipt.json").exists()
    assert not (out/"receipt.pending.json").exists()
