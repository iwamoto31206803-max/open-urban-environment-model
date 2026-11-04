import io
import json
from zipfile import ZipFile

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from ouem import terrain_candidate_b_preflight as p


def test_catalogued_index_filter():
    frame = gpd.GeoDataFrame(
        {"MESH_NO":["09LD3423","09LD3433"],
         "URL":[f"{p.S3}/2023/dig/grd50/09LD3423.zip","https://invalid.example/"]},
        geometry=[box(*p.AOI),box(0,0,1,1)],crs=6677).to_crs(3857)
    assert p.index_tiles(p.AOI) == [(14,14544,6453)]
    assert p.tile_urls(frame,"2023",box(*p.AOI)) == {"09LD3423":f"{p.S3}/2023/dig/grd50/09LD3423.zip"}
    with pytest.raises(ValueError,match="unexpected terrain URL"):
        p.tile_urls(frame,"2023",box(-23000,-41000,20,20))
    with pytest.raises(ValueError,match="MVT CRS"):
        p.tile_urls(frame.to_crs(6677),"2023",box(*p.AOI))


def test_unpacks_exact_member_and_rejects_duplicate(tmp_path):
    archive = tmp_path/"tile.zip"
    with ZipFile(archive,"w") as z:
        z.writestr("../outside.tif",b"ignored")
        z.writestr("09LD3423.tif",b"authored")
    assert p.unpack(archive,"09LD3423").read_bytes() == b"authored"
    assert not (tmp_path.parent/"outside.tif").exists()
    with pytest.warns(UserWarning,match="Duplicate name"):
        with ZipFile(archive,"a") as z:
            z.writestr("09LD3423.tif",b"duplicate")
    with pytest.raises(ValueError,match="expected one"):
        p.unpack(archive,"09LD3423")


def write(path, values, x):
    with rasterio.open(path,"w",driver="GTiff",width=2,height=2,count=1,dtype="float32",
                       crs="EPSG:6677",transform=from_origin(x,1,.5,.5),nodata=-9999) as ds:
        ds.write(np.asarray(values,dtype=np.float32),1)
    return path


def test_aligned_coverage_nodata_and_overlap(tmp_path):
    a = write(tmp_path/"a.tif",[[2,-9999],[0,4]],0)
    b = write(tmp_path/"b.tif",[[3,9],[7,10]],.5)
    _,x,xa = p.raster_cells(a,(0,0,1.5,1))
    _,y,ya = p.raster_cells(b,(0,0,1.5,1))
    result = p.summarize({"first":{"a":(x,xa)},"second":{"b":(y,ya)}})
    assert p.coverage([x],[xa]) == dict(cells=6,valid=3,footprint=4,nodata_only=1,uncovered=3,overlapping=0)
    assert result["combined"] == dict(cells=6,valid=6,footprint=6,nodata_only=0,uncovered=0,overlapping=1)
    assert result["minimum_full_tile_sets"] == [["first/a","second/b"]]
    assert result["single_sources"] == []
    assert result["pairs"]["first/a -> second/b"]["overlap"]["b_minus_a_m"]["max"] == 3
    assert result["pairs"]["first/a -> second/b"]["exclusive_adjacent"]["edges"] == 1


def test_misalignment_is_rejected(tmp_path):
    path = write(tmp_path/"a.tif",[[1,2],[3,4]],.25)
    with pytest.raises(ValueError,match="grid misalignment"):
        p.raster_cells(path,(0,0,1,1))


def test_unnamed_datum_is_only_conditionally_comparable():
    wkt = ('PROJCS["JGD2011 / Japan Plane Rectangular CS IX",GEOGCS["unknown",'
           'DATUM["unnamed",SPHEROID["GRS 1980",6378137,298.257222101004]],'
           'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
           'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",36],'
           'PARAMETER["central_meridian",139.833333333333],PARAMETER["scale_factor",0.9999],'
           'PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1],'
           'AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","6677"]]')
    crs = rasterio.crs.CRS.from_wkt(wkt)
    assert crs.to_epsg() is None
    assert p.horizontal_status(crs,catalogue_declares_ix=True).startswith("conditional")
    with pytest.raises(ValueError,match="ambiguous horizontal CRS"):
        p.horizontal_status(crs)
    wrong = rasterio.crs.CRS.from_wkt(wkt.replace('false_easting",0','false_easting",1'))
    with pytest.raises(ValueError,match="does not support"):
        p.horizontal_status(wrong,catalogue_declares_ix=True)


def test_download_size_failure_and_blocked_report(tmp_path,monkeypatch):
    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": str(p.MAX_BYTES+1)}
        def geturl(self):
            return "https://example.org/data"
    monkeypatch.setattr(p,"urlopen",lambda *args,**kwargs:Response(b"x"))
    receipts=[]
    with pytest.raises(ValueError,match="download size limit"):
        p.download("https://example.org/data",tmp_path/"large",receipts)
    assert receipts[0]["http_status"] == 200 and "size limit" in receipts[0]["error"]
    report = p.run(tmp_path/"run")
    assert report["status"] == "BLOCKED" and "combined" not in report
    assert all("error" in source for source in report["sources"].values())
    assert json.loads((tmp_path/"run/report.json").read_bytes())["status"] == "BLOCKED"
    with pytest.raises(FileExistsError):
        p.run(tmp_path/"run")
