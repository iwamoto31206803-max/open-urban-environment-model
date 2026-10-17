"""Synthetic post-CRS Adapter behavior; no Komae real data or acceptance."""
import json
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pytest
import shapely
from shapely.geometry import GeometryCollection, Polygon, mapping, shape

from ouem.adapters import voxcity as adapter
from ouem import komae_crs_repair_evaluation as evaluation
from tests.test_komae_crs_repair_evaluation import frame as synthetic_frame


def _source():
    return synthetic_frame(count=2)


def _projected(source):
    footprints = {row.ouem_id: adapter.build_normalized_footprint(row.geometry, row.ouem_id)
                  for row in source.itertuples()}
    normalized = adapter._set_normalized_footprints(source, footprints)
    return adapter._to_voxcity_building_crs(normalized), footprints


def test_valid_passthrough_preserves_exact_geometry_crs_and_attributes():
    transformed, footprints = _projected(_source())
    valid = transformed.iloc[[1]].copy()
    before = valid.geometry.iloc[0].wkb
    valid['height'] = 12.5
    valid['min_height'] = 0.0
    result, diagnostics = adapter._repair_post_crs(valid, footprints)
    assert result is valid and diagnostics == {}
    assert result.crs.to_epsg() == 4326
    assert result.geometry.iloc[0].wkb == before
    assert result[['ouem_id', 'height', 'min_height']].to_dict('records') == [
        {'ouem_id': 'oub-001', 'height': 12.5, 'min_height': 0.0}]


def test_invalid_post_crs_geometry_matches_pr42_candidate_a_and_projected_metrics():
    transformed, footprints = _projected(_source())
    assert not transformed.geometry.iloc[0].is_valid
    healthy_wkb = transformed.geometry.iloc[1].wkb
    repaired, diagnostics = adapter._repair_post_crs(transformed, footprints)
    expected, operation = evaluation.candidate_geometry(
        footprints['oub-000'][0], transformed.geometry.iloc[0], 'A', None)
    assert operation.startswith('make_valid after CRS')
    assert repaired.geometry.iloc[0].wkb == expected.wkb
    assert repaired.geometry.iloc[0].geom_type == 'MultiPolygon'
    assert repaired.geometry.iloc[0].is_valid
    assert repaired.geometry.iloc[1].wkb == healthy_wkb
    assert list(diagnostics) == ['oub-000']
    record = diagnostics['oub-000']
    assert record['before']['geometry_type'] == 'Polygon'
    assert record['before']['valid'] is False
    assert record['after']['geometry_type'] == 'MultiPolygon'
    assert record['after']['valid'] is True
    assert record['after']['polygons'] > record['before']['polygons']
    assert all(record['after'][key] > 0 for key in ('rings', 'vertices'))
    metrics = record['projected_comparison']
    assert metrics['crs'] == 'EPSG:6677'
    assert metrics['source_footprint_area_m2'] == pytest.approx(footprints['oub-000'][0].area)
    assert metrics['after_area_m2'] - metrics['source_footprint_area_m2'] == pytest.approx(
        metrics['area_difference_vs_source_m2'])
    assert metrics['symmetric_difference_vs_source_m2'] >= 0
    assert metrics['hausdorff_vs_source_m'] >= 0
    assert json.loads(adapter.canonical_json(diagnostics)) == diagnostics


def test_geometry_collection_and_nonpolygonal_candidate_are_rejected(monkeypatch):
    transformed, footprints = _projected(_source())
    original = shapely.make_valid
    candidate = original(transformed.geometry.iloc[0])
    from shapely.geometry import LineString
    line = LineString([(139.0, 35.0), (139.001, 35.001)])
    for unsupported in (GeometryCollection([candidate, line]), line):
        monkeypatch.setattr(shapely, 'make_valid', lambda _geometry: unsupported)
        with pytest.raises(adapter.VoxCityAdapterError, match='unsupported.*GeometryCollection|unsupported.*LineString'):
            adapter._repair_post_crs(transformed, footprints)
    assert not transformed.geometry.iloc[0].is_valid


def _fake_voxcity(monkeypatch):
    parent = ModuleType('voxcity')
    parent.__path__ = []
    parent.__version__ = adapter.VOXCITY_VERSION
    geoprocessor = ModuleType('voxcity.geoprocessor')
    geoprocessor.__path__ = []
    raster = ModuleType('voxcity.geoprocessor.raster')
    observed = []
    def building_grid(buildings, meshsize, rectangle, *, overlapping_footprint):
        assert overlapping_footprint is adapter.VOXCITY_PRECISE_RASTERIZATION
        assert [int(v) for v in buildings.id] == [1, 2]
        assert all(geometry.is_valid for geometry in buildings.geometry)
        observed.append([geometry.wkb for geometry in buildings.geometry])
        ids = np.array([[1, 2], [1, 2]], dtype=int)
        return None, None, ids
    raster.create_dem_grid_from_geotiff_polygon = lambda *args, **kwargs: np.full((2, 2), 10.0)
    raster.create_building_height_grid_from_gdf_polygon = building_grid
    raster.process_grid = lambda ids, dem: dem
    for name, module in [('voxcity', parent), ('voxcity.geoprocessor', geoprocessor),
                         ('voxcity.geoprocessor.raster', raster)]:
        monkeypatch.setitem(sys.modules, name, module)
    return observed


def test_production_worker_manifest_and_serialization_regression(tmp_path, monkeypatch):
    assert adapter.ADAPTER_VERSION == '0.1.1'
    observed = _fake_voxcity(monkeypatch)
    source = _source()
    transformed, footprints = _projected(source)
    expected, _ = evaluation.candidate_geometry(
        footprints['oub-000'][0], transformed.geometry.iloc[0], 'A', None)
    building = tmp_path/'standard.gpkg'
    source.to_file(building, layer='building')
    terrain = tmp_path/'standard.tif'
    terrain.write_bytes(b'synthetic DEM: mocked grid reader')
    Path(str(building) + '.manifest.json').write_bytes(adapter.canonical_json({
        'schema': 'ouem-standard-building-manifest/v0.1',
        'z_reference': 'absolute T.P. elevation in metres'}))
    Path(str(terrain) + '.manifest.json').write_bytes(adapter.canonical_json({
        'schema': 'ouem-standard-terrain-manifest/v0.1',
        'vertical_reference': {'status': 'verified', 'name': 'T.P.'}}))
    first = adapter.adapt_standard_to_voxcity(building, terrain, tmp_path/'first.json', meshsize=1)
    second = adapter.adapt_standard_to_voxcity(building, terrain, tmp_path/'second.json', meshsize=1)
    assert Path(first.output).read_bytes() == Path(second.output).read_bytes()
    manifest = json.loads(Path(first.manifest).read_text(encoding='utf-8'))
    geojson = json.loads(Path(first.output).read_text(encoding='utf-8'))
    assert len(observed) == 4 and observed[0] == observed[1] == observed[2] == observed[3]
    assert observed[0][0] == expected.wkb
    assert observed[0][1] == transformed.geometry.iloc[1].wkb
    assert manifest['post_crs_repair']['affected_ouem_ids'] == ['oub-000']
    assert manifest['post_crs_repair']['repaired_count'] == 1
    assert manifest['voxcity']['commit'] == adapter.VOXCITY_COMMIT
    assert len(manifest['buildings']) == len(geojson['features']) == 2
    assert 'post_crs_repair' in manifest['buildings'][0]
    assert 'post_crs_repair' not in manifest['buildings'][1]
    for number, feature in enumerate(geojson['features'], 1):
        props = feature['properties']
        assert props['ouem_id'] == f'oub-{number-1:03}'
        assert props['id'] == props['voxcity_id'] == number
        assert props['height'] == pytest.approx(10.0)
        assert props['min_height'] == 0.0
        assert 'post_crs_repair' not in props
        assert shape(feature['geometry']).is_valid
    expected_serialized = shape(json.loads(adapter.canonical_json(mapping(expected))))
    assert shape(geojson['features'][0]['geometry']).wkb == expected_serialized.wkb
    assert shape(geojson['features'][1]['geometry']).wkb == transformed.geometry.iloc[1].wkb
