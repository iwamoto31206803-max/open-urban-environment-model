"""Fixed-condition synthetic Building A/B analysis using the actual VoxCity solar API."""
from dataclasses import dataclass
import hashlib
import io
import math

import numpy as np

from ouem.adapters.source_h_synthetic_voxel import voxelize_synthetic_source_h, _source_identity
from ouem.native.building.source_h_geometry import require


@dataclass
class SyntheticSolarResult:
    terrain_only: np.ndarray
    with_buildings: np.ndarray
    reduction: np.ndarray  # A-B, positive means less horizontal direct irradiance
    valid_ground: np.ndarray
    building_ids: np.ndarray
    metadata: dict


def run_synthetic_building_solar(standard_manifest, artifact_root, study_area_config, *,
                                 terrain, synthetic_source_ids):
    """Fixed artificial sun135°/35°, DNI800; no real weather/time or canopy physics.

    Consumer, 2.5D and actual voxelization run upstream. Case A changes ONLY
    Building=-3 to air=0. Both get the same two top air layers and ground mask.
    """
    from voxcity.models import VoxCity, VoxelGrid, GridMetadata, BuildingGrid, LandCoverGrid, DemGrid, CanopyGrid
    from voxcity.simulator.solar.radiation import get_direct_solar_irradiance_map
    from voxcity.simulator.solar.kernels import compute_direct_solar_irradiance_map_binary
    from voxcity.simulator.common.raytracing import trace_ray_generic
    from voxcity.utils.orientation import direction_to_axis_vector

    model = voxelize_synthetic_source_h(standard_manifest,artifact_root,study_area_config,
        terrain=terrain,synthetic_source_ids=synthetic_source_ids)
    buffer=io.BytesIO();np.save(buffer,model.voxels,allow_pickle=False)
    base_sha=hashlib.sha256(buffer.getvalue()).hexdigest()
    b=np.pad(model.voxels,((0,0),(0,0),(0,2)),constant_values=0)
    a=b.copy();a[a==-3]=0
    require(np.array_equal(a[b!=-3],b[b!=-3]),'case_pair','non-Building classes changed')
    ids=model.building_ids
    valid=ids==0  # explicit SAME physical ground columns; never infer from finite result alone
    require(valid.any() and np.all(a[:,:,0]==1) and np.all(b[:,:,0]==1)
            and np.all(a[valid,1:3]==0) and np.all(b[valid,1:3]==0),
            'observer','common ground transition and observer air cells required')
    azimuth,elevation,dni,requested_height=135.,35.,800.,1.5
    rotation=model.metadata['grid']['axis0_true_azimuth_deg']
    angle=math.radians(azimuth-rotation);alt=math.radians(elevation)
    direction=np.array([math.cos(alt)*math.cos(angle),math.cos(alt)*math.sin(angle),math.sin(alt)])
    require(np.allclose(direction,direction_to_axis_vector(azimuth,elevation,rotation),rtol=0,atol=1e-12),
            'sun','independent clockwise true-north direction differs from public helper')
    rectangle=model.metadata['grid']['rectangle_vertices']
    bounds=(min(p[0] for p in rectangle),min(p[1] for p in rectangle),
            max(p[0] for p in rectangle),max(p[1] for p in rectangle))
    meta=GridMetadata('EPSG:4326',bounds,1.)
    def scene(voxels,with_buildings):
        height=model.building_heights.copy() if with_buildings else np.zeros(ids.shape)
        owner=ids.copy() if with_buildings else np.zeros_like(ids)
        segments=np.empty(ids.shape,dtype=object)
        for i,j in np.ndindex(ids.shape):
            segments[i,j]=[[0.,float(height[i,j])]] if owner[i,j] else []
        return VoxCity(VoxelGrid(voxels,meta),BuildingGrid(height,segments,owner,meta),
            LandCoverGrid(np.ones(ids.shape,dtype=np.int64),meta),DemGrid(model.effective_dem.copy(),meta),
            CanopyGrid(np.zeros(ids.shape),meta,bottom=np.zeros(ids.shape)),
            extras={'rotation_angle':rotation,'rectangle_vertices':rectangle,
                    'D0_effective_H_m':model.metadata['vertical']['D0_effective_H_m']})
    before_a,before_b=a.copy(),b.copy()
    kwargs=dict(show_plot=False,view_point_height=requested_height,include_building_roofs=False,
                tree_k=.6,tree_lad=1.)  # irrelevant optical defaults: no TREE voxels
    raw_a=get_direct_solar_irradiance_map(scene(a,False),azimuth,elevation,dni,**kwargs)
    raw_b=get_direct_solar_irradiance_map(scene(b,True),azimuth,elevation,dni,**kwargs)
    require(np.array_equal(a,before_a) and np.array_equal(b,before_b),'read_only','solar mutated voxel inputs')
    require(raw_a.shape==raw_b.shape==ids.shape,'solar_shape','solar output grid mismatch')
    require(np.isfinite(raw_a).all() and np.array_equal(np.isfinite(raw_b),valid),
            'solar_validity','unexpected API NaN/nonfinite cells; do not silently change comparison mask')
    baseline=dni*math.sin(alt)
    tolerance=1e-9  # W/m2 arithmetic budget, not ecological/measurement acceptance
    require(np.allclose(raw_a,baseline,rtol=0,atol=tolerance), 'baseline','flat unobstructed DNI*sin(elevation) mismatch')
    solar_a=np.where(valid,raw_a,np.nan);solar_b=np.where(valid,raw_b,np.nan)
    reduction=solar_a-solar_b
    require(np.all((solar_b[valid]>=-tolerance)&(solar_b[valid]<=baseline+tolerance))
            and np.all(reduction[valid]>=-tolerance),'solar_range','invalid irradiance or increase')
    shadow=valid & (reduction>tolerance)
    require(shadow.any(),'shadow','actual API did not detect Building shade')

    # Coarse PLANAR QA, not a ray tracer: a shaded sample must have a Building
    # column toward the sun within the horizontal cell-square lateral radius.
    shadow_points=np.argwhere(shadow).astype(float)
    building_points=np.argwhere(ids>0).astype(float)
    delta=building_points[None,:,:]-shadow_points[:,None,:]
    sun_xy=direction[:2]/np.linalg.norm(direction[:2])
    forward=delta@sun_xy
    lateral=np.abs(delta[:,:,0]*sun_xy[1]-delta[:,:,1]*sun_xy[0])
    min_lateral=np.min(np.where(forward>0,lateral,np.inf),axis=1)
    require(np.all(min_lateral<=math.sqrt(2)/2+1e-8),'shadow_direction',
            'shade lacks a sunward Building column in the cell-width corridor')
    du,dv=model.metadata['grid']['adjusted_horizontal_mesh_m']
    nvalid,nshadow=int(valid.sum()),int(shadow.sum())
    boundary=np.zeros(ids.shape,dtype=bool);boundary[[0,-1],:]=True;boundary[:,[0,-1]]=True
    observer_index=1+int(requested_height)  # kernel transition z1 plus integer view height
    observer_centre=observer_index+.5  # trace_ray_generic adds half a cell
    d0=model.metadata['vertical']['D0_effective_H_m']
    metadata={'technical_validation':'PASS','scope':'synthetic-building-direct-solar/v0.1',
        'solar_api':'voxcity.simulator.solar.radiation.get_direct_solar_irradiance_map',
        'actual_api_calls':2,'voxelization':model.metadata,'base_voxel_npy_sha256':base_sha,
        'grid':dict(model.metadata['grid'],shape=list(b.shape)),
        'case_pair':{'method':'A = B with BUILDING -3 replaced by air0; all other classes unchanged',
            'common_top_air_layers_added':2,'common_ground_H_m':d0,'same_observer_on_common_mask':True},
        'sun':{'true_azimuth_clockwise_deg':azimuth,'elevation_deg':elevation,'DNI_W_m2':dni,
            'artificial_condition':True,'date_weather_observation':None,'rotation_angle_clockwise_deg':rotation,
            'ray_toward_sun_uv_up':direction.tolist(),'expected_flat_horizontal_W_m2':baseline},
        'observer':{'api_requested_height_m':requested_height,'include_building_roofs':False,
            'first_air_transition_k':1,'integer_height_offset':int(requested_height),
            'API_origin_index_k':observer_index,'DDA_origin_cell_centre_k':observer_centre,
            'nominal_origin_H_m':d0+observer_centre,'nominal_origin_above_source_ground_m':observer_centre,
            'interpretation':'same grid-cell centres in both cases; requested1.5m is not exact physical1.5m'},
        'results':{'valid_ground_cells':nvalid,'excluded_building_columns':int((ids>0).sum()),
            'shadow_cells':nshadow,'shadow_fraction_of_valid_ground':nshadow/nvalid,
            'shadow_area_nominal_m2':float(nshadow),'shadow_area_adjusted_approx_m2':float(nshadow*du*dv),
            'shadow_cells_on_domain_boundary':int((shadow&boundary).sum()),
            'boundary_shadow_counts':{'south_i0':int(shadow[0,:].sum()),'north_i_last':int(shadow[-1,:].sum()),
                                     'west_j0':int(shadow[:,0].sum()),'east_j_last':int(shadow[:,-1].sum())},
            'maximum_reduction_W_m2':float(np.max(reduction[valid])),
            'mean_reduction_valid_ground_W_m2':float(np.mean(reduction[valid])),
            'mean_reduction_shadow_only_W_m2':float(np.mean(reduction[shadow])),
            'mean_A_W_m2':float(np.mean(solar_a[valid])),'mean_B_W_m2':float(np.mean(solar_b[valid])),
            'raw_API_nan_counts':{'A':int(np.isnan(raw_a).sum()),'B':int(np.isnan(raw_b).sum())},
            'saved_common_mask_nan_counts':{'A':int(np.isnan(solar_a).sum()),'B':int(np.isnan(solar_b).sum())}},
        'qa':{'baseline':'PASS','same_grid_ground_and_observer':'PASS','shadow_direction_corridor':'PASS',
            'shadow_corridor_max_min_lateral_cells':float(min_lateral.max()),
            'unexpected_invalid_valid_ground_cells':0,'irradiance_increase_cells':int((reduction[valid]<-tolerance).sum()),
            'numeric_tolerance_W_m2':tolerance,'reduction_definition':'A-B; positive = less horizontal direct irradiance'},
        # Numba dispatcher is not inspectable as a Python function; py_func is
        # used ONLY to identify source bytes, never to execute a fallback solver.
        'sources':[_source_identity(getattr(f,'py_func',f)) for f in (get_direct_solar_irradiance_map,
            direction_to_axis_vector,compute_direct_solar_irradiance_map_binary,trace_ray_generic)],
        'source_h_eligibility':'NOT_ESTABLISHED','human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED',
        'phase5_gates':dict.fromkeys(('A1','A2','A3','A4'),'OPEN'),
        'limitations':['Synthetic, constant artificial sun only; no real-data/scientific or formal acceptance.',
            'No canopy, diffuse/reflected/global radiation, weather/time series or thermal analysis.',
            'Inherited surface+1 and Building rounding retained; observer origin is discretized.',
            'Finite64m scene: outside occluders absent, no halo-convergence or general boundary sufficiency claim.',
            'Planar corridor is coarse direction QA, not independent exact-shadow/irradiance validation.']}
    return SyntheticSolarResult(solar_a,solar_b,reduction,valid,ids.copy(),metadata)
