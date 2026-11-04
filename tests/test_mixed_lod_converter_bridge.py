"""Bridge reconciliation fixtures. No external Converter process is used."""
import json

import pytest

from ouem import mixed_lod_converter_bridge as bridge
from ouem import mixed_lod_selector as raw
from test_mixed_lod_selector import B, BOUNDS, add_lod, archive, building, cube, split_lod2_surfaces
from test_source_h_ingestion import blob, db, write_gpkg

MEMBER = "udx/bldg/a.gml"
RELEASE = "hand-authored"


def gpkg(tmp_path, rows):
    path = tmp_path / "converter.gpkg"
    write_gpkg(path)
    with db(path) as conn:
        conn.execute('DELETE FROM "bldg:Building"')
        conn.executemany('INSERT INTO "bldg:Building"(id,geometry) VALUES(?,?)',
                         [(sid, blob(faces)) for sid, faces in rows])
        conn.commit()
    return path


def test_both_passes_cover_raw_presence_and_selected_geometry(tmp_path):
    one = building("one", two=False)
    two = building("two", one=False, refs=True)
    split_lod2_surfaces(two)
    dual = building("dual")
    hole = ((139.58002, 35.64002, 10.25), (139.58004, 35.64002, 10.25),
            (139.58004, 35.64004, 10.25), (139.58002, 35.64002, 10.25))
    base = cube()
    faces_with_hole = ((base[0][0], hole), *base[1:])
    one.remove(one.find(B+"lod1Solid"))
    add_lod(one, 1, faces_with_hole)
    path = archive(tmp_path, [one, two, dual, building("none", one=False, two=False)])
    receipt = tmp_path / "selector"
    raw.run(path, [MEMBER], release=RELEASE, bounds=BOUNDS, output_dir=receipt)
    replay, selected = bridge.load_selector(receipt/"manifest.json", path, MEMBER, RELEASE, BOUNDS)
    extracted = bridge.extract(path, MEMBER, tmp_path/"extracted")
    expected = bridge.expected_by_lod(replay["records"], selected, extracted)
    assert {r["source_id"]: r["selected_lod"] for r in replay["records"]} == {
        "one": 1, "two": 2, "dual": 2, "none": None,
    }
    top = cube(top=20.75)
    assert expected == {1: {"one": faces_with_hole, "dual": base}, 2: {"two": top, "dual": top}}
    for lod, converter_rows in [(1, [("one", faces_with_hole), ("dual", base)]),
                                (2, [("two", top[::-1]), ("dual", top)])]:
        folder = tmp_path/str(lod)
        folder.mkdir()
        snapshot = bridge.inspect_geopackage(gpkg(folder, converter_rows), bridge.LAYER)
        result = bridge.reconcile(expected[lod], snapshot)["features"]
        assert result["dual"]["result"] == "EXACT"
        if lod == 1:
            assert result["one"]["result"] == "EXACT"
            assert result["one"]["converter_interiors"] == 1
        else:
            assert result["two"]["result"] == "ORDER_ONLY"


@pytest.mark.parametrize(("rows", "result"), [
    ([("other", cube())], {"chosen": "MISSING", "other": "UNEXPECTED"}),
    ([("chosen", cube(top=18.251))], {"chosen": "GEOMETRY_MISMATCH"}),
    ([("chosen", cube()[:-1])], {"chosen": "GEOMETRY_MISMATCH"}),
    ([("chosen", (*cube(), cube()[0]))], {"chosen": "GEOMETRY_MISMATCH"}),
])
def test_converter_disagreements_remain_visible(tmp_path, rows, result):
    snapshot = bridge.inspect_geopackage(gpkg(tmp_path, rows), bridge.LAYER)
    expected = {"chosen": cube()}
    assert {sid: feature["result"] for sid, feature in bridge.reconcile(expected, snapshot)["features"].items()} == result


def test_duplicate_features_rejected(tmp_path):
    path = gpkg(tmp_path, [("chosen", cube()), ("chosen", cube())])
    with pytest.raises(ValueError, match="unique text"):
        bridge.inspect_geopackage(path, bridge.LAYER)


def test_changed_converter_artifact_rejected(tmp_path):
    path = gpkg(tmp_path, [("chosen", cube())])
    identity = bridge.artifact(path)
    with db(path) as conn:
        conn.execute('UPDATE "bldg:Building" SET measuredHeight=42')
        conn.commit()
    with pytest.raises(ValueError, match="identity changed"):
        bridge.verify_artifact(identity)


@pytest.mark.parametrize("case", ["invalid_lod2", "old_manifest", "wrong_release", "forged_selection"])
def test_selector_rejection_precedes_converter_execution(tmp_path, monkeypatch, case):
    node = building()
    path = archive(tmp_path, [node])
    receipt = tmp_path/"selector"
    manifest = receipt/"manifest.json"
    raw.run(path, [MEMBER], release=RELEASE, bounds=BOUNDS, output_dir=receipt)
    saved = json.loads(manifest.read_bytes())
    if case == "invalid_lod2":
        node.find(B+"lod2MultiSurface")[0].clear()
        path = archive(tmp_path, [node])
    elif case == "old_manifest":
        saved["implementation_sha256"] = "0"*64
    elif case == "forged_selection":
        saved["records"][0]["selected_lod"] = 1
    manifest.write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(bridge.platform, "platform", lambda: "synthetic")
    monkeypatch.setattr(bridge.subprocess, "run", lambda *a, **k: pytest.fail("Converter executed"))
    out = tmp_path/"run"
    result = bridge.run(manifest, path, tmp_path/"unused.exe", out, member=MEMBER,
                        release="different" if case == "wrong_release" else RELEASE, bounds=BOUNDS)
    assert result["execution_status"] == "FAILED"
    assert result["mixed_native_handoff"] == "BLOCKED"
    assert "branches" not in result
    if case == "invalid_lod2":
        assert "LOD2_INVALID" in result["error"]
    with pytest.raises(FileExistsError):
        bridge.run(manifest, path, tmp_path/"unused.exe", out, member=MEMBER, release=RELEASE, bounds=BOUNDS)
