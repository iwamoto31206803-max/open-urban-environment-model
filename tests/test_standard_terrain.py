import hashlib
import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin

from ouem.native.terrain import NativeTerrainError, accept_native_terrain
from ouem.standardize.terrain import StandardTerrainError, standardize_native_terrain


ROOT = Path(__file__).parents[1]
STUDY_AREA = ROOT / "config/study_areas/komae_09LD3451.yaml"


def dem(path, *, crs="EPSG:6677", nodata=-32767.0):
    values = np.array([[10.25, nodata, 12.5], [13.0, 14.75, 15.0]], dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", width=3, height=2, count=1,
                       dtype="float32", crs=crs,
                       transform=from_origin(-23600, -40500, .5, .5), nodata=nodata) as dst:
        dst.write(values, 1)
    return values


def accept(source, manifest, **kwargs):
    return accept_native_terrain(
        source, manifest, provider="Synthetic provider", source_dataset="Synthetic DEM",
        vertical_reference_status="unresolved", **kwargs
    )


def test_native_to_standard_preserves_grid_values_and_records_provenance(tmp_path):
    source = tmp_path / "source.tif"
    original = dem(source)
    native_path = tmp_path / "native.json"
    native = accept(source, native_path)
    output = tmp_path / "standard.tif"

    result = standardize_native_terrain(native_path, output, study_area_config=STUDY_AREA)

    assert native.pixel_size == [.5, .5]
    assert native.horizontal_crs == "EPSG:6677"
    assert native.vertical_reference_status == "unresolved"
    assert native.vertical_reference is native.vertical_reference_source is None
    assert result.grid_preserved and result.elevations_preserved
    with rasterio.open(source) as src, rasterio.open(output) as dst:
        assert dst.transform == src.transform
        assert dst.bounds == src.bounds
        assert dst.crs == src.crs
        assert dst.res == (.5, .5)
        assert dst.nodata == -9999.0
        written = dst.read(1)
        assert np.array_equal(written[original != -32767], original[original != -32767])
        assert written[0, 1] == -9999.0
        assert dst.tags()["VERTICAL_REFERENCE_STATUS"] == "unresolved"
        assert dst.tags()["VERTICAL_REFERENCE"] == "unresolved"
    manifest = json.loads(output.with_suffix(".tif.manifest.json").read_text())
    assert manifest["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["standard"]["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert manifest["vertical_reference"] == {"name": None, "source": None, "status": "unresolved"}
    assert "No reprojection or resampling" in manifest["processing"]


def test_same_native_input_produces_deterministic_geotiff(tmp_path):
    source = tmp_path / "source.tif"
    dem(source)
    native = tmp_path / "native.json"
    accept(source, native)
    first, second = tmp_path / "one.tif", tmp_path / "two.tif"
    standardize_native_terrain(native, first, study_area_config=STUDY_AREA)
    standardize_native_terrain(native, second, study_area_config=STUDY_AREA)
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("crs", [None, "EPSG:4326"])
def test_missing_or_unsupported_horizontal_crs_fails(tmp_path, crs):
    source = tmp_path / "source.tif"
    dem(source, crs=crs)
    native = tmp_path / "native.json"
    if crs is None:
        with pytest.raises(NativeTerrainError, match="no horizontal CRS"):
            accept(source, native)
    else:
        accept(source, native)
        with pytest.raises(StandardTerrainError, match="expected EPSG:6677"):
            standardize_native_terrain(native, tmp_path / "out.tif", study_area_config=STUDY_AREA)


def test_native_manifest_detects_changed_source_and_vertical_semantics_are_explicit(tmp_path):
    source = tmp_path / "source.tif"
    dem(source)
    native = tmp_path / "native.json"
    accept(source, native)
    source.write_bytes(source.read_bytes() + b"changed")
    with pytest.raises(NativeTerrainError, match="fingerprint changed"):
        standardize_native_terrain(native, tmp_path / "out.tif", study_area_config=STUDY_AREA)
    with pytest.raises(NativeTerrainError, match="requires a name and evidence"):
        accept_native_terrain(source, native, provider="x", source_dataset="x",
                              vertical_reference_status="verified")
