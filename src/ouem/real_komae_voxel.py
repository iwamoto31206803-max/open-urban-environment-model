"""Bounded real Komae Building + Terrain experiment on the actual VoxCity grid."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import geopandas as gpd
import numpy as np
from pyproj import Transformer, Geod
import rasterio
from affine import Affine
from shapely.geometry import Polygon, box

from ouem.canopy_shadow_poc import ROI, DOMAIN  # Reuse extents only; no canopy/solar calls.
from ouem.consumers.source_h_standard import Watch, validate_source_h_standard, SOURCE_H_PROFILE
from ouem.consumers._source_h_geometry import read_standard
from ouem.standardize.building import deterministic_ouem_id
from ouem.standardize.building.source_h_geometry import as_shape, points
from ouem.native.building.source_h_geometry import require
from ouem.adapters.voxcity import build_normalized_footprint, numeric_id_mapping, derive_attributes
from ouem.komae_integration import environment, voxcity_provenance
from ouem.real_komae_source_h import digest, distribution, write


def sample_dem(path, lons, lats):
    """Nearest source pixel at every actual engine centre; fail on outside/NoData."""
    x, y = Transformer.from_crs(4326, 6677, always_xy=True).transform(lons, lats, errcheck=True)
    x, y = np.asarray(x), np.asarray(y)
    with rasterio.open(path) as ds:
        require(ds.crs.to_epsg() == 6677 and ds.count == 1 and ds.dtypes == ('float32',)
                and ds.nodata == -9999.0 and ds.transform.b == ds.transform.d == 0
                and ds.transform.a > 0 and ds.transform.e < 0,
                'Terrain', 'Standard north-up Float32 EPSG:6677 DEM required')
        require(np.isfinite(x).all() and np.isfinite(y).all() and
                ((x >= ds.bounds.left) & (x < ds.bounds.right) &
                 (y > ds.bounds.bottom) & (y <= ds.bounds.top)).all(),
                'Terrain.coverage', 'engine centre outside DEM; no extrapolation')
        rows, cols = rasterio.transform.rowcol(ds.transform, x.ravel(), y.ravel())
        rows, cols = np.asarray(rows), np.asarray(cols)
        require(((rows >= 0) & (rows < ds.height) & (cols >= 0) & (cols < ds.width)).all(),
                'Terrain.coverage', 'engine centre maps outside DEM')
        values = ds.read(1, masked=True)[rows, cols]
        require(not np.ma.getmaskarray(values).any() and np.isfinite(values).all(),
                'Terrain.NoData', 'masked/nonfinite centre sample; no filling')
        dem = np.asarray(values, dtype=np.float64).reshape(x.shape)
    return dem, x, y


def effective_ground(ids, dem):
    """Independent absolute form of pinned process_grid; never alters source DEM."""
    conditioned = dem.copy()
    for identifier in np.unique(ids[ids > 0]):
        mask = ids == identifier
        conditioned[mask] = np.mean(dem[mask], dtype=np.float64)
    return conditioned, float(conditioned.min())


def audit_voxels(voxels, ids, dem, segments, effective, d0, *, numba):
    """Independent scalar QA after real public API execution, never model output."""
    require(voxels.ndim == 3 and voxels.shape[:2] == dem.shape == ids.shape == effective.shape,
            'voxel.shape', 'inconsistent common grid')
    # Numba receives float32 DEM but divides/adds using float64 voxel_size.
    # Promote before +0.5: float32 addition would round values just below a tie.
    kernel_dem = np.asarray(effective, dtype=np.float32 if numba else np.float64).astype(np.float64)
    ground = (kernel_dem + .5).astype(int) + 1
    expected = np.zeros_like(voxels)
    roofs, top_errors, overlaps = [], [], 0
    for i, j in np.ndindex(ids.shape):
        g = int(ground[i, j])
        require(0 < g <= voxels.shape[2], 'ground', 'surface out of vertical grid')
        expected[i, j, :g] = -1
        expected[i, j, g-1] = 1  # minimal Bareland surface, not measured land cover
        cell = segments[i, j]
        require(bool(cell) == bool(ids[i, j]), 'segments', 'ID/segment support differs')
        overlaps += int(len(cell) > 1)
        for low, high in cell:
            require(low == 0 and np.isfinite(high) and high > 0, 'segments', 'ordinary grounded segment required')
            end = g + int(float(high) + .5)
            require(g < end <= voxels.shape[2], 'vertical', 'empty or clipped building segment')
            expected[i, j, g:end] = -3
        if cell:
            occupied = np.flatnonzero(voxels[i, j] == -3)
            require(occupied.size and occupied[0] == g, 'placement', 'floating/buried or missing building')
            top = d0 + int(occupied[-1]) + 1
            target = d0 + effective[i, j] + max(s[1] for s in cell)
            roofs.append(top)
            top_errors.append(top-target)
    require(np.array_equal(expected, voxels), 'voxel.scalar_qa', 'engine classes/position differ from scalar rules')
    require(top_errors and max(abs(v) for v in top_errors) <= 2.0,
            'roof', 'voxel top outside 2m discretization budget')
    surface = d0 + ground
    return dict(status='PASS', full_array_scalar_oracle='PASS',
                surface_upper_edge_minus_effective_ground=distribution(surface-(d0+effective)),
                surface_upper_edge_minus_raw_terrain=distribution(surface-dem),
                roof_upper_edge_minus_segment_envelope=distribution(top_errors),
                overlap_cells=overlaps, building_columns=int(np.count_nonzero(ids)),
                missing_or_floating_or_buried_columns=0), ground


def prepare_buildings(features):
    """Full source-H surface supports; source geometry and H are read-only."""
    mapping = numeric_id_mapping(deterministic_ouem_id(k) for k in features)
    rows, inventory = [], []
    for source_id, (tree, _, measured) in sorted(features.items()):
        ouem_id = deterministic_ouem_id(source_id)
        footprint, diagnostics = build_normalized_footprint(as_shape(tree), ouem_id)
        zs = [p[2] for p in points(tree)]
        item = dict(source_id=source_id, ouem_id=ouem_id, id=mapping[ouem_id],
                    z_top_abs=max(zs), z_bottom_geom_abs=min(zs), measured_height=measured,
                    intersects_projected_domain=bool(footprint.intersects(box(*DOMAIN))),
                    crosses_projected_domain=bool(footprint.intersects(box(*DOMAIN)) and not box(*DOMAIN).covers(footprint)),
                    footprint_diagnostics=diagnostics)
        inventory.append(item)
        rows.append(dict(source_id=source_id, ouem_id=ouem_id, id=mapping[ouem_id],
                         height=1., min_height=0., geometry=footprint))
    return gpd.GeoDataFrame(rows, geometry='geometry', crs=6677), inventory


def raster_buildings(frame, rectangle, dem, inventory):
    from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon as raster
    lookup = {r['id']: r for r in inventory}
    previous = None
    # Ownership depends on relative-height order in overlapping cells. Re-evaluate
    # until the actual ID grid used for per-building ground assignment is stable.
    for iteration in range(8):
        heights, segments, ids, filtered = raster(frame.copy(), 1., rectangle, overlapping_footprint=True)
        require(heights.shape == segments.shape == ids.shape == dem.shape,
                'common_grid', 'engine Building/Terrain shapes differ')
        require(all(int(r.id) == lookup[int(r.id)]['id'] and
                    r.source_id == lookup[int(r.id)]['source_id'] for r in filtered.itertuples()),
                'engine.ids', 'engine overlap processing remapped a source ID')
        require(set(map(int, filtered.id)) == set(map(int, frame.id)), 'engine.ids', 'filtered building lost')
        require(all(r.geometry.wkb == frame.loc[frame.source_id == r.source_id].geometry.iloc[0].wkb
                    for r in filtered.itertuples()), 'engine.geometry', 'engine changed full footprint')
        ids = ids.astype(np.int64)
        require(set(np.unique(ids[ids > 0])) == set(map(int, frame.id)), 'engine.ids', 'building assigned no engine cell')
        attrs = {}
        for identifier in frame.id:
            r = lookup[int(identifier)]
            attrs[int(identifier)] = derive_attributes([r['z_bottom_geom_abs'], r['z_top_abs']], dem[ids == identifier].tolist())
        if previous is not None and np.array_equal(previous, ids):
            require(all(abs(float(r.height)-attrs[int(r.id)]['height']) < 1e-10 for r in frame.itertuples()),
                    'ground', 'height/ground fixed point inconsistent')
            return frame, heights, segments, ids, attrs, iteration+1
        previous = ids.copy()
        frame = frame.copy()
        frame['height'] = [attrs[int(i)]['height'] for i in frame.id]
    require(False, 'ground', 'engine ownership/height iteration did not stabilize')


def execute_model(features, terrain, *, rectangle=None):
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords, process_grid, create_cell_polygon
    from voxcity.generator.voxelizer import Voxelizer, NUMBA_AVAILABLE
    geographic = Transformer.from_crs(6677, 4326, always_xy=True)
    xmin, ymin, xmax, ymax = DOMAIN
    rectangle = rectangle or [geographic.transform(x, y) for x, y in
                              ((xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin))]
    geom = compute_cell_center_coords(rectangle, 1.)
    dem, x, y = sample_dem(terrain, geom['lons'], geom['lats'])
    roi_mask = (x >= ROI[0]) & (x < ROI[2]) & (y >= ROI[1]) & (y < ROI[3])
    require(int(roi_mask.sum()) > 0, 'ROI', 'empty evaluation ROI')
    projected, inventory = prepare_buildings(features)
    geographic_frame = projected.to_crs(4326)
    origin = np.asarray(geom['origin'])
    u = geom['adj_mesh'][0]*np.asarray(geom['u_vec'])
    v = geom['adj_mesh'][1]*np.asarray(geom['v_vec'])
    nx, ny = dem.shape
    actual_domain = Polygon([origin, origin+nx*u, origin+nx*u+ny*v, origin+ny*v])
    included = geographic_frame.geometry.intersects(actual_domain)
    selected = geographic_frame.loc[included].copy()
    require(len(selected) > 0, 'buildings', 'no building intersects actual engine domain')
    require(selected.is_valid.all(), 'footprint', 'invalid selected geographic footprint; no implicit repair')
    # Full footprints remain uncut, including crossing objects.
    frame, heights, segments, ids, attrs, iterations = raster_buildings(selected, rectangle, dem, inventory)
    conditioned, d0_effective = effective_ground(ids, dem)
    effective = process_grid(ids, dem-dem.min())
    require(np.allclose(effective, conditioned-d0_effective, atol=1e-10, rtol=0),
            'effective_ground', 'engine ground disagrees with independent absolute reconstruction')
    cover = np.ones(ids.shape, dtype=np.int64)
    trees = np.zeros(ids.shape, dtype=np.float64)
    voxels = Voxelizer(1., 'Standard').generate_combined(
        heights.copy(), segments.copy(), ids.copy(), cover, dem.copy(), trees, print_class_info=False)
    qa, ground_indices = audit_voxels(voxels, ids, dem, segments, effective, d0_effective, numba=NUMBA_AVAILABLE)
    details, cells = [], []
    with rasterio.open(terrain) as ds:
        dem_bounds = box(*ds.bounds)
    for row in inventory:
        identifier = row['id']
        p = projected.loc[projected.id == identifier].geometry.iloc[0]
        row['whole_footprint_in_dem_bounds'] = bool(dem_bounds.covers(p))
        row['intersects_actual_engine_domain'] = identifier in attrs
        if identifier not in attrs:
            row['disposition'] = 'OUTSIDE_ACTUAL_ENGINE_DOMAIN'
            continue
        geo = frame.loc[frame.id == identifier].geometry.iloc[0]
        row.update(attrs[identifier], owned_engine_cells=int(np.count_nonzero(ids == identifier)),
                   crosses_actual_engine_domain=not actual_domain.covers(geo), disposition='RASTERIZED')
        require(abs(row['ground_eff_abs']+row['height']-row['z_top_abs']) < 1e-9,
                'H', 'roof/ground/relative-height identity failed')
        row['bottom_minus_effective_ground_m'] = row['z_bottom_geom_abs']-row['ground_eff_abs']
        row['geometry_height_m'] = row['z_top_abs']-row['z_bottom_geom_abs']
        details.append(row)
    # Geometric contributor IDs are independent of last-wins ownership. Validate
    # each actual cell's segment multiset, including adjacent/overlapping buildings.
    source_top_errors = []
    for i, j in np.argwhere(ids > 0):
        cell = create_cell_polygon(geom['origin'], int(i), int(j), geom['adj_mesh'], geom['u_vec'], geom['v_vec'])
        contributors = [r for r in frame.itertuples() if r.geometry.intersection(cell).area/cell.area > .3]
        require(sorted(float(r.height) for r in contributors) == sorted(float(s[1]) for s in segments[i, j]),
                'cell.contributors', 'source footprints and engine segments differ')
        require(all(segments[i, j][k][0] == 0 for k in range(len(segments[i, j]))), 'segments', 'nonzero base')
        for r in contributors:
            # Per-segment voxel endpoint, not the tallest anonymous class voxel
            # attributed to a possibly different last-wins owner.
            edge = d0_effective + int(ground_indices[i, j]) + int(float(r.height)+.5)
            source_top_errors.append(edge-next(d['z_top_abs'] for d in details if d['id'] == int(r.id)))
        cells.append(dict(i=int(i), j=int(j), owner_id=int(ids[i, j]),
                          contributor_ids=[int(r.id) for r in contributors], segments=segments[i, j]))
    qa['source_roof_segment_edge_minus_H_m'] = distribution(source_top_errors)
    qa['source_roof_segment_max_error_m'] = max(map(abs, source_top_errors))
    require(qa['source_roof_segment_max_error_m'] <= 2., 'source.roof', 'source roof/voxel segment discrepancy over 2m')
    require(max(abs(r['bottom_minus_effective_ground_m']) for r in details) <= 3.,
            'source.bottom', 'source bottom/effective ground discrepancy over exploratory 3m review threshold')
    qa.update(source_H_transform='NONE; Standard bytes read only', independent_cell_contributors='PASS',
              building_id_bijection='PASS', original_geometry_clipping='NONE', missing_buildings=[])
    for field in next(iter(attrs.values())):
        frame[field] = [attrs[int(i)][field] for i in frame.id]
    azimuth, _, _ = Geod(ellps='WGS84').inv(*rectangle[0], *rectangle[1])
    grid = dict(schema='ouem-real-komae-voxcity-grid/v0.1', nominal_voxel_size_m=1.,
                axes=['u approximately north', 'v approximately east', 'up'], layout='uv_m/SOUTH_UP',
                rectangle_crs='EPSG:4326', rectangle_vertices_lonlat=rectangle,
                origin_lonlat=origin.tolist(), u_step_lonlat=u.tolist(), v_step_lonlat=v.tolist(),
                adjusted_horizontal_mesh_m=list(map(float, geom['adj_mesh'])), shape=list(voxels.shape),
                projected_reference_crs='EPSG:6677', projected_domain_bounds=list(DOMAIN),
                projected_evaluation_ROI_bounds=list(ROI), halo_m=32, evaluation_cell_count=int(roi_mask.sum()),
                centre_mapping='origin+(i+0.5)*u_step+(j+0.5)*v_step; no flip/transpose',
                axis0_true_azimuth_deg=float(azimuth),
                D0_raw_H_m=float(dem.min()), D0_effective_H_m=d0_effective,
                z_edge_mapping='D0_effective_H_m+k*1m; centre adds 0.5m',
                ground_semantics='process_grid: raw DEM conditioned to per-owner building mean then minimum-normalized; surface upper edge round(float32(D_eff))+1 for numba, building starts above surface',
                terrain_sampling='EPSG:4326 actual engine centres -> EPSG:6677, containing source pixel (nearest); no fill/resampling of Standard',
                reuse='Use saved lon/lat and projected centre arrays, ROI mask, raw Terrain and effective Terrain; do not substitute a projected north-up grid. Adding canopy must retain the same IDs and D0/effective ground or re-audit.')
    values, counts = np.unique(voxels, return_counts=True)
    metadata = dict(grid=grid, qa=qa, building_inventory=inventory, selected_buildings=details,
                    ownership_iterations=iterations, class_counts={str(int(k)): int(v) for k, v in zip(values, counts)},
                    class_codes={'0':'air', '1':'common Bareland surface (unobserved)', '-1':'subsurface', '-3':'building'},
                    raw_terrain=distribution(dem), effective_ground_H=distribution(conditioned),
                    engine_ground_conditioning_delta_m=distribution(conditioned-dem), numba=NUMBA_AVAILABLE,
                    valid_dem_centres=int(dem.size), invalid_dem_centres=0,
                    limitations=['2.5D whole footprint and one roof proxy per source Building; original LoD2 shapes stay in unchanged Standard.',
                                 'Voxel classes carry no Building ID; separate last-wins ID and contributor grids bind identities.',
                                 'Boundary-crossing geometry is retained; only intersecting computation cells are voxelized.',
                                 'Source-declared H/T.P. compatibility and numerical diagnostics are not survey verification.',
                                 '32m halo is a chosen geometry domain, not demonstrated sufficient for future solar conditions.',
                                 'No canopy, solar, land-cover observations, visual/formal acceptance or eligibility approval.'])
    arrays = dict(voxels=voxels, building_ids=ids, building_heights=heights, terrain_H=dem,
                  effective_dem=effective, effective_ground_H=conditioned, ground_indices=ground_indices,
                  centre_lon=geom['lons'], centre_lat=geom['lats'], centre_x=x, centre_y=y, roi_mask=roi_mask)
    return arrays, metadata, frame, cells


def export_outputs(run, arrays, metadata, frame, cells):
    write(run/'grid.json', metadata['grid'])
    for name, array in arrays.items():
        with (run/(name+'.npy')).open('xb') as stream: np.save(stream, array, allow_pickle=False)
        require(np.array_equal(array, np.load(run/(name+'.npy'), allow_pickle=False)), 'readback', name)
    write(run/'building_segments.json', dict(shape=list(arrays['building_ids'].shape), cells=cells))
    frame.to_file(run/'whole_building_footprints.geojson', driver='GeoJSON')
    # An exact affine exists in lon/lat. Write rows north-to-south by reversing
    # u, with columns along v. EPSG:6677 needs nonlinear reprojection; avoid a
    # misleading projected affine. Original uv arrays remain authoritative.
    g = metadata['grid']; origin = np.asarray(g['origin_lonlat']); u = np.asarray(g['u_step_lonlat']); v = np.asarray(g['v_step_lonlat'])
    start = origin+arrays['terrain_H'].shape[0]*u
    transform = Affine(v[0], -u[0], start[0], v[1], -u[1], start[1])
    for name in ('terrain_H', 'effective_ground_H', 'building_ids', 'building_heights', 'roi_mask'):
        raster = arrays[name][::-1, :].copy()
        if raster.dtype == bool: raster = raster.astype('uint8')
        with rasterio.open(run/(name+'.tif'), 'w', driver='GTiff', width=raster.shape[1], height=raster.shape[0],
                           count=1, dtype=raster.dtype, crs='EPSG:4326', transform=transform) as ds:
            ds.write(raster, 1)
            ds.update_tags(layout='row reversed u; column v; exact engine lon/lat affine', source='experimental MODEL diagnostic; not Standard')
        with rasterio.open(run/(name+'.tif')) as ds:
            require(np.array_equal(ds.read(1), raster), 'GeoTIFF.readback', name)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, key, title in zip(axes, ('terrain_H', 'building_ids', 'building_heights'), ('Raw Terrain H', 'VoxCity owner ID', 'Relative Building height')):
        im = ax.imshow(arrays[key], origin='lower', interpolation='nearest')
        ax.contour(arrays['roi_mask'], levels=[.5], colors='red', linewidths=1)
        ax.set_title(title); ax.set_xlabel('v / approximately east'); ax.set_ylabel('u / approximately north')
        fig.colorbar(im, ax=ax)
    fig.tight_layout(); fig.savefig(run/'plan.png', dpi=150); plt.close(fig)
    occupied = np.argwhere(arrays['building_ids'] > 0)
    cut = int(np.median(occupied[:, 1]))
    d0 = g['D0_effective_H_m']
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.imshow(arrays['voxels'][:, cut, :].T, origin='lower', aspect='auto', interpolation='nearest',
              extent=[0, arrays['voxels'].shape[0], d0, d0+arrays['voxels'].shape[2]],
              cmap=ListedColormap(['#db8e34', '#775c44', '#ffffff', '#80a565']),
              norm=BoundaryNorm([-3.5, -2, -.5, .5, 1.5], 4))
    ax.plot(np.arange(arrays['terrain_H'].shape[0])+.5, arrays['terrain_H'][:, cut], label='raw DEM H', color='blue')
    ax.plot(np.arange(arrays['terrain_H'].shape[0])+.5, arrays['effective_ground_H'][:, cut], label='engine conditioned ground H', color='red')
    ax.set_title(f'Actual VoxCity section v={cut}; nominal index-edge H; ground +1 layer retained')
    ax.set_xlabel('u / approximately north'); ax.set_ylabel('H (m)'); ax.legend()
    fig.tight_layout(); fig.savefig(run/'section.png', dpi=150); plt.close(fig)
    metadata['section_fixed_v_index'] = cut
    metadata['GeoTIFF'] = dict(crs='EPSG:4326', affine=list(transform)[:6],
                               array_mapping='raster[row,col] = uv[n_u-1-row,col]; exact geographic affine, not a regular EPSG:6677 grid')


def run(args):
    run_dir = args.run_dir.resolve(); run_dir.mkdir()  # no overwrite/resume
    report = dict(status='RUNNING', source_h_eligibility='NOT_ESTABLISHED', formal_acceptance='NOT_VERIFIED',
                  phase5_gates=dict.fromkeys(('A1','A2','A3','A4'), 'OPEN'), started_at=datetime.now(timezone.utc).isoformat())
    started = time.perf_counter()
    watch = None
    try:
        report['environment'] = environment()
        require(report['environment']['voxcity']['verified'], 'VoxCity', 'fixed engine provenance failed')
        consumer = validate_source_h_standard(args.building_manifest.resolve(), args.artifact_root.resolve(),
                    SOURCE_H_PROFILE, study_area_config=args.study_area.resolve())
        report['consumer'] = consumer
        require(consumer['technical_validation'] == 'PASS', 'Consumer', str(consumer['issues']))
        watch = Watch(args.artifact_root.resolve())
        manifest = None
        for key, identity in consumer['artifacts'].items():
            value = watch.capture(key, identity['path'], identity['sha256'], identity['size_bytes'], json_data=key == 'standard_manifest')
            require(watch.identities[key] == identity, key, 'changed since Consumer observation')
            if key == 'standard_manifest': manifest = value
        require(manifest is not None, 'manifest', 'missing Standard record')
        for key, path in (('terrain_manifest', args.terrain.with_suffix('.tif.manifest.json')), ('terrain', args.terrain),
                          ('roi_definition', Path(sys.modules['ouem.canopy_shadow_poc'].__file__)),
                          ('implementation', Path(__file__))):
            value = watch.capture(key, path.resolve().relative_to(watch.root).as_posix(), json_data=key == 'terrain_manifest')
            if key == 'terrain_manifest': terrain_meta = value
        require(terrain_meta['schema'] == 'ouem-standard-terrain-manifest/v0.1' and
                terrain_meta['standard']['sha256'] == watch.identities['terrain']['sha256'] and
                terrain_meta['standard']['crs'] == 'EPSG:6677', 'Terrain', 'manifest/hash/CRS mismatch')
        require(terrain_meta['vertical_reference']['status'] in ('source-declared', 'verified') and
                terrain_meta['vertical_reference']['name'] == 'T.P. (Tokyo Peil / Tokyo Bay mean sea level)' and
                bool(terrain_meta['vertical_reference']['source']) and manifest['vertical_crs'] == 'EPSG:6695',
                'vertical', 'explicit Komae source-declared H/T.P. compatibility required')
        features = read_standard(watch.resolve(manifest['standard_output']['path']), 'building')
        coordinates = np.asarray([p for tree, _, _ in features.values() for p in points(tree)])
        building_bounds = [float(coordinates[:, 0].min()), float(coordinates[:, 1].min()),
                           float(coordinates[:, 0].max()), float(coordinates[:, 1].max())]
        with rasterio.open(args.terrain) as ds:
            terrain_bounds = list(ds.bounds)
        require(box(*building_bounds).intersects(box(*terrain_bounds)),
                'preflight.overlap', 'Building/Terrain horizontal extents do not overlap')
        require(box(*manifest['study_area']['extent']).covers(box(*DOMAIN)) and box(*DOMAIN).covers(box(*ROI)),
                'domain', 'existing ROI/domain must lie inside study area')
        report['preflight'] = dict(status='PASS', standard_features=len(features), ROI=list(ROI), domain=list(DOMAIN),
                                   building_manifest=manifest['standard_output'], terrain_vertical=terrain_meta['vertical_reference'],
                                   building_bounds=building_bounds, terrain_bounds=terrain_bounds, horizontal_overlap=True)
        arrays, meta, frame, cells = execute_model(features, args.terrain.resolve())
        watch.unchanged()
        export_outputs(run_dir, arrays, meta, frame, cells)
        report.update(model=meta, status='COMPLETED', input_artifacts=watch.identities)
        watch.unchanged()
        require(voxcity_provenance() == report['environment']['voxcity'], 'engine', 'engine changed during run')
        report['input_immutability'] = 'PASS'
    except Exception as exc:
        report.update(status='FAILED', error=str(exc))
        raise
    finally:
        report['elapsed_seconds'] = time.perf_counter()-started
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        report['outputs'] = {p.name: dict(sha256=digest(p), size_bytes=p.stat().st_size) for p in run_dir.iterdir() if p.is_file()}
        write(run_dir/'report.json', report)
        with (run_dir/'RESULTS.md').open('x', encoding='utf-8') as stream:
            stream.write(f"# Real Komae Building + Terrain VoxCity\n\nStatus: {report['status']}\n\n"
                         "See report.json for fresh Consumer, input fingerprints, actual grid, ID/ground/roof and scalar voxel QA.\n\n"
                         "![Plan](plan.png)\n\n![Section](section.png)\n\n"
                         "No canopy/solar. Eligibility NOT_ESTABLISHED; formal acceptance NOT_VERIFIED; Phase 5 gates OPEN.\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run-dir', 'building-manifest', 'terrain', 'study-area', 'artifact-root'):
        parser.add_argument('--'+key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
