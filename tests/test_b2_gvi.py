"""Small authored saved-B1 handoff, genuine CPU API and geographic roundtrips."""
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from pyproj import Transformer

from ouem import b2_gvi as m
from ouem.native.building.source_h_geometry import GeometryValidationError
from test_gis_visualization import authored_run, inventory, ref, save


def b1_run(tmp_path):
    root = authored_run(tmp_path, shape=(8, 10))
    shape = (8, 10, 9)
    current = np.zeros(shape, np.int8)
    current[:, :, 0] = 1
    current[0, 0, :3] = -3
    current[5, 2:8, 2:5] = -2
    valid = np.ones(shape[:2], bool)
    valid[0, 0] = False
    roi = np.zeros(shape[:2], bool)
    roi[2:6, 2:8] = True
    arrays = dict(current_voxels=current, no_canopy_voxels=np.where(current == -2, 0, current).astype('int8'),
                  tree_mask=current == -2, observer_index_k=np.full(shape[:2], 2, dtype='int64'),
                  canopy_missing=np.zeros(shape[:2], bool), canopy_outside=np.zeros(shape[:2], bool))
    for name, array in arrays.items():
        np.save(root/'solar'/(name+'.npy'), array)
    for name in ('terrain_H', 'effective_ground_H', 'effective_dem'):
        np.save(root/'voxel'/(name+'.npy'), np.full(shape[:2], 10.))
    lon, lat = (np.load(root/'voxel'/('centre_'+s+'.npy')) for s in ('lon', 'lat'))
    x,y = Transformer.from_crs(4326, 6677, always_xy=True).transform(lon, lat)
    bounds = [float(x[roi].min())-.1, float(y[roi].min())-.1,
              float(x[roi].max())+.1, float(y[roi].max())+.1]
    cfg = json.loads((root/'run-config.json').read_text())
    cfg['analysis_extent'] = bounds
    # Synthetic upstream identities; no real-data acquisition.
    for key, identity in dict(cfg['inputs'], study_area=cfg['study_area']).items():
        path = tmp_path/identity['path']
        path.write_text(key, encoding='utf-8')
        identity['sha256'] = m.sha(path)
    save(root/'run-config.json', cfg)
    save(root/'submitted-config.json', dict(cfg, artifact_root='.'))
    grid = json.loads((root/'solar/grid.json').read_text())
    grid.update(projected_evaluation_ROI_bounds=bounds,
                projected_domain_bounds=[bounds[0]-2,bounds[1]-2,bounds[2]+2,bounds[3]+2],
                rectangle_vertices_lonlat=[[float(lon.min()),float(lat.min())], [float(lon.max()),float(lat.max())]])
    for stage in ('voxel','solar'):
        save(root/stage/'grid.json', grid)
        np.save(root/stage/'roi_mask.npy', roi)
        with rasterio.open(root/'solar/roi_mask.tif') as ds:
            affine = ds.transform
        m.raster(root/stage/'roi_mask.tif', roi, affine)
    record = dict(schema=cfg['schema'],path='runs/authored/run-config.json',sha256=m.sha(root/'run-config.json'),
                  artifact_root=str(tmp_path), run_root=str(root),settings=cfg,computation_reference_bounds=grid['projected_domain_bounds'])
    watches = {key:dict(path='runs/authored/'+name, **ref(root/name)) for key,name in
               [('run_config','run-config.json'),('submitted_config','submitted-config.json')]}
    for stage in ('voxel','solar'):
        report = json.loads((root/stage/'report.json').read_text())
        report['run_config'] = record
        report['input_artifacts'].update(watches)
        if stage == 'voxel':
            report['model']['grid'] = grid
        else:
            model_sha = m.sha(root/'voxel/report.json')
            report['preflight']['source_model_report_sha256'] = model_sha
            report['input_artifacts']['PR98_report'] = dict(path='runs/authored/voxel/report.json', **ref(root/'voxel/report.json'))
        report['outputs'] = {p.name:ref(p) for p in (root/stage).iterdir() if p.name != 'report.json'}
        save(root/stage/'report.json', report)
    save(root/'voxel-receipt.json', dict(schema='ouem-e2e-voxel-receipt/v0.1',run_config_sha256=record['sha256'],
                                       report_sha256=m.sha(root/'voxel/report.json')))
    return root


def test_saved_handoff_full_domain_and_roi_provenance(tmp_path):
    root = b1_run(tmp_path)
    before = inventory(root)
    loaded = m.load_run(root)
    assert loaded['current'].shape == (8,10,9)
    assert not loaded['current'].flags.writeable
    assert loaded['preflight']['roi_uv_bounds_exclusive'] == [2,6,2,8]
    assert loaded['preflight']['evaluation_cells'] == 24
    assert loaded['preflight']['observers_in_TREE'] == 6
    assert m.provenance(loaded)['files']['output:solar/current_voxels.npy']['sha256'] == m.sha(root/'solar/current_voxels.npy')
    m.unchanged(loaded)
    assert inventory(root) == before


@pytest.mark.parametrize('target', ['solar/current_voxels.npy','solar/tree_mask.npy','solar/grid.json',
                                    'voxel-receipt.json','run-config.json'])
def test_tampered_input_fails(tmp_path, target):
    root = b1_run(tmp_path)
    with (root/target).open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises((GeometryValidationError, ValueError)):
        m.load_run(root)


def test_changed_input_after_load_is_detected(tmp_path):
    root = b1_run(tmp_path)
    loaded = m.load_run(root)
    with (root/'solar/current_voxels.npy').open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(GeometryValidationError):
        m.unchanged(loaded)


def test_real_public_api_fixed_settings_and_cleanup(monkeypatch):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from voxcity.simulator.visibility import view
    original = view.get_view_index
    calls = []
    def spy(scene, **kwargs):
        calls.append((scene.voxels.classes.shape, kwargs))
        return original(scene, **kwargs)
    monkeypatch.setattr(view, 'get_view_index', spy)
    voxels = np.zeros((5,7,5), np.int8)
    voxels[:,:,0] = 1
    voxels[3,:,2] = -2
    voxels.flags.writeable = False
    before = voxels.copy()
    retained = plt.figure()
    figures = set(plt.get_fignums())
    try:
        result, timing = m.calculate(voxels, {'rectangle_vertices_lonlat':[[139.,35.],[139.01,35.01]]})
        m.check_result(result, np.ones((5,7),bool))
        assert set(plt.get_fignums()) == figures
    finally:
        plt.close(retained)
    assert calls == [((5,7,5), dict(m.SETTINGS, num_threads=2))]
    assert calls[0][1]['fast_path'] is False
    assert calls[0][1]['hit_values'] == (-2,)
    assert calls[0][1]['N_azimuth']*calls[0][1]['N_elevation'] == 2400
    assert timing['sampled_peak_working_set_bytes'] > 0
    assert timing['wall_seconds'] > 0 and timing['process_cpu_seconds'] >= 0
    np.testing.assert_array_equal(voxels, before)


def test_full_compute_then_crop_and_raster_roundtrip(tmp_path, monkeypatch):
    root = b1_run(tmp_path)
    before = inventory(root)
    seen = []
    def compute(voxels, grid, threads):
        seen.append(voxels.shape)
        # Unique u/v values prove flips/crops, including a finite zero.
        values = np.arange(80, dtype=float).reshape(8,10)/100
        values[0,0] = np.nan
        values[0,1] = 0
        return values, {'wall_seconds':1., 'process_cpu_seconds':1.}
    monkeypatch.setattr(m, 'calculate', compute)
    loaded = m.load_run(root)
    receipt = tmp_path/'benchmark.json'
    save(receipt, dict(status='BENCHMARK_COMPLETED', feasible=True, source_run=str(root),
                       settings=json.loads(json.dumps(dict(m.SETTINGS, num_threads=2))),
                       current_sha256=m.sha(root/'solar/current_voxels.npy')))
    out = tmp_path/'result'
    result = m.execute(root, out, benchmark_report=receipt)
    assert seen == [(8,10,9)]  # Full context delivered to API, never ROI crop.
    assert result['status'] == 'COMPLETED' and result['input_immutability'] == 'PASS'
    assert result['settings']['mode'] is None
    assert result['settings']['fast_path'] is False
    assert result['metric'] == 'CPU weighted first-TREE view index'
    assert result['benchmark']['sha256'] == m.sha(receipt)
    values = np.load(out/'view_index.npy')
    np.testing.assert_array_equal(np.load(out/'evaluation_view_index.npy'), values[2:6,2:8])
    with rasterio.open(out/'view_index.tif') as full, rasterio.open(out/'evaluation_view_index.tif') as crop:
        assert full.crs.to_epsg() == crop.crs.to_epsg() == 4326
        assert full.shape == (8,10) and crop.shape == (4,6)
        assert full.transform == loaded['affine']
        assert crop.transform == full.transform @ Affine.translation(2,2)
        np.testing.assert_array_equal(full.read(1), values[::-1])
        np.testing.assert_array_equal(crop.read(1), values[2:6,2:8][::-1])
        assert full.read_masks(1)[7,0] == 0 and full.read_masks(1)[7,1] == 255
        assert np.isnan(full.nodata)
        # Independent saved centres versus GIS pixel centres at corners/interior.
        lon = np.load(root/'voxel/centre_lon.npy')
        lat = np.load(root/'voxel/centre_lat.npy')
        for u,v in ((0,0),(3,4),(7,9)):
            assert full.xy(7-u,v) == pytest.approx((lon[u,v],lat[u,v]), abs=1e-12, rel=0)
    assert result['outputs']['view_index.tif']['sha256'] == m.sha(out/'view_index.tif')
    assert m.sha(out/'settings.json') == result['settings_sha256']
    assert inventory(root) == before


@pytest.mark.parametrize('fault', ['no-receipt','wrong-source','wrong-settings','wrong-hash','infeasible'])
def test_benchmark_gate(tmp_path, fault):
    root = b1_run(tmp_path)
    receipt = dict(status='BENCHMARK_COMPLETED', feasible=True, source_run=str(root),
                   settings=json.loads(json.dumps(dict(m.SETTINGS, num_threads=2))),
                   current_sha256=m.sha(root/'solar/current_voxels.npy'))
    if fault == 'wrong-source': receipt['source_run'] = 'another'
    if fault == 'wrong-settings': receipt['settings']['N_azimuth'] = 60
    if fault == 'wrong-hash': receipt['current_sha256'] = '0'*64
    if fault == 'infeasible': receipt['feasible'] = False
    save(tmp_path/'benchmark.json', receipt)
    out = tmp_path/'result'
    with pytest.raises(GeometryValidationError):
        m.execute(root, out, benchmark_report=None if fault == 'no-receipt' else tmp_path/'benchmark.json')
    assert not out.exists()


def test_observer_capacity_and_nodata_are_not_silently_repaired():
    voxels = np.zeros((2,3,2),np.int8)
    voxels[:,:,0] = 1
    with pytest.raises(GeometryValidationError, match='capacity'):
        m.observers(voxels)
    with pytest.raises(GeometryValidationError, match='mask'):
        m.check_result(np.zeros((2,3)), np.zeros((2,3),bool))
    with pytest.raises(GeometryValidationError, match='range'):
        m.check_result(np.full((2,3), 1.01), np.ones((2,3),bool))


def test_output_overlap_rejected(tmp_path):
    root = b1_run(tmp_path)
    with pytest.raises(GeometryValidationError, match='outside B1'):
        m.execute(root, root/'new')
    assert not (root/'new').exists()
