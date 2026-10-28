"""Minimal synthetic flat-ground connection to pinned VoxCity public generators."""
from dataclasses import dataclass
import hashlib
from importlib.metadata import distribution, version
import inspect
import json

import numpy as np
from pyproj import Transformer, Geod
from shapely.geometry import Polygon

from ouem.adapters.source_h_synthetic import adapt_synthetic_source_h
from ouem.native.building.source_h_geometry import require

PIN = 'fa212656305328a9a657973bae26f352bfe813bc'


@dataclass
class SyntheticVoxelResult:
    voxels: np.ndarray
    building_ids: np.ndarray
    building_heights: np.ndarray
    terrain_H: np.ndarray
    effective_dem: np.ndarray
    metadata: dict


def _source_identity(function):
    path = inspect.getsourcefile(function)
    with open(path,'rb') as stream:
        digest = hashlib.sha256(stream.read()).hexdigest()
    return {'module':function.__module__,'name':function.__name__,'sha256':digest}


def voxelize_synthetic_source_h(standard_manifest, artifact_root, study_area_config, *,
                               terrain, synthetic_source_ids):
    """Fresh Consumer → 2.5D → public raster → authored engine DEM → real Voxelizer.

    No diagnostic EPSG:6677 arrays are used as engine inputs. No canopy/solar.
    Synthetic-only ordinary grounded buildings on a complete constant-H plane.
    """
    from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon, process_grid
    from voxcity.geoprocessor.raster.core import compute_cell_center_coords
    from voxcity.generator.voxelizer import Voxelizer, NUMBA_AVAILABLE

    direct = json.loads(distribution('voxcity').read_text('direct_url.json'))
    require(version('voxcity')=='1.7.0' and direct.get('vcs_info',{}).get('commit_id')==PIN,
            'voxcity','installed version/direct-URL commit must match pin')
    model = adapt_synthetic_source_h(standard_manifest,artifact_root,study_area_config,
        terrain=terrain,synthetic_source_ids=synthetic_source_ids)
    require(terrain.resolution==1.,'voxel_size','initial synthetic case is1m')
    xmin,ymin,xmax,ymax = terrain.bounds
    project = Transformer.from_crs(6677,4326,always_xy=True)
    rectangle = [project.transform(x,y) for x,y in ((xmin,ymin),(xmin,ymax),(xmax,ymax),(xmax,ymin))]
    heights,segments,ids,filtered = create_building_height_grid_from_gdf_polygon(
        model.voxcity_buildings.copy(),1.,rectangle,overlapping_footprint=True)
    expected_ids = {int(r.id) for r in model.buildings.itertuples()}
    require(set(np.unique(ids))=={0,*expected_ids} and set(filtered.id)==expected_ids,
            'building_ids','engine lost or remapped a Building')
    geom = compute_cell_center_coords(rectangle,1.)
    require(heights.shape==ids.shape==segments.shape==tuple(geom['grid_size']),
            'engine_grid','raster and coordinate geometry shapes differ')
    # This is a NEW authored constant plane on the ACTUAL engine grid, not
    # resampling/reusing the unrelated projected centre-sampled arrays.
    dem = np.full(ids.shape,terrain.elevation_H,dtype=np.float64)
    d0 = float(dem.min())
    effective = process_grid(ids,dem-d0)
    require(np.all(effective==0),'ground','flat plane conditioning unexpectedly changed')
    cover = np.ones(ids.shape,dtype=np.int64)  # authored Standard Bareland=1
    trees = np.zeros(ids.shape,dtype=np.float64)
    voxels = Voxelizer(1.,'Standard').generate_combined(
        heights.copy(),segments.copy(),ids.copy(),cover,dem.copy(),trees,print_class_info=False)
    require(voxels.ndim==3 and voxels.shape[:2]==ids.shape,'voxels','3D engine output required')

    # Independent scalar-rule oracle AFTER actual engine execution. It is a QA
    # reference, never the returned/generated model. Full array equality catches
    # classification, position, clipping and outside-footprint leakage.
    expected = np.zeros_like(voxels)
    expected[:,:,0] = 1
    details = []
    origin,u,v = (np.asarray(geom[k],dtype=float) for k in ('origin','u_vec','v_vec'))
    du,dv = map(float,geom['adj_mesh'])
    for row in model.voxcity_buildings.itertuples():
        mask = ids==row.id
        require(np.all(heights[mask]==row.height) and all(cell==[[0.,row.height]] for cell in segments[mask]),
                row.source_id,'engine height/segment changed')
        high = int(float(row.height)+.5)  # positive h,1m; pinned half-up integer rule
        require(high>0 and 1+high<=voxels.shape[2],row.source_id,'invalid/clipped vertical extent')
        expected[mask,1:1+high] = -3
        fractions = []
        for i,j in np.argwhere(mask):
            a = origin+i*du*u+j*dv*v
            cell = Polygon([a,a+du*u,a+du*u+dv*v,a+dv*v])
            fractions.append(row.geometry.intersection(cell).area/cell.area)
        require(min(fractions)>.3,row.source_id,'owned engine cell does not meet footprint intersection rule')
        occupied = voxels[mask]==-3
        require(int(occupied.sum())==int(mask.sum())*high,row.source_id,'Building count/height mismatch')
        details.append({'source_id':row.source_id,'ouem_id':row.ouem_id,'id':int(row.id),
            'input_max_H_m':float(row.z_top_abs),'ground_H_m':d0,'relative_height_m':float(row.height),
            'horizontal_cells':int(mask.sum()),'building_voxels':int(occupied.sum()),
            'k_start_inclusive':1,'k_end_exclusive':1+high,'occupied_thickness_m':float(high),
            'height_rounding_delta_m':float(high-row.height),'surface_layer_shift_m':1.,
            'nominal_index_edge_H_bottom_m':d0+1,'nominal_index_edge_H_top_m':d0+1+high,
            'top_edge_minus_input_H_m':float(d0+1+high-row.z_top_abs),
            'minimum_owned_cell_footprint_fraction':float(min(fractions))})
    require(np.array_equal(voxels,expected),'voxel_qa','actual engine output differs from independent scalar oracle')
    require(not np.any(voxels[ids==0]==-3) and not np.any(voxels[:,:,0]==-3),
            'placement','unexpected Building outside ownership or in ground layer')
    require(all(not cell for cell in segments[ids==0]) and np.all(heights[ids==0]==0),
            'background','unexpected background segments/heights')
    azimuth,_,_ = Geod(ellps='WGS84').inv(*rectangle[0],*rectangle[1])
    sources = [_source_identity(f) for f in (create_building_height_grid_from_gdf_polygon,
        compute_cell_center_coords,process_grid,Voxelizer.generate_combined)]
    values,counts = np.unique(voxels,return_counts=True)
    metadata = {'technical_validation':'PASS','scope':'synthetic-flat-ground-voxcity-voxel/v0.1',
        'consumer_validation':model.summary['consumer_validation'],'input_artifacts':model.summary['input_artifacts'],
        'voxcity':{'version':version('voxcity'),'commit':PIN,'numba_available':NUMBA_AVAILABLE,
            'raster_api':'create_building_height_grid_from_gdf_polygon(overlapping_footprint=True)',
            'voxel_api':'Voxelizer(1.0, Standard).generate_combined','sources':sources},
        'grid':{'axes':['u (approximately north)','v (approximately east)','up'],
            'layout':'uv_m/SOUTH_UP; no flip/transpose between engine raster and voxels',
            'shape':list(voxels.shape),'dtype':str(voxels.dtype),'nominal_voxel_size_m':1.,
            'rectangle_crs':'EPSG:4326','rectangle_vertices':rectangle,'origin_lonlat':origin.tolist(),
            'u_vector_lonlat_per_m':u.tolist(),'v_vector_lonlat_per_m':v.tolist(),
            'adjusted_horizontal_mesh_m':[du,dv],'axis0_true_azimuth_deg':float(azimuth),
            'centre_mapping':'origin+(i+0.5)*du*u+(j+0.5)*dv*v; k increases upward',
            'projected_diagnostic_arrays_used':False},
        'vertical':{'quantity':'gravity_related_height','crs':'EPSG:6695','unit':'metre',
            'authored_declaration':terrain.declaration,
            'authored_ground_H_m':d0,'D0_raw_H_m':d0,'D0_effective_H_m':d0,
            'effective_dem_min_max_m':[float(effective.min()),float(effective.max())],
            'ground_index':0,'ground_level_exclusive':1,
            'nominal_index_edge_H':'D0_effective + k*1m; centre is D0_effective+(k+0.5)*1m',
            'interpretation':'nominal cell-edge mapping, not calibrated physical Z; retained +1 surface layer and round error are reported, not corrected',
            'terrain_method':'new authored constant on engine grid; no diagnostic array copying or real DEM sampling'},
        'class_codes':{'0':'air','1':'authored Bareland surface','-1':'ground/subsurface (none here)','-2':'TREE (none)','-3':'BUILDING'},
        'class_counts':{str(int(v)):int(n) for v,n in zip(values,counts)},'buildings':details,
        'qa':{'full_array_scalar_oracle':'PASS','both_building_ids':'PASS','actual_footprint_intersections':'PASS',
            'outside_building_and_ground_layer_leakage':'NONE'},
        'source_h_eligibility':'NOT_ESTABLISHED','human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED',
        'phase5_gates':dict.fromkeys(('A1','A2','A3','A4'),'OPEN'),
        'limitations':['Synthetic flat Terrain only; no real-data eligibility or acceptance.',
            'Projected diagnostic and geographic engine grids are distinct; no cross-grid array fusion.',
            'Voxel class array has no Building IDs: bind separate engine ID grid and mapping.',
            'Ground+1 layer shifts nominal top in addition to rounding; no physical-height correction applied.',
            'No solar/observer validation, canopy, sloped/NoData Terrain, general overlap or rare geometry.']}
    return SyntheticVoxelResult(voxels,ids.astype(np.int64),heights,dem,effective,metadata)
