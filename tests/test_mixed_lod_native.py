"""Mixed Native synthetic GPKGs and hand-authored geometry; no CLI converter."""
from collections import Counter
import json
from pathlib import Path

import pytest
from pyproj import Transformer

from ouem import mixed_lod_selector as raw
from ouem.native.building import mixed_lod as native
from ouem.standardize.building.source_h import validate_native
from test_mixed_lod_converter_bridge import gpkg, MEMBER, RELEASE
from test_mixed_lod_selector import B, add_lod, archive, building, cube, split_lod2_surfaces
from test_source_h_ingestion import blob, db

bridge = native.bridge


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    one = building("one", two=False)
    dual = building("dual")
    split_lod2_surfaces(dual)
    two = building("two", one=False)
    hole = ((139.58002, 35.64002, 10.25), (139.58004, 35.64002, 10.25),
            (139.58004, 35.64004, 10.25), (139.58002, 35.64002, 10.25))
    base = cube()
    with_hole = ((base[0][0], hole), *base[1:])
    one.remove(one.find(B+"lod1Solid"))
    add_lod(one, 1, with_hole)
    boundary_faces, outside_faces = cube(x=139.575), cube(x=139.57)
    boundary = building("boundary", one=False, two=False)
    outside = building("outside", one=False, two=False)
    add_lod(boundary, 1, boundary_faces)
    add_lod(outside, 1, outside_faces)
    proj = Transformer.from_crs(6668, 6677, always_xy=True)
    xmin = max(proj.transform(x, y)[0] for face in boundary_faces for ring in face for x, y, _ in ring)
    bounds = (xmin, -41000., -22000., -39000.)
    path = archive(tmp_path, [one, dual, two, boundary, outside, building("none", one=False, two=False)])
    selector = tmp_path/"selector"
    result = raw.run(path, [MEMBER], release=RELEASE, bounds=bounds, output_dir=selector)
    out = tmp_path/"bridge"
    out.mkdir()
    executable = tmp_path/"synthetic.exe"
    executable.write_bytes(b"fixture; never executed")
    monkeypatch.setattr(bridge, "CLI_SHA", raw.digest(executable))
    extracted = bridge.extract(path, MEMBER, out/"extracted")
    top = cube(top=20.75)
    expected = {1: dict(one=with_hole, dual=base, boundary=boundary_faces, outside=outside_faces),
                2: dict(dual=top, two=top)}
    branches = {}
    for lod, rows in expected.items():
        folder = out/str(lod)
        folder.mkdir()
        f = gpkg(folder, [(sid, faces[::-1] if sid == "dual" and lod == 2 else faces)
                          for sid, faces in rows.items()])
        g = f.rename(out/f"lod{lod}.gpkg")
        with db(g) as conn:
            conn.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,?)",
                             [(str(code), code, "EPSG" if code == 4326 else "NONE", code, "undefined", "")
                              for code in (-1, 0, 4326)])
            conn.execute('UPDATE "bldg:Building" SET measuredHeight=-9999 WHERE id=?', ("one",))
            conn.commit()
        branch = bridge.reconcile(rows, bridge.inspect_geopackage(g, bridge.LAYER))
        for stream in ("stdout", "stderr"):
            log = out/f"lod{lod}.{stream}.log"
            log.touch()
            branch[stream] = bridge.artifact(log)
        branch.update(gpkg=bridge.artifact(g), exit_code=0, started_at="2026-01-01T00:00:00Z",
                      ended_at="2026-01-01T00:00:01Z",
                      argv=[str(executable), str(extracted), "--sink", "gpkg", "--output", str(g),
                            "--epsg", "6697", "-t", f"use_lod=lod{lod}", "-t", "split_components=false"])
        branches[str(lod)] = branch
    selection = []
    for r in result["records"]:
        lod, sid = r["selected_lod"], r["source_id"]
        selection.append({key: r[key] for key in ("source_id", "selected_lod", "selection_reason", "aoi_intersects")}
                         | dict(feature=branches[str(lod)]["features"][sid] if lod else None,
                                feature_eligible=lod is not None))
    receipt = out/"bridge.json"
    bridge.write(receipt, dict(
        schema=bridge.SCHEMA, status="EXPERIMENTAL", execution_status="COMPLETED", mixed_native_handoff="ELIGIBLE",
        raw_source=result["source"], aoi=result["aoi"], crs=result["crs"], raw_counts=result["counts"],
        selector_manifest=bridge.artifact(selector/"manifest.json"),
        selector_geometry=bridge.artifact(selector/"geometries.jsonl"),
        implementation=bridge.artifact(Path(bridge.__file__)),
        converter=dict(commit=bridge.COMMIT, version=bridge.VERSION, binary=bridge.artifact(executable)),
        extracted_member=bridge.artifact(extracted), branches=branches, selection=selection,
        candidate=dict(selected=4, feature_eligible=4),
    ))
    return receipt, selector/"manifest.json", path, tmp_path/"native", bounds


def run(inputs, receipt_sha=None):
    receipt, selector, path, out, bounds = inputs
    return native.run(receipt, receipt_sha or raw.digest(receipt), selector, path, out,
                      member=MEMBER, release=RELEASE, bounds=bounds)


def test_selected_copy_and_exclusions(inputs):
    receipt, _, _, out, _ = inputs
    manifest = run(inputs)
    assert manifest["counts"] == {"included": 4, "by_lod": {"1": 2, "2": 2}, "excluded": 2}
    assert {r["source_id"]: r["disposition"] for r in manifest["decisions"]} == {
        "one": "INCLUDED", "two": "INCLUDED", "dual": "INCLUDED", "boundary": "INCLUDED",
        "outside": "OUTSIDE_AOI", "none": "NO_SUPPORTED_LOD",
    }
    with native.open_readonly(out/"native.gpkg") as conn:
        data = {r[0]: r[1:] for r in conn.execute(
            'SELECT id,selected_lod,converter_pass,geometry,measured_height_raw,measuredHeight FROM "bldg:Building"')}
    assert set(data) == {"one", "two", "dual", "boundary"}
    assert data["one"][0:2] == (1, "lod1")
    assert data["one"][3:] == (-9999., None)
    assert data["two"][3:] == (None, None)
    assert data["dual"][0:2] == (2, "lod2")
    assert data["dual"][2] == blob(cube(top=20.75)[::-1])
    snapshot = bridge.inspect_geopackage(out/"native.gpkg", bridge.LAYER)
    assert bridge.polygons(snapshot.features["one"])[0][1][0] == (139.58002, 35.64002, 10.25)
    for sid, (lod, _, geom, _, _) in data.items():
        with native.open_readonly(receipt.parent/f"lod{lod}.gpkg") as conn:
            assert conn.execute('SELECT geometry FROM "bldg:Building" WHERE id=?', (sid,)).fetchone() == (geom,)
    assert Counter(r[0] for r in data.values()) == {1: 2, 2: 2}
    assert (out/"manifest.json").exists()
    with pytest.raises(ValueError, match="Native.provenance"):
        validate_native(out/"manifest.json", out)
    with pytest.raises(FileExistsError):
        run(inputs)


@pytest.mark.parametrize(("case", "error"), [
    ("receipt_sha", "receipt SHA mismatch"),
    ("blocked", "eligible completed"),
    ("stale", "stale implementation"),
    ("wrong_lod", "selection does not match"),
    ("modified", "artifact identity changed"),
    ("xyz", "reconciliation differs"),
    ("crs", "mandatory Z, no M and 6697 required"),
    ("duplicate", "unique text"),
])
def test_revalidation_fail_closed(inputs, case, error):
    receipt, _, _, out, _ = inputs
    saved = json.loads(receipt.read_bytes())
    g = receipt.parent/"lod2.gpkg"
    pinned = raw.digest(receipt)
    if case == "blocked":
        saved["mixed_native_handoff"] = "BLOCKED"
    elif case == "stale":
        saved["implementation"]["sha256"] = "0"*64
    elif case == "wrong_lod":
        next(row for row in saved["selection"] if row["source_id"] == "dual")["selected_lod"] = 1
    elif case in ("modified", "xyz", "crs", "duplicate"):
        with db(g) as conn:
            if case == "modified":
                conn.execute('UPDATE "bldg:Building" SET measuredHeight=12')
            elif case == "xyz":
                conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?', (blob(cube(top=20.751)), "dual"))
            elif case == "crs":
                conn.execute("UPDATE gpkg_geometry_columns SET srs_id=4326")
            else:
                conn.execute('INSERT INTO "bldg:Building"(id,geometry) SELECT id,geometry FROM "bldg:Building" LIMIT 1')
            conn.commit()
        if case != "modified":
            saved["branches"]["2"]["gpkg"] = bridge.artifact(g)
    receipt.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        run(inputs, pinned if case == "receipt_sha" else None)
    assert (out/"failure.json").exists()
    assert not (out/"manifest.json").exists()
    assert not (out/"native.gpkg").exists()


def test_stage_with_reordered_blob_fails_even_when_raw_xyz_matches(inputs, monkeypatch):
    original = native.write_gpkg

    def mutate(path, records, source):
        original(path, records, source)
        with db(path) as conn:
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?', (blob(cube(top=20.75)), "dual"))
            conn.commit()

    monkeypatch.setattr(native, "write_gpkg", mutate)
    with pytest.raises(ValueError, match="BLOB bytes or attributes differ"):
        run(inputs)
    assert not (inputs[3]/"manifest.json").exists()
    assert not (inputs[3]/"native.gpkg").exists()


def test_input_change_immediately_before_marker_rolls_back(inputs, monkeypatch):
    original = native.check_inputs
    out = inputs[3]

    def mutate(artifacts):
        if (out/"native.gpkg").exists():
            with db(inputs[0].parent/"lod2.gpkg") as conn:
                conn.execute('UPDATE "bldg:Building" SET measuredHeight=13')
                conn.commit()
        original(artifacts)

    monkeypatch.setattr(native, "check_inputs", mutate)
    with pytest.raises(ValueError, match="artifact identity changed"):
        run(inputs)
    assert (out/"failure.json").exists()
    assert not (out/"manifest.json").exists()
    assert not (out/"native.gpkg").exists()
