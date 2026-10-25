"""Offline acquisition tests with tiny synthetic COGs, no public datasets."""
import io
import json

import numpy as np
import pytest
import rasterio
from rasterio.shutil import copy as rio_copy
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from shapely.geometry import box, mapping

from ouem.acquire import meta_chmv2 as chm
from ouem.study_area import StudyArea

K1, K2, K3 = "0"*10, "0"*9+"1", "0"*9+"2"


def cog(root, key, data, *, x=0, nodata=255, crs=3857, scale=1):
    plain = root / (key+"-source.tif")
    path = root / (key+".tif")
    data = np.asarray(data, dtype="uint8")
    with rasterio.open(plain, "w", driver="GTiff", width=data.shape[1], height=data.shape[0],
                       count=1, dtype="uint8", crs=f"EPSG:{crs}",
                       transform=from_origin(x, 2, 1, 1), nodata=nodata) as dst:
        dst.write(data, 1)
        dst.scales = (scale,)
    rio_copy(plain, path, driver="COG")
    return path


def area(extent=(0, 0, 4, 2)):
    return StudyArea("synthetic", "synthetic", 3857, *extent)


def feature(key, bounds):
    bounds = transform_bounds(3857, 4326, *bounds)
    return {"type": "Feature", "properties": {"tile": key}, "geometry": mapping(box(*bounds))}


def index():
    return {"type": "FeatureCollection", "features": [
        feature(K2, (2, 0, 4, 2)), feature(K1, (0, 0, 2, 2)),
        feature(K3, (20, 0, 22, 2))]}


def config(tmp_path):
    path = tmp_path / "area.yaml"
    path.write_text("study_area:\n  id: synthetic\ncrs:\n  epsg: 3857\nextent:\n  xmin: 0\n  ymin: 0\n  xmax: 4\n  ymax: 2\n", encoding="utf-8")
    return path


def test_index_uses_existing_features_and_ignores_boundary_only():
    assert chm.select_tiles(index(), area()) == [K1, K2]
    assert chm.select_tiles(index(), area((0, 0, 2, 2))) == [K1]


@pytest.mark.parametrize("change", ["missing", "duplicate", "bad_key", "wrong_crs"])
def test_index_blocks_missing_or_ambiguous_coverage(change):
    value = index()
    if change == "missing": value["features"] = value["features"][:1]
    if change == "duplicate": value["features"].append(value["features"][1])
    if change == "bad_key": value["features"][1]["properties"]["tile"] = "../unsafe"
    if change == "wrong_crs": value["crs"] = {"properties": {"name": "EPSG:3857"}}
    with pytest.raises(chm.AcquisitionError): chm.select_tiles(value, area())


def test_mosaic_preserves_native_samples_nodata_and_output_alignment(tmp_path):
    a = cog(tmp_path, K1, [[0, 255], [2, 3]])
    b = cog(tmp_path, K2, [[4, 5], [6, 7]], x=2)
    before = [chm.sha256(a), chm.sha256(b)]
    outputs = []
    for n in range(2):
        output = tmp_path / f"out{n}.tif"
        record = chm.mosaic_crop([a, b], area((0.2, 0.1, 3.7, 1.8)), output)
        with rasterio.open(output) as dst:
            assert dst.crs.to_epsg() == 3857
            assert dst.transform == from_origin(0, 2, 1, 1)
            assert dst.read(1).tolist() == [[0, 255, 4, 5], [2, 3, 6, 7]]
            assert dst.read_masks(1).tolist() == [[255, 0, 255, 255], [255]*4]
            assert dst.nodata == 255 and dst.dtypes == ("uint8",)
        assert record["nodata_pixels"] == 1
        outputs.append(chm.sha256(output))
    assert outputs[0] == outputs[1]
    assert before == [chm.sha256(a), chm.sha256(b)]


def test_nodata_absent_does_not_make_valid_zero_missing(tmp_path):
    path = cog(tmp_path, K1, [[0, 1], [2, 3]], nodata=None, scale=0.5)
    output = tmp_path / "out.tif"
    chm.mosaic_crop([path], area((0, 0, 2, 2)), output)
    with rasterio.open(output) as src:
        assert src.nodata is None and src.scales == (0.5,)
        assert src.read_masks(1).min() == 255
        assert src.read(1)[0, 0] == 0


@pytest.mark.parametrize("problem", ["gap", "crs", "alignment", "nodata", "overlap", "limit"])
def test_mosaic_refuses_implicit_conversion_and_missing_coverage(tmp_path, problem):
    a = cog(tmp_path, K1, [[1, 1], [1, 1]])
    b = cog(tmp_path, K2, [[2, 2], [2, 2]],
            x=3 if problem == "gap" else 2.5 if problem == "alignment" else 0 if problem == "overlap" else 2,
            crs=6677 if problem == "crs" else 3857,
            nodata=254 if problem == "nodata" else 255)
    with pytest.raises(chm.AcquisitionError):
        chm.mosaic_crop([a, b], area(), tmp_path/"out.tif", max_pixels=1 if problem == "limit" else 100)
    assert not (tmp_path/"out.tif").exists()


def test_offline_acquisition_records_lineage_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(chm.urllib.request, "urlopen", lambda *a, **kw: pytest.fail("network used"))
    cog(tmp_path, K1, [[0, 255], [1, 2]])
    cog(tmp_path, K2, [[3, 4], [5, 6]], x=2)
    idx = tmp_path/"index.json"
    idx.write_text(json.dumps(index()))
    raw, work = tmp_path/"raw", tmp_path/"work"
    result = chm.acquire(config(tmp_path), raw, work, index=idx, tiles_dir=tmp_path)
    assert result["status"] == "COMPLETED"
    assert result["selected_quadkeys"] == [K1, K2]
    assert not (raw/(K3+".tif")).exists()
    assert result["tiles"][0]["acquired_at"] is None
    assert result["tiles"][0]["method"] == "local_copy"
    assert result["output"]["sha256"] == chm.sha256(work/"chmv2_aoi.tif")
    assert result["index"]["sha256"] == chm.sha256(idx)
    assert result["tiles"][0]["raster"]["nodata"] == 255
    assert json.loads((work/"acquisition-record.json").read_text())["status"] == "COMPLETED"
    with pytest.raises(chm.AcquisitionError): chm.acquire(config(tmp_path), raw, work)


def test_failed_network_retains_failure_record(tmp_path, monkeypatch):
    def fail(*a, **kw): raise OSError("offline")
    monkeypatch.setattr(chm.urllib.request, "urlopen", fail)
    with pytest.raises(OSError, match="offline"):
        chm.acquire(config(tmp_path), tmp_path/"raw", tmp_path/"work")
    record = json.loads((tmp_path/"work/acquisition-record.json").read_text())
    assert record["status"] == "FAILED"
    assert "output" not in record
    assert "offline" in record["error"]


def test_download_stream_limit_and_receipt(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        url = "https://example.test/object"
        headers = {"Content-Length": "3", "ETag": "test", "Last-Modified": "test-date"}
    monkeypatch.setattr(chm.urllib.request, "urlopen", lambda *a, **kw: Response(b"abc"))
    receipt = chm.download(Response.url, tmp_path/"object", 4)
    assert receipt["sha256"] == chm.sha256(tmp_path/"object")
    assert receipt["acquired_at"] and receipt["etag"] == "test"
    with pytest.raises(chm.AcquisitionError, match="limit"):
        chm.download(Response.url, tmp_path/"too-big", 2)
    assert not (tmp_path/"too-big").exists()


def test_internal_mask_preserved_without_declared_nodata(tmp_path):
    path = cog(tmp_path, K1, [[0, 99], [2, 3]], nodata=None)
    source = tmp_path/(K1+"-source.tif")
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(source, "r+") as dst:
            dst.write_mask(np.array([[255, 0], [255, 255]], dtype="uint8"))
    # Create another COG from the masked source; never edit a finished COG.
    masked_cog = tmp_path/"masked.tif"
    rio_copy(source, masked_cog, driver="COG")
    output = tmp_path/"out.tif"
    chm.mosaic_crop([masked_cog], area((0, 0, 2, 2)), output)
    with rasterio.open(output) as dst:
        assert dst.nodata is None
        assert dst.read(1).tolist() == [[0, 99], [2, 3]]
        assert dst.read_masks(1).tolist() == [[255, 0], [255, 255]]


def test_nan_nodata_is_preserved_and_json_safe(tmp_path):
    source, tile = tmp_path/"source.tif", tmp_path/"nan.tif"
    with rasterio.open(source, "w", driver="GTiff", width=2, height=2,
                       count=1, dtype="float32", crs="EPSG:3857",
                       transform=from_origin(0, 2, 1, 1), nodata=float("nan")) as dst:
        dst.write(np.array([[0, np.nan], [2, 3]], dtype="float32"), 1)
    rio_copy(source, tile, driver="COG")
    output = tmp_path/"out.tif"
    record = chm.mosaic_crop([tile], area((0, 0, 2, 2)), output)
    assert record["nodata_pixels"] == 1
    json.dumps(record, allow_nan=False)
    with rasterio.open(output) as dst:
        assert np.isnan(dst.nodata) and np.isnan(dst.read(1)[0, 1])
        assert dst.read_masks(1)[0, 0] == 255


def test_truncated_download_does_not_publish_completed_raw(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        url = "https://example.test/truncated"
        headers = {"Content-Length": "10"}
    monkeypatch.setattr(chm.urllib.request, "urlopen", lambda *a, **kw: Response(b"abc"))
    with pytest.raises(chm.AcquisitionError, match="Truncated"):
        chm.download(Response.url, tmp_path/"tile.tif", 20)
    assert not (tmp_path/"tile.tif").exists()
    assert (tmp_path/"tile.tif.part").read_bytes() == b"abc"


def test_canonical_komae_yaml_selects_only_intersecting_synthetic_index_tile():
    from pathlib import Path
    from ouem.study_area import load_study_area
    repo = Path(__file__).resolve().parents[1]
    aoi = load_study_area(repo/"config/study_areas/komae_09LD3451.yaml")
    bounds = transform_bounds(aoi.epsg, 4326, *aoi.extent, densify_pts=21)
    left, bottom, right, top = bounds
    value = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"tile": K1},
         "geometry": mapping(box(left-.01, bottom-.01, right+.01, top+.01))},
        {"type": "Feature", "properties": {"tile": K2},
         "geometry": mapping(box(left+.1, bottom+.1, right+.1, top+.1))}]}
    assert chm.select_tiles(value, aoi) == [K1]
