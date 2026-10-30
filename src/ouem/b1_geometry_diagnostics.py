"""Read saved configured B1 runs; diagnose geometry without executing VoxCity."""
import argparse
import csv
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
from types import SimpleNamespace

import numpy as np
import rasterio
from shapely.geometry import Polygon, shape
from shapely.strtree import STRtree

from ouem.consumers.source_h_standard import Watch
from ouem.gis_visualization import inspect_run
from ouem.height_envelope import sample_raster
from ouem.native.building.source_h_geometry import require


def stats(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not values.size:
        return dict(count=0, status='UNAVAILABLE')
    return dict(count=int(values.size), **dict(zip(
        ('min', 'p05', 'median', 'p95', 'max'), map(float, np.percentile(values, [0,5,50,95,100])))))


def analyze(a, s, grid, cells, buildings, *, numba):
    """Independent scalar interval reconstruction, not a voxel allocator.

    Return diagnostics even when an occupancy comparison fails; never repair.
    Reject malformed dimensions rather than broadcasting incompatible evidence.
    """
    current, absent, base = s['current_voxels'], s['no_canopy_voxels'], a['voxels']
    ids, g = a['building_ids'], a['ground_indices']
    shape2 = ids.shape
    require(current.ndim == 3 and current.shape == absent.shape and current.shape[:2] == shape2
            and list(current.shape) == grid['shape'] and base.shape[:2] == shape2
            and base.shape[2] <= current.shape[2], 'geometry.shape', 'incompatible 3D grids')
    require(all(v.shape == shape2 for k,v in a.items() if k != 'voxels')
            and all(v.shape == shape2 for k,v in s.items() if v.ndim == 2),
            'geometry.shape', 'incompatible 2D grids')
    require(g.dtype.kind in 'iu' and s['observer_index_k'].dtype.kind in 'iu'
            and np.all((g > 0) & (g < current.shape[2])), 'geometry.indices', 'invalid ground index')
    require(all(np.isfinite(a[k]).all() for k in ('terrain_H','effective_ground_H','effective_dem')),
            'geometry.ground', 'nonfinite ground')
    d0 = grid['D0_effective_H_m']
    require(np.isfinite(d0) and grid['nominal_voxel_size_m'] == 1., 'geometry.Z', 'unsupported origin/resolution')
    tree, building = current == -2, current == -3
    valid, roi = s['observer_valid'], a['roi_mask']
    require(valid.dtype == bool and roi.dtype == bool, 'geometry.mask', 'boolean masks required')
    surface = np.argmax(absent == 1, axis=2)+1
    maps = dict(terrain_H=a['terrain_H'], effective_ground_H=a['effective_ground_H'],
                ground_conditioning=a['effective_ground_H']-a['terrain_H'],
                surface_H=d0+surface, observer_H=d0+s['observer_index_k']+.5,
                surface_minus_effective=d0+surface-a['effective_ground_H'])
    maps['observer_minus_dem'] = maps['observer_H']-a['terrain_H']
    maps['observer_minus_effective'] = maps['observer_H']-a['effective_ground_H']
    maps['observer_minus_surface'] = maps['observer_H']-maps['surface_H']
    checks = dict(pair_non_TREE_mismatch=int(np.count_nonzero(np.where(tree,0,current) != absent)),
        base_prefix_mismatch=int(np.count_nonzero(absent[:,:,:base.shape[2]] != base)),
        base_extra_non_air=int(np.count_nonzero(absent[:,:,base.shape[2]:])),
        building_changed=int(np.count_nonzero(building != (absent == -3))),
        mask_vs_ids=int(np.count_nonzero(valid != (ids == 0))),
        surface_count_mismatch=int(np.count_nonzero((absent == 1).sum(axis=2) != 1)),
        saved_ground_vs_surface=int(np.count_nonzero(g != surface)),
        ground_rounding_mismatch=int(np.count_nonzero(g != (np.asarray(a['effective_dem'],
            dtype=np.float32 if numba else np.float64).astype(float)+.5).astype(int)+1)),
        tree_in_non_air=int(np.count_nonzero(tree & (absent != 0))))
    for name, vox in [('current',current),('no_canopy',absent)]:
        walk = ((vox[:,:,1:] == 0) | (vox[:,:,1:] == -2)) & ~np.isin(vox[:,:,:-1], [0,-2])
        first = np.argmax(walk, axis=2)+1
        checks[name+'_observer_transition_mismatch'] = int(np.count_nonzero(
            valid & (~walk.any(axis=2) | (first+1 != s['observer_index_k']))))
    checks['observer_capacity'] = int(np.count_nonzero(valid &
        ((s['observer_index_k'] < 0) | (s['observer_index_k'] >= current.shape[2]))))
    for name in ('solar_current','solar_no_canopy','solar_difference'):
        checks[name+'_mask'] = int(np.count_nonzero(np.isfinite(s[name]) != valid))
    checks['difference_mismatch'] = int(np.count_nonzero(~np.isclose(s['solar_difference'],
        s['solar_no_canopy']-s['solar_current'], rtol=0, atol=0, equal_nan=True)))

    # Every contributor segment is checked independently of last-wins owner ID.
    by_id = {b['id']:b for b in buildings}
    expected_building = np.zeros_like(building)
    contributor_count = np.zeros(shape2, dtype=int)
    roof_error = np.full(shape2, np.nan)
    segment_rows = []
    for cell in cells:
        i,j = cell['i'],cell['j']
        require(ids[i,j] == cell['owner_id'] and len(cell['segments']) == len(cell['contributor_ids']),
                'geometry.contributors', 'invalid saved owner/contributors')
        require(sorted(cell['segments']) == sorted([[0.,by_id[k]['height']] for k in cell['contributor_ids']]),
                'geometry.segments','recorded segments differ from source building heights')
        contributor_count[i,j] = len(cell['segments'])
        tops = []
        # Contributor order need not match segment order; ground-based heights identify them.
        for identifier in cell['contributor_ids']:
            b = by_id[identifier]
            end = int(g[i,j])+int(float(b['height'])+.5)
            expected_building[i,j,int(g[i,j]):end] = True
            tops.append(b['z_top_abs'])
            segment_rows.append(dict(i=i,j=j,id=identifier,source_id=b['source_id'],ouem_id=b['ouem_id'],
                relative_height_m=b['height'],source_top_H=b['z_top_abs'],
                voxel_top_H=d0+end,top_error_m=d0+end-b['z_top_abs']))
        if tops and building[i,j].any():
            roof_error[i,j] = d0+np.flatnonzero(building[i,j])[-1]+1-max(tops)
    checks['building_interval_mismatch'] = int(np.count_nonzero(building != expected_building))
    checks['building_ID_support_mismatch'] = int(np.count_nonzero(building.any(axis=2) != (ids > 0)))
    maps['building_top_error'] = roof_error

    top,bottom = s['canopy_top_H'],s['canopy_bottom_H']
    candidate = s['canopy_candidate']
    envelope_valid = (~s['canopy_missing'] & ~s['canopy_outside'] & np.isfinite(top)
                      & np.isfinite(bottom) & (s['envelope_state'] == 1))
    checks['candidate_mismatch'] = int(np.count_nonzero(candidate != (envelope_valid & (top > bottom))))
    below = candidate & (bottom < a['effective_ground_H'])
    active = candidate & ~below
    expected_tree = np.zeros_like(tree)
    plan_bottom,plan_top = np.full(shape2,np.nan),np.full(shape2,np.nan)
    expanded, vanished = np.zeros(shape2,bool),np.zeros(shape2,bool)
    dtype = np.float32 if numba else np.float64
    for i,j in np.argwhere(active):
        lo,hi = (int(float(dtype(v-a['effective_ground_H'][i,j]))+.5) for v in (bottom[i,j],top[i,j]))
        if lo == hi and lo > 0: lo -= 1; expanded[i,j] = True
        if hi <= lo: vanished[i,j] = True; continue
        start,end = int(g[i,j])+lo,int(g[i,j])+hi
        require(0 <= start < end <= current.shape[2], 'geometry.capacity', 'saved interval exceeds Z; no clipping')
        expected_tree[i,j,start:end] = True
        plan_bottom[i,j],plan_top[i,j] = d0+start,d0+end
    removed = expected_tree & building
    expected_tree[building] = False
    checks['TREE_interval_mismatch'] = int(np.count_nonzero(expected_tree != tree))
    checks['saved_TREE_mask_mismatch'] = int(np.count_nonzero(tree != s['tree_mask']))
    present = tree.any(axis=2)
    actual_bottom = np.where(present,d0+np.argmax(tree,axis=2),np.nan)
    actual_top = np.where(present,d0+tree.shape[2]-np.argmax(tree[:,:,::-1],axis=2),np.nan)
    maps.update(tree_bottom_error_pre_priority=plan_bottom-bottom, tree_top_error_pre_priority=plan_top-top,
                tree_bottom_error_actual=actual_bottom-bottom, tree_top_error_actual=actual_top-top,
                crown_depth=top-bottom, crown_thickness_error=(actual_top-actual_bottom)-(top-bottom))
    counts = dict(candidate=int(candidate.sum()), valid_zero_depth=int((envelope_valid & ~candidate).sum()),
        below_effective_ground=int(below.sum()), thin_expanded=int(expanded.sum()), rounded_vanished=int(vanished.sum()),
        tree_columns=int(present.sum()), tree_voxels=int(tree.sum()), priority_removed_voxels=int(removed.sum()),
        disconnected_TREE_columns=int(np.count_nonzero((np.diff(np.pad(tree.astype(int),((0,0),(0,0),(1,0))),axis=2)>0).sum(axis=2)>1)),
        fully_removed_columns=int((active & np.isfinite(plan_top) & ~present).sum()),
        overlap_contributor_cells=int((contributor_count>1).sum()),
        tree_below_surface_voxels=int(np.count_nonzero(tree & (np.arange(tree.shape[2])[None,None,:] < surface[:,:,None]))))
    groups = dict(roi_valid=roi & valid, domain_valid=valid, roi_excluded=roi & ~valid, domain_excluded=~valid)
    distributions = {scope:{key:stats(value[mask]) for key,value in maps.items()} for scope,mask in groups.items()}
    flags = dict(below=below, thin_expanded=expanded, rounded_vanished=vanished,
                 priority_removed=removed.any(axis=2), contributor_count=contributor_count)
    return dict(checks=checks, counts=counts, distributions=distributions,
                segment_top_errors=stats([r['top_error_m'] for r in segment_rows])), maps, flags, segment_rows


def footprint_check(grid, features, cells):
    """Compare saved footprint fractions with contributor records; no engine rasterization."""
    geometries = [shape(f['geometry']) for f in features]
    identifiers = [int(f['properties']['id']) for f in features]
    index = STRtree(geometries)
    saved = {(c['i'],c['j']):sorted(c['contributor_ids']) for c in cells}
    origin,u,v = (np.asarray(grid[k]) for k in ('origin_lonlat','u_step_lonlat','v_step_lonlat'))
    mismatches=[]
    for i,j in np.ndindex(tuple(grid['shape'][:2])):
        p=origin+i*u+j*v
        cell=Polygon([p,p+u,p+u+v,p+v])
        actual=sorted(identifiers[k] for k in index.query(cell,predicate='intersects')
                      if geometries[k].intersection(cell).area/cell.area > .3)
        if actual != saved.get((i,j),[]): mismatches.append(dict(i=i,j=j,footprint=actual,saved=saved.get((i,j),[])))
    return dict(fraction_rule='intersection_area/cell_area > 0.3 in original lon/lat grid',
                checked_cells=int(np.prod(grid['shape'][:2])),mismatch_cells=mismatches)


def source_samples(top_path, chm_path, dem_path, x, y):
    """CHM/DEM at Envelope source-pixel centres, avoiding a different sampling path."""
    with rasterio.open(top_path) as ds:
        require(ds.crs.to_epsg() == 6677, 'Envelope.CRS', 'EPSG:6677 required')
        c,r = (~ds.transform)@(x,y)
        require(np.all((c>=0)&(r>=0)&(c<ds.width)&(r<ds.height)), 'Envelope.coverage','outside source grid')
        ex,ey = ds.transform@(np.floor(c)+.5,np.floor(r)+.5)
    centres = SimpleNamespace(height=x.shape[0],width=x.shape[1],epsg=6677,centres=lambda:(ex,ey))
    result=[]
    for path in (chm_path,dem_path):
        sample=sample_raster(path,centres)
        require(not np.any(sample.missing|sample.outside) and np.isfinite(sample.values).all(),
                'source.coverage','missing CHM/DEM source-pixel samples')
        result.append(sample.values)
    return result


def _json(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)


def _csv(path, rows):
    with path.open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def generate(root, output):
    root,output=Path(root).resolve(strict=True),Path(output).resolve()
    require(not output.exists() and not output.is_relative_to(root) and not root.is_relative_to(output),
            'output','new directory outside the saved run required')
    watch,cfg,grid,affine,_=inspect_run(root)
    names=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())
    for name in names: watch.capture('inventory:'+name,name)
    reports={stage:json.loads((root/stage/'report.json').read_text(encoding='utf-8')) for stage in ('voxel','solar')}
    upstream=Watch((root/cfg['artifact_root']).resolve())
    unavailable=[]
    for stage,report in reports.items():
        for key,ref in report['input_artifacts'].items():
            locator=ref['resolved_path']
            if locator in upstream.identities:
                require(upstream.identities[locator]['sha256']==ref['sha256'], 'upstream','conflicting recorded hash')
            elif not (upstream.root/locator).exists(): unavailable.append(dict(key=stage+':'+key,path=locator,status='UNAVAILABLE'))
            else: upstream.capture(locator,locator,ref['sha256'],ref['size_bytes'])
    # Every delivered output (including 3D arrays) is authenticated before use.
    for stage,report in reports.items():
        for name,ref in report['outputs'].items():
            watch.capture('output:'+stage+'/'+name,stage+'/'+name,ref['sha256'],ref['size_bytes'])
    def arrays(stage):
        return {p.stem:np.load(p,allow_pickle=False) for p in (root/stage).glob('*.npy')}
    a,s=arrays('voxel'),arrays('solar')
    require({'voxels','building_ids','building_heights','ground_indices','terrain_H','effective_dem',
             'effective_ground_H','centre_x','centre_y','centre_lon','centre_lat','roi_mask'} <= a.keys()
            and {'current_voxels','no_canopy_voxels','tree_mask','observer_index_k','observer_valid',
                 'canopy_top_H','canopy_bottom_H','canopy_candidate','canopy_missing','canopy_outside',
                 'envelope_state','solar_current','solar_no_canopy','solar_difference'} <= s.keys(),
            'saved.arrays','UNAVAILABLE: required saved arrays missing; no model regeneration')
    # Only matching-dimensional diagnostic inputs; cropped solar arrays are not full-domain maps.
    s={k:v for k,v in s.items() if not k.startswith('cropped_')}
    cells=json.loads((root/'voxel/building_segments.json').read_text())['cells']
    model=reports['voxel']['model']
    summary,maps,flags,segments=analyze(a,s,grid,cells,model['selected_buildings'],numba=model['numba'])
    geo=json.loads((root/'voxel/whole_building_footprints.geojson').read_text())
    summary['footprints']=footprint_check(grid,geo['features'],cells)
    # Read actual Standard XYZ BLOBs; no Standardizer or model is executed.
    from ouem.consumers._source_h_geometry import read_standard
    from ouem.standardize.building.source_h_geometry import points,as_shape
    from ouem.adapters.voxcity import build_normalized_footprint
    from pyproj import Transformer
    from shapely.ops import transform
    standard_manifest=upstream.capture('diagnostic_building_manifest',cfg['inputs']['building_manifest']['path'],
        cfg['inputs']['building_manifest']['sha256'],json_data=True)
    ref=standard_manifest['standard_output']
    standard=upstream.capture('diagnostic_standard',ref['path'],ref['sha256'],ref['size_bytes'])
    features=read_standard(standard,ref['layer'])
    saved_geo={int(f['properties']['id']):shape(f['geometry']) for f in geo['features']}
    tx=Transformer.from_crs(4326,6677,always_xy=True)
    top_residual,bottom_residual,footprint_distance=[],[],[]
    for b in model['selected_buildings']:
        tree=features[b['source_id']][0]
        zs=[p[2] for p in points(tree)]
        top_residual.append(max(zs)-b['z_top_abs']);bottom_residual.append(min(zs)-b['z_bottom_geom_abs'])
        normalized,_=build_normalized_footprint(as_shape(tree),b['ouem_id'])
        footprint_distance.append(normalized.hausdorff_distance(transform(tx.transform,saved_geo[b['id']])))
    summary['standard_geometry']=dict(selected=len(top_residual),top_H_residual=stats(top_residual),
        bottom_H_residual=stats(bottom_residual),projected_footprint_Hausdorff_m=stats(footprint_distance),
        vertical_crs=standard_manifest['vertical_crs'],vertical_operation=standard_manifest['vertical_operation'])
    envelope_path=upstream.resolve(cfg['inputs']['envelope_manifest']['path'])
    envelope=json.loads(envelope_path.read_text())
    for name,ref in envelope['outputs'].items():
        upstream.capture('envelope:'+name,(envelope_path.parent/name).relative_to(upstream.root).as_posix(),
                         ref['sha256'],ref['bytes'])
    source_paths={k:Path(v['path']) for k,v in envelope['input_files'].items()}
    # Bind sources used for diagnostic re-sampling as well as those recorded by Solar.
    for key in ('chm','terrain'):
        ref=envelope['input_files'][key]; path=source_paths[key].resolve(strict=True)
        upstream.capture('sample:'+key,path.relative_to(upstream.root).as_posix(),ref['sha256'],ref['bytes'])
    top_path=envelope_path.parent/'canopy_top_z.tif'
    chm,dem=source_samples(top_path,source_paths['chm'],source_paths['terrain'],a['centre_x'],a['centre_y'])
    cr=envelope['cr_model']['parameters']['cr']
    require(cr == .6, 'CR','this diagnostic supports recorded constant CR=0.60 only')
    top_expected=(dem+chm).astype('float32').astype(float)
    bottom_expected=(dem+(1-cr)*chm).astype('float32').astype(float)
    summary['envelope_source_check']=dict(cr=cr,
        top_mismatch=int(np.count_nonzero(top_expected != s['canopy_top_H'])),
        bottom_mismatch=int(np.count_nonzero(bottom_expected != s['canopy_bottom_H'])),
        CHM=stats(chm), thickness_minus_CR_CHM=stats((s['canopy_top_H']-s['canopy_bottom_H'])-cr*chm),
        voxel_DEM_minus_envelope_DEM=stats(a['terrain_H']-dem))
    summary['source_rasters']={}
    for key,path in dict(CHM=source_paths['chm'],Terrain=source_paths['terrain'],Envelope_top=top_path).items():
        with rasterio.open(path) as ds:
            summary['source_rasters'][key]=dict(path=str(path),crs=str(ds.crs),shape=list(ds.shape),
                affine=list(ds.transform)[:6],resolution=list(ds.res),dtype=ds.dtypes[0],
                nodata='NaN' if ds.nodata is not None and np.isnan(ds.nodata) else ds.nodata)
    maps['source_CHM']=chm
    # Neighbour jumps are candidates, not errors; avoid an arbitrary height threshold.
    jumps=[]
    for axis in (0,1):
        diff=np.diff(s['canopy_top_H'],axis=axis)
        for flat in np.argsort(np.abs(diff),axis=None)[-5:]:
            i,j=np.unravel_index(flat,diff.shape)
            jumps.append(dict(i=int(i),j=int(j),axis=axis,delta_H=float(diff[i,j])))
    summary['largest_adjacent_top_steps']=sorted(jumps,key=lambda r:abs(r['delta_H']),reverse=True)
    output.mkdir(parents=True,exist_ok=False)
    cell_rows=[]
    for i,j in np.ndindex(a['building_ids'].shape):
        row=dict(i=i,j=j,x=float(a['centre_x'][i,j]),y=float(a['centre_y'][i,j]),
                 lon=float(a['centre_lon'][i,j]),lat=float(a['centre_lat'][i,j]),
                 ROI=bool(a['roi_mask'][i,j]),valid=bool(s['observer_valid'][i,j]),
                 owner_id=int(a['building_ids'][i,j]),observer_k=int(s['observer_index_k'][i,j]))
        row.update({k:float(v[i,j]) for k,v in maps.items()})
        row.update({k:int(v[i,j]) for k,v in flags.items()})
        cell_rows.append(row)
    _csv(output/'cells.csv',cell_rows)
    _csv(output/'building_segments.csv',segments)
    _csv(output/'buildings.csv',[{k:b[k] for k in ('id','source_id','ouem_id','height','z_top_abs',
        'z_bottom_geom_abs','ground_eff_abs','owned_engine_cells','bottom_minus_effective_ground_m',
        'crosses_actual_engine_domain')} for b in model['selected_buildings']])
    for name,values in maps.items():
        values=values.copy()
        if name.startswith('observer_'): values[~s['observer_valid']]=np.nan
        with rasterio.open(output/(name+'.tif'),'w',driver='GTiff',width=values.shape[1],height=values.shape[0],
                           count=1,dtype='float64',crs=4326,transform=affine,nodata=np.nan) as ds:
            ds.write(values[::-1,:],1)
    _figures(output,a,s,grid,maps)
    watch.unchanged();upstream.unchanged()
    require(names==sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()),
            'immutability','saved run inventory changed')
    summary.update(run_id=cfg['run_id'],grid=grid,saved_consumer=reports['voxel']['consumer']['technical_validation'],
        generator=dict(module=__name__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            python=platform.python_version(),packages={k:metadata.version(k) for k in ('numpy','rasterio','pyproj','voxcity')}),
        missing_upstream=unavailable,source_immutability='PASS',
        inventory=dict(root=str(root),files=watch.identities,upstream_root=str(upstream.root),upstream=upstream.identities),
        scientific_validation='UNVERIFIED',model_execution='NONE')
    _json(output/'diagnostics.json',summary)
    return summary


def _figures(output,a,s,grid,maps):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,10),constrained_layout=True)
    for ax,key in zip(axes.flat,('observer_minus_dem','surface_minus_effective','ground_conditioning',
                                'building_top_error','tree_top_error_actual','tree_bottom_error_actual')):
        values=maps[key].copy()
        if key.startswith('observer'): values[~s['observer_valid']]=np.nan
        image=ax.imshow(values,origin='lower',cmap='viridis')
        ax.contour(a['roi_mask'].astype(float),levels=[.5],colors='red',linewidths=.8)
        ax.set(title=key+' [m]',xlabel='v (~east), cell index',ylabel='u (~north), cell index')
        fig.colorbar(image,ax=ax)
    fig.suptitle('Saved-grid diagnostics; red = ROI; NaN transparent; source data unchanged')
    fig.savefig(output/'diagnostic_maps.png',dpi=200);plt.close(fig)
    roi_valid=a['roi_mask'] & s['observer_valid']
    candidates=np.argwhere(roi_valid)
    offsets=maps['observer_minus_dem'][roi_valid]
    points=[candidates[np.argmin(offsets)],candidates[np.argsort(offsets)[len(offsets)//2]],candidates[np.argmax(offsets)]]
    fig,axes=plt.subplots(3,1,figsize=(15,11),constrained_layout=True)
    for ax,(i,j) in zip(axes,points):
        from matplotlib.colors import ListedColormap,BoundaryNorm
        # Explicit code order: subsurface, TREE, Building, air, surface.
        codes=np.array([-3,-2,-1,0,1]); colors=['#555555','#248c4d','#ad876a','#ffffff','#e0bf6a']
        indices=np.searchsorted(codes,s['current_voxels'][:,j,:])
        ax.imshow(indices.T,origin='lower',aspect='auto',extent=(0,indices.shape[0],grid['D0_effective_H_m'],
            grid['D0_effective_H_m']+indices.shape[1]),cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(6)-.5,5))
        x=np.arange(indices.shape[0])+.5
        for key,label,color in [('terrain_H','source DEM','blue'),('effective_ground_H','effective ground','orange')]:
            ax.plot(x,a[key][:,j],color=color,label=label,lw=1)
        for key,label,color in [('canopy_top_H','envelope top','green'),('canopy_bottom_H','envelope bottom','olive')]:
            ax.plot(x,s[key][:,j],color=color,label=label,lw=.7)
        mask=s['observer_valid'][:,j]
        ax.plot(x[mask],maps['observer_H'][:,j][mask],'r.',ms=2,label='valid observer centres')
        ax.axvline(i+.5,color='purple',ls='--',label=f'representative u={i},v={j}')
        ax.set(xlabel='u (~north), cell edge',ylabel='H [m]',title=f'Section v={j}, selected observer offset={maps["observer_minus_dem"][i,j]:.6f}m')
        ax.legend(fontsize=7,ncol=4)
    fig.savefig(output/'representative_sections.png',dpi=200);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=generate(args.run_root,args.output)
    print(json.dumps(dict(run_id=result['run_id'],checks=result['checks'],counts=result['counts'],
                          immutability=result['source_immutability'])))


if __name__ == '__main__':
    main()
