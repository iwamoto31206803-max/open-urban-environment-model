"""Authored samples and real public engine calls; no real-data acceptance."""
import json

import numpy as np
from pyproj import Transformer
import pytest
import rasterio
from rasterio.transform import from_origin

from ouem import real_komae_voxel as m
from ouem.native.building.source_h_geometry import GeometryValidationError


def terrain(path, values, bounds):
    xmin, ymin, xmax, ymax = bounds
    with rasterio.open(path, 'w', driver='GTiff', count=1, width=values.shape[1], height=values.shape[0],
                       dtype='float32', crs=6677, nodata=-9999.,
                       transform=from_origin(xmin, ymax, (xmax-xmin)/values.shape[1], (ymax-ymin)/values.shape[0])) as ds:
        ds.write(values.astype('float32'), 1)


@pytest.mark.parametrize('case', ['valid', 'nodata', 'outside'])
def test_cell_centres_crs_orientation_and_dem_boundaries(tmp_path, case):
    path = tmp_path/'dem.tif'
    bounds = (-23352, -40792, -23348, -40788)
    values = np.arange(16).reshape(4, 4).astype('float32') + 10
    if case == 'nodata': values[0, 0] = -9999
    terrain(path, values, bounds)
    x = np.array([[-23351.5, -23348.5], [-23351.5, -23348.5]])
    y = np.array([[-40788.5, -40788.5], [-40791.5, -40791.5]])
    if case == 'outside': x[0, 0] = bounds[0]-1
    lon, lat = Transformer.from_crs(6677, 4326, always_xy=True).transform(x, y)
    if case != 'valid':
        with pytest.raises(GeometryValidationError, match='coverage|NoData'): m.sample_dem(path, lon, lat)
    else:
        sampled, actual_x, actual_y = m.sample_dem(path, lon, lat)
        assert np.array_equal(sampled, [[10, 13], [22, 25]])
        assert np.allclose(actual_x, x, atol=1e-7, rtol=0)
        assert np.allclose(actual_y, y, atol=1e-7, rtol=0)


def test_effective_d0_is_not_assumed_raw_minimum():
    ids = np.array([[1, 1], [0, 0]])
    dem = np.array([[10., 20.], [12., 14.]])
    conditioned, d0 = m.effective_ground(ids, dem)
    assert np.array_equal(conditioned, [[15., 15.], [12., 14.]])
    assert d0 == 12 and dem.min() == 10


def test_actual_engine_rounding_just_below_float32_half_tie():
    from voxcity.generator.voxelizer import Voxelizer, NUMBA_AVAILABLE
    dem = np.array([[0., float(np.nextafter(np.float32(.5), np.float32(0)))]])
    ids = np.array([[0, 1]])
    heights = np.array([[0., 2.]])
    segments = np.empty(ids.shape, object)
    segments[0, 0] = []; segments[0, 1] = [[0., 2.]]
    voxels = Voxelizer(1., 'Standard').generate_combined(
        heights, segments, ids, np.ones(ids.shape, dtype=int), dem,
        np.zeros(ids.shape), print_class_info=False)
    report, ground = m.audit_voxels(voxels, ids, dem, segments, dem, 0., numba=NUMBA_AVAILABLE)
    assert ground.tolist() == [[1, 1]] and report['status'] == 'PASS'


@pytest.mark.parametrize('corrupt', [False, True])
def test_scalar_ground_surface_and_building_position(corrupt):
    ids = np.array([[1, 1]])
    dem = np.array([[100., 101.2]])
    effective = dem-100
    segments = np.empty(ids.shape, object)
    segments[0, 0] = [[0., 2.]]; segments[0, 1] = [[0., 2.]]
    voxels = np.array([[[1, -3, -3, 0, 0, 0], [-1, 1, -3, -3, 0, 0]]], dtype='int8')
    if corrupt: voxels[0, 1, 2] = 0
    if corrupt:
        with pytest.raises(GeometryValidationError): m.audit_voxels(voxels, ids, dem, segments, effective, 100., numba=True)
    else:
        report, ground = m.audit_voxels(voxels, ids, dem, segments, effective, 100., numba=True)
        assert report['status'] == 'PASS' and ground.tolist() == [[1, 2]]


def box_tree(x, y, size, bottom=10., top=20.):
    def face(z):
        return 'Polygon', (((x,y,z),(x+size,y,z),(x+size,y+size,z),(x,y+size,z),(x,y,z)),)
    return 'MultiPolygon', (face(bottom), face(top))


def test_public_voxcity_sloped_grid_and_export_readback(tmp_path):
    path = tmp_path/'synthetic-dem.tif'
    values = 10+np.indices((128, 128))[0]*.005
    terrain(path, values, m.DOMAIN)
    features = {'authored_a': (box_tree(-23312, -40740, 8), None, None),
                'authored_boundary': (box_tree(m.DOMAIN[0]-2, -40750, 8), None, None)}
    arrays, meta, frame, cells = m.execute_model(features, path)
    assert arrays['voxels'].ndim == 3 and arrays['terrain_H'].shape == (128, 128)
    assert arrays['roi_mask'].sum() == 4096
    assert meta['qa']['full_array_scalar_oracle'] == meta['qa']['independent_cell_contributors'] == 'PASS'
    assert set(np.unique(arrays['building_ids'])) == {0, 1, 2}
    assert meta['qa']['source_roof_segment_max_error_m'] <= 2
    assert any(r['crosses_actual_engine_domain'] for r in meta['selected_buildings'])
    # Boundary source support remains complete: it has 8x8m area, not a clipped 6x8m.
    projected = frame.to_crs(6677)
    assert np.allclose(projected.area, 64., atol=1e-6, rtol=0)
    output = tmp_path/'output'; output.mkdir()
    m.export_outputs(output, arrays, meta, frame, cells)
    with rasterio.open(output/'terrain_H.tif') as ds:
        assert np.array_equal(ds.read(1), arrays['terrain_H'][::-1, :])
        # Check pixel-centre mapping with both indices, catching flip/transpose.
        lon, lat = ds.xy(7, 13)
        assert lon == pytest.approx(arrays['centre_lon'][-8, 13], abs=1e-12)
        assert lat == pytest.approx(arrays['centre_lat'][-8, 13], abs=1e-12)
    saved = json.loads((output/'building_segments.json').read_text())
    assert len(saved['cells']) == meta['qa']['building_columns']
    assert np.array_equal(np.load(output/'voxels.npy', allow_pickle=False), arrays['voxels'])


def test_engine_overlap_id_remapping_fails_explicitly(tmp_path):
    path = tmp_path/'dem.tif'
    terrain(path, np.full((128, 128), 10, dtype='float32'), m.DOMAIN)
    tree = box_tree(-23312, -40740, 8)
    with pytest.raises(GeometryValidationError, match='remapped'):
        m.execute_model({'authored_a': (tree, None, None), 'authored_b': (tree, None, None)}, path)
