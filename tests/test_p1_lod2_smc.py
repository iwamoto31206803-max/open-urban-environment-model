"""Independent synthetic P1-1b controls; no external engine or real fixture."""
import json
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import numpy as np
import pytest

from ouem import p1_lod2_smc as p


def ring(points):
    xyz = np.array([[x, y, 7.] for x, y in points])
    return np.vstack((xyz, xyz[0]))


@pytest.fixture
def metric(monkeypatch):
    monkeypatch.setattr(p.f, "project", lambda xyz: xyz.copy())


def test_rectangle_and_source_H_identity(metric):
    r = ring([(0, 0), (4, 0), (4, 3), (0, 3)])
    t = np.array([[0, 1, 2], [0, 2, 3]])
    result = p.triangle_support([r], r[:-1], t)
    assert result["source_projected_area_m2"] == 12
    assert result["uncovered_m2"] == result["outside_m2"] == 0
    changed = r[:-1].copy()
    changed[0, 2] += 1
    with pytest.raises(ValueError, match="XYZ/H"):
        p.triangle_support([r], changed, t)


def test_hole_support_and_exterior_fallback_rejection(metric):
    exterior = ring([(0, 0), (3, 0), (3, 3), (0, 3)])
    hole = ring([(1, 1), (1, 2), (2, 2), (2, 1)])
    v = np.vstack((exterior[:-1], hole[:-1]))
    t = np.array([[0, 1, 7], [0, 7, 4], [1, 2, 6], [1, 6, 7],
                  [2, 3, 5], [2, 5, 6], [3, 0, 4], [3, 4, 5]])
    result = p.triangle_support([exterior, hole], v, t)
    assert result["holes"] == 1 and result["source_projected_area_m2"] == 8
    assert max(result[k] for k in ("outside_m2", "uncovered_m2", "overlap_m2")) == 0
    with pytest.raises(ValueError, match="support"):
        p.triangle_support([exterior, hole], v, np.array([[0, 1, 2], [0, 2, 3]]))


@pytest.mark.parametrize("t", [np.array([[0, 1, 2]]),
                                  np.array([[0, 1, 2], [0, 2, 3], [0, 1, 2]]),
                                  np.array([[0, 1, 9]])])
def test_missing_duplicate_and_invalid_triangles_rejected(metric, t):
    r = ring([(0, 0), (4, 0), (4, 3), (0, 3)])
    with pytest.raises(ValueError):
        p.triangle_support([r], r[:-1], t)


def test_exact_id_and_lod_hole_records(tmp_path):
    source_id = p.IDENTITIES["S"]
    root = ET.Element("CityModel")
    def building(identifier):
        b = ET.SubElement(root, "{" + p.f.NS["bldg"] + "}Building",
                          {"{" + p.f.NS["gml"] + "}id": identifier})
        bounded = ET.SubElement(b, "{" + p.f.NS["bldg"] + "}boundedBy")
        roof = ET.SubElement(bounded, "{" + p.f.NS["bldg"] + "}RoofSurface")
        lod = ET.SubElement(roof, "{" + p.f.NS["bldg"] + "}lod2MultiSurface")
        poly = ET.SubElement(lod, "{" + p.f.NS["gml"] + "}Polygon",
                             {"{" + p.f.NS["gml"] + "}id": "roof"})
        for name, pts in [("exterior", "0 0 7 3 0 7 3 3 7 0 3 7 0 0 7"),
                          ("interior", "1 1 7 1 2 7 2 2 7 2 1 7 1 1 7")]:
            node = ET.SubElement(poly, "{" + p.f.NS["gml"] + "}" + name)
            ET.SubElement(node, "{" + p.f.NS["gml"] + "}posList").text = pts
        return b, lod
    building("neighbor")
    building(source_id)
    member = tmp_path / "fixture.gml"
    ET.ElementTree(root).write(member)
    selected, b = p.select_building(member, source_id)
    assert len(selected) == 1
    sample = {"semantic_counts": {"RoofSurface": 1}}
    archived = {"faces": [{"polygon_id": "roof", "mapping": "VERIFIED"}]}
    assert len(p.read_faces(b, sample, archived)[0]["rings"]) == 2
    lod = b.find(".//bldg:lod2MultiSurface", p.f.NS)
    lod.tag = "{" + p.f.NS["bldg"] + "}lod1MultiSurface"
    with pytest.raises(ValueError, match="LoD2"):
        p.read_faces(b, sample, archived)
    building(source_id)
    ET.ElementTree(root).write(member)
    with pytest.raises(ValueError, match="duplicated"):
        p.select_building(member, source_id)


def test_shape_delta_reports_removed_faces_and_changed_H():
    v = np.array([[0., 0., 7.], [1., 0., 7.], [0., 1., 8.], [1., 1., 8.]])
    t = np.array([[0, 1, 2], [1, 2, 3]])
    result = p.shape_delta(v, t, v.copy(), t[:1])
    assert result["triangles_removed_at_merge_precision"] == 1
    assert result["triangles_added_at_merge_precision"] == 0
    changed = v.copy()
    changed[0, 2] += .01
    assert p.shape_delta(v, t, changed, t)["new_H_values"] == [7.01]


def test_partial_failure_does_not_report_geometry_success(tmp_path, monkeypatch):
    monkeypatch.setattr(p.sys, "prefix", p.sys.base_prefix)
    missing = tmp_path / "missing"
    output = tmp_path / "failed"
    result = p.run(missing, missing, missing, output)
    assert result["status"] == "BLOCKED"
    assert "buildings" not in result
    assert json.loads((output / "manifest.json").read_bytes())["status"] == "BLOCKED"
    assert not list(output.rglob("*.npy"))


def test_explicit_repair_trace_restores_engine_hooks(monkeypatch):
    monkeypatch.setattr(p, "topology", lambda v, t: {"vertices": len(v), "triangles": len(t)})
    operation = lambda v, t, **kwargs: (v, t)
    validate = lambda v, t: (True, v, t[:, ::-1].copy())
    engine = SimpleNamespace(_merge_vertices=operation, _trimesh_repair=operation,
                             _validate_watertight=validate)
    called = []
    def make(v, t, method, precision):
        called.append((method, precision))
        v, t = getattr(engine, "_merge_vertices" if method == "merge" else "_trimesh_repair")(v, t)
        return engine._validate_watertight(v, t)
    engine.make_watertight_mesh = make
    v = np.array([[0., 0., 7.], [1., 0., 7.], [0., 1., 7.]])
    t = np.array([[0, 1, 2]])
    _, trace = p.traced_watertight(engine, v, t, "repair")
    assert called == [("repair", 6)]
    assert [step["operation"] for step in trace] == ["_trimesh_repair", "_validate_watertight"]
    assert trace[-1]["faces_array_changed"]
    np.testing.assert_array_equal(t, [[0, 1, 2]])
    assert engine._trimesh_repair is operation and engine._validate_watertight is validate
    with pytest.raises(ValueError, match="outside scope"):
        p.traced_watertight(engine, v, t, "auto")
    def failed(*args, **kwargs):
        raise RuntimeError("synthetic failure")
    engine.make_watertight_mesh = failed
    with pytest.raises(RuntimeError):
        p.traced_watertight(engine, v, t, "merge")
    assert engine._merge_vertices is operation and engine._validate_watertight is validate


def test_input_SHA_mismatch_stops_before_engine_import(tmp_path, monkeypatch):
    monkeypatch.setattr(p.sys, "prefix", str(tmp_path / "ouem-voxcitygml-p1"))
    inputs = []
    for name in ("53393466_bldg_6697_op.gml", "standard.gpkg", "report.json"):
        path = tmp_path / name
        path.write_text("tampered synthetic input")
        inputs.append(path)
    result = p.run(*inputs, tmp_path / "failed")
    assert result["status"] == "BLOCKED" and "SHA mismatch" in result["error"]
    assert "environment" not in result and "buildings" not in result
