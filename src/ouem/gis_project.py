"""Standalone existing-QGIS Python entry: verified manifest -> referenced QGZ.

Run this file directly; no OUEM package import, model execution or data export.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PureWindowsPath
import sys
import tempfile


# Top-to-bottom drawing order; only Current and gray excluded observers start on.
LAYERS = {
    'roi_mask': 'Evaluation ROI (cell fill)',
    'canopy_candidate': 'Estimated canopy candidates',
    'observer_valid': 'Excluded Building observers',
    'shadow_categories': 'Building / additional canopy attenuation',
    'solar_difference': 'No-Canopy minus Current [W/m²]',
    'solar_no_canopy': 'No-Canopy [W/m²]',
    'solar_current': 'Current [W/m²]',
}
VISIBLE = {'observer_valid', 'solar_current'}


def _json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+v)))


def _relative(base, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or PureWindowsPath(value).drive or PureWindowsPath(value).root or ':' in value:
        raise ValueError('Relative local reference required: '+str(value))
    path = (base/value).resolve()
    if not path.is_file():
        raise ValueError('Missing referenced file: '+str(path))
    return path


def _hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect(manifest):
    """Validate the existing presentation manifest and all referenced bytes.

    This checks saved evidence identities, not fresh Consumer/model acceptance.
    Parent-relative paths are necessary for the existing visualization layout.
    """
    path = Path(manifest).resolve(strict=True)
    data = _json(path)
    if data['schema'] != 'ouem-gis-visualization/v0.1' or data['validation']['saved_evidence_and_consumed_outputs'] != 'PASS':
        raise ValueError('Completed v0.1 visualization manifest required')
    assets = {path: _hash(path)}
    def reference(ref):
        file = _relative(path.parent, ref['path'])
        if file.stat().st_size != ref['size_bytes'] or _hash(file) != ref['sha256']:
            raise ValueError('Reference size/hash mismatch: '+str(file))
        assets[file] = ref['sha256']
        return file
    sources = {key: reference(ref) for key, ref in data['sources'].items()}
    items = data['layers']
    if len(items) != len(LAYERS) or {item['name'] for item in items} != set(LAYERS):
        raise ValueError('Exactly seven distinct supported layers required')
    layers = {}
    for item in items:
        if item['source'] != 'solar/'+item['name']+'.tif':
            raise ValueError('Unexpected layer source: '+item['name'])
        layers[item['name']] = (sources[item['source']], reference(item['qml']), item['style'])
    grid = _json(sources[data['spatial']['grid']])
    roi = grid['projected_evaluation_ROI_bounds']
    if (data['spatial']['crs'] != 'EPSG:4326' or grid['projected_reference_crs'] != 'EPSG:6677'
            or type(roi) is not list or len(roi) != 4 or
            not all(type(v) in (int,float) and math.isfinite(v) for v in roi)
            or not (roi[0] < roi[2] and roi[1] < roi[3])):
        raise ValueError('Finite EPSG:6677 ROI required')
    return data, layers, roi, assets


def _unchanged(assets):
    for path, digest in assets.items():
        if not path.is_file() or _hash(path) != digest:
            raise ValueError('Source changed during project operation: '+str(path))


def _helper():
    spec = importlib.util.spec_from_file_location('gis_display', Path(__file__).with_name('gis_display.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _style(layer):
    renderer = layer.renderer()
    result = dict(type=renderer.type(), opacity=renderer.opacity(), alpha=renderer.alphaBand(), bands=renderer.usesBands())
    if renderer.type() == 'paletted':
        classes = renderer.classes()
    elif renderer.type() == 'singlebandpseudocolor':
        shader = renderer.shader().rasterShaderFunction()
        classes = shader.colorRampItemList()
        result.update(minimum=renderer.classificationMin(), maximum=renderer.classificationMax(),
                      ramp=int(shader.colorRampType()), suffix=shader.legendSettings().suffix())
    else:
        raise ValueError('Unsupported renderer: '+renderer.type())
    result['stops'] = [dict(value=c.value,color=c.color.name(),alpha=c.color.alpha(),label=c.label) for c in classes]
    return result


def _styled(source, qml, settings):
    from qgis.core import QgsRasterLayer
    layer = QgsRasterLayer(str(source), 'style reference', 'gdal')
    _helper().apply_qml(layer, qml)
    signature = _style(layer)
    if (layer.crs().authid() != 'EPSG:4326' or signature['type'] != settings['renderer']
            or signature['stops'] != settings['stops'] or signature['opacity'] != 1):
        raise ValueError('Layer CRS/style differs from manifest: '+str(source))
    if signature['type'] == 'singlebandpseudocolor' and (
            signature['minimum'] != settings['minimum'] or signature['maximum'] != settings['maximum']
            or signature['suffix'] != ' W/m²'):
        raise ValueError('Solar legend differs from manifest: '+str(source))
    return layer


def generate(manifest, output):
    """Save project.qgz + small provenance receipt into an exclusive directory."""
    from osgeo import gdal
    from qgis.core import Qgis, QgsProject, QgsRectangle, QgsReferencedRectangle, QgsCoordinateReferenceSystem
    with gdal.config_option('GDAL_PAM_ENABLED', 'NO'):
        data, layers, roi, assets = inspect(manifest)
        destination = Path(output).resolve()
        if destination.exists() or not destination.parent.is_dir() or any(destination.is_relative_to(p.parent) for p in assets):
            raise ValueError('New output directory outside all source directories required; no overwrite')
        project = QgsProject()
        project.setCrs(QgsCoordinateReferenceSystem('EPSG:6677'))
        project.setFilePathStorage(Qgis.FilePathType.Relative)
        project.setTitle(data['run_id']+' — Solar comparison')
        root = project.layerTreeRoot()
        for name, title in LAYERS.items():
            layer = _styled(*layers[name])
            layer.setName(title)
            layer.setCustomProperty('ouem/layer', name)
            project.addMapLayer(layer, False)
            node = root.addLayer(layer)
            node.setItemVisibilityChecked(name in VISIBLE)
            node.setExpanded(False)
        project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(*roi), project.crs()))
        _unchanged(assets)
        destination.mkdir()  # exclusive; failed partial outputs remain for diagnosis
        path = destination/'project.qgz'
        if not project.write(str(path)):
            raise ValueError('QGIS project save failed: '+str(path))
        _unchanged(assets)
        receipt = dict(schema='ouem-gis-project/v0.1', run_id=data['run_id'],
                       manifest=dict(path=os.path.relpath(Path(manifest).resolve(),destination), sha256=assets[Path(manifest).resolve()]),
                       project=dict(path=path.name,sha256=_hash(path)), qgis=Qgis.QGIS_VERSION,
                       python=sys.version, source_immutability='PASS',
                       separate_process_reopen='NOT_VERIFIED', gui='NOT_VERIFIED')
        (destination/'project.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        return receipt


def verify(manifest, path):
    """Reopen and compare to source manifest; run in a separate GIS process."""
    from osgeo import gdal
    from qgis.core import Qgis, QgsProject
    with gdal.config_option('GDAL_PAM_ENABLED', 'NO'):
        _, layers, roi, assets = inspect(manifest)
        project = QgsProject()
        if not project.read(str(Path(path).resolve(strict=True))):
            raise ValueError('QGIS project read failed')
        nodes = project.layerTreeRoot().findLayers()
        if len(nodes) != 7 or project.crs().authid() != 'EPSG:6677':
            raise ValueError('Project layer count/CRS mismatch')
        for node, (name, title) in zip(nodes, LAYERS.items()):
            layer = node.layer()
            if layer is None or not layer.isValid():
                raise ValueError('Missing/invalid project raster; QGZ does not embed GeoTIFFs: '+name)
            if (layer.customProperty('ouem/layer') != name or layer.name() != title
                    or layer.crs().authid() != 'EPSG:4326'
                    or Path(layer.source()).resolve() != layers[name][0] or node.itemVisibilityChecked() != (name in VISIBLE)):
                raise ValueError('Project source/order/name/visibility mismatch: '+name)
            if _style(layer) != _style(_styled(*layers[name])):
                raise ValueError('Saved style/alpha differs from source QML: '+name)
        extent = project.viewSettings().defaultViewExtent()
        bounds = [extent.xMinimum(),extent.yMinimum(),extent.xMaximum(),extent.yMaximum()]
        if extent.crs().authid() != 'EPSG:6677' or bounds != roi or project.filePathStorage() != Qgis.FilePathType.Relative:
            raise ValueError('Saved ROI extent/path policy mismatch')
        _unchanged(assets)
        return dict(reopen='PASS',qgis=Qgis.QGIS_VERSION,layers=list(LAYERS),visible=sorted(VISIBLE),
                    crs=project.crs().authid(),roi_bounds=bounds,source_immutability='PASS',gui='NOT_VERIFIED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--output',type=Path,help='new directory for project.qgz and project.json')
    target.add_argument('--verify',type=Path,help='existing QGZ to reopen; does not repair or write it')
    args = parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    os.environ['GDAL_PAM_ENABLED'] = 'NO'
    from qgis.core import QgsApplication
    with tempfile.TemporaryDirectory() as profile:
        app = QgsApplication([],False,profile)
        app.initQgis()
        try:
            result = verify(args.manifest,args.verify) if args.verify else generate(args.manifest,args.output)
            print(json.dumps(result,indent=2,ensure_ascii=False))
        finally:
            app.exitQgis()


if __name__ == '__main__':
    main()
