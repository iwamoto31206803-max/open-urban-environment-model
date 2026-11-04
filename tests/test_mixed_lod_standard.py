"""Authored Mixed Native fixtures and projected output corruption controls."""
from collections import Counter
import json
import math
import struct

import pytest
from pyproj import Transformer

from ouem.standardize.building import mixed_lod as standard
from ouem.consumers._source_h_geometry import decode
from test_mixed_lod_native import inputs, run as write_native  # pytest fixture
from test_source_h_ingestion import db

native = standard.native


@pytest.fixture
def ready(inputs, tmp_path):
    write_native(inputs)
    path = inputs[3]/"manifest.json"
    return path, inputs[4], tmp_path/"standard"


def run(ready, sha=None):
    path, bounds, out = ready
    return standard.run(path, sha or native.raw.digest(path), out, bounds=bounds)


def test_projection_control_and_wall_height():
    # Zone IX natural origin: longitude 139°50', latitude 36°.
    wall = ("Polygon", (((139+50/60, 36., -0.0), (139+50/60, 36., 30.5),
                         (139.84, 36., 30.5), (139+50/60, 36., -0.0)),))
    transform = Transformer.from_crs(6668, 6677, always_xy=True, allow_ballpark=False, only_best=True)
    result = standard.map_xy(wall, transform.transform)
    first, second = result[1][0][:2]
    assert math.hypot(*first[:2]) <= 1e-7
    assert first[:2] == second[:2]
    assert struct.pack("<d", first[2]) == struct.pack("<d", -0.0)
    assert second[2] == 30.5


def test_full_mixed_projection(ready):
    path, _, out = ready
    report = run(ready)
    expected = {"one": 1, "boundary": 1, "two": 2, "dual": 2}
    assert {r["source_id"]: r["source_lod"] for r in report["buildings"]} == expected
    assert Counter(r["source_lod"] for r in report["buildings"]) == {1: 2, 2: 2}
    assert report["validation"]["by_lod"]["1"]["interior_rings"] == 1
    assert report["validation"]["h_exact"] is True
    assert report["validation"]["aoi_intersecting"] == 4
    with native.open_readonly(out/"standard.gpkg") as conn:
        rows = conn.execute(f"SELECT geometry,{standard.FIELDS} FROM building").fetchall()
    with native.open_readonly(path.with_name("native.gpkg")) as conn:
        src = {row[0]: row[1:] for row in conn.execute(f"SELECT {native.FIELDS} FROM {native.TABLE}")}
    for blob, sid, oid, dataset, lod, reason, member, release, branch, height, raw_height in rows:
        original = src[sid]
        assert (oid, lod, reason, member, release, branch) == original[1:7]
        assert dataset == "PLATEAU CityGML"
        assert (height, raw_height) == (original[-1], original[-2])
        source = native.inspect_geopackage(path.with_name("native.gpkg"), native.bridge.LAYER).features[sid]
        assert [p[2] for p in standard.points(decode(blob))] == [p[2] for p in standard.points(source)]
    attributes = {r["source_id"]: r for r in report["buildings"]}
    assert (attributes["one"]["measured_height"], attributes["one"]["measured_height_raw"]) == (None, -9999)
    assert (attributes["two"]["measured_height"], attributes["two"]["measured_height_raw"]) == (None, None)
    with pytest.raises(FileExistsError):
        run(ready)


@pytest.mark.parametrize(("mode", "message"), [
    ("manifest_sha", "pinned SHA mismatch"),
    ("manifest_decision", "selection or exclusions"),
    ("stale", "stale writer identity"),
    ("lod", "BLOB bytes or attributes differ"),
    ("geometry", "BLOB bytes or attributes differ"),
    ("crs", "mandatory Z, no M and 6697 required"),
])
def test_native_tampering(ready, mode, message):
    path, _, out = ready
    sha = native.raw.digest(path)
    manifest = json.loads(path.read_bytes())
    if mode == "manifest_sha":
        manifest["status"] = "modified"
    elif mode == "manifest_decision":
        next(r for r in manifest["decisions"] if r["source_id"] == "dual")["selected_lod"] = 1
    elif mode == "stale":
        manifest["implementation"]["sha256"] = "0"*64
    else:
        gpkg = path.with_name("native.gpkg")
        with db(gpkg) as conn:
            if mode == "lod":
                conn.execute('UPDATE "bldg:Building" SET selected_lod=1,converter_pass=\'lod1\' WHERE id=\'dual\'')
            elif mode == "geometry":
                conn.execute('UPDATE "bldg:Building" SET geometry=(SELECT geometry FROM "bldg:Building" WHERE id=\'one\') WHERE id=\'dual\'')
            else:
                conn.execute("UPDATE gpkg_geometry_columns SET z=0")
            conn.commit()
        manifest["native"] = native.bridge.artifact(gpkg) | {"layer": native.bridge.LAYER}
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        run(ready, sha if mode == "manifest_sha" else None)
    assert (out/"failure.json").exists()
    assert not (out/"manifest.json").exists()
    assert not (out/"standard.gpkg").exists()


@pytest.mark.parametrize(("mode", "message"), [("lod_missing", "source_lod"),
    ("aoi_difference", "reopened geometry disagrees"), ("xy", "independent XY tolerance"),
    ("h", "H bits changed")])
def test_output_audit_fail_closed(ready, monkeypatch, mode, message):
    original = standard.write_gpkg
    out = ready[2]

    def corrupt(path, features, attributes, timestamp):
        if mode == "xy":
            features["one"] = standard.map_xy(features["one"], lambda x, y: (x+.001, y))
        if mode == "h":
            def alter(tree):
                kind, parts = tree
                if kind == "Polygon":
                    return kind, tuple(tuple((x,y,h+.01) for x,y,h in ring) for ring in parts)
                return kind, tuple(alter(c) for c in parts)
            features["one"] = alter(features["one"])
        original(path, features, attributes, timestamp)
        if mode == "lod_missing":
            with db(path) as conn:
                conn.execute("CREATE TABLE incomplete AS SELECT fid,geometry,source_id,ouem_id,source_dataset,"
                             "selection_reason,source_member,source_release,converter_pass,measured_height,measured_height_raw FROM building")
                conn.execute("DROP TABLE building")
                conn.execute("ALTER TABLE incomplete RENAME TO building")

    monkeypatch.setattr(standard, "write_gpkg", corrupt)
    if mode == "aoi_difference":
        original_intersects = standard.intersects
        monkeypatch.setattr(standard, "intersects",
                            lambda tree, bounds: original_intersects(tree, (-23000., -41000., -22700., -39000.)))
    with pytest.raises((ValueError, standard.sqlite3.Error), match=message):
        run(ready)
    assert not (out/"standard.gpkg").exists()
    assert not (out/"manifest.json").exists()


def test_change_after_gpkg_publication_before_manifest(ready, monkeypatch):
    path, _, out = ready
    original = standard.check_inputs

    def mutate(inputs):
        if (out/"standard.gpkg").exists():
            path.write_bytes(path.read_bytes()+b" ")
        original(inputs)

    monkeypatch.setattr(standard, "check_inputs", mutate)
    with pytest.raises(ValueError, match="artifact identity changed"):
        run(ready)
    assert (out/"failure.json").exists()
    assert not (out/"standard.gpkg").exists()
    assert not (out/"manifest.json").exists()
