"""Experimental, synthetic-only flat-ground 2.5D preparation; no engine execution."""
from dataclasses import dataclass
import math

import geopandas as gpd
import numpy as np
from shapely import covers, points
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from ouem.consumers.source_h_standard import (
    SOURCE_H_PROFILE, Watch, validate_source_h_standard,
)
from ouem.consumers._source_h_geometry import read_standard
from ouem.native.building.source_h_geometry import require
from ouem.standardize.building import deterministic_ouem_id
from ouem.adapters.voxcity import numeric_id_mapping, derive_attributes


@dataclass(frozen=True)
class FlatSyntheticTerrain:
    """Authored constant H on a north-up EPSG:6677 diagnostic grid, not Standard Terrain."""
    bounds: tuple[float, float, float, float]
    resolution: float
    elevation_H: float
    vertical_crs: str
    vertical_quantity: str
    vertical_unit: str
    declaration: str


@dataclass
class SyntheticBuildingResult:
    buildings: gpd.GeoDataFrame  # whole 2D support, EPSG:6677
    voxcity_buildings: gpd.GeoDataFrame  # public raster API input shape, EPSG:4326
    terrain_H: np.ndarray  # north-up; diagnostic, NOT an engine grid
    building_ids: np.ndarray  # same north-up grid; cell-centre ownership
    summary: dict


def _surfaces(tree):
    if tree[0]=='Polygon':
        yield tree[1]
    else:
        for child in tree[1]:
            yield from _surfaces(child)


def _footprint(tree):
    retained, zs, walls = [], [], 0
    for rings in _surfaces(tree):
        zs.extend(p[2] for ring in rings for p in ring)
        face = Polygon([p[:2] for p in rings[0]], [[p[:2] for p in r] for r in rings[1:]])
        if face.area==0:
            walls += 1
            continue
        require(face.is_valid, 'footprint', 'invalid positive-area XY face; no repair supported')
        retained.append(face)
    require(retained, 'footprint', 'no positive-area XY surfaces')
    footprint = unary_union(retained)
    require(footprint.is_valid and not footprint.is_empty
            and footprint.geom_type in ('Polygon','MultiPolygon'), 'footprint', 'invalid 2.5D support')
    return footprint, zs, walls


def adapt_synthetic_source_h(standard_manifest, artifact_root, study_area_config, *,
                             terrain: FlatSyntheticTerrain, synthetic_source_ids):
    """Validate fresh bytes, derive full footprints/relative heights, return in-memory data.

    Explicit synthetic_source_ids is an authored scope declaration, NOT automatic
    detection/authentication of synthetic data or source-H eligibility approval.
    Neither the consumer nor Adapter v0.1 is changed or bypassed.
    """
    consumer = validate_source_h_standard(standard_manifest,artifact_root,SOURCE_H_PROFILE,
        study_area_config=study_area_config)
    require(consumer['technical_validation']=='PASS', 'consumer', str(consumer['issues']), 'CONSUMER_FAILED')

    # Bind every consumed artifact to the successful observation, not merely a
    # caller-supplied PASS dict. Recheck at use and after reading/deriving output.
    watch = Watch(artifact_root)
    manifest = None
    for key, identity in consumer['artifacts'].items():
        value = watch.capture(key,identity['path'],identity['sha256'],identity['size_bytes'],
                              json_data=key=='standard_manifest')
        require(watch.identities[key]==identity,key,'changed since Consumer validation','INPUT_CHANGED')
        if key=='standard_manifest':
            manifest = value
    require(manifest is not None,'manifest','missing Consumer input identity')
    require(isinstance(terrain,FlatSyntheticTerrain),'terrain','authored flat synthetic Terrain required')
    require((terrain.vertical_crs,terrain.vertical_quantity,terrain.vertical_unit)==
            (manifest['vertical_crs'],manifest['vertical_quantity'],manifest['vertical_unit']),
            'terrain.vertical_reference','explicit Building/Terrain H declarations must agree','VERTICAL_MISMATCH')
    require(isinstance(terrain.declaration,str) and terrain.declaration.strip(),
            'terrain.declaration','authored synthetic datum/ground declaration required')
    xmin,ymin,xmax,ymax = terrain.bounds
    require(all(type(v) in (float,int) and math.isfinite(v)
                for v in (*terrain.bounds,terrain.resolution,terrain.elevation_H)), 'grid','finite scalars required')
    require(xmin<xmax and ymin<ymax and terrain.resolution>0,'grid','positive bounds/resolution required')
    width,height = (xmax-xmin)/terrain.resolution,(ymax-ymin)/terrain.resolution
    require(width.is_integer() and height.is_integer() and width*height<=65536,
            'grid','integer dimensions, at most65536 synthetic cells')
    cols,rows = int(width),int(height)
    dem = np.full((rows,cols),terrain.elevation_H,dtype=np.float64)
    ids = np.zeros((rows,cols),dtype=np.int64)
    x = xmin+(np.arange(cols)+.5)*terrain.resolution
    y = ymax-(np.arange(rows)+.5)*terrain.resolution
    xx,yy = np.meshgrid(x,y)
    centres = points(xx,yy)
    features = read_standard(watch.resolve(manifest['standard_output']['path']),manifest['standard_output']['layer'])
    require(type(synthetic_source_ids) in (list,tuple) and synthetic_source_ids
            and all(type(v) is str and v for v in synthetic_source_ids)
            and len(set(synthetic_source_ids))==len(synthetic_source_ids)
            and set(synthetic_source_ids)==features.keys(), 'synthetic_source_ids',
            'explicit exact authored synthetic Building ID list required')
    mapping = numeric_id_mapping(deterministic_ouem_id(k) for k in features)
    records, footprints = [], []
    for source_id,(tree,_,_) in sorted(features.items()):
        footprint,zs,walls = _footprint(tree)
        require(box(*terrain.bounds).covers(footprint),'coverage','whole footprint must lie within synthetic domain')
        require(all(footprint.intersection(p).area==0 for p in footprints),
                'ownership','overlapping footprints outside minimal scope')
        footprint_mask = covers(footprint,centres)
        require(footprint_mask.any() and not np.any(ids[footprint_mask]),
                'ownership','each Building needs non-conflicting centre samples')
        ouem_id = deterministic_ouem_id(source_id)
        number = mapping[ouem_id]
        ids[footprint_mask] = number
        derived = derive_attributes(zs,dem[ids==number].tolist())
        require(derived['z_bottom_geom_abs']==terrain.elevation_H,
                'synthetic_ground','minimal scope requires authored Building base H equal to flat Terrain H')
        records.append({'source_id':source_id,'ouem_id':ouem_id,'id':number,'voxcity_id':number,
            **derived,'footprint_area_m2':float(footprint.area),'discarded_vertical_faces':walls,
            'geometry':footprint})
        footprints.append(footprint)
    buildings = gpd.GeoDataFrame(records,geometry='geometry',crs=6677)
    geographic = buildings.to_crs(4326)
    require(geographic.is_valid.all(),'voxcity.geometry','geographic footprint invalid; no repair supported')
    watch.unchanged()
    summary = {'technical_validation':'PASS','scope':'synthetic-only-flat-ground-2.5d/v0.1',
        'consumer_validation':'PASS','consumer_profile':consumer['verified_profile'],
        'input_artifacts':watch.identities,'input_binding':'fresh Consumer + at-use and post-read identity/hash checks',
        'grid':{'horizontal_crs':'EPSG:6677','bounds':list(terrain.bounds),'resolution_m':terrain.resolution,
            'shape':[rows,cols],'layout':'north-up row0 north; cell centres; not VoxCity rasterization',
            'affine':[terrain.resolution,0,xmin,0,-terrain.resolution,ymax]},
        'terrain':{'elevation_H':terrain.elevation_H,'vertical_crs':terrain.vertical_crs,
            'vertical_quantity':terrain.vertical_quantity,'vertical_unit':terrain.vertical_unit,
            'declaration':terrain.declaration,'method':'authored constant on entire domain; no NoData/extrapolation'},
        'ground_assignment':'mean of diagnostic building-owner DEM cells; constant Terrain makes all assignments identical',
        'buildings':[{k:v for k,v in r.items() if k!='geometry'} for r in records],
        'voxcity_boundary':'EPSG:4326 GeoDataFrame with id,height,min_height; Adapter itself makes no engine call',
        'source_h_eligibility':'NOT_ESTABLISHED','human_review':'NOT_VERIFIED','formal_acceptance':'NOT_VERIFIED',
        'phase5_gates':dict.fromkeys(('A1','A2','A3','A4'),'OPEN')}
    return SyntheticBuildingResult(buildings,geographic,dem,ids,summary)
