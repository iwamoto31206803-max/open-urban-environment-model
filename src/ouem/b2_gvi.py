"""Experimental saved-B1 Current -> pinned CPU view index -> geographic rasters.

No preparation, revoxelization, Solar calculation or scientific metric adoption.
The saved B1 handoff inspector is deliberately reused only for completed B1 runs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import time

import numpy as np
import rasterio
from affine import Affine

from ouem.consumers.source_h_standard import Watch, strict_json
from ouem.gis_visualization import inspect_run
from ouem.komae_integration import environment, voxcity_provenance
from ouem.native.building.source_h_geometry import require

METRIC = 'CPU weighted first-TREE view index'
SETTINGS = dict(fast_path=False, mode=None, hit_values=(-2,), inclusion_mode=True,
                tree_k=0.5, tree_lad=1.0, view_point_height=1.5,
                N_azimuth=120, N_elevation=20, elevation_min_degrees=-30,
                elevation_max_degrees=30, ray_sampling='grid',
                include_building_roofs=False, obj_export=False)
SCHEMA = 'ouem-b2-cpu-gvi-experiment/v0.1'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)


def distribution(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    if not values.size:
        return dict(count=0)
    return dict(count=int(values.size), zero=int((values == 0).sum()),
                positive=int((values > 0).sum()), mean=float(values.mean()),
                **dict(zip(('min', 'p05', 'median', 'p95', 'max'),
                           map(float, np.percentile(values, [0, 5, 50, 95, 100])))))


def observers(voxels, height=1.5, mesh=1.):
    """Independent surface/observer diagnostic; no ray tracing or engine helper."""
    shape = voxels.shape[:2]
    index = np.full(shape, -1, dtype=np.int64)
    selected = np.zeros(shape, dtype=bool)
    valid = np.zeros(shape, dtype=bool)
    for z in range(1, voxels.shape[2]):
        above, below = voxels[:, :, z], voxels[:, :, z-1]
        transition = (~selected & np.isin(above, (0, -2)) & ~np.isin(below, (0, -2)))
        selected |= transition
        allowed = transition & (below >= 0) & ~np.isin(below, (7, 8, 9))
        index[allowed] = z + int(height / mesh)
        valid |= allowed
    capacity = valid & ((index < 0) | (index >= voxels.shape[2]))
    require(not capacity.any(), 'B2.observer.capacity', 'selected observer outside Z; no finite-zero repair')
    origin_class = np.full(shape, 127, dtype=np.int8)
    i, j = np.where(valid)
    origin_class[i, j] = voxels[i, j, index[i, j]]
    require(np.isin(origin_class[valid], (0, -2)).all(), 'B2.observer.class', 'observer in opaque voxel')
    return index, valid, origin_class


def roi_window(roi):
    require(roi.dtype == bool and roi.ndim == 2 and roi.any(), 'B2.ROI', 'nonempty boolean mask required')
    i, j = np.where(roi)
    bounds = [int(i.min()), int(i.max())+1, int(j.min()), int(j.max())+1]
    u0, u1, v0, v1 = bounds
    require(roi[u0:u1, v0:v1].all() and int(roi.sum()) == (u1-u0)*(v1-v0),
            'B2.ROI', 'rectangular saved ROI required; do not invent a new crop')
    return bounds


def load_run(root):
    watch, config, grid, affine, _ = inspect_run(root)
    # Protect every existing run file, not just directly consumed arrays.
    inventory = sorted(p.relative_to(watch.root).as_posix() for p in watch.root.rglob('*') if p.is_file())
    for name in inventory:
        watch.capture('inventory:'+name, name)
    reports = {stage: strict_json((watch.root/stage/'report.json').read_bytes()) for stage in ('voxel', 'solar')}
    for stage, report in reports.items():
        for name, ref in report['outputs'].items():
            watch.capture('output:'+stage+'/'+name, stage+'/'+name, ref['sha256'], ref['size_bytes'])
    upstream = Watch((watch.root/config['artifact_root']).resolve())
    for name, ref in dict(config['inputs'], study_area=config['study_area']).items():
        upstream.capture(name, ref['path'], ref['sha256'])

    def array(stage, name):
        # capture above verifies output size/hash; mmap prevents file writes.
        return np.load(watch.resolve(stage+'/'+name+'.npy'), allow_pickle=False, mmap_mode='r')
    current = array('solar', 'current_voxels')
    require(current.dtype == np.int8 and list(current.shape) == grid['shape'],
            'B2.voxels', 'Current dtype/shape differs from saved grid')
    codes, counts = np.unique(current, return_counts=True)
    require(set(map(int, codes)) <= {-3, -2, -1, 0, 1}, 'B2.classes', 'unsupported/NoData voxel class')
    require(np.array_equal(current == -2, array('solar', 'tree_mask')), 'B2.TREE', 'saved TREE mask mismatch')
    require(np.array_equal(np.where(current == -2, 0, current), array('solar', 'no_canopy_voxels')),
            'B2.Current', 'non-TREE occupancy differs from saved control')
    index, valid, origin_class = observers(current)
    require(np.array_equal(valid, array('solar', 'observer_valid')) and
            np.array_equal(index[valid], array('solar', 'observer_index_k')[valid]),
            'B2.observer', 'independent GVI observers differ from saved B1')
    for name in ('terrain_H', 'effective_ground_H', 'effective_dem'):
        require(np.isfinite(array('voxel', name)).all(), 'B2.ground', 'missing ground; no fill')
    roi = array('voxel', 'roi_mask')
    bounds = roi_window(roi)
    missing, outside = (array('solar', name) for name in ('canopy_missing', 'canopy_outside'))
    preflight = dict(shape_uvz=list(current.shape), dtype=str(current.dtype),
        classes={str(int(k)):int(v) for k, v in zip(codes, counts)},
        class_meanings={'-3':'Building', '-2':'TREE', '-1':'subsurface', '0':'AIR', '1':'Bareland surface'},
        domain_cells=int(valid.size), valid_observers=int(valid.sum()),
        invalid_observers=int((~valid).sum()), observers_in_TREE=int((origin_class[valid] == -2).sum()),
        selected_observer_index_range=[int(index[valid].min()), int(index[valid].max())],
        observer_centre_H_range_m=[float(grid['D0_effective_H_m']+index[valid].min()+.5),
                                   float(grid['D0_effective_H_m']+index[valid].max()+.5)],
        roi_uv_bounds_exclusive=bounds, evaluation_cells=int(roi.sum()),
        evaluation_shape_uv=[bounds[1]-bounds[0], bounds[3]-bounds[2]],
        canopy_missing_cells=int(missing.sum()), canopy_outside_cells=int(outside.sum()),
        source_NoData_policy='Ground must be finite; canopy missing/outside retained as source uncertainty, not absence proof',
        provenance_scope='Completed B1 reports/receipt, all delivered output hashes and frozen config input identities; no fresh Consumer/rebuild')
    watch.unchanged()
    upstream.unchanged()
    return dict(root=watch.root, watch=watch, upstream=upstream, inventory=inventory,
                config=config, grid=grid, affine=affine, current=current, roi=roi,
                index=index, valid=valid, origin_class=origin_class, preflight=preflight)


def unchanged(saved):
    inventory = sorted(p.relative_to(saved['root']).as_posix() for p in saved['root'].rglob('*') if p.is_file())
    require(inventory == saved['inventory'], 'B2.immutability', 'run file inventory changed')
    saved['watch'].unchanged()
    saved['upstream'].unchanged()


def memory_bytes():
    """Current process working set, stdlib only; no new monitoring dependency."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        query.restype = wintypes.BOOL
        if not query(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError('GetProcessMemoryInfo failed')
        return int(counters.WorkingSetSize)
    # Linux RSS, for synthetic CI only. Targeted execution is ordinary Windows.
    return int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')


def calculate(voxels, grid, threads=2):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from numba import get_num_threads, set_num_threads
    from voxcity.models import VoxCity, VoxelGrid, GridMetadata
    from voxcity.simulator.visibility.view import get_view_index
    require(type(threads) is int and 1 <= threads <= 8, 'B2.threads', '1..8 CPU threads required')
    previous = get_num_threads()
    set_num_threads(threads)
    before = set(plt.get_fignums())
    digest = hashlib.sha256(voxels.tobytes()).hexdigest()
    rectangle = grid['rectangle_vertices_lonlat']
    meta = GridMetadata('EPSG:4326', (min(p[0] for p in rectangle), min(p[1] for p in rectangle),
                                   max(p[0] for p in rectangle), max(p[1] for p in rectangle)), 1.)
    scene = VoxCity(VoxelGrid(voxels, meta), None, None, None, None)
    samples = [memory_bytes()]
    stop = threading.Event()
    def monitor():
        while not stop.wait(.1):
            samples.append(memory_bytes())
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    started, cpu = time.perf_counter(), time.process_time()
    try:
        result = get_view_index(scene, **SETTINGS, num_threads=threads)
        elapsed, cpu_seconds = time.perf_counter()-started, time.process_time()-cpu
    finally:
        stop.set()
        monitor_thread.join()
        samples.append(memory_bytes())
        for number in set(plt.get_fignums())-before:
            plt.close(number)
        set_num_threads(previous)
    require(set(plt.get_fignums()) == before, 'B2.figures', 'new API figures remain')
    require(hashlib.sha256(voxels.tobytes()).hexdigest() == digest, 'B2.input', 'API modified Current')
    timing = dict(wall_seconds=elapsed, process_cpu_seconds=cpu_seconds,
                  mean_cpu_cores=cpu_seconds/elapsed, logical_cpu_count=os.cpu_count(), numba_threads=threads,
                  working_set_start_bytes=samples[0], sampled_peak_working_set_bytes=max(samples),
                  working_set_end_bytes=samples[-1], memory_sample_interval_seconds=.1,
                  scope='Public API including JIT/cache loading, map and Agg plot/show; imports excluded')
    return result, timing


def check_result(values, valid):
    require(values.shape == valid.shape and values.dtype == np.float64, 'B2.result', 'wrong map shape/dtype')
    require(np.array_equal(np.isfinite(values), valid) and np.isnan(values[~valid]).all(),
            'B2.mask', 'unexpected API finite/NaN mask; no replacement')
    require(np.all((values[valid] >= 0) & (values[valid] <= 1)), 'B2.range', 'outside dimensionless 0..1')


def raster(path, values, affine):
    data = values[::-1, :].astype('uint8') if values.dtype == bool else values[::-1, :]
    nodata = np.nan if data.dtype.kind == 'f' else None
    with rasterio.open(path, 'w', driver='GTiff', count=1, crs=4326, transform=affine,
                       height=data.shape[0], width=data.shape[1], dtype=data.dtype,
                       nodata=nodata, compress='deflate') as ds:
        ds.write(data, 1)
        ds.update_tags(metric=METRIC, units='dimensionless', uv_to_raster='row=nu-1-u; col=v')
    with rasterio.open(path) as ds:
        require(ds.crs.to_epsg() == 4326 and ds.transform == affine and ds.shape == data.shape and
                np.array_equal(ds.read(1), data, equal_nan=True), 'B2.TIFF', 'CRS/affine/shape/values mismatch')
        valid = ~np.isnan(data) if data.dtype.kind == 'f' else np.ones(data.shape, dtype=bool)
        require(np.array_equal(ds.read_masks(1) > 0, valid), 'B2.TIFF.mask', 'NoData/zero mask mismatch')


def export(output, saved, values):
    affine, roi = saved['affine'], saved['roi']
    u0, u1, v0, v1 = roi_window(roi)
    evaluation = values[u0:u1, v0:v1]  # Always extract AFTER full-domain API call.
    crop_affine = affine @ Affine.translation(v0, values.shape[0]-u1)
    arrays = dict(view_index=values, observer_valid=saved['valid'], roi_mask=roi,
                  observer_index_k=saved['index'], evaluation_view_index=evaluation)
    for name, array in arrays.items():
        np.save(output/(name+'.npy'), array, allow_pickle=False)
        if name != 'observer_index_k':
            raster(output/(name+'.tif'), array, crop_affine if name.startswith('evaluation_') else affine)
    # The full affine was independently checked against existing B1 TIFFs by inspect_run.
    return dict(crs='EPSG:4326', project_crs='EPSG:6677', full_affine=list(affine)[:6],
                evaluation_affine=list(crop_affine)[:6], full_shape_uv=list(values.shape),
                evaluation_shape_uv=list(evaluation.shape), roi_uv_bounds_exclusive=[u0,u1,v0,v1],
                mapping='TIFF[row,col]=UV[nu-1-row,col]; evaluation has translated full-grid affine',
                full_grid_matches_B1='PASS', TIFF_roundtrip='PASS')


def provenance(saved):
    return dict(run_root=str(saved['root']), files=saved['watch'].identities,
                config_input_root=str(saved['upstream'].root), config_inputs=saved['upstream'].identities)


def execute(root, output, *, benchmark=False, benchmark_report=None, threads=2):
    output = Path(output).resolve()
    root = Path(root).resolve(strict=True)
    require(not output.exists() and output.parent.is_dir() and not output.is_relative_to(root)
            and not root.is_relative_to(output), 'B2.output', 'new directory outside B1 Run required')
    engine = voxcity_provenance()
    require(engine['verified'], 'B2.engine', str(engine))
    saved = load_run(root)
    profile = dict(SETTINGS, num_threads=threads)
    receipt = None
    if not benchmark:
        require(benchmark_report is not None, 'B2.benchmark', 'matching feasibility report required before full run')
        receipt_path = Path(benchmark_report).resolve(strict=True)
        receipt = strict_json(receipt_path.read_bytes())
        require(receipt['status'] == 'BENCHMARK_COMPLETED' and receipt['feasible'] and
                receipt['source_run'] == str(root) and receipt['settings'] == json.loads(json.dumps(profile)) and
                receipt['current_sha256'] == saved['watch'].identities['output:solar/current_voxels.npy']['sha256'],
                'B2.benchmark', 'mismatched/unsuccessful subset receipt')
        receipt = dict(path=str(receipt_path), sha256=sha(receipt_path), report=receipt)
    output.mkdir()
    write_json(output/'settings.json', profile)
    report = dict(schema=SCHEMA, metric=METRIC, processed_at=datetime.now(timezone.utc).isoformat(),
                  status='STARTED', source_run=str(root), settings=json.loads(json.dumps(profile)),
                  current_sha256=saved['watch'].identities['output:solar/current_voxels.npy']['sha256'],
                  preflight=saved['preflight'], grid=saved['grid'], engine=engine,
                  environment=environment(), implementation_sha256=sha(__file__),
                  settings_sha256=sha(output/'settings.json'), provenance=provenance(saved),
                  benchmark=receipt, scientific_validation='NOT_VERIFIED', qgis_GUI='NOT_VERIFIED')
    write_json(output/'preflight.json', report)
    try:
        if benchmark:
            u0,u1,v0,v1 = roi_window(saved['roi'])
            su, sv = min(16,u1-u0), min(16,v1-v0)
            subset = saved['current'][u0:u0+su, v0:v0+sv, :].copy()
            subset.flags.writeable = False
            mask = observers(subset)[1]
            require(mask.any(), 'B2.benchmark', 'subset has no observers')
            timings = []
            for _ in range(2):
                values, timing = calculate(subset, saved['grid'], threads)
                check_result(values, mask)
                timings.append(timing)
            # Cropped rays are shorter. Include the domain/subset diameter factor;
            # this is a feasibility estimate, never an accuracy/context experiment.
            ratio = saved['valid'].sum()/mask.sum()
            diameter_ratio = max(saved['current'].shape[:2])/min(su,sv)
            upper = timings[0]['wall_seconds'] + timings[1]['wall_seconds']*ratio*diameter_ratio
            peak = max(t['sampled_peak_working_set_bytes'] for t in timings)
            report.update(status='BENCHMARK_COMPLETED', subset_uv=[u0,u0+su,v0,v0+sv],
                          subset_shape=list(subset.shape), subset_valid=int(mask.sum()), timings=timings,
                          estimated_full_seconds=float(upper),
                          estimate_method='first-call overhead + repeat wall * full/subset observers * XY diameter ratio; not a bound',
                          feasible=bool(upper <= 600 and peak < 2*1024**3),
                          feasibility_limits=dict(estimated_seconds_per_site=600, process_working_set_bytes=2*1024**3),
                          limitation='Cropped subset is only a cost probe; its boundary-biased values are not evaluation results')
        else:
            values, timing = calculate(saved['current'], saved['grid'], threads)
            check_result(values, saved['valid'])
            report.update(status='COMPLETED', timing=timing, spatial=export(output, saved, values),
                          statistics={scope:dict(cells=int(mask.sum()), invalid=int((mask & ~saved['valid']).sum()),
                                                values=distribution(values[mask]))
                                      for scope, mask in dict(domain=np.ones(values.shape, bool), evaluation=saved['roi']).items()})
        unchanged(saved)
        report['input_immutability'] = 'PASS'
        report['outputs'] = {p.name:dict(sha256=sha(p), size_bytes=p.stat().st_size)
                             for p in sorted(output.iterdir()) if p.is_file()}
        write_json(output/'report.json', report)
    except Exception as exc:
        report.update(status='FAILED', error=f'{type(exc).__name__}: {exc}')
        write_json(output/'failure.json', report)
        raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--benchmark', action='store_true')
    parser.add_argument('--benchmark-report', type=Path)
    args = parser.parse_args(argv)
    report = execute(args.run_root, args.output, benchmark=args.benchmark,
                     benchmark_report=args.benchmark_report, threads=args.threads)
    print(json.dumps({k:report[k] for k in ('status', 'source_run', 'preflight')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
