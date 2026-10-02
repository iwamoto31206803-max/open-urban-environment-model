import json
from pathlib import Path

import pytest

from ouem.native.building import _plateau_gdal_worker as worker
from ouem.native.building import plateau


ROOT = Path(__file__).parents[1]


def runtime():
    return plateau.GISRuntime(
        "gis-python",
        ogr2ogr="ogr2ogr",
        ogrinfo="ogrinfo",
        output_encoding="cp932",
        environment={"PATH": "/gis"},
    )


def worker_result():
    return {
        "input_layer": "building",
        "output_layer": "building",
        "input_features": 2,
        "output_features": 2,
        "non_empty_geometries": 2,
        "z_geometries": 2,
        "geometry_type": "3D Multi Polygon",
        "crs": "EPSG:6697",
        "preserved_fields": ["gml_id", "measuredHeight", "usage"],
        "warnings": [],
        "errors": [],
    }


def test_gdal_subprocess_output_does_not_depend_on_cp932(monkeypatch):
    monkeypatch.setattr(plateau.shutil, "which", lambda name, **kwargs: f"/gis/{name}")
    diagnostic = "GIS子プロセスの診断".encode("utf-8")
    monkeypatch.setattr(
        plateau.subprocess,
        "run",
        lambda command, **kwargs: plateau.subprocess.CompletedProcess(
            command, 1, b"", diagnostic
        ),
    )

    with pytest.raises(plateau.PlateauBuildingError, match="GIS子プロセスの診断"):
        plateau.require_gdal(runtime())


def test_load_gis_runtime_snapshot(tmp_path):
    snapshot = tmp_path / "gis.json"
    snapshot.write_text(
        json.dumps(
            {
                "python": "C:/QGIS/bin/python.exe",
                "ogr2ogr": "C:/QGIS/bin/ogr2ogr.exe",
                "ogrinfo": "C:/QGIS/bin/ogrinfo.exe",
                "output_encoding": "cp932",
                "environment": {"PATH": "C:/QGIS/bin"},
            }
        ),
        encoding="utf-8",
    )

    value = plateau.load_gis_runtime(snapshot)

    assert value.python == "C:/QGIS/bin/python.exe"
    assert value.output_encoding == "cp932"
    assert value.environment == {"PATH": "C:/QGIS/bin"}


def test_rejects_non_geopackage_input(tmp_path, monkeypatch):
    source = tmp_path / "building.gml"
    source.write_text("not used", encoding="utf-8")
    monkeypatch.setattr(plateau, "require_gdal", lambda _runtime: None)

    with pytest.raises(plateau.PlateauBuildingError, match="Converter GeoPackage"):
        plateau.ingest_converter_geopackage(
            source, tmp_path / "native.gpkg", runtime=runtime()
        )


def test_ingest_writes_receipt_manifest_and_summary(tmp_path, monkeypatch):
    source = tmp_path / "converted.gpkg"
    source.write_bytes(b"synthetic converter fixture")
    output = tmp_path / "data/native/building/test.gpkg"
    monkeypatch.setattr(plateau, "require_gdal", lambda _runtime: None)

    def run_worker(_runtime, **kwargs):
        assert kwargs["mode"] == "ingest"
        assert kwargs["source"] == source.resolve()
        kwargs["output"].write_bytes(b"native")
        return worker_result()

    monkeypatch.setattr(plateau, "_run_worker", run_worker)

    result = plateau.ingest_converter_geopackage(
        source, output, runtime=runtime(), source_layer="building"
    )

    assert result.input_features == result.output_features == 2
    assert result.non_empty_geometries == result.z_geometries == 2
    assert result.geometry_type == "3D Multi Polygon"
    assert not result.reused
    receipt = json.loads(
        output.with_suffix(".gpkg.receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["source_sha256"] == plateau._source_fingerprint(source)
    manifest = json.loads(
        output.with_suffix(".gpkg.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["manual_preprocessor"] == "PLATEAU GIS Converter GUI"
    assert manifest["validation"]["preserved_fields"] == [
        "gml_id",
        "measuredHeight",
        "usage",
    ]
    assert "Non-empty/Z geometries: 2/2" in result.summary()


def test_matching_source_fingerprint_reuses_valid_native(tmp_path, monkeypatch):
    source = tmp_path / "converted.gpkg"
    source.write_bytes(b"converter")
    output = tmp_path / "native.gpkg"
    output.write_bytes(b"native")
    output.with_suffix(".gpkg.receipt.json").write_text(
        json.dumps(plateau._receipt_value(source.resolve(), None)),
        encoding="utf-8",
    )
    monkeypatch.setattr(plateau, "require_gdal", lambda _runtime: None)
    calls = []

    def run_worker(_runtime, **kwargs):
        calls.append(kwargs)
        return worker_result()

    monkeypatch.setattr(plateau, "_run_worker", run_worker)

    result = plateau.ingest_converter_geopackage(
        source, output, runtime=runtime()
    )

    assert result.reused
    assert calls[0]["mode"] == "compare"
    assert calls[0]["source"] == source.resolve()
    assert calls[0]["output"] == output


def test_pilot_expected_count_is_checked_after_manifest(tmp_path, monkeypatch):
    source = tmp_path / "converted.gpkg"
    source.write_bytes(b"converter")
    output = tmp_path / "native.gpkg"
    monkeypatch.setattr(plateau, "require_gdal", lambda _runtime: None)

    def run_worker(_runtime, **kwargs):
        kwargs["output"].write_bytes(b"native")
        return worker_result()

    monkeypatch.setattr(plateau, "_run_worker", run_worker)

    with pytest.raises(plateau.PlateauBuildingError, match="expected 3637"):
        plateau.ingest_converter_geopackage(
            source, output, runtime=runtime(), expected_count=3637
        )

    manifest = json.loads(
        output.with_suffix(".gpkg.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["parameters"]["expected_count"] == 3637


class FakeGeometry:
    def __init__(self, *, empty=False, has_z=True):
        self.empty = empty
        self.has_z = has_z

    def IsEmpty(self):
        return self.empty

    def Is3D(self):
        return self.has_z

    def GetCoordinateDimension(self):
        return 3 if self.has_z else 2

    def GetPointCount(self):
        return 1

    def GetPoint(self, _index):
        return (139.0, 35.0, 12.5) if self.has_z else (139.0, 35.0)

    def GetGeometryCount(self):
        return 0


class FakeFeature:
    def __init__(self, geometry):
        self.geometry = geometry

    def GetGeometryRef(self):
        return self.geometry


class FakeField:
    def __init__(self, name):
        self.name = name

    def GetName(self):
        return self.name


class FakeDefinition:
    def __init__(self, fields):
        self.fields = fields

    def GetFieldCount(self):
        return len(self.fields)

    def GetFieldDefn(self, index):
        return FakeField(self.fields[index])


class FakeSRS:
    def GetAuthorityName(self, _target):
        return "EPSG"

    def GetAuthorityCode(self, _target):
        return "6697"


class FakeLayer:
    def __init__(self, geometries, fields=("gml_id", "measuredHeight")):
        self.features = [FakeFeature(item) for item in geometries]
        self.definition = FakeDefinition(list(fields))

    def GetFeatureCount(self):
        return len(self.features)

    def GetLayerDefn(self):
        return self.definition

    def ResetReading(self):
        pass

    def __iter__(self):
        return iter(self.features)

    def GetSpatialRef(self):
        return FakeSRS()


def test_3d_multipolygon_validation_requires_non_empty_z_geometry():
    values = worker._validate_layer(
        FakeLayer([FakeGeometry(), FakeGeometry()]), ["measuredHeight"]
    )

    assert values["features"] == 2
    assert values["non_empty_geometries"] == 2
    assert values["z_geometries"] == 2
    assert values["crs"] == "EPSG:6697"


@pytest.mark.parametrize(
    ("geometry", "message"),
    [
        (FakeGeometry(empty=True), "empty building geometry"),
        (FakeGeometry(has_z=False), "without Z"),
    ],
)
def test_geometry_validation_rejects_empty_or_2d(geometry, message):
    with pytest.raises(RuntimeError, match=message):
        worker._validate_layer(FakeLayer([geometry]), ["measuredHeight"])


def test_validation_requires_measured_height():
    with pytest.raises(RuntimeError, match="measuredHeight"):
        worker._validate_layer(
            FakeLayer([FakeGeometry()], fields=("gml_id",)), ["measuredHeight"]
        )


def test_geometry_type_must_be_3d_multipolygon():
    worker._require_3d_multipolygon("3D Multi Polygon")

    with pytest.raises(RuntimeError, match="3D Multi Polygon"):
        worker._require_3d_multipolygon("3D PolyhedralSurface")


class FakeNamedLayer:
    def __init__(self, name):
        self.name = name

    def GetName(self):
        return self.name


class FakeDataset:
    def __init__(self, names):
        self.layers = [FakeNamedLayer(name) for name in names]

    def GetLayerCount(self):
        return len(self.layers)

    def GetLayer(self, index):
        return self.layers[index]

    def GetLayerByName(self, name):
        return next((layer for layer in self.layers if layer.name == name), None)


def test_building_layer_resolution_is_conservative():
    selected = worker._resolve_layer(FakeDataset(["metadata", "building"]), None)
    assert selected.GetName() == "building"


def test_converter_building_layer_is_selected_among_plateau_attribute_layers():
    dataset = FakeDataset(
        [
            "bldg:Building",
            "core:Address",
            "uro:DataQualityAttribute",
            "uro:KeyValuePairAttribute",
            "uro:RiverFloodingRiskAttribute",
            "uro:BuildingIDAttribute",
            "uro:BuildingDetailAttribute",
        ]
    )

    selected = worker._resolve_layer(dataset, None)

    assert selected.GetName() == "bldg:Building"


def test_explicit_converter_building_layer_is_preserved():
    converter_layer = worker._resolve_layer(
        FakeDataset(["building", "bldg:Building"]), "bldg:Building"
    )
    assert converter_layer.GetName() == "bldg:Building"


def test_ambiguous_building_layers_require_explicit_selection():
    with pytest.raises(RuntimeError, match="--source-layer"):
        worker._resolve_layer(FakeDataset(["building", "bldg:Building"]), None)


def test_missing_building_layer_requires_explicit_selection():
    with pytest.raises(RuntimeError, match="could not find a building layer"):
        worker._resolve_layer(FakeDataset(["core:Address", "uro:DataQuality"]), None)


def test_komae_acceptance_records_verified_expected_count():
    script = (
        ROOT / "scripts/work/plateau_komae_local_acceptance.cmd"
    ).read_text(encoding="utf-8")

    assert "--expected-count 3637 ^" in script
    assert '--source-layer "%SOURCE_LAYER%" ^' in script


def test_komae_acceptance_resolves_converter_paths_from_repository_root():
    script = (
        ROOT / "scripts/work/plateau_komae_local_acceptance.cmd"
    ).read_text(encoding="utf-8")

    assert 'for %%I in ("%~dp0..\\..") do set "REPO=%%~fI"' in script
    assert 'call :resolve_converter_gpkg "%~2"' in script
    assert (
        'set "CONVERTER_GPKG=%REPO%\\data\\converted\\building\\plateau_komae\\'
        '53393465_bldg_6697_op_convert.gpkg"'
    ) in script
    assert (
        'if not "%CONVERTER_GPKG:~1,1%"==":" '
        'if not "%CONVERTER_GPKG:~0,1%"=="\\" '
        'set "CONVERTER_GPKG=%REPO%\\%CONVERTER_GPKG%"'
    ) in script
    assert 'for %%I in ("%CONVERTER_GPKG%") do set "CONVERTER_GPKG=%%~fI"' in script
