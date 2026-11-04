import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

from ouem import terrain_candidate_b_t3 as t3


def test_priority_fallback_and_signed_zero():
    heights, ids = t3.select(np.array([[[1.,2.]],[[np.nan,np.nan]],
                                       [[-0.,np.nan]],[[np.nan,np.nan]]],dtype="float32"))
    np.testing.assert_array_equal(ids,[[3,1]])
    np.testing.assert_array_equal(heights,[[0,2]])
    assert np.signbit(heights[0,0])


@pytest.mark.parametrize(("values","error"), [
    ([np.nan]*4,"uncovered cell"),([1.,2.,3.,np.nan],"same-source valid tile overlap"),
    ([1.,np.nan,2.,3.],"same-source valid tile overlap"),
])
def test_missing_or_competing_tiles(values,error):
    with pytest.raises(ValueError,match=error):
        t3.select(np.array(values,dtype="float32").reshape(4,1,1))


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    root = tmp_path/"raw"
    hashes = {}
    for tile in t3.TILES.values():
        path = root/(tile+".tif")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(tile.encode())
        hashes[tile] = t3.digest(path)
    monkeypatch.setattr(t3,"HASHES",hashes)
    return root


def test_hash_mismatch_blocks(tmp_path,inputs):
    (inputs/"tama/09LD3423.tif").write_bytes(b"tampered")
    out = tmp_path/"out"
    assert "SHA-256 mismatch" in t3.run(inputs,out)["error"]
    assert [p.name for p in out.iterdir()]==["failure.json"]
    assert json.loads((out/"failure.json").read_bytes())["status"]=="BLOCKED"


def test_misaligned_real_tiff_blocks(tmp_path,inputs):
    key = "tama/09LD3423"
    path = inputs/(key+".tif")
    with rasterio.open(path,"w",driver="GTiff",width=1,height=1,count=1,dtype="float32",
                       crs="EPSG:6677",transform=t3.AFFINE.translation(.25,0)*t3.AFFINE,
                       nodata=t3.HEIGHT_NODATA) as dst:
        dst.write(np.ones((1,1),dtype="float32"),1)
    t3.HASHES[key] = t3.digest(path)
    out = tmp_path/"out"
    assert "grid misalignment" in t3.run(inputs,out)["error"]
    assert not (out/"manifest.json").exists()


@pytest.mark.parametrize("phase",["none","write","publish","tamper"])
def test_stage_audit_and_completion_marker(tmp_path,inputs,monkeypatch,phase):
    def read(path,*args,**kwargs):
        tile = path.relative_to(inputs).with_suffix("").as_posix()
        array = np.full((200,200),np.nan)
        if tile=="tama/09LD3423":
            array[:,:100] = 1.
        if tile=="23ku/09LD3433":
            array[:,100:] = -0.
        return {"sha256":t3.HASHES[tile],"dtype":"float32"},array,None

    monkeypatch.setattr(t3,"raster_cells",read)
    monkeypatch.setattr(t3,"diagnostics",lambda *args:{"synthetic":True})
    original = t3.write_raster

    def write(path,array,nodata,label):
        if phase=="write" and label=="source_tile":
            path.write_bytes(b"partial")
            raise OSError("synthetic write failure")
        if phase=="tamper" and label=="terrain":
            array = array.copy()
            array[0,100] = 0.
        original(path,array,nodata,label)

    monkeypatch.setattr(t3,"write_raster",write)
    rename = Path.rename

    def fail_marker(path,target):
        if path.name=="manifest.json":
            raise OSError("synthetic manifest publication failure")
        return rename(path,target)

    if phase=="publish":
        monkeypatch.setattr(Path,"rename",fail_marker)
    out = tmp_path/"out"
    result = t3.run(inputs,out)
    if phase=="none":
        assert result["status"]=="COMPLETED"
        assert result["terrain_integration_ready"] is False
        assert set(result["outputs"])=={"artifacts/terrain.tif","artifacts/source_tile.tif","artifacts/validation.json"}
        with pytest.raises(FileExistsError):
            t3.run(inputs,out)
    else:
        assert result["status"]=="BLOCKED"
        assert not (out/"manifest.json").exists()
        assert (out/"failure.json").exists()
        assert not list(out.glob(".stage-*"))
        if phase=="publish":
            assert (out/"artifacts/terrain.tif").exists()  # Uncommitted without the manifest.
        else:
            assert not (out/"artifacts").exists()
        if phase=="tamper":
            assert "Float32 bits" in result["error"]
