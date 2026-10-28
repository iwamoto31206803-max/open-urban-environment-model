import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ouem import real_komae_source_h as k
from ouem.native.building.source_h_geometry import GeometryValidationError


@pytest.mark.parametrize('partial,nodata', [(False, False), (True, False), (False, True)])
def test_diagnostic_ground_and_coverage(tmp_path, monkeypatch, partial, nodata):
    terrain = tmp_path/'terrain.tif'
    grid = np.full((4, 4), 10, dtype='float32')
    if nodata: grid[1, 1] = -9999
    with rasterio.open(terrain, 'w', driver='GTiff', height=4, width=4, count=1,
                       dtype='float32', crs='EPSG:6677', transform=from_origin(0, 4, 1, 1), nodata=-9999) as ds:
        ds.write(grid, 1)
    terrain.with_suffix('.tif.manifest.json').write_text(json.dumps(dict(
        standard=dict(sha256=k.digest(terrain)), vertical_reference=dict(status='source-declared',
        name='T.P. (Tokyo Peil / Tokyo Bay mean sea level)'))))
    left = -1 if partial else 1
    tree = ('Polygon', (((left, 1, 10), (3, 1, 20), (3, 3, 20), (left, 3, 10), (left, 1, 10)),))
    monkeypatch.setattr(k, 'read_standard', lambda *a: {'authored': (tree, None, None)})
    if nodata:
        with pytest.raises(GeometryValidationError, match='NoData'): k.compare_terrain(Path('unused'), terrain)
    else:
        result = k.compare_terrain(Path('unused'), terrain)
        row = result['buildings'][0]
        assert row['top_minus_dem_mean'] == 10 and row['bottom_minus_dem_mean'] == 0
        assert row['complete_coverage'] is not partial
        assert row['flags'] == (['PARTIAL_DEM_COVERAGE'] if partial else [])


def test_distribution_rejects_nonfinite():
    with pytest.raises(GeometryValidationError): k.distribution([float('nan')])


def test_runner_keeps_zip_layout_and_passes_explicit_config(tmp_path, monkeypatch):
    archive = tmp_path/'raw.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('codelists/', '')
        z.writestr('codelists/example.xml', '<list/>')
        for name in k.MEMBERS: z.writestr('udx/bldg/'+name, '<synthetic/>')
    cli = tmp_path/'cli.exe'
    cli.write_bytes(b'authored-placeholder')
    monkeypatch.setattr(k, 'CLI_SHA', k.digest(cli))
    terrain = tmp_path/'terrain.tif'
    terrain.write_bytes(b'authored-placeholder')
    terrain.with_suffix('.tif.manifest.json').write_text('{}')
    area = tmp_path/'area.yaml'
    area.write_text('synthetic')
    run_dir = tmp_path/'new-run'
    def converter(argv, **kwargs):
        assert (run_dir/'extracted/codelists/example.xml').exists()
        assert all((run_dir/'extracted/udx/bldg'/name).exists() for name in k.MEMBERS)
        Path(argv[argv.index('--output')+1]).write_bytes(b'placeholder')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(k.subprocess, 'run', converter)
    monkeypatch.setattr(k.platform, 'platform', lambda: 'synthetic-test-runtime')
    monkeypatch.setattr(k, 'ingest_source_h', lambda *a, **kw: {'manifest': str(run_dir/'native/native.gpkg.manifest.json')})
    monkeypatch.setattr(k, 'standardize_source_h', lambda **kw: {'manifest': str(run_dir/'standard/standard.gpkg.manifest.json'), 'output': str(run_dir/'standard/standard.gpkg')})
    def consumer(*args, **kw):
        assert kw['study_area_config'] == area.resolve()
        return dict(technical_validation='PASS', feature_count=2, vertex_count=20, issues=[] )
    monkeypatch.setattr(k, 'validate_source_h_standard', consumer)
    monkeypatch.setattr(k, 'compare_terrain', lambda *a: {'synthetic': True})
    monkeypatch.chdir(tmp_path)
    result = k.run(SimpleNamespace(artifact_root=tmp_path, run_dir=run_dir, zip=archive,
                                  converter=cli, terrain=terrain, study_area=Path('area.yaml')))
    assert result['status'] == 'COMPLETED' and result['input_unchanged']
    assert 'Standard buildings: 2' in (run_dir/'RESULTS.md').read_text()
    with pytest.raises(FileExistsError):
        k.run(SimpleNamespace(artifact_root=tmp_path, run_dir=run_dir, zip=archive,
                             converter=cli, terrain=terrain, study_area=area))
