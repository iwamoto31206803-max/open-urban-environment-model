import json
from pathlib import Path

import pytest

from ouem.native.building.plateau import GISRuntime
from ouem.standardize import building
from ouem.standardize.building import _gdal_worker as worker


ROOT = Path(__file__).parents[1]


def runtime():
    return GISRuntime("gis-python", environment={"PATH": "/gis"})


def successful_result(source, output):
    return {
        "input_path": str(source), "output_path": str(output),
        "input_layer": "building", "output_layer": "building",
        "input_features": 3, "output_features": 2,
        "input_crs": "EPSG:4979", "output_crs": "EPSG:6677",
        "geometry_type": "3D Multi Polygon", "z_geometries": 2,
        "study_area_extent": [-23600.0, -40800.0, -23200.0, -40500.0],
        "required_metadata": True, "z_preserved": True, "max_z_delta": 0.0,
        "deterministic_ids": True,
    }


def test_conversion_uses_config_extent_crs_and_reports_acceptance(tmp_path, monkeypatch):
    source = tmp_path / "native.gpkg"
    source.write_bytes(b"native")
    output = tmp_path / "data/standard/building/komae.gpkg"
    manifest_path = output.with_suffix(".gpkg.manifest.json")
    monkeypatch.setattr(building, "require_gdal", lambda _runtime: None)

    def run_worker(_runtime, job):
        assert job["source"] == str(source.resolve())
        assert job["target_epsg"] == 6677
        assert job["extent"] == [-23600.0, -40800.0, -23200.0, -40500.0]
        assert job["z_tolerance"] == 1e-9
        assert job["source_dataset"] == "PLATEAU CityGML"
        assert not manifest_path.exists()
        return successful_result(source.resolve(), output)

    monkeypatch.setattr(building, "_run_worker", run_worker)
    result = building.standardize_native_buildings(
        source, output,
        study_area_config=ROOT / "config/study_areas/komae_09LD3451.yaml",
        runtime=runtime(),
    )

    assert result.output_crs == "EPSG:6677"
    assert result.geometry_type == "3D Multi Polygon"
    assert result.z_geometries == result.output_features
    assert "Selected/output features: 2" in result.summary()
    assert "Z preservation (max delta 0 m): PASS" in result.summary()
    assert result.summary().endswith("Result: PASS")
    # The worker is mocked, so it must return only its result contract.  It must
    # not manufacture output or manifest content; the orchestration under test
    # owns the adjacent manifest and writes the single JSON document asserted
    # below.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["selection"].endswith("complete selected geometry retained")
    assert manifest["metadata_mapping"] == {"source_id": "Native Building id"}
    assert manifest["status"].startswith("PROVISIONAL")


def test_deterministic_id_is_stable_and_depends_on_source_identity():
    first = building.deterministic_ouem_id("bldg-123")
    assert first == building.deterministic_ouem_id("bldg-123")
    assert first != building.deterministic_ouem_id("bldg-124")
    assert first.startswith("oub-")


class Geometry:
    def __init__(self, points=None, children=None):
        self.points = list(points or [])
        self.children = list(children or [])

    def GetPointCount(self):
        return len(self.points)

    def GetPoint(self, index):
        return self.points[index]

    def SetPoint(self, index, x, y, z):
        self.points[index] = (x, y, z)

    def GetGeometryCount(self):
        return len(self.children)

    def GetGeometryRef(self, index):
        return self.children[index]


def test_horizontal_reprojection_restores_every_nested_z_value():
    geometry = Geometry(
        [(100.0, 200.0, -999.0)],
        [Geometry([(300.0, 400.0, -999.0), (500.0, 600.0, -999.0)])],
    )
    original = [(139.0, 35.0, 8.25), (139.1, 35.1, 12.5), (139.2, 35.2, 19.75)]

    assert worker._restore_z(geometry, original) == 3
    assert worker._points(geometry) == [
        (100.0, 200.0, 8.25), (300.0, 400.0, 12.5), (500.0, 600.0, 19.75)
    ]


class FakeSRS:
    def __init__(self, epsg=None):
        self.epsg = epsg
        self.axis_strategy = None

    def ImportFromEPSG(self, epsg):
        self.epsg = epsg

    def SetAxisMappingStrategy(self, strategy):
        self.axis_strategy = strategy

    def IsSame(self, other):
        return self.epsg == other.epsg

    def GetAuthorityName(self, _target):
        return "EPSG"

    def GetAuthorityCode(self, _target):
        return str(self.epsg)


class FakeOSR:
    OAMS_TRADITIONAL_GIS_ORDER = "traditional"

    def __init__(self):
        self.created = []
        self.transformation = None

    def SpatialReference(self):
        value = FakeSRS()
        self.created.append(value)
        return value

    def CoordinateTransformation(self, source, target):
        self.transformation = (source, target)
        return self.transformation


def test_epsg4979_conversion_uses_only_epsg4326_horizontal_component():
    osr = FakeOSR()
    target = FakeSRS()
    target.ImportFromEPSG(6677)

    transform = worker._horizontal_transform(osr, target)

    source, transformed_target = transform
    assert source.epsg == 4326
    assert transformed_target.epsg == 6677
    assert source.axis_strategy == target.axis_strategy == "traditional"


def test_only_accepted_native_epsg4979_is_validated_as_formal_input():
    osr = FakeOSR()

    assert worker._is_source_crs(osr, FakeSRS(4979))
    assert not worker._is_source_crs(osr, FakeSRS(6697))


def test_worker_selects_by_intersection_without_clipping_source_geometry():
    source = Path(worker.__file__).read_text(encoding="utf-8")
    assert 'if not transformed.Intersects(boundary):' in source
    assert "record.SetGeometry(transformed)" in source
    assert 'checked_layer = check.GetLayerByName(job["output_layer"])' in source
    assert "written Z preservation failed" in source
    assert ".Clip(" not in source and ".Intersection(" not in source


def test_required_standard_metadata_is_exact_and_provider_fields_are_not_copied():
    assert worker.REQUIRED_FIELDS == (
        "ouem_id", "source_id", "source_dataset", "source_lod", "measured_height"
    )


def test_actual_native_id_field_maps_to_standard_source_id():
    actual_native_fields = {
        "id": "id",
        "description": "description",
        "name": "name",
        "creationdate": "creationDate",
    }

    assert worker.NATIVE_SOURCE_ID_FIELD == "id"
    assert worker._field(
        actual_native_fields, (worker.NATIVE_SOURCE_ID_FIELD,), required=True
    ) == "id"


def test_standardizer_does_not_require_plateau_specific_gml_id():
    with pytest.raises(RuntimeError, match="expected field: id"):
        worker._field(
            {"gml_id": "gml_id", "measuredheight": "measuredHeight"},
            (worker.NATIVE_SOURCE_ID_FIELD,),
            required=True,
        )


@pytest.mark.parametrize("name", ["missing.gpkg", "native.txt"])
def test_missing_or_invalid_input_has_useful_message(tmp_path, monkeypatch, name):
    path = tmp_path / name
    if path.suffix == ".txt":
        path.write_text("not a geopackage")
    monkeypatch.setattr(building, "require_gdal", lambda _runtime: None)
    with pytest.raises(building.StandardBuildingError, match="accepted Native Building GeoPackage"):
        building.standardize_native_buildings(
            path, tmp_path / "standard.gpkg",
            study_area_config=ROOT / "config/study_areas/komae_09LD3451.yaml",
            runtime=runtime(),
        )
