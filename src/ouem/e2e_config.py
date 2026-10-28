"""Bounded experimental E2E settings; not an OUEM Standard/StudyArea contract."""
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
import math
import re

from ouem.consumers.source_h_standard import Watch, strict_json, same_json
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_source_h import digest, write
from ouem.study_area import load_study_area

SCHEMA = 'ouem-e2e-run/v0.1'
RECEIPT_SCHEMA = 'ouem-e2e-voxel-receipt/v0.1'
ROI = (-23320, -40760, -23256, -40696)
DOMAIN = (-23352, -40792, -23224, -40664)


def keys(value, expected, field):
    require(type(value) is dict and set(value) == set(expected), field, 'exact known keys required')
    return value


def number(value, field):
    require(type(value) in (int, float), field, 'finite number required')
    try:
        result = float(value)
    except OverflowError:
        require(False, field, 'finite number required')
    require(math.isfinite(result), field, 'finite number required')
    return result


def rectangle(values, field):
    require(type(values) in (list, tuple) and len(values) == 4, field, 'four coordinates required')
    result = tuple(number(v, field) for v in values)
    require(result[0] < result[2] and result[1] < result[3], field, 'ordered positive rectangle required')
    return result


def covers(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


@dataclass(frozen=True)
class Extent:
    analysis: tuple = ROI
    buffer_m: float = 32.

    def __post_init__(self):
        object.__setattr__(self, 'analysis', rectangle(self.analysis, 'analysis_extent'))
        value = number(self.buffer_m, 'context_buffer_m')
        require(value > 0, 'context_buffer_m', 'positive context required for existing crop diagnostics')
        object.__setattr__(self, 'buffer_m', value)
        rectangle(self.domain, 'computation_reference')

    @property
    def domain(self):
        x0, y0, x1, y1 = self.analysis
        b = self.buffer_m
        return x0-b, y0-b, x1+b, y1+b


def confined(root, locator):
    require(type(locator) is str and bool(locator.strip()) and '\x00' not in locator,
            'path', 'nonblank relative locator required')
    win, path = PureWindowsPath(locator), Path(locator)
    require(not path.is_absolute() and not win.drive and not win.root and
            '..' not in path.parts and '..' not in win.parts, 'path', 'relative confined locator required')
    result = (root/path).resolve()
    require(result.is_relative_to(root), 'path', 'path escapes artifact root')
    return result


@dataclass(frozen=True)
class RunConfig:
    path: Path
    sha256: str
    root: Path
    document: dict
    extent: Extent

    @classmethod
    def load(cls, path):
        path = Path(path).resolve(strict=True)
        require(path.stat().st_size <= 1024*1024, 'config', 'configuration exceeds 1 MiB')
        data = strict_json(path.read_bytes())
        keys(data, ('schema','artifact_root','study_area','analysis_extent','context_buffer_m',
                    'inputs','output_parent','run_id'), 'config')
        require(data['schema'] == SCHEMA, 'config.schema', 'unsupported schema')
        require(type(data['artifact_root']) is str and data['artifact_root'].strip(), 'artifact_root', 'path required')
        root = (path.parent/data['artifact_root']).resolve(strict=True)
        require(root.is_dir() and path.is_relative_to(root), 'artifact_root', 'must contain config and inputs')
        extent = Extent(data['analysis_extent'], data['context_buffer_m'])
        keys(data['inputs'], ('building_manifest','terrain','terrain_manifest','envelope_manifest'), 'inputs')
        rid = data['run_id']
        reserved = {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
        require(type(rid) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',rid)
                and rid.upper() not in reserved, 'run_id', 'new portable run ID required')
        parent = confined(root, data['output_parent'])
        require(parent.is_dir(), 'output_parent', 'create output parent explicitly before running')
        cfg = cls(path, digest(path), root, data, extent)
        watch = Watch(root)
        cfg.capture(watch)
        area = load_study_area(cfg.input_path('study_area'))
        require(area.epsg == 6677 and all(math.isfinite(v) for v in area.extent)
                and covers(area.extent, extent.domain), 'domain', 'computation reference must fit EPSG:6677 study area')
        require(cfg.input_path('terrain_manifest') == cfg.input_path('terrain').with_suffix('.tif.manifest.json'),
                'terrain_manifest', 'adjacent Terrain manifest required')
        for binding in [data['study_area'], *data['inputs'].values()]:
            source = confined(root, binding['path'])
            require(not source.is_relative_to(cfg.run_root) and source != cfg.run_root,
                    'output', 'run directory must not contain inputs')
        watch.unchanged()
        return cfg

    def binding(self, name):
        return self.document['study_area'] if name == 'study_area' else self.document['inputs'][name]

    def input_path(self, name):
        return confined(self.root, self.binding(name)['path'])

    @property
    def run_root(self):
        return confined(self.root, self.document['output_parent'])/self.document['run_id']

    def capture(self, watch):
        require(watch.root == self.root, 'config.root', 'watch/config root differs')
        data = watch.capture('run_config', self.path.relative_to(self.root).as_posix(), self.sha256, json_data=True)
        same_json(data, self.document, 'config.identity')
        for name in ('study_area', *self.document['inputs']):
            binding = keys(self.binding(name), ('path','sha256'), 'inputs.'+name)
            require(type(binding['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', binding['sha256']),
                    name+'.sha256', 'lowercase SHA-256 required')
            confined(self.root, binding['path'])
            watch.capture('config_input:'+name, binding['path'], binding['sha256'])

    def record(self):
        return dict(schema=SCHEMA, path=self.path.relative_to(self.root).as_posix(), sha256=self.sha256,
                    artifact_root=str(self.root), run_root=str(self.run_root), settings=self.document,
                    computation_reference_bounds=list(self.extent.domain))

    def arguments(self, stage):
        require(stage in ('voxel','solar'), 'stage', 'unsupported stage')
        return SimpleNamespace(config=self, artifact_root=self.root, study_area=self.input_path('study_area'),
            building_manifest=self.input_path('building_manifest'), terrain=self.input_path('terrain'),
            envelope_run=self.input_path('envelope_manifest').parent.parent,
            base_run=self.run_root/'voxel', run_dir=self.run_root/stage)

    def prepare(self, stage):
        if stage == 'voxel':
            self.run_root.mkdir()  # exclusive: no resume, even after failure
        else:
            require(self.run_root.is_dir(), 'run_root', 'run the voxel stage first')

    def seal_voxel(self):
        report = self.run_root/'voxel/report.json'
        watch = Watch(self.root)
        self.capture(watch)
        value = watch.capture('completed_model', report.relative_to(self.root).as_posix(), json_data=True)
        require(value['status'] == 'COMPLETED' and value['input_immutability'] == 'PASS', 'receipt', 'incomplete model')
        same_json(value['run_config'], self.record(), 'receipt.config')
        watch.unchanged()
        write(self.run_root/'voxel-receipt.json', dict(schema=RECEIPT_SCHEMA, run_config_sha256=self.sha256,
              report_sha256=watch.identities['completed_model']['sha256']))

    def model_sha(self, watch):
        receipt = watch.capture('voxel_receipt', (self.run_root/'voxel-receipt.json').relative_to(self.root).as_posix(), json_data=True)
        keys(receipt, ('schema','run_config_sha256','report_sha256'), 'receipt')
        require(receipt['schema'] == RECEIPT_SCHEMA and receipt['run_config_sha256'] == self.sha256,
                'receipt', 'model is not bound to this exact run configuration')
        require(type(receipt['report_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', receipt['report_sha256']),
                'receipt.sha256', 'SHA-256 required')
        return receipt['report_sha256']


def configured_arguments(parser, args, stage):
    if args.config is not None:
        require(all(value is None for key,value in vars(args).items() if key != 'config'),
                'arguments', '--config cannot be mixed with legacy path arguments')
        return RunConfig.load(args.config).arguments(stage)
    for key, value in vars(args).items():
        if key != 'config' and value is None:
            parser.error('--'+key.replace('_','-')+' is required without --config')
    return args
