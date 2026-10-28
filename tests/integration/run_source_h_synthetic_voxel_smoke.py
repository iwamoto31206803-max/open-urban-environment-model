"""Execute real pinned VoxCity voxelization on a fresh synthetic-only local run."""
import argparse
import csv
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
from ouem.adapters import source_h_synthetic_voxel as adapter


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args()
    started=time.perf_counter()
    run=args.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    root=run/'chain';root.mkdir()
    standard,config,terrain=build_chain(root)
    result=adapter.voxelize_synthetic_source_h(standard['manifest'],root,config,terrain=terrain,
        synthetic_source_ids=['synthetic_tokyo','synthetic_niigata'])
    m=result.metadata
    for name,array in (('voxel_grid',result.voxels),('building_id_grid',result.building_ids),
                       ('building_height_grid',result.building_heights),('terrain_H',result.terrain_H),
                       ('effective_dem',result.effective_dem)):
        path=run/(name+'.npy')
        with path.open('xb') as stream:np.save(stream,array,allow_pickle=False)
        assert np.array_equal(np.load(path,allow_pickle=False),array)
    fields=['source_id','ouem_id','id','relative_height_m','horizontal_cells','building_voxels',
            'k_start_inclusive','k_end_exclusive','nominal_index_edge_H_bottom_m','nominal_index_edge_H_top_m']
    with (run/'building_ids.csv').open('x',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:row[k] for k in fields} for row in m['buildings'])

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    fig,axes=plt.subplots(1,3,figsize=(13,4.5))
    counts=(result.voxels==-3).sum(axis=2)
    image=axes[0].imshow(counts,origin='lower',interpolation='nearest',vmin=0,vmax=15)
    axes[0].set_title('Actual BUILDING voxels\nper horizontal column')
    axes[0].set_xlabel('j / v (approximately east)');axes[0].set_ylabel('i / u (approximately north)')
    fig.colorbar(image,ax=axes[0],label='1 m layers')
    cmap=ListedColormap(['#e58e26','#ffffff','#8caa78'])
    norm=BoundaryNorm([-3.5,-1.5,.5,1.5],3)
    cuts=[];d0=m['vertical']['D0_effective_H_m']
    for ax,row in zip(axes[1:],m['buildings']):
        cells=np.argwhere(result.building_ids==row['id'])
        j=int(np.median(cells[:,1]))
        ax.imshow(result.voxels[:,j,:].T,origin='lower',interpolation='nearest',cmap=cmap,norm=norm,
            extent=[0,result.voxels.shape[0],d0,d0+result.voxels.shape[2]],aspect='auto')
        ax.axhline(d0,color='green',linestyle='--',label='Authored ground H')
        ax.axhline(row['input_max_H_m'],color='navy',linestyle='--',label='Input roof proxy H')
        ax.set_xlim(max(0,cells[:,0].min()-3),min(result.voxels.shape[0],cells[:,0].max()+4))
        ax.set_title(f"ID {row['id']} / j={j}: {row['relative_height_m']:g} m -> {row['occupied_thickness_m']:g} layers")
        ax.set_xlabel('i / u index');ax.set_ylabel('Nominal index-edge H (m)')
        ax.legend(fontsize=7,loc='upper left')
        cuts.append({'id':row['id'],'fixed_j':j})
    fig.suptitle('Synthetic VoxCity output: +1 surface layer retained; not physical-height acceptance')
    fig.tight_layout();fig.savefig(run/'sections.png',dpi=140);plt.close(fig)
    m['diagnostic_sections']=cuts
    m['execution']={'utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'git_dirty':bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
        'module_sha256':sha(adapter.__file__),'runner_sha256':sha(__file__),
        'elapsed_seconds':time.perf_counter()-started,'voxel_array_bytes':result.voxels.nbytes,
        'generated_fixture_note':'same relocated two boxes as PR94; synthetic Converter identity, Converter NOT RUN'}
    m['saved_array_readback']='PASS: all five arrays exactly equal after allow_pickle=False reload'
    m['outputs']={p.name:{'sha256':sha(p),'size_bytes':p.stat().st_size} for p in run.iterdir() if p.is_file()}
    with (run/'voxel_metadata.json').open('x',encoding='utf-8') as stream:
        json.dump(m,stream,indent=2,allow_nan=False);stream.write('\n')
    lines=['# Synthetic VoxCity voxelization — technical PASS','',
        'Real Voxelizer.generate_combined executed. No real data, canopy or solar calculation.',
        '',f"Shape {list(result.voxels.shape)}, dtype {result.voxels.dtype}; D0/ground H={d0}m.",
        '', '| ID | Input height m | Layers | Voxels | k range | Nominal top H m | Top minus input H m |',
        '|---|---:|---:|---:|---|---:|---:|']
    for r in m['buildings']:
        lines.append(f"| {r['id']} | {r['relative_height_m']} | {r['occupied_thickness_m']} | {r['building_voxels']} | [{r['k_start_inclusive']},{r['k_end_exclusive']}) | {r['nominal_index_edge_H_top_m']} | +{r['top_edge_minus_input_H_m']} |")
    lines += ['', 'The nominal +1 surface-layer shift and half-up rounding are measured, not corrected.',
        'Building begins above the surface layer; source ground/roof H and voxel indices are distinct.',
        '', '![Actual sections](sections.png)', '',
        'See [metadata](voxel_metadata.json) and [Building ID mapping](building_ids.csv).',
        '', 'source-H eligibility NOT_ESTABLISHED; Human Review/Formal Acceptance NOT_VERIFIED; Phase5 A1-A4 OPEN.',
        '', f"Voxel SHA-256: {sha(run/'voxel_grid.npy')}", f"Metadata SHA-256: {sha(run/'voxel_metadata.json')}",
        '', 'Next solar inputs: this voxel array, voxel_size1m, rectangle/orientation, chosen sun azimuth/elevation and DNI, observer policy and shared validity mask. No solar success claimed.']
    with (run/'RESULTS.md').open('x',encoding='utf-8') as stream:stream.write('\n'.join(lines)+'\n')
    print(json.dumps({'status':'PASS','run':str(run),'shape':list(result.voxels.shape),
        'class_counts':m['class_counts'],'buildings':m['buildings'],'execution':m['execution']},indent=2))


if __name__=='__main__':main()
