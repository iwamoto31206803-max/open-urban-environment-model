import json
from pathlib import Path

import pytest

from ouem.native.building import plateau
from ouem.study_area import StudyArea


def test_recursive_discovery_accepts_packaged_and_standalone_buildings(tmp_path):
    accepted_upper = tmp_path / "download" / "UDX" / "BLDG" / "A.GML"
    accepted_nested = tmp_path / "city" / "udx" / "bldg" / "nested" / "b.gml"
    accepted_standalone = tmp_path / "53394525_bldg_6697_op.gml"
    skipped = tmp_path / "city" / "udx" / "tran" / "road.gml"
    skipped_arbitrary = tmp_path / "buildings.gml"
    skipped_nested_standalone = tmp_path / "loose" / "53394526_bldg_6697_op.gml"
    skipped_wrong_suffix = tmp_path / "53394527_bldg_6697.gml"
    ignored = tmp_path / "city" / "udx" / "bldg" / "readme.txt"
    for path in (
        accepted_upper,
        accepted_nested,
        accepted_standalone,
        skipped,
        skipped_arbitrary,
        skipped_nested_standalone,
        skipped_wrong_suffix,
        ignored,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")

    result = plateau.discover_building_gml(tmp_path)

    assert result.accepted == (accepted_standalone, accepted_nested, accepted_upper)
    assert result.skipped == (
        skipped_wrong_suffix,
        skipped_arbitrary,
        skipped,
        skipped_nested_standalone,
    )
    assert result.discovered == 7


def test_deterministic_ids_ignore_iteration_order_and_distinguish_sources():
    one = plateau.deterministic_ouem_id("udx/bldg/a.gml", "building-4")
    repeated = plateau.deterministic_ouem_id("udx/bldg/a.gml", "building-4")
    other_file = plateau.deterministic_ouem_id("udx/bldg/b.gml", "building-4")

    assert one == repeated
    assert one != other_file


@pytest.mark.parametrize(
    ("envelope", "expected"),
    [
        ((0, 1, 0, 1), True),
        ((10, 12, 10, 12), False),
        ((2, 3, 0, 1), True),  # boundary touch is an intersection
        ((-1, 4, -1, 4), True),  # crossing feature remains selected
    ],
)
def test_extent_intersection(envelope, expected):
    assert plateau.intersects_extent(envelope, (0, 0, 2, 2)) is expected


def test_native_gdal_command_preserves_xyz_and_layer(tmp_path):
    source = tmp_path / "udx/bldg/one.gml"
    output = tmp_path / "native/one.gpkg"

    command = plateau.build_native_command(source, output)

    assert command[:4] == ["ogr2ogr", "-f", "GPKG", str(output)]
    assert command[4:6] == [str(source), "Building"]
    assert command[command.index("-dim") + 1] == "XYZ"
    assert command[command.index("-nln") + 1] == "building"


def test_missing_gdal_has_actionable_failure(monkeypatch):
    monkeypatch.setattr(plateau.shutil, "which", lambda _name: None)

    with pytest.raises(plateau.PlateauBuildingError, match="ogr2ogr executable"):
        plateau.require_gdal("gis-python")


def test_gdal_check_uses_external_gis_python(monkeypatch):
    calls = []
    monkeypatch.setattr(plateau.shutil, "which", lambda name: f"/gis/{name}")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return plateau.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(plateau.subprocess, "run", run)

    plateau.require_gdal("gis-python")

    assert calls[0][0] == [
        "/gis/gis-python",
        "-c",
        "from osgeo import ogr, osr",
    ]


def test_manifest_contains_provenance_counts_and_parameters(tmp_path):
    dataset = tmp_path / "plateau"
    source = dataset / "udx/bldg/one.gml"
    source.parent.mkdir(parents=True)
    source.write_text("fixture", encoding="utf-8")
    native = tmp_path / "native.gpkg"
    standard = tmp_path / "standard.gpkg"
    destination = tmp_path / "standard.gpkg.manifest.json"
    area = StudyArea("test", "Test", 6677, 0, 1, 2, 3)
    result = plateau.PlateauRunResult(
        gml_discovered=1,
        gml_accepted=1,
        source_features=4,
        native_features=4,
        standard_features=2,
        study_area_intersections=2,
        native_created=1,
        invalid_geometries=1,
        warnings=["example warning"],
    )

    plateau.write_manifest(
        destination,
        dataset_dir=dataset,
        sources=[source],
        native_outputs=[native],
        standard_output=standard,
        area=area,
        parameters={"selection": "intersects; complete geometry retained"},
        result=result,
    )
    manifest = json.loads(destination.read_text(encoding="utf-8"))

    assert manifest["provider"] == "PLATEAU"
    assert manifest["source"]["files"] == ["udx/bldg/one.gml"]
    assert manifest["source"]["crs"] == "EPSG:6697"
    assert manifest["target_crs"] == "EPSG:6677"
    assert manifest["vertical"]["unit"] == "metre"
    assert manifest["study_area"] == {"id": "test", "extent": [0, 1, 2, 3]}
    assert manifest["counts"]["standard_features"] == 2
    assert manifest["warnings"] == ["example warning"]
    assert "processed_at" in manifest


def test_run_summary_contains_required_operational_counts():
    result = plateau.PlateauRunResult(3, 2, 1, 8, 8, 4, 4, 1, 1, 2, 1)

    summary = result.summary()

    assert "GML discovered/accepted/skipped: 3/2/1" in summary
    assert "Source/native/standard features: 8/8/4" in summary
    assert "Study-area intersections: 4" in summary
    assert "Native reused/new: 1/1" in summary
    assert "Invalid/failed geometries: 2/1" in summary
