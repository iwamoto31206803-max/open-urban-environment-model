"""Offline synthetic ZIP tests; no public-data acceptance claims."""
import hashlib
import io
import json
import stat
import urllib.error
import zipfile

import numpy as np
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import Affine

from ouem.acquire import tokyo_tama_dem as m
from ouem.native.terrain import accept_native_terrain, load_native_manifest, sha256_file


def raster_bytes(**overrides):
    profile = dict(driver="GTiff", width=800, height=600, count=1, dtype="float32",
                   crs="EPSG:6677", transform=Affine(0.5, 0, -23600, 0, -0.5, -40500),
                   nodata=1.701410009187828e38)
    profile.update(overrides)
    values = np.full((profile["count"], profile["height"], profile["width"]), 22, dtype=profile["dtype"])
    with MemoryFile() as mem:
        with mem.open(**profile) as dst:
            dst.write(values)
        return mem.read()


def zip_bytes(data, name=m.MEMBER, *, comment=b""):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(name, data)
        bundle.comment = comment
    return stream.getvalue()


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data)), "ETag": '"test-etag"',
                        "Last-Modified": "synthetic", "Content-Type": "application/zip"}
        if headers:
            self.headers.update(headers)

    def geturl(self):
        return m.URL


@pytest.fixture
def setup(tmp_path, monkeypatch):
    data = raster_bytes()
    monkeypatch.setattr(m, "TIFF_SHA256", hashlib.sha256(data).hexdigest())
    def serve(payload=None, headers=None, response=None):
        payload = zip_bytes(data) if payload is None else payload
        def opener(url, timeout):
            assert url == m.URL
            assert timeout > 0
            return response if response is not None else Response(payload, headers)
        monkeypatch.setattr(m.urllib.request, "urlopen", opener)
    serve()
    return tmp_path / "tokyo_tama_dem_050m" / "run", data, serve


def failed_only(out):
    assert not (out / "09LD3451.zip").exists()
    assert not (out / m.MEMBER).exists()
    assert not (out / "acquisition-manifest.json").exists()
    assert not list(out.glob(".staging-*"))
    record = json.loads((out / "acquisition-failed.json").read_text(encoding="utf-8"))
    assert record["status"] == "FAILED"
    return record


def test_acquire_and_native_round_trip(setup, tmp_path):
    out, data, _ = setup
    historical = tmp_path / "historical.tif"
    historical.write_bytes(b"old artifact")
    record = m.acquire(out)
    assert record["status"] == "COMPLETED"
    assert (out / m.MEMBER).read_bytes() == data
    assert record["tiff"]["sha256"] == hashlib.sha256(data).hexdigest()
    assert record["archive"]["sha256"] == sha256_file(out / "09LD3451.zip")
    assert record["source"]["vertical_reference"]["status"] == "source-declared"
    assert record["http"]["acquired_at"] and record["http"]["etag"]
    assert record["implementation_start"] == record["implementation_end"]
    assert record["implementation_start"]["module_sha256"]
    saved = json.loads((out / "acquisition-manifest.json").read_text(encoding="utf-8"))
    assert saved == record
    native = tmp_path / "native.json"
    accepted = accept_native_terrain(out / m.MEMBER, native,
        provider=record["provider"], source_dataset=record["dataset"],
        vertical_reference_status="source-declared", vertical_reference=m.VERTICAL_NAME,
        vertical_reference_source=m.VERTICAL_SOURCE)
    assert load_native_manifest(native) == accepted
    assert accepted.source_sha256 == record["tiff"]["sha256"]
    assert (out / m.MEMBER).read_bytes() == data
    assert historical.read_bytes() == b"old artifact"
    assert not list(out.glob(".staging-*"))


def test_hash_mismatch_is_candidate_not_accepted(setup, monkeypatch):
    out, _, _ = setup
    monkeypatch.setattr(m, "TIFF_SHA256", "0" * 64)
    with pytest.raises(m.TerrainAcquisitionError, match="different-version candidate"):
        m.acquire(out)
    record = failed_only(out)
    assert record["candidate_revision"] is True
    assert record["tiff"]["sha256"] != record["baseline"]["tiff_sha256"]


def test_zip_repack_is_recorded_not_mistaken_for_tiff_revision(setup):
    out, data, serve = setup
    serve(zip_bytes(data, comment=b"repacked unchanged TIFF"))
    record = m.acquire(out)
    assert record["archive"]["matches_survey_zip"] is False
    assert record["status"] == "COMPLETED"


@pytest.mark.parametrize("name", ["../09LD3451.tif", "/09LD3451.tif", "C:/09LD3451.tif",
    "..\\09LD3451.tif", "sub/09LD3451.tif", "09LD3451.tif:stream", "other.tif"])
def test_unsafe_or_unexpected_zip_member(setup, name):
    out, data, serve = setup
    serve(zip_bytes(data, name))
    with pytest.raises(m.TerrainAcquisitionError, match="Unsafe or unexpected"):
        m.acquire(out)
    failed_only(out)


def test_duplicate_member_rejected(setup):
    out, data, serve = setup
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr(m.MEMBER, data)
        z.writestr("extra.txt", b"not allowed")
    serve(stream.getvalue())
    with pytest.raises(m.TerrainAcquisitionError, match="exactly"):
        m.acquire(out)
    failed_only(out)


def test_symlink_member_rejected(setup):
    out, _, serve = setup
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        member = zipfile.ZipInfo(m.MEMBER)
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(member, b"../target")
    serve(stream.getvalue())
    with pytest.raises(m.TerrainAcquisitionError, match="Unsafe"):
        m.acquire(out)
    failed_only(out)


@pytest.mark.parametrize("corrupt_crc", [False, True])
def test_invalid_zip_and_crc(setup, corrupt_crc):
    out, _, serve = setup
    if corrupt_crc:
        s = io.BytesIO()
        with zipfile.ZipFile(s, "w", zipfile.ZIP_STORED) as z:
            z.writestr(m.MEMBER, b"unique-payload")
        payload = s.getvalue().replace(b"unique-payload", b"unique-damaged")
    else:
        payload = b"not a zip"
    serve(payload)
    with pytest.raises(m.TerrainAcquisitionError, match="File is not a zip|Bad CRC"):
        m.acquire(out)
    failed_only(out)


def test_expanded_limit(setup):
    out, _, serve = setup
    serve(zip_bytes(b"x" * (m.MAX_TIFF_BYTES + 1)))
    with pytest.raises(m.TerrainAcquisitionError, match="expanded byte limit"):
        m.acquire(out)
    failed_only(out)


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "99999999"}, {"Content-Length": None}])
def test_download_limit(setup, headers):
    out, _, serve = setup
    serve(b"x" * 100, headers)
    with pytest.raises(m.TerrainAcquisitionError, match="byte limit"):
        m.acquire(out, max_bytes=10)
    failed_only(out)


def test_truncated_download(setup):
    out, _, serve = setup
    serve(b"small", {"Content-Length": "50"})
    with pytest.raises(m.TerrainAcquisitionError, match="Truncated"):
        m.acquire(out)
    failed_only(out)


@pytest.mark.parametrize("during_read", [False, True])
def test_network_failure(setup, monkeypatch, during_read):
    out, _, serve = setup
    if during_read:
        class Broken(Response):
            def read(self, size):
                raise TimeoutError("connection stalled")
        serve(response=Broken(b"zip"))
    else:
        def broken(*args, **kwargs):
            raise urllib.error.URLError("no network")
        monkeypatch.setattr(m.urllib.request, "urlopen", broken)
    with pytest.raises(m.TerrainAcquisitionError):
        m.acquire(out)
    failed_only(out)


def test_deadline(setup, monkeypatch):
    out, _, _ = setup
    ticks = iter([0, 61])
    monkeypatch.setattr(m.time, "monotonic", lambda: next(ticks))
    with pytest.raises(m.TerrainAcquisitionError, match="deadline"):
        m.acquire(out)
    failed_only(out)


@pytest.mark.parametrize("overrides", [dict(crs="EPSG:3857"), dict(width=799),
    dict(transform=Affine(1, 0, -23600, 0, -1, -40500)), dict(nodata=-9999),
    dict(dtype="float64"), dict(count=2), dict(nodata=None)])
def test_metadata_gate(setup, monkeypatch, overrides):
    out, _, serve = setup
    data = raster_bytes(**overrides)
    monkeypatch.setattr(m, "TIFF_SHA256", hashlib.sha256(data).hexdigest())
    serve(zip_bytes(data))
    with pytest.raises(m.TerrainAcquisitionError):
        m.acquire(out)
    failed_only(out)


@pytest.mark.parametrize("empty", [False, True])
def test_existing_directory_untouched(setup, empty, monkeypatch):
    out, _, _ = setup
    out.mkdir(parents=True)
    if not empty:
        (out / m.MEMBER).write_bytes(b"keep")
    def forbidden(*args, **kwargs):
        pytest.fail("Must refuse before accessing network")
    monkeypatch.setattr(m.urllib.request, "urlopen", forbidden)
    with pytest.raises(FileExistsError):
        m.acquire(out)
    assert sorted(p.name for p in out.iterdir()) == ([] if empty else [m.MEMBER])
    if not empty:
        assert (out / m.MEMBER).read_bytes() == b"keep"


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_publication_failure_rolls_back(setup, monkeypatch, fail_at):
    out, _, _ = setup
    link, count = m.os.link, 0
    def fail(src, dst):
        nonlocal count
        count += 1
        if count == fail_at:
            raise PermissionError("hard link denied")
        link(src, dst)
    monkeypatch.setattr(m.os, "link", fail)
    with pytest.raises(m.TerrainAcquisitionError, match="hard link denied"):
        m.acquire(out)
    failed_only(out)


def test_concurrent_existing_file_not_removed(setup, monkeypatch):
    out, _, _ = setup
    link = m.os.link
    def race(src, dst):
        if dst.name == m.MEMBER:
            dst.write_bytes(b"someone else's file")
        link(src, dst)
    monkeypatch.setattr(m.os, "link", race)
    with pytest.raises(m.TerrainAcquisitionError):
        m.acquire(out)
    assert (out / m.MEMBER).read_bytes() == b"someone else's file"
    assert not (out / "09LD3451.zip").exists()
    assert not (out / "acquisition-manifest.json").exists()


def test_code_or_worktree_change_blocks_publication(setup, monkeypatch):
    out, _, _ = setup
    identities = iter([{"module_sha256": "a"}, {"module_sha256": "b"}])
    monkeypatch.setattr(m, "identity", lambda: next(identities))
    with pytest.raises(m.TerrainAcquisitionError, match="worktree changed"):
        m.acquire(out)
    failed_only(out)


def test_rollback_denial_is_reported_and_other_links_still_removed(setup, monkeypatch):
    out, _, _ = setup
    link, unlink = m.os.link, m.Path.unlink
    def fail_manifest(src, dst):
        if dst.name == "acquisition-manifest.json":
            raise OSError("publication failed")
        link(src, dst)
    def deny_one(path, *args, **kwargs):
        if path == out / m.MEMBER:
            raise PermissionError("rollback denied")
        return unlink(path, *args, **kwargs)
    monkeypatch.setattr(m.os, "link", fail_manifest)
    monkeypatch.setattr(m.Path, "unlink", deny_one)
    with pytest.raises(m.TerrainAcquisitionError, match="retained paths") as error:
        m.acquire(out)
    assert isinstance(error.value.__cause__, OSError)
    record = json.loads((out / "acquisition-failed.json").read_text(encoding="utf-8"))
    assert record["status"] == "FAILED"
    assert record["retained_final_paths"] == [str(out / m.MEMBER)]
    assert not (out / "09LD3451.zip").exists()
    assert not (out / "acquisition-manifest.json").exists()
    # Restore permission simulation so pytest can dispose its synthetic fixture.
    monkeypatch.setattr(m.Path, "unlink", unlink)


def test_validation_failure_never_publishes_raw(setup, monkeypatch):
    out, _, _ = setup
    def invalid(path):
        raise m.TerrainAcquisitionError("inspection failed")
    monkeypatch.setattr(m, "validate_original", invalid)
    with pytest.raises(m.TerrainAcquisitionError, match="inspection failed"):
        m.acquire(out)
    failed_only(out)


def test_unexpected_redirect_rejected(setup):
    out, _, serve = setup
    class Redirect(Response):
        def geturl(self):
            return "https://other.example/data"
    serve(response=Redirect(b"not requested"))
    with pytest.raises(m.TerrainAcquisitionError, match="redirect"):
        m.acquire(out)
    failed_only(out)


def test_refuse_historical_tree(tmp_path):
    with pytest.raises(m.TerrainAcquisitionError, match="historical"):
        m.acquire(tmp_path / "tokyo_23ku_dem_050m" / "new")


@pytest.mark.parametrize("timeout,limit", [(0, 10), (float('nan'), 10), (60, 0)])
def test_invalid_limits_before_creating_directory(tmp_path, timeout, limit):
    out = tmp_path / "new"
    with pytest.raises(m.TerrainAcquisitionError):
        m.acquire(out, timeout=timeout, max_bytes=limit)
    assert not out.exists()


def test_cli_failure_is_nonzero(setup, capsys):
    out, _, serve = setup
    serve(b"invalid")
    assert m.main(["--raw-dir", str(out)]) == 2
    assert "FAILED" in capsys.readouterr().err
