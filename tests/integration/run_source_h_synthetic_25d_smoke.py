"""Opt-in synthetic demo; creates only a fresh local run, never real-data artifacts."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distribution, version
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration.source_h_25d_fixture import build_chain
from ouem.adapters import source_h_synthetic as adapter
from ouem.adapters.source_h_synthetic import adapt_synthetic_source_h


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def engine_check(result):
    """Actual public raster call only; not voxelization or Terrain integration."""
    import numpy as np
    import inspect
    from pyproj import Transformer
    from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon
    direct = json.loads(distribution('voxcity').read_text('direct_url.json'))
    pin = 'fa212656305328a9a657973bae26f352bfe813bc'
    assert version('voxcity')=='1.7.0' and direct['vcs_info']['commit_id']==pin
    xmin,ymin,xmax,ymax = result.summary['grid']['bounds']
    project = Transformer.from_crs(6677,4326,always_xy=True)
    rectangle = [project.transform(x,y) for x,y in ((xmin,ymin),(xmin,ymax),(xmax,ymax),(xmax,ymin))]
    heights,segments,ids,filtered = create_building_height_grid_from_gdf_polygon(
        result.voxcity_buildings.copy(),1.,rectangle,overlapping_footprint=True)
    expected = {r.id:r.height for r in result.voxcity_buildings.itertuples()}
    assert set(np.unique(ids))=={0,*expected}
    assert set(filtered.id)==set(expected)
    details = {}
    for identifier,height in expected.items():
        mask = ids==identifier
        assert np.isfinite(heights[mask]).all() and np.all(heights[mask]==height)
        assert all(cell==[[0.0,height]] for cell in segments[mask])
        details[str(identifier)] = {'cells':int(mask.sum()),'relative_height_m':height}
    return {'status':'PASS','version':version('voxcity'),'commit':pin,
        'api':'voxcity.geoprocessor.raster.create_building_height_grid_from_gdf_polygon',
        'api_module_sha256':sha(inspect.getsourcefile(create_building_height_grid_from_gdf_polygon)),
        'layout':'VoxCity geographic raster, distinct from diagnostic EPSG:6677 centre grid',
        'shape':list(ids.shape),'building_cells':details,'voxelization':'NOT RUN','solar':'NOT RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--run-voxcity',action='store_true')
    args = parser.parse_args()
    start = time.perf_counter()
    run = args.run_dir.resolve()
    run.mkdir(parents=True,exist_ok=False)
    root = run/'chain';root.mkdir()
    standard,config,terrain = build_chain(root)
    result = adapt_synthetic_source_h(standard['manifest'],root,config,terrain=terrain,
        synthetic_source_ids=['synthetic_tokyo','synthetic_niigata'])
    # All derived outputs are isolated from inputs in the new run.
    output = run/'derived';output.mkdir()
    result.buildings.to_file(output/'buildings_25d.gpkg',layer='building_25d',driver='GPKG')
    result.voxcity_buildings.to_file(output/'voxcity_buildings.geojson',driver='GeoJSON')
    import geopandas as gpd
    reopened = gpd.read_file(output/'buildings_25d.gpkg',layer='building_25d').set_index('source_id')
    assert reopened.crs.to_epsg()==6677 and set(reopened.index)==set(result.buildings.source_id)
    for row in result.buildings.itertuples():
        saved = reopened.loc[row.source_id]
        assert saved.geometry.equals_exact(row.geometry,0)
        assert (saved.ouem_id,saved.id,saved.z_top_abs,saved.ground_eff_abs,saved.height)==(
            row.ouem_id,row.id,row.z_top_abs,row.ground_eff_abs,row.height)
    fields = ['source_id','ouem_id','id','z_top_abs','ground_eff_abs','height','min_height','ground_sample_count','footprint_area_m2']
    with (output/'buildings.csv').open('x',newline='',encoding='utf-8') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in result.summary['buildings'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(1,2,figsize=(11,5))
    result.buildings.plot(column='height',ax=axes[0],legend=True,edgecolor='black')
    for r in result.buildings.itertuples():
        p = r.geometry.representative_point()
        axes[0].text(p.x,p.y,f'ID {r.id}\nHtop={r.z_top_abs:g}\nh={r.height:g}',fontsize=8,ha='center')
    axes[0].set_title('Whole 2.5D footprints; relative height (m)')
    axes[1].imshow(result.building_ids,
        extent=[terrain.bounds[0],terrain.bounds[2],terrain.bounds[1],terrain.bounds[3]],origin='upper',interpolation='nearest')
    axes[1].set_title('Diagnostic centre-sampled IDs; flat H=10.25 m')
    for ax in axes:
        ax.set_xlim(terrain.bounds[0],terrain.bounds[2]);ax.set_ylim(terrain.bounds[1],terrain.bounds[3])
        ax.set_xlabel('EPSG:6677 X (m)');ax.set_ylabel('Y (m)');ax.set_aspect('equal')
    fig.suptitle('Synthetic only: technical illustration, not accepted Building/Terrain data')
    fig.tight_layout();fig.savefig(output/'overview.png',dpi=140);plt.close(fig)
    summary = result.summary
    summary['derived_gpkg_readback'] = 'PASS: CRS, full 2D geometry, identities and H/height attributes'
    summary['voxcity_execution'] = engine_check(result) if args.run_voxcity else {'status':'NOT RUN'}
    summary['execution'] = {'utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
        'main_or_branch_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'git_dirty':bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
        'module_sha256':sha(adapter.__file__),
        'elapsed_seconds':time.perf_counter()-start,
        'fixture':'relocated authored synthetic boxes, synthetic Converter bytes; Converter NOT RUN'}
    summary['outputs'] = {p.name:{'size_bytes':p.stat().st_size,'sha256':sha(p)} for p in output.iterdir()}
    (run/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    lines = ['# Synthetic 2.5D Building smoke','',
        'Technical PASS only. source-H eligibility NOT_ESTABLISHED; human review/Formal Acceptance NOT_VERIFIED; Phase5 A1-A4 OPEN.',
        '', '| Source ID | Max vertex H | Ground H | Relative height | Cells |', '|---|---:|---:|---:|---:|']
    for row in summary['buildings']:
        lines.append(f"| {row['source_id']} | {row['z_top_abs']} | {row['ground_eff_abs']} | {row['height']} | {row['ground_sample_count']} |")
    lines += ['', 'See [summary.json](summary.json) for hashes, conditions and actual engine scope.',
        '', '![Diagnostic view](derived/overview.png)', '',
        'GPKG is a 2D footprint with absolute/relative height attributes, not a 3D roof mesh. No real municipality data, voxel/solar calculation or formal acceptance.']
    (run/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','run':str(run),'seconds':summary['execution']['elapsed_seconds'],
        'buildings':summary['buildings'],'voxcity_execution':summary['voxcity_execution']},indent=2))


if __name__=='__main__':main()
