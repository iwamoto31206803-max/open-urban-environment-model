"""Synthetic CityGML-to-Adapter height provenance; no Komae real data."""
import json

import geopandas as gpd
import pandas as pd
import pytest

from ouem import komae_integration as runner
from ouem import komae_vertical_provenance as vertical
from tests.test_komae_geometry_provenance import SOURCE_ID, make_run, reindex, tree_bytes


def _gml(path, ids_and_z):
    buildings = []
    for identifier, z, measured in ids_and_z:
        buildings.append(f'''<bldg:Building gml:id="{identifier}"><bldg:measuredHeight>{measured}</bldg:measuredHeight>
          <gml:Polygon><gml:exterior><gml:LinearRing>
          <gml:posList srsDimension="3">139 35 {z} 139.001 35 {z} 139.001 35.001 {z} 139 35 {z}</gml:posList>
          </gml:LinearRing></gml:exterior></gml:Polygon></bldg:Building>''')
    path.write_text('''<core:CityModel xmlns:core="http://www.opengis.net/citygml/2.0"
      xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
      xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:6697">'''
                    + "".join(buildings) + "</core:CityModel>", encoding="utf-8")


def test_citygml_streams_all_vertices_and_missing_height(tmp_path):
    path = tmp_path / "buildings.gml"
    _gml(path, [("a", 24.44, "4.4"), ("b", 61.7, "-9999")])
    records = vertical.citygml_buildings(path, ["a", "b"])
    assert records["a"]["vertex_count"] == 4
    assert records["a"]["z_min_m"] == records["a"]["z_max_m"] == 24.44
    assert records["a"]["measured_height_m"] == 4.4
    assert records["b"]["measured_height_m"] is None
    assert len(records["a"]["axis_order"]) == 3


def test_citygml_checks_full_vertex_range_not_one_roof_point(tmp_path):
    path = tmp_path / "varying.gml"
    path.write_text('''<bldg:Building xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
      xmlns:gml="http://www.opengis.net/gml" gml:id="target" srsName="EPSG:6697">
      <gml:posList srsDimension="3">139 35 24.44 139.001 35 61.70 139.001 35.001 64.17</gml:posList>
      <gml:pos>139 35.001 25.0</gml:pos></bldg:Building>''', encoding="utf-8")
    result = vertical.citygml_buildings(path, ["target"])["target"]
    assert result["vertex_count"] == 4
    assert result["z_min_m"] == 24.44 and result["z_max_m"] == 64.17


def test_missing_representative_in_single_citygml_tile_is_explicit(tmp_path):
    path = tmp_path / "one-tile.gml"
    _gml(path, [("target", 24.44, "4.4")])
    assert set(vertical.citygml_buildings(path, ["target", "other"], require_all=False)) == {"target"}
    with pytest.raises(vertical.provenance.Inconclusive, match="missing"):
        vertical.citygml_buildings(path, ["target", "other"])


def test_representatives_include_valid_low_high_and_minus_9999():
    frame = pd.DataFrame({"source_id": ["target", "low", "high", "missing", "outside"],
                          "ouem_id": ["t", "l", "h", "m", "o"],
                          "measured_height": [4.4, 3.0, 20.0, "-9999", 45.0]})
    selected = vertical._select(frame, "tar", (), {"t", "l", "h", "m"})
    assert selected == [("target", "target"), ("low", "low_measured_height"),
                        ("high", "high_measured_height"),
                        ("missing", "measured_height_minus_9999")]


@pytest.mark.parametrize("fragment", [
    '<gml:posList srsDimension="2">139 35 139.01 35</gml:posList>',
    '<gml:surfaceMember xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#unresolved"/>',
])
def test_citygml_rejects_uninspected_geometry(tmp_path, fragment):
    path = tmp_path / "incomplete.gml"
    path.write_text('''<bldg:Building xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
      xmlns:gml="http://www.opengis.net/gml" gml:id="a" srsName="EPSG:6697">'''
                    + fragment + '</bldg:Building>', encoding="utf-8")
    with pytest.raises(vertical.provenance.Inconclusive, match="unsupported CityGML geometry"):
        vertical.citygml_buildings(path, ["a"])


def test_classification_locates_first_numeric_change_without_claiming_root_cause():
    base = vertical.z_summary([24.4, 25.0])
    shifted = vertical.z_summary([61.7, 64.2])
    stages = {"citygml": base, "converter": shifted, "native": shifted, "standard": shifted}
    finding = vertical._classify(stages, {"height": 39.4}, False)
    assert finding["first_z_max_change"] == "citygml_to_converter"
    assert finding["level"] == "LIKELY"  # CityGML SHA is not in the Converter receipt.
    assert "final cause" in finding["meaning"]
    stages["converter"] = base
    finding = vertical._classify(stages, {"height": 39.4}, False)
    assert finding["first_z_max_change"] == "converter_to_native"
    assert finding["level"] == "CONFIRMED"


@pytest.mark.parametrize("gml_z,first_change", [(20, "NONE_OBSERVED"), (24.44, "citygml_to_converter")])
def test_saved_run_vertical_trace_is_read_only(tmp_path, gml_z, first_change):
    root = make_run(tmp_path)
    city = tmp_path / "source.gml"
    _gml(city, [(SOURCE_ID, gml_z, "4.4")])
    native = tmp_path / "受入 Native.gpkg"
    converter = tmp_path / "converter.gpkg"
    source = gpd.read_file(native, layer="source_surfaces")
    source["measuredHeight"] = 4.4
    source.to_file(converter, layer="converter_building", driver="GPKG")
    manifest_path = runner.adjacent(native)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"] = {"file": str(converter), "sha256": runner.sha256_file(converter),
                          "layer_resolved": "converter_building"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for number in (1, 2):
        folder = root / f"試験 {number}"
        full, subset = folder / "complete.gpkg", folder / "selection.gpkg"
        for path in (full, subset):
            frame = gpd.read_file(path)
            frame["measured_height"] = 4.4
            frame.to_file(path, layer="standard_surfaces", driver="GPKG")
        subset_manifest = runner.adjacent(subset)
        subset_doc = json.loads(subset_manifest.read_text(encoding="utf-8"))
        subset_doc["parent"]["building"] = runner.fingerprint(full)
        subset_manifest.write_text(json.dumps(subset_doc), encoding="utf-8")
        adapter_manifest = runner.adjacent(folder / "engine.json")
        adapter_doc = json.loads(adapter_manifest.read_text(encoding="utf-8"))
        adapter_doc["crs"] = {"target": "EPSG:4326"}
        adapter_doc["inputs"]["standard_building"]["sha256"] = runner.sha256_file(subset)
        adapter_doc["buildings"][0].update(voxcity_id=1, z_top_abs=20, z_bottom_geom_abs=20,
            ground_eff_abs=15, ground_sample_min_abs=15, ground_sample_max_abs=15,
            ground_sample_count=1, height=5)
        adapter_manifest.write_text(json.dumps(adapter_doc), encoding="utf-8")
    report_path = root / "integration-report.json"
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    saved["inputs"]["native_building_manifest"] = runner.fingerprint(manifest_path)
    report_path.write_text(json.dumps(saved), encoding="utf-8")
    reindex(root)
    before = tree_bytes(tmp_path)
    report = vertical.diagnose_run(root, city, SOURCE_ID[:10])
    assert tree_bytes(tmp_path) == before
    row = report["buildings"][0]
    assert row["source_id"] == row["gml_id"] == SOURCE_ID
    assert row["stages"]["citygml"]["z_max_m"] == gml_z
    assert row["stages"]["native"]["z_max_m"] == 20
    assert row["stages"]["standard"]["z_max_m"] == 20
    assert row["stages"]["native"]["crs_axis_order"] == ["north", "east", "up"]
    assert row["stages"]["standard"]["crs_axis_order"] == ["north", "east"]
    assert row["repeats"][0]["adapter"]["crs"] == "EPSG:4326"
    assert all(item["adapter_consistent"] for item in row["repeats"])
    assert row["classification"]["first_z_max_change"] == first_change
    assert row["classification"]["level"] == ("UNRESOLVED" if gml_z == 20 else "LIKELY")
    assert all(report["input_integrity"].values())
    json.dumps(report, allow_nan=False)
