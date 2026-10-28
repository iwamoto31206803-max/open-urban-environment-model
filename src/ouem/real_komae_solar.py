"""Exploratory real Building/Terrain/estimated Canopy fixed-sun PoC."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
from pyproj import Transformer
import rasterio
from affine import Affine

from ouem.consumers.source_h_standard import Watch, validate_source_h_standard, SOURCE_H_PROFILE, same_json
from ouem.height_envelope import sample_raster, validate_sources, GridSpec
from ouem.e2e_config import configured_arguments
from ouem.komae_integration import environment, voxcity_provenance
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_source_h import write, digest, distribution
from ouem.real_komae_voxel import effective_ground, sample_dem, audit_voxels
from ouem.consumers._source_h_geometry import read_standard
from ouem.standardize.building.source_h_geometry import points

BASE_REPORT_SHA = '9af5854c6838ecf14af09e0315ca09c77756af5a962f4f473d4eb4a7ffe6eb64'
ENVELOPE_SHA = '6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68'
AZIMUTH, ELEVATION, DNI = 135., 35., 800.


def sample_canopy(paths, x, y):
    """Reuse nearest sampler with saved engine centres, never a projected grid."""
    grid = SimpleNamespace(height=x.shape[0], width=x.shape[1], epsg=6677, centres=lambda: (x, y))
    samples = [sample_raster(p, grid) for p in paths]
    for sample in samples:
        require(sample.metadata['crs'] == 'EPSG:6677', 'Canopy.CRS', 'explicit EPSG:6677 required')
    top, bottom, state = (s.values for s in samples)
    missing = np.logical_or.reduce([s.missing for s in samples])
    outside = np.logical_or.reduce([s.outside for s in samples])
    finite = np.isfinite(top) & np.isfinite(bottom) & np.isfinite(state)
    valid = ~missing & ~outside & finite & (state == 1)
    require(not np.any(valid & (bottom > top)), 'Canopy.order', 'valid bottom exceeds top')
    candidate = valid & (top > bottom)
    return dict(top=top, bottom=bottom, state=state, missing=missing, outside=outside,
                valid=valid, candidate=candidate)


def integrate_canopy(base, a, segments, sampled, d0, *, numba):
    """Public API creates trees before Building; crop only unoccupied allocation air."""
    from voxcity.generator.voxelizer import Voxelizer
    ground = a['effective_ground_H']
    candidate = sampled['candidate']
    below = candidate & (sampled['bottom'] < ground)
    active = candidate & ~below
    high = np.where(active, sampled['top']-ground, 0.)
    low = np.where(active, sampled['bottom']-ground, 0.)
    require(np.all((0 <= low) & (low <= high)), 'Canopy.relative', 'unsupported relative interval')
    generated = Voxelizer(1., 'Standard').generate_combined(
        a['building_heights'].copy(), segments.copy(), a['building_ids'].copy(),
        np.ones(ground.shape, dtype=int), a['terrain_H'].copy(), high, low, print_class_info=False)
    allocated = list(generated.shape)
    nz = base.shape[2]
    require(not np.any(generated[:, :, nz:] != 0), 'Canopy.Z', 'occupied voxel exceeds fixed PR98 Z extent; no clipping')
    if generated.shape[2] < nz:
        generated = np.pad(generated, ((0,0),(0,0),(0,nz-generated.shape[2])))
    current = generated[:, :, :nz].copy()
    tree = current == -2
    no_canopy = current.copy(); no_canopy[tree] = 0
    require(np.array_equal(no_canopy, base), 'case_pair', 'non-TREE voxels differ from PR98 base')
    expected = np.zeros(base.shape, dtype=bool)
    removed_building, expanded, vanished = 0, 0, 0
    top_error, bottom_error = [], []
    dtype = np.float32 if numba else np.float64
    for i, j in np.argwhere(active):
        g = int(a['ground_indices'][i, j])
        lo, hi = (int(float(dtype(v))+.5) for v in (low[i,j], high[i,j]))
        if lo == hi and lo > 0: lo -= 1; expanded += 1
        require(g+hi <= nz, 'Canopy.Z', 'tree interval exceeds fixed grid')
        if hi <= lo: vanished += 1; continue
        expected[i,j,g+lo:g+hi] = True
        removed_building += int(np.count_nonzero(base[i,j,g+lo:g+hi] == -3))
        bottom_error.append(d0+g+lo-sampled['bottom'][i,j])
        top_error.append(d0+g+hi-sampled['top'][i,j])
    expected[base == -3] = False
    require(np.array_equal(expected, tree), 'TREE.scalar_qa', 'public TREE placement differs from scalar interval oracle')
    require(not np.any(tree & (base != 0)), 'TREE.overlap', 'TREE inside Building/ground/surface')
    require(tree.any(), 'TREE', 'no candidate produced TREE voxels')
    return current, no_canopy, tree, high, low, dict(
        status='PASS', candidate_columns=int(candidate.sum()), zero_depth_valid_columns=int((sampled['valid'] & ~candidate).sum()),
        below_effective_ground_excluded_columns=int(below.sum()), active_columns=int(active.sum()),
        tree_columns=int(tree.any(axis=2).sum()), tree_voxels=int(tree.sum()),
        building_priority_removed_tree_voxels=removed_building, thin_crown_expanded_columns=expanded,
        zero_after_rounding_columns=vanished, public_api_allocated_shape=allocated, saved_shape=list(current.shape),
        bottom_edge_minus_envelope_H_m=distribution(bottom_error), top_edge_minus_envelope_H_m=distribution(top_error),
        building_and_ground_unchanged=True, no_canopy_equals_PR98=True,
        method='Public generate_combined with unchanged Building/DEM; remove unused allocation air only; no occupied Z clipping or H offset.',
        presence_rule='state1 AND unmasked/inside/finite AND top>bottom; positive estimated crown depth, not verified tree presence; exclude below-effective-ground intervals without adjusting H')


def solar_pair(current, no_canopy, a, grid, high, low, *, maximum_source_H=None):
    from voxcity.models import VoxCity, VoxelGrid, GridMetadata, BuildingGrid, LandCoverGrid, DemGrid, CanopyGrid
    from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
    from voxcity.utils.orientation import direction_to_axis_vector
    ids = a['building_ids']; valid = ids == 0
    origin_k = a['ground_indices']+1  # int(1.5 / 1m) added to first walkable transition
    rotation = grid['axis0_true_azimuth_deg']
    rectangle = grid['rectangle_vertices_lonlat']
    bounds = (min(p[0] for p in rectangle), min(p[1] for p in rectangle), max(p[0] for p in rectangle), max(p[1] for p in rectangle))
    meta = GridMetadata('EPSG:4326', bounds, 1.)
    def calculate(vox, *, offset=(0,0)):
        sl = np.s_[offset[0]:offset[0]+vox.shape[0], offset[1]:offset[1]+vox.shape[1]]
        present = bool(np.any(vox == -2))
        scene = VoxCity(VoxelGrid(vox, meta), BuildingGrid(a['building_heights'][sl], a['building_segments'][sl], ids[sl], meta),
                        LandCoverGrid(np.ones(vox.shape[:2], dtype=int), meta), DemGrid(a['effective_dem'][sl], meta),
                        CanopyGrid(high[sl] if present else np.zeros(vox.shape[:2]), meta,
                                   bottom=low[sl] if present else np.zeros(vox.shape[:2])), extras={'rotation_angle':rotation})
        before = vox.copy()
        result = get_direct_solar_irradiance_map(scene, AZIMUTH, ELEVATION, DNI, show_plot=False,
                    view_point_height=1.5, include_building_roofs=False, tree_k=.6, tree_lad=1.)
        require(np.array_equal(vox, before), 'solar.inputs', 'API changed voxel input')
        require(np.array_equal(np.isfinite(result), valid[sl]), 'solar.mask', 'unexpected observer mask')
        return np.where(valid[sl], result, np.nan)
    now, absent = calculate(current), calculate(no_canopy)
    terrain_only = no_canopy.copy(); terrain_only[terrain_only == -3] = 0
    # Diagnostic only: same original non-building observers, retained conditioned
    # ground. Public API now also returns finite roof-removed columns; mask them.
    def terrain_control():
        from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
        empty = np.empty(ids.shape, object)
        for ij in np.ndindex(ids.shape): empty[ij] = []
        scene = VoxCity(VoxelGrid(terrain_only, meta), BuildingGrid(np.zeros(ids.shape), empty, np.zeros_like(ids), meta),
                        LandCoverGrid(np.ones(ids.shape, dtype=int), meta), DemGrid(a['effective_dem'], meta),
                        CanopyGrid(np.zeros(ids.shape), meta), extras={'rotation_angle':rotation})
        result = get_direct_solar_irradiance_map(scene, AZIMUTH, ELEVATION, DNI, show_plot=False,
                    view_point_height=1.5, include_building_roofs=False, tree_k=.6, tree_lad=1.)
        require(np.isfinite(result[valid]).all(), 'control.mask', 'missing original observers')
        return np.where(valid, result, np.nan)
    terrain_solar = terrain_control()
    reduction = absent-now; building_reduction = terrain_solar-absent
    tolerance = 1e-9
    baseline = DNI*math.sin(math.radians(ELEVATION))
    require(np.all(reduction[valid] >= -tolerance) and np.all(building_reduction[valid] >= -tolerance),
            'solar.sign', 'irradiance increased under added occluders')
    require(np.all((now[valid] >= 0) & (terrain_solar[valid] <= baseline+tolerance)), 'solar.range', 'irradiance outside physical range')
    roi = a['roi_mask']; observed = roi & valid
    require(observed.any() and np.any(reduction[observed] > tolerance), 'solar.ROI', 'no canopy reduction on shared ROI observers')
    def statistics(mask):
        return dict(observers=int(mask.sum()), current=distribution(now[mask]), no_canopy=distribution(absent[mask]),
                    mean_current_W_m2=float(now[mask].mean()), mean_no_canopy_W_m2=float(absent[mask].mean()),
                    mean_reduction_W_m2=float(reduction[mask].mean()), reduction=distribution(reduction[mask]),
                    reduction_cells=int((reduction[mask] > tolerance).sum()),
                    building_shadow_cells=int((building_reduction[mask] > tolerance).sum()),
                    canopy_reduction_in_building_shadow_cells=int(((reduction[mask]>tolerance) & (building_reduction[mask]>tolerance)).sum()))
    ii, jj = np.where(roi)
    slices = np.s_[ii.min():ii.max()+1, jj.min():jj.max()+1]
    require(np.all(roi[slices]), 'ROI', 'crop diagnostic requires rectangular centre mask')
    crop_now = calculate(current[slices].copy(), offset=(int(ii.min()), int(jj.min())))
    crop_absent = calculate(no_canopy[slices].copy(), offset=(int(ii.min()), int(jj.min())))
    local_valid = valid[slices]
    halo_delta = crop_now-now[slices]
    require(np.all(halo_delta[local_valid] >= -tolerance), 'halo', 'removing outside ROI occluders reduced irradiance')
    direction = np.asarray(direction_to_axis_vector(AZIMUTH, ELEVATION, rotation))
    angle = math.radians(AZIMUTH-rotation); elevation = math.radians(ELEVATION)
    independent = [math.cos(elevation)*math.cos(angle), math.cos(elevation)*math.sin(angle), math.sin(elevation)]
    require(np.allclose(direction, independent, atol=1e-12, rtol=0), 'sun.direction', 'rotation/sign mismatch')
    unit = direction[:2]/np.linalg.norm(direction[:2])
    min_border_distance = float('inf')
    for axis, component in enumerate(unit):
        indices = np.indices(ids.shape)[axis][observed]+.5
        distance = (ids.shape[axis]-indices)/component if component > 0 else indices/-component
        min_border_distance = min(min_border_distance, float(distance.min()))
    occupied = np.argwhere((current == -2) | (current == -3))
    highest_edge = grid['D0_effective_H_m']+int(occupied[:,2].max())+1
    lowest_observer = grid['D0_effective_H_m']+float(origin_k[observed].min())+.5
    conservative_edge = max(highest_edge, maximum_source_H+2. if maximum_source_H is not None else highest_edge)
    reach = max(0., conservative_edge-lowest_observer)/math.tan(elevation)
    context = grid.get('halo_m', 32.)
    categories = np.zeros(ids.shape, dtype='uint8')
    categories[building_reduction > tolerance] = 1
    categories[reduction > tolerance] = 2
    categories[(building_reduction > tolerance) & (reduction > tolerance)] = 3
    categories[~valid] = 4
    return dict(solar_current=now, solar_no_canopy=absent, solar_difference=reduction,
                solar_terrain_control=terrain_solar, building_solar_reduction=building_reduction,
                shadow_categories=categories, observer_valid=valid, observer_index_k=origin_k,
                cropped_current=crop_now, cropped_no_canopy=crop_absent), dict(
        status='PASS', api='get_direct_solar_irradiance_map', actual_api_calls=5,
        sun=dict(azimuth_deg=AZIMUTH, elevation_deg=ELEVATION, DNI_W_m2=DNI, rotation_deg=rotation,
                 direction_uv_up=direction.tolist(), flat_horizontal_W_m2=baseline, artificial_fixed_condition=True),
        optics=dict(tree_k=.6, tree_lad=1., note='Uncalibrated homogeneous extinction/LAD assumptions'),
        observer=dict(requested_height_m=1.5, kernel_index='ground_indices+int(1.5)=g+1',
                      nominal_H='D0_effective+g+1.5; identical in both cases; not measured 1.5m above source ground',
                      common_columns=int(valid.sum()), excluded_building_columns=int((~valid).sum()), roofs=False),
        ROI=statistics(observed), outside_ROI=statistics(valid & ~roi),
        halo=dict(highest_known_occluder_edge_H=highest_edge, lowest_ROI_observer_H=lowest_observer,
                  full_AOI_maximum_source_H=maximum_source_H, conservative_edge_bound_H=conservative_edge,
                  source_edge_rounding_allowance_m=2.,
                  horizontal_reach_m=reach, isotropic_32m_bound_sufficient=bool(reach+2 <= 32),
                  context_buffer_m=context, isotropic_context_bound_sufficient=bool(reach+2 <= context),
                  minimum_sunward_exit_distance_m=min_border_distance,
                  directional_known_height_bound_sufficient=bool(reach+2 <= min_border_distance), margin_m=2.,
                  crop_ROI_increase_cells=int((halo_delta[local_valid] > tolerance).sum()),
                  crop_ROI_max_increase_W_m2=float(halo_delta[local_valid].max()),
                  general_external_occluder_sufficiency='UNVERIFIED: objects outside source domain may be taller; no expanded-domain convergence run'),
        technical_calculation='COMPLETED', canopy_effect_detected=bool(np.any(reduction[observed] > tolerance)),
        invariants=dict(common_grid_D0_building_ground_observers_ROI='PASS', non_TREE_voxels_equal='PASS',
                        irradiance_increase_cells=int((reduction[valid] < -tolerance).sum()), tolerance_W_m2=tolerance))


def preflight(args, watch):
    config = getattr(args, 'config', None)
    if config:
        config.capture(watch)
    base_dir = args.base_run.resolve()
    def capture(key, path, sha=None, size=None, json_data=False):
        return watch.capture(key, Path(path).resolve().relative_to(watch.root).as_posix(), sha, size, json_data=json_data)
    model_sha = config.model_sha(watch) if config else BASE_REPORT_SHA
    previous = capture('PR98_report', base_dir/'report.json', model_sha, json_data=True)
    if config:
        same_json(previous.get('run_config'), config.record(), 'model.config')
    require(previous['status'] == 'COMPLETED' and previous['consumer']['technical_validation'] == 'PASS'
            and previous['input_immutability'] == 'PASS', 'PR98', 'incomplete previous model/Consumer')
    for key, ref in previous['input_artifacts'].items():
        watch.capture('base_input:'+key, ref['path'], ref['sha256'], ref['size_bytes'])
    for name, ref in previous['outputs'].items():
        capture('base_output:'+name, base_dir/name, ref['sha256'], ref['size_bytes'])
    consumer_ref = previous['consumer']['artifacts']
    manifest_path = watch.resolve(consumer_ref['standard_manifest']['path'])
    if config:
        require(manifest_path == config.input_path('building_manifest'), 'model.inputs', 'different Building manifest')
    consumer = validate_source_h_standard(manifest_path, watch.root, SOURCE_H_PROFILE,
                    study_area_config=args.study_area.resolve())
    require(consumer['technical_validation'] == 'PASS', 'Consumer', str(consumer['issues']))
    for key, identity in consumer['artifacts'].items():
        old = consumer_ref[key]
        require(all(identity[k] == old[k] for k in ('path','sha256','size_bytes')), 'Consumer.binding', 'source changed since PR98')
    grid = capture('grid', base_dir/'grid.json', previous['outputs']['grid.json']['sha256'], json_data=True)
    shape = grid['shape']
    require(type(shape) is list and len(shape) == 3 and all(type(n) is int and n > 0 for n in shape),
            'grid.shape', 'positive integer 3D shape required')
    require(grid == previous['model']['grid'] and (config is not None or shape == [128,128,27]) and grid['layout'] == 'uv_m/SOUTH_UP',
            'grid', 'unexpected PR98 grid')
    if config:
        require(grid['nominal_voxel_size_m'] == 1. and grid['projected_reference_crs'] == 'EPSG:6677'
                and grid['rectangle_crs'] == 'EPSG:4326'
                and grid['projected_evaluation_ROI_bounds'] == list(config.extent.analysis)
                and grid['projected_domain_bounds'] == list(config.extent.domain)
                and grid['halo_m'] == config.extent.buffer_m, 'grid.config', 'model grid differs from configuration')
        from voxcity.geoprocessor.raster.core import compute_cell_center_coords
        xmin,ymin,xmax,ymax = config.extent.domain
        transform = Transformer.from_crs(6677,4326,always_xy=True)
        rectangle = [transform.transform(x,y) for x,y in ((xmin,ymin),(xmin,ymax),(xmax,ymax),(xmax,ymin))]
        require(np.allclose(rectangle, grid['rectangle_vertices_lonlat'], atol=1e-12, rtol=0),
                'grid.rectangle', 'actual rectangle is not the configured domain')
        fresh_grid = compute_cell_center_coords(rectangle, 1.)
        require(fresh_grid['lons'].shape == tuple(shape[:2]), 'grid.shape', 'engine/config shape mismatch')
    arrays = {p.stem: np.load(p, allow_pickle=False) for p in base_dir.glob('*.npy') if p.name in previous['outputs']}
    require(arrays['voxels'].shape == tuple(shape) and all(arrays[k].shape == tuple(shape[:2]) for k in
            ('building_ids','building_heights','terrain_H','effective_ground_H','effective_dem','ground_indices',
             'centre_lon','centre_lat','centre_x','centre_y','roi_mask')), 'grid.arrays', 'array shape mismatch')
    indices = np.indices(shape[:2])
    for axis, key in enumerate(('centre_lon', 'centre_lat')):
        reconstructed = grid['origin_lonlat'][axis]+(indices[0]+.5)*grid['u_step_lonlat'][axis]+(indices[1]+.5)*grid['v_step_lonlat'][axis]
        require(np.allclose(reconstructed, arrays[key], atol=1e-12, rtol=0), 'grid.centres', key)
        if config:
            require(np.allclose(fresh_grid['lons' if axis == 0 else 'lats'], arrays[key], atol=1e-12, rtol=0),
                    'grid.engine_centres', key)
    x,y = Transformer.from_crs(4326,6677,always_xy=True).transform(arrays['centre_lon'], arrays['centre_lat'])
    require(np.allclose(x, arrays['centre_x'], atol=1e-7, rtol=0) and np.allclose(y, arrays['centre_y'], atol=1e-7, rtol=0), 'grid.XY', 'saved CRS centres differ')
    xmin,ymin,xmax,ymax = grid['projected_evaluation_ROI_bounds']
    require(np.array_equal(arrays['roi_mask'], (x>=xmin)&(x<xmax)&(y>=ymin)&(y<ymax)), 'ROI', 'saved ROI mask differs')
    dem_path = watch.resolve(previous['input_artifacts']['terrain']['path'])
    if config:
        require(dem_path == config.input_path('terrain'), 'model.inputs', 'different Terrain')
    sampled,_,_ = sample_dem(dem_path, arrays['centre_lon'], arrays['centre_lat'])
    require(np.array_equal(sampled, arrays['terrain_H']), 'Terrain', 'actual centre DEM differs')
    ground, d0 = effective_ground(arrays['building_ids'], sampled)
    require(np.array_equal(ground, arrays['effective_ground_H']) and d0 == grid['D0_effective_H_m']
            and np.allclose(ground-d0, arrays['effective_dem'], atol=1e-10, rtol=0), 'D0', 'effective ground/D0 differs')
    segment_record = capture('segments', base_dir/'building_segments.json', previous['outputs']['building_segments.json']['sha256'], json_data=True)
    require(segment_record['shape'] == shape[:2], 'segments.shape', 'wrong segment dimensions')
    segments = np.empty(shape[:2], object)
    for ij in np.ndindex(segments.shape): segments[ij] = []
    for cell in segment_record['cells']: segments[cell['i'], cell['j']] = cell['segments']
    _, fresh_ground = audit_voxels(arrays['voxels'], arrays['building_ids'], sampled, segments, arrays['effective_dem'], d0, numba=previous['model']['numba'])
    require(np.array_equal(fresh_ground, arrays['ground_indices']), 'observer.ground', 'saved ground indices differ')
    arrays['building_segments'] = segments
    envelope_path = config.input_path('envelope_manifest') if config else args.envelope_run.resolve()/'generated/height_envelope_manifest.json'
    envelope_dir = envelope_path.parent
    envelope_sha = config.binding('envelope_manifest')['sha256'] if config else ENVELOPE_SHA
    envelope = capture('envelope_manifest', envelope_path, envelope_sha, json_data=True)
    require(envelope['status'] == 'COMPLETED' and envelope['schema'] == 'ouem-height-envelope-poc/v0.1'
            and envelope['cr_model']['parameters']['cr'] == .6, 'Envelope', 'unexpected/incomplete CR model')
    for key, ref in envelope['input_files'].items(): capture('envelope_input:'+key, ref['path'], ref['sha256'], ref['bytes'])
    inputs = envelope['input_files']
    semantics = validate_sources(*(inputs[k]['path'] for k in ('chm','acquisition_record','chm_evidence','terrain','terrain_manifest','terrain_acceptance')))
    require(inputs['terrain']['sha256'] == previous['input_artifacts']['terrain']['sha256'], 'vertical', 'Canopy and model use different source DEM')
    acquisition = json.loads(Path(inputs['acquisition_record']['path']).read_text(encoding='utf-8'))
    for i, tile in enumerate(acquisition['tiles']): capture('raw_chm_tile:'+str(i), tile['path'], tile['sha256'], tile['bytes'])
    evidence = json.loads(Path(inputs['chm_evidence']['path']).read_text(encoding='utf-8'))
    review = evidence['compatibility_review']
    capture('limited_review_record', Path(inputs['chm_evidence']['path']).parent/review['approval_record_path'], review['approval_record_sha256'])
    paths = [envelope_dir/n for n in ('canopy_top_z.tif','canopy_bottom_z.tif','height_envelope_state.tif')]
    source_grid = GridSpec(tuple(envelope['grid_spec']['bounds']), envelope['grid_spec']['resolution'], envelope['grid_spec']['epsg'])
    require(envelope['grid_spec']['width'] == source_grid.width and envelope['grid_spec']['height'] == source_grid.height
            and envelope['grid_spec']['transform'] == list(source_grid.transform)[:6], 'Envelope.grid', 'inconsistent source grid metadata')
    for path in paths:
        ref = envelope['outputs'][path.name]; capture('canopy_output:'+path.name, path, ref['sha256'], ref['bytes'])
        with rasterio.open(path) as ds:
            require(ds.crs.to_epsg()==6677 and ds.shape==(source_grid.height,source_grid.width)
                    and list(ds.transform)[:6]==envelope['grid_spec']['transform'], 'Envelope.grid', 'source CRS/shape/affine mismatch')
    canopy = sample_canopy(paths, arrays['centre_x'], arrays['centre_y'])
    require(canopy['valid'].all(), 'Envelope.coverage', 'missing/invalid/outside/state cells: cannot infer absence')
    standard_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    all_buildings = read_standard(watch.resolve(standard_manifest['standard_output']['path']), 'building')
    maximum_source_H = max(p[2] for tree,_,_ in all_buildings.values() for p in points(tree))
    with rasterio.open(paths[0]) as ds:
        maximum_source_H = max(maximum_source_H, float(ds.read(1, masked=True).max()))
    watch.unchanged()
    return arrays, grid, segments, canopy, dict(status='PASS', fresh_consumer=consumer, envelope_semantics=semantics,
            source_CR=.6, maximum_source_H=maximum_source_H,
            state_rule='1=valid computation only; not canopy presence', source_model_report_sha256=model_sha)


def export(run, arrays, grid):
    origin=np.asarray(grid['origin_lonlat']); u=np.asarray(grid['u_step_lonlat']); v=np.asarray(grid['v_step_lonlat'])
    nu,nv,nz = arrays['current_voxels'].shape
    start=origin+nu*u; transform=Affine(v[0],-u[0],start[0],v[1],-u[1],start[1])
    for key, array in arrays.items():
        with (run/(key+'.npy')).open('xb') as stream: np.save(stream, array, allow_pickle=False)
        require(np.array_equal(array,np.load(run/(key+'.npy'),allow_pickle=False),equal_nan=True), 'readback', key)
        if array.shape != (nu,nv): continue
        raster=array[::-1,:].copy()
        if raster.dtype==bool: raster=raster.astype('uint8')
        nodata=np.nan if raster.dtype.kind=='f' and np.isnan(raster).any() else None
        with rasterio.open(run/(key+'.tif'),'w',driver='GTiff',width=nv,height=nu,count=1,dtype=raster.dtype,
                           crs=4326,transform=transform,nodata=nodata) as ds: ds.write(raster,1)
        with rasterio.open(run/(key+'.tif')) as ds:
            require(np.array_equal(ds.read(1),raster,equal_nan=True), 'GeoTIFF.readback', key)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,4,figsize=(17,4))
    for ax,key,title in zip(axes,('solar_current','solar_no_canopy','solar_difference','shadow_categories'),
                           ('Current direct W/m2','No-Canopy direct W/m2','No-Canopy - Current W/m2','1:Building; 2:Canopy; 3:both; 4:roof')):
        im=ax.imshow(arrays[key],origin='lower',interpolation='nearest',vmin=0,vmax=4 if key=='shadow_categories' else DNI*math.sin(math.radians(ELEVATION)))
        ax.contour(arrays['roi_mask'],levels=[.5],colors='red',linewidths=1)
        ax.set_title(title);ax.set_xlabel('v / approximately east');ax.set_ylabel('u / approximately north');fig.colorbar(im,ax=ax)
    fig.tight_layout();fig.savefig(run/'solar_comparison.png',dpi=150);plt.close(fig)
    tree_count=arrays['tree_mask'].sum(axis=2)
    cut=int(np.argmax(tree_count.sum(axis=0)))
    fig,ax=plt.subplots(figsize=(11,4))
    from matplotlib.colors import ListedColormap, BoundaryNorm
    d0=grid['D0_effective_H_m']
    ax.imshow(arrays['current_voxels'][:,cut,:].T,origin='lower',aspect='auto',interpolation='nearest',
              extent=[0,nu,d0,d0+nz],cmap=ListedColormap(['#c68a3f','#1d9949','#776044','#ffffff','#b8a67b']),
              norm=BoundaryNorm([-3.5,-2.5,-1.5,-.5,.5,1.5],5))
    ax.set_title(f'Current section v={cut}: Building brown, estimated TREE green; nominal index-edge H')
    ax.set_xlabel('u / approximately north');ax.set_ylabel('H (m)')
    fig.tight_layout();fig.savefig(run/'section.png',dpi=150);plt.close(fig)


def run(args):
    config = getattr(args, 'config', None)
    if config:
        config = config.prepare('solar')
        args = config.arguments('solar')
    output=args.run_dir.resolve();output.mkdir()
    report=dict(status='RUNNING',started_at=datetime.now(timezone.utc).isoformat(),
                source_h_eligibility='NOT_ESTABLISHED',formal_acceptance='NOT_VERIFIED',phase5_gates=dict.fromkeys(('A1','A2','A3','A4'),'OPEN'))
    started=time.perf_counter();watch=Watch(args.artifact_root.resolve())
    try:
        report['environment']=environment()
        if config:
            report['run_config'] = config.record()
            watch.capture('config_implementation',Path(__file__).with_name('e2e_config.py').resolve().relative_to(watch.root).as_posix())
        require(report['environment']['voxcity']['verified'],'engine','fixed VoxCity installation not verified')
        watch.capture('implementation',Path(__file__).resolve().relative_to(watch.root).as_posix())
        a,grid,segments,canopy,checks=preflight(args,watch);report['preflight']=checks
        from voxcity.generator.voxelizer import NUMBA_AVAILABLE
        current,absent,tree,high,low,tree_qa=integrate_canopy(a['voxels'],a,segments,canopy,grid['D0_effective_H_m'],numba=NUMBA_AVAILABLE)
        report['tree']=tree_qa
        solar,solar_qa=solar_pair(current,absent,a,grid,high,low,maximum_source_H=checks['maximum_source_H']);report['solar']=solar_qa
        arrays=dict(current_voxels=current,no_canopy_voxels=absent,tree_mask=tree,
                    canopy_top_H=canopy['top'],canopy_bottom_H=canopy['bottom'],envelope_state=canopy['state'],
                    canopy_candidate=canopy['candidate'],canopy_missing=canopy['missing'],canopy_outside=canopy['outside'],
                    roi_mask=a['roi_mask'].copy(),**solar)
        export(output,arrays,grid)
        write(output/'grid.json',grid)
        write(output/'statistics.json',solar_qa)
        watch.unchanged();require(voxcity_provenance()==report['environment']['voxcity'],'engine','engine changed')
        report.update(status='COMPLETED',input_immutability='PASS',input_artifacts=watch.identities)
    except Exception as exc:
        report.update(status='FAILED',error=str(exc));raise
    finally:
        report['elapsed_seconds']=time.perf_counter()-started
        report['outputs']={p.name:dict(sha256=digest(p),size_bytes=p.stat().st_size) for p in output.iterdir() if p.is_file()}
        write(output/'report.json',report)
        with (output/'RESULTS.md').open('x',encoding='utf-8') as stream:
            stream.write(f"# Real Komae three-element solar PoC\n\nStatus: {report['status']}\n\nSee report.json for input hashes, sampling, TREE placement, common observers and ROI/halo results.\n\n![Solar](solar_comparison.png)\n\n![Section](section.png)\n\nEstimated canopy / CR0.60; fixed artificial sun, no formal acceptance or gate change.\n")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path)
    for key in ('run-dir','base-run','envelope-run','artifact-root','study-area'): parser.add_argument('--'+key,type=Path)
    run(configured_arguments(parser, parser.parse_args(), 'solar'))


if __name__=='__main__': main()
