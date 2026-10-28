"""Run the actual fixed-condition CPU solar A/B experiment in a new local directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration.source_h_25d_fixture import build_chain
from ouem import synthetic_building_solar as analysis


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args();started=time.perf_counter()
    run=args.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    root=run/'chain';root.mkdir()
    standard,config,terrain=build_chain(root)
    result=analysis.run_synthetic_building_solar(standard['manifest'],root,config,terrain=terrain,
        synthetic_source_ids=['synthetic_tokyo','synthetic_niigata'])
    for name,array in (('solar_terrain_only',result.terrain_only),('solar_with_buildings',result.with_buildings),
                       ('solar_difference',result.reduction),('valid_ground_mask',result.valid_ground),
                       ('building_id_grid',result.building_ids)):
        path=run/(name+'.npy')
        with path.open('xb') as stream:np.save(stream,array,allow_pickle=False)
        assert np.array_equal(np.load(path,allow_pickle=False),array,equal_nan=True)
    m=result.metadata
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
    baseline=m['sun']['expected_flat_horizontal_W_m2']
    for ax,values,title,cmap in zip(axes,(result.terrain_only,result.with_buildings,result.reduction),
            ('A: Terrain only','B: Terrain + Buildings','Reduction A-B'),('viridis','viridis','YlOrRd')):
        palette=plt.get_cmap(cmap).copy();palette.set_bad('#bbbbbb')
        image=ax.imshow(values,origin='lower',interpolation='nearest',vmin=0,vmax=baseline,cmap=palette)
        ax.contour(result.building_ids>0,levels=[.5],colors='black',linewidths=.7)
        ax.set_title(title);ax.set_xlabel('j / v (approximately east)');ax.set_ylabel('i / u (approximately north)')
        fig.colorbar(image,ax=ax,shrink=.75,label='W/m², horizontal direct')
    direction=np.array(m['sun']['ray_toward_sun_uv_up'][:2]);direction/=np.linalg.norm(direction)
    axes[1].annotate('toward sun',xy=(50+10*direction[1],53+10*direction[0]),xytext=(42,56),
        color='red',arrowprops={'arrowstyle':'->','color':'red'})
    fig.suptitle('Synthetic only: true sun 135° / altitude 35° / DNI 800 W/m²; grey = common excluded Building columns')
    fig.savefig(run/'solar_comparison.png',dpi=140);plt.close(fig)
    m['execution']={'utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'git_dirty':bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
        'module_sha256':sha(analysis.__file__),'runner_sha256':sha(__file__),
        'elapsed_seconds':time.perf_counter()-started,
        'note':'authored relocated synthetic boxes; dummy Converter execution identity, Converter NOT RUN'}
    m['saved_array_readback']='PASS: five arrays exactly match including NaN after allow_pickle=False reload'
    m['outputs']={p.name:{'size_bytes':p.stat().st_size,'sha256':sha(p)} for p in run.iterdir() if p.is_file()}
    with (run/'solar_metadata.json').open('x',encoding='utf-8') as stream:
        json.dump(m,stream,indent=2,allow_nan=False);stream.write('\n')
    stats=m['results']
    lines=['# Synthetic Building direct solar / shadow — technical PASS','',
        'Actual pinned VoxCity CPU solar API called for A/B. Fixed artificial sun, not observed weather/date.',
        '', '| Metric | Result |', '|---|---:|']
    for label,key in [('Valid ground cells','valid_ground_cells'),('Shadow cells','shadow_cells'),
        ('Shadow area within domain, nominal m²','shadow_area_nominal_m2'),('Max reduction W/m²','maximum_reduction_W_m2'),
        ('Mean reduction over valid ground W/m²','mean_reduction_valid_ground_W_m2'),
        ('Mean A W/m²','mean_A_W_m2'),('Mean B W/m²','mean_B_W_m2')]:
        lines.append(f'| {label} | {stats[key]} |')
    lines += ['', 'Reduction is A-B. Excluded Building columns remain NaN in both saved maps and difference.',
        'Shadow reaches the western domain boundary; reported area is in-domain only, not total untruncated shadow area.',
        'API requested observer1.5m is discretized: actual nominal ray centre k2.5, H12.75m (2.5m over authored source ground).',
        'No height correction; surface+1 and Building rounding inherited. Both scenarios have the SAME observer.',
        '', '![Actual comparison](solar_comparison.png)', '', 'See [metadata](solar_metadata.json) for all conditions, input/output hashes and limits.',
        '', 'No independent physical accuracy, canopy/diffuse/reflected/global irradiance, real-data or formal acceptance.',
        'source-H eligibility NOT_ESTABLISHED; Human Review/Formal Acceptance NOT_VERIFIED; Phase5 A1-A4 OPEN.',
        '', f"Metadata SHA-256: {sha(run/'solar_metadata.json')}"]
    with (run/'RESULTS.md').open('x',encoding='utf-8') as stream:stream.write('\n'.join(lines)+'\n')
    print(json.dumps({'status':'PASS','run':str(run),'results':stats,'observer':m['observer'],
        'qa':m['qa'],'execution':m['execution']},indent=2))


if __name__=='__main__':main()
