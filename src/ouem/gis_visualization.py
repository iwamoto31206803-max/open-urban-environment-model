"""Read-only presentation of completed configured E2E runs; no model execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer
import rasterio
from affine import Affine

from ouem.consumers.source_h_standard import Watch, same_json
from ouem.native.building.source_h_geometry import require

VERSION = '0.1'
SCHEMA = 'ouem-gis-visualization/v0.1'
LAYERS = {
    'solar_current': ('Current direct irradiance', 'W/m²', 'Current'),
    'solar_no_canopy': ('No-Canopy direct irradiance', 'W/m²', 'No-Canopy'),
    'solar_difference': ('No-Canopy − Current: additional canopy attenuation', 'W/m²', 'No-Canopy − Current'),
    'shadow_categories': ('Incremental Building / canopy obstruction relationship', 'category', 'comparison'),
    'observer_valid': ('Common observers; gray excludes Building columns', 'boolean', 'common'),
    'canopy_candidate': ('Estimated positive-depth candidate; not verified TREE presence', 'boolean', 'Current'),
    'roi_mask': ('Evaluation ROI cell membership; outside remains context', 'boolean', 'common'),
}


def _extent(config):
    bounds = config['analysis_extent']
    require(type(bounds) is list and len(bounds) == 4 and
            all(type(v) in (int, float) and math.isfinite(v) for v in bounds), 'config.extent', 'finite rectangle required')
    x0, y0, x1, y1 = bounds
    b = config['context_buffer_m']
    require(x0 < x1 and y0 < y1 and type(b) in (int, float) and math.isfinite(b) and b > 0,
            'config.extent', 'ordered rectangle and positive buffer required')
    # RunConfig's Extent canonicalizes coordinates/buffer to floats even when
    # the submitted JSON uses integers. Preserve its exact recorded JSON types.
    return [float(x0)-float(b), float(y0)-float(b), float(x1)+float(b), float(y1)+float(b)]


def inspect_run(root):
    """Validate saved handoff and consumed outputs, without requiring Raw/engine.

    Intentionally do not call RunConfig.load: that performs fresh upstream input
    validation and imports preparation runners. This reader validates the recorded
    v0.1 configuration identity, not new model eligibility or Consumer execution.
    """
    watch = Watch(root)
    cfg = watch.capture('config', 'run-config.json', json_data=True)
    submitted = watch.capture('submitted_config', 'submitted-config.json', json_data=True)
    require(cfg['schema'] == 'ouem-e2e-run/v0.1', 'config', 'configured v0.1 run required')
    same_json({k:v for k,v in cfg.items() if k != 'artifact_root'},
              {k:v for k,v in submitted.items() if k != 'artifact_root'}, 'config.snapshot')
    domain = _extent(cfg)
    require(type(cfg['artifact_root']) is str and bool(cfg['artifact_root'].strip()), 'config.root', 'root locator required')
    artifact_root = (watch.root/cfg['artifact_root']).resolve()
    require(watch.root.is_relative_to(artifact_root) and cfg['run_id'] == watch.root.name,
            'config.root', 'saved run location/ID mismatch')
    # Resolve without reading upstream inputs; both reports must identify this exact saved run.
    require(type(cfg['output_parent']) is str, 'config.output', 'locator required')
    require((artifact_root/cfg['output_parent']/cfg['run_id']).resolve() == watch.root,
            'config.output', 'saved output location mismatch')
    record = dict(schema=cfg['schema'], path=(watch.root/'run-config.json').relative_to(artifact_root).as_posix(),
                  sha256=watch.identities['config']['sha256'], artifact_root=str(artifact_root),
                  run_root=str(watch.root), settings=cfg, computation_reference_bounds=domain)
    receipt = watch.capture('receipt', 'voxel-receipt.json', json_data=True)
    require(set(receipt) == {'schema','run_config_sha256','report_sha256'} and
            receipt['schema'] == 'ouem-e2e-voxel-receipt/v0.1' and
            receipt['run_config_sha256'] == record['sha256'], 'receipt', 'configuration binding mismatch')
    voxel = watch.capture('voxel_report', 'voxel/report.json', receipt['report_sha256'], json_data=True)
    solar = watch.capture('solar_report', 'solar/report.json', json_data=True)
    for stage, report in (('voxel', voxel), ('solar', solar)):
        require(report['status'] == 'COMPLETED' and report['input_immutability'] == 'PASS', stage, 'incomplete run')
        same_json(report['run_config'], record, stage+'.config')
        for name, key in (('config','run_config'), ('submitted_config','submitted_config')):
            ref = report['input_artifacts'][key]
            actual = watch.identities[name]
            require(ref['sha256'] == actual['sha256'] and ref['size_bytes'] == actual['size_bytes'] and
                    ref['path'] == (watch.root/actual['path']).relative_to(artifact_root).as_posix(),
                    stage+'.config', 'saved configuration watch mismatch')
    model_sha = watch.identities['voxel_report']['sha256']
    ref = solar['input_artifacts']['PR98_report']
    require(solar['preflight']['source_model_report_sha256'] == model_sha == ref['sha256'] and
            ref['size_bytes'] == watch.identities['voxel_report']['size_bytes'] and
            ref['path'] == (watch.root/'voxel/report.json').relative_to(artifact_root).as_posix(),
            'case_pair', 'Solar references another Voxel report')
    require(voxel['consumer']['technical_validation'] == 'PASS' and
            solar['preflight']['fresh_consumer']['technical_validation'] == 'PASS', 'Consumer', 'saved validation not PASS')

    def output(stage, name, *, document=False):
        report = voxel if stage == 'voxel' else solar
        ref = report['outputs'][name]
        return watch.capture(stage+'/'+name, stage+'/'+name, ref['sha256'], ref['size_bytes'], json_data=document)

    def array(stage, name):
        return np.load(output(stage, name+'.npy'), allow_pickle=False)

    base_grid = output('voxel', 'grid.json', document=True)
    grid = output('solar', 'grid.json', document=True)
    same_json(base_grid, voxel['model']['grid'], 'voxel.grid')
    same_json({k:v for k,v in grid.items() if k not in ('shape','vertical_domain')},
              {k:v for k,v in base_grid.items() if k != 'shape'}, 'grid.XY')
    for g in (base_grid, grid):
        require(type(g['shape']) is list and len(g['shape']) == 3 and
                all(type(v) is int and v > 0 for v in g['shape']), 'grid.shape', 'positive dimensions required')
    if 'vertical_domain' in grid:
        same_json(grid['vertical_domain'], solar['tree']['vertical_domain'], 'grid.Z')
        require(grid['vertical_domain']['shared_shape'] == grid['shape'] and
                grid['vertical_domain']['base_shape'] == base_grid['shape'], 'grid.Z', 'shared/base shape mismatch')
    shape = tuple(grid['shape'][:2])
    require(shape == tuple(base_grid['shape'][:2]) and grid['shape'][2] >= base_grid['shape'][2]
            and grid['layout'] == 'uv_m/SOUTH_UP' and grid['rectangle_crs'] == 'EPSG:4326'
            and grid['projected_reference_crs'] == 'EPSG:6677' and grid['nominal_voxel_size_m'] == 1.,
            'grid', 'unsupported grid or changed base')
    require(grid['projected_evaluation_ROI_bounds'] == cfg['analysis_extent'] and
            grid['projected_domain_bounds'] == domain and grid['halo_m'] == cfg['context_buffer_m'],
            'grid.config', 'grid differs from saved extents')
    vectors = np.asarray([grid[k] for k in ('origin_lonlat','u_step_lonlat','v_step_lonlat')], dtype=float)
    require(vectors.shape == (3,2) and np.isfinite(vectors).all() and
            np.linalg.det(vectors[1:]) != 0, 'grid.affine', 'finite nondegenerate geographic basis required')
    origin, u, v = vectors
    start = origin+shape[0]*u
    affine = Affine(v[0], -u[0], start[0], v[1], -u[1], start[1])
    ii, jj = np.indices(shape)
    lon, lat = (array('voxel', 'centre_'+axis) for axis in ('lon','lat'))
    for axis, centres in enumerate((lon, lat)):
        require(centres.shape == shape and np.isfinite(centres).all() and
                np.allclose(centres, origin[axis]+(ii+.5)*u[axis]+(jj+.5)*v[axis], atol=1e-12, rtol=0),
                'grid.centres', 'saved cell centres differ from affine')
    x, y = Transformer.from_crs(4326, 6677, always_xy=True).transform(lon, lat)
    x0, y0, x1, y1 = cfg['analysis_extent']
    roi = (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
    ids = array('voxel', 'building_ids')
    require(ids.shape == shape and ids.dtype.kind in 'iu' and np.all(ids >= 0), 'building_ids', 'invalid ID grid')
    base_roi = array('voxel', 'roi_mask')
    require(base_roi.dtype == bool and np.array_equal(roi, base_roi) and roi.any(), 'ROI', 'incorrect centre mask')

    maps = {}
    for name in LAYERS:
        values = array('solar', name)
        require(values.shape == shape, name, 'wrong array dimensions')
        with rasterio.open(output('solar', name+'.tif')) as ds:
            require(ds.driver == 'GTiff' and ds.count == 1 and ds.shape == shape and
                    ds.crs is not None and ds.crs.to_epsg() == 4326 and ds.transform == affine,
                    name, 'TIFF CRS/affine/dimensions mismatch')
            expected = values[::-1, :].astype('uint8') if values.dtype == bool else values[::-1, :]
            require(np.dtype(ds.dtypes[0]) == expected.dtype and np.array_equal(ds.read(1), expected, equal_nan=True),
                    name, 'TIFF differs from saved UV array')
            nan = np.isnan(expected) if expected.dtype.kind == 'f' else np.zeros(shape, bool)
            require((ds.nodata is not None and math.isnan(ds.nodata)) if nan.any() else ds.nodata is None,
                    name, 'unexpected NoData declaration')
            require(np.array_equal(ds.read_masks(1) > 0, ~nan), name, 'unexpected TIFF validity mask')
        maps[name] = values
    valid = maps['observer_valid']
    require(valid.dtype == bool and np.array_equal(valid, ids == 0), 'observer_valid', 'common observer mask mismatch')
    require(maps['roi_mask'].dtype == bool and np.array_equal(maps['roi_mask'], roi)
            and maps['canopy_candidate'].dtype == bool, 'masks', 'boolean ROI/candidate required')
    stats = output('solar', 'statistics.json', document=True)
    same_json(stats, solar['solar'], 'statistics')
    maximum = stats['sun']['flat_horizontal_W_m2']
    require(type(maximum) in (int, float) and math.isfinite(maximum) and maximum > 0,
            'solar.range', 'positive recorded irradiance bound required')
    tolerance = stats['invariants']['tolerance_W_m2']
    require(type(tolerance) in (int, float) and tolerance == 1e-9, 'solar.tolerance', 'unsupported saved QA tolerance')
    for name in ('solar_current','solar_no_canopy','solar_difference'):
        values = maps[name]
        require(values.dtype.kind == 'f' and np.array_equal(np.isfinite(values), valid) and
                np.isnan(values[~valid]).all() and np.all(values[valid] >= -tolerance) and
                np.all(values[valid] <= maximum+tolerance), name, 'range/observer validity mismatch')
    require(np.array_equal(maps['solar_difference'], maps['solar_no_canopy']-maps['solar_current'], equal_nan=True),
            'solar_difference', 'expected No-Canopy minus Current')
    building_reduction = array('solar', 'building_solar_reduction')
    require(building_reduction.shape == shape and np.array_equal(np.isfinite(building_reduction), valid),
            'shadow_categories', 'invalid Building control')
    categories = maps['shadow_categories']
    expected = np.where(valid, (building_reduction > tolerance).astype('uint8')+2*(maps['solar_difference'] > tolerance), 4)
    require(categories.dtype.kind in 'iu' and np.array_equal(categories, expected), 'shadow_categories', 'codes 0–4 differ from controls')
    watch.unchanged()
    return watch, cfg, grid, affine, float(maximum)


def style(name, maximum):
    """Explicit display choices, never scientific thresholds or data edits."""
    if name.startswith('solar_'):
        colors = ['#ffffff','#dadaeb','#bcbddc','#807dba','#54278f'] if name == 'solar_difference' else [
            '#000004','#51127c','#b73779','#fc8961','#fcfdbf']
        stops = [dict(value=maximum*i/4, color=c, alpha=255, label=f'{maximum*i/4:.2f} W/m²') for i,c in enumerate(colors)]
        return dict(renderer='singlebandpseudocolor', band=1, interpolation='linear', minimum=0., maximum=maximum,
                    stops=stops, nodata='transparent; gray observer_valid=0 overlay', resampling='nearest')
    palettes = {
        'shadow_categories': [(0,'#fff4c4',255,'Neither incremental reduction (not proof of full sun)'),
                              (1,'#46546a',255,'Building reduction only'),(2,'#1b9e77',255,'Additional canopy reduction only'),
                              (3,'#935bb2',255,'Both reductions'),(4,'#b9bec5',255,'Excluded Building observer')],
        'observer_valid': [(0,'#b9bec5',255,'Excluded Building observer'),(1,'#000000',0,'Valid common observer')],
        'canopy_candidate': [(0,'#000000',0,'No positive-depth candidate'),(1,'#1b9e77',96,'Estimated positive-depth candidate')],
        'roi_mask': [(0,'#000000',0,'Outside evaluation ROI (context)'),(1,'#dc243a',64,'Evaluation ROI cell')],
    }
    return dict(renderer='paletted', band=1, interpolation='exact', resampling='nearest',
                stops=[dict(value=v, color=c, alpha=a, label=l) for v,c,a,l in palettes[name]])


def qml_bytes(name, settings):
    """Minimal QGIS 3.40-format raster style, no providers, paths or macros."""
    root = ET.Element('qgis', version='3.40.0', styleCategories='Symbology|Rendering')
    ET.SubElement(root, 'layername').text = LAYERS[name][0]
    pipe = ET.SubElement(root, 'pipe')
    provider = ET.SubElement(pipe, 'provider')
    ET.SubElement(provider, 'resampling', enabled='false', maxOversampling='2',
                  zoomedInResamplingMethod='nearestNeighbour', zoomedOutResamplingMethod='nearestNeighbour')
    attributes = dict(type=settings['renderer'], band='1', opacity='1', alphaBand='-1', nodataColor='')
    if settings['renderer'] == 'singlebandpseudocolor':
        attributes.update(classificationMin='0', classificationMax=repr(settings['maximum']))
    renderer = ET.SubElement(pipe, 'rasterrenderer', attributes)
    origin = ET.SubElement(renderer, 'minMaxOrigin')
    ET.SubElement(origin, 'limits').text = 'None'
    if settings['renderer'] == 'singlebandpseudocolor':
        shader = ET.SubElement(renderer, 'rastershader')
        ramp = ET.SubElement(shader, 'colorrampshader', colorRampType='INTERPOLATED', classificationMode='1',
                             clip='0', minimumValue='0', maximumValue=repr(settings['maximum']), labelPrecision='2')
        for stop in settings['stops']:
            ET.SubElement(ramp, 'item', {k:str(v) for k,v in stop.items()})
        ET.SubElement(ramp, 'rampLegendSettings', useContinuousLegend='1', suffix=' W/m²')
    else:
        palette = ET.SubElement(renderer, 'colorPalette')
        for stop in settings['stops']:
            ET.SubElement(palette, 'paletteEntry', {k:str(v) for k,v in stop.items()})
    # Empty rasterresampler selects nearest at both zoom levels; no interpolation of cells.
    ET.SubElement(pipe, 'rasterresampler', maxOversampling='2')
    ET.SubElement(pipe, 'resamplingStage').text = 'resamplingFilter'
    ET.indent(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def generate(run_root, output):
    root = Path(run_root).resolve(strict=True)
    destination = Path(output).resolve()
    require(not destination.exists() and not destination.is_relative_to(root) and not root.is_relative_to(destination),
            'output', 'new directory outside the run required; no overwrite')
    require(destination.parent.is_dir(), 'output', 'create output parent first')
    watch, config, grid, affine, maximum = inspect_run(root)
    destination.mkdir()  # exclusive, only after preflight; partial failures remain for inspection
    layers = []
    for name, (meaning, unit, scenario) in LAYERS.items():
        settings = style(name, maximum)
        data = qml_bytes(name, settings)
        path = destination/(name+'.qml')
        with path.open('xb') as stream:
            stream.write(data)
        layers.append(dict(name=name, meaning=meaning, unit=unit, scenario=scenario,
                           source='solar/'+name+'.tif', style=settings,
                           qml=dict(path=path.name, sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))))
    watch.unchanged()
    manifest = dict(schema=SCHEMA, run_id=config['run_id'], run_root=os.path.relpath(root, destination),
        created_at=datetime.now(timezone.utc).isoformat(),
        references=dict(configuration='config', submitted_configuration='submitted_config', receipt='receipt',
                        voxel_report='voxel_report', solar_report='solar_report', statistics='solar/statistics.json'),
        sources={key:dict(path=os.path.relpath(root/ref['path'], destination), sha256=ref['sha256'], size_bytes=ref['size_bytes'])
                 for key,ref in watch.identities.items()},
        spatial=dict(grid='solar/grid.json', base_grid='voxel/grid.json', crs='EPSG:4326',
                     display_project_crs='EPSG:6677', shape_uv=grid['shape'][:2], affine=list(affine)[:6],
                     array_mapping='raster[row,col] = uv[n_u-1-row,col]', nominal_resolution_m=1.,
                     note='Exact geographic affine at saved VoxCity centres; not a regular projected metre grid.'),
        difference='solar_no_canopy - solar_current', range_source='solar_report#/solar/sun/flat_horizontal_W_m2',
        layers=layers, generator=dict(module='ouem.gis_visualization', version=VERSION,
            qml_format_target='QGIS 3.40 raster style; load/display not tested',
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            python=sys.version, platform=platform.platform(), numpy=np.__version__, rasterio=rasterio.__version__,
            gdal=rasterio.__gdal_version__),
        validation=dict(saved_evidence_and_consumed_outputs='PASS', source_immutability='PASS', qgis_load_display='NOT_VERIFIED'),
        limitations=['Display colors are not scientific thresholds. No fresh Consumer, model or scientific validation.',
                     'Local hashes/receipt detect mismatches, not coordinated rewriting or authenticated execution.',
                     'Relative sources require the run and visualization directory topology; QML does not load layers or create a project.',
                     'Load observer_valid above solar layers for gray exclusions; ROI style is a cell fill, not a vector outline.'])
    with (destination/'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    generate(args.run_root, args.output)
    print('Created QML + manifest; QGIS load/display NOT_VERIFIED. No model execution.')


if __name__ == '__main__':
    main()
