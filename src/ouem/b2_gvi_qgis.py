"""Standalone existing-QGIS Python: B2 reports -> A/B presentation and checks.

No OUEM install in GIS Python, no B1 seven-layer contract, no model calculation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


METRIC = 'CPU weighted first-TREE view index'
COLORS = ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect(report_paths):
    """Check immutable calculation reports and delivered products before QGIS use."""
    reports, assets = [], {}
    for name in report_paths:
        path = Path(name).resolve(strict=True)
        report = json.loads(path.read_text(encoding='utf-8'))
        if (report['schema'] != 'ouem-b2-cpu-gvi-experiment/v0.1' or report['status'] != 'COMPLETED'
                or report['input_immutability'] != 'PASS' or report['metric'] != METRIC):
            raise ValueError('Completed B2 CPU report required')
        assets[path] = sha(path)
        for key, ref in report['outputs'].items():
            file = (path.parent/key).resolve(strict=True)
            if not file.is_relative_to(path.parent) or file.stat().st_size != ref['size_bytes'] or sha(file) != ref['sha256']:
                raise ValueError('B2 output size/hash mismatch: '+key)
            assets[file] = ref['sha256']
        reports.append((path, report))
    return reports, assets


def unchanged(assets):
    for path, digest in assets.items():
        if sha(path) != digest:
            raise ValueError('Source changed: '+str(path))


def install_renderer(layer, renderer):
    """Preserve provider alpha for the rotated geographic display grid (B1 lesson)."""
    from qgis.core import Qgis
    provider = layer.dataProvider()
    bands = [i for i in range(1,provider.bandCount()+1)
             if provider.colorInterpretation(i) == Qgis.RasterColorInterpretation.AlphaBand]
    if len(bands) > 1:
        raise ValueError('Ambiguous provider alpha')
    renderer.setAlphaBand(bands[0] if bands else -1)
    layer.setRenderer(renderer)


def index_renderer(layer):
    from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer
    from qgis.PyQt.QtGui import QColor
    ramp = QgsColorRampShader(0., 1.)
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    ramp.setColorRampItemList([QgsColorRampShader.ColorRampItem(i/4, QColor(c), f'{i/4:.2f}')
                               for i,c in enumerate(COLORS)])
    shader = QgsRasterShader(0., 1.)
    shader.setRasterShaderFunction(ramp)
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
    renderer.setClassificationMin(0.)
    renderer.setClassificationMax(1.)
    install_renderer(layer, renderer)


def invalid_renderer(layer):
    from qgis.core import QgsPalettedRasterRenderer
    from qgis.PyQt.QtGui import QColor
    install_renderer(layer, QgsPalettedRasterRenderer(layer.dataProvider(), 1, [
        QgsPalettedRasterRenderer.Class(0, QColor('#b9bec5'), 'Excluded observer'),
        QgsPalettedRasterRenderer.Class(1, QColor(0,0,0,0), 'Valid observer')]))


def numeric_check(path, report):
    """All-cell GDAL roundtrip versus original UV; no display-grid Identify oracle."""
    import numpy as np
    from osgeo import gdal, osr
    checks = {}
    for name in ('view_index','evaluation_view_index','observer_valid','roi_mask'):
        array = np.load(path.parent/(name+'.npy'), allow_pickle=False)
        ds = gdal.Open(str(path.parent/(name+'.tif')), gdal.GA_ReadOnly)
        if ds is None:
            raise ValueError('GDAL raster open failed')
        raster = ds.ReadAsArray()
        srs = osr.SpatialReference(wkt=ds.GetProjection())
        srs.AutoIdentifyEPSG()
        affine = report['spatial']['evaluation_affine' if name.startswith('evaluation_') else 'full_affine']
        a,b,c,d,e,f = affine
        if (srs.GetAuthorityCode(None) != '4326' or ds.GetGeoTransform() != (c,a,b,f,d,e)
                or not np.array_equal(raster,array[::-1],equal_nan=True)):
            raise ValueError('GIS CRS/affine/value mismatch: '+name)
        valid = ~np.isnan(raster) if raster.dtype.kind == 'f' else np.ones(raster.shape,bool)
        if not np.array_equal(ds.GetRasterBand(1).GetMaskBand().ReadAsArray() > 0, valid):
            raise ValueError('GIS NoData mask mismatch')
        checks[name] = dict(shape=list(raster.shape), all_cells='PASS', valid=int(valid.sum()))
        ds = None
    return checks


def generate(paths, output):
    from qgis.core import (Qgis, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsFillSymbol,
                           QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY,
                           QgsReferencedRectangle, QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob)
    from qgis.PyQt.QtCore import QSize
    from qgis.PyQt.QtGui import QColor
    reports, assets = inspect(paths)
    out = Path(output).resolve()
    if out.exists() or not out.parent.is_dir() or any(out.is_relative_to(p.parent) for p in assets):
        raise ValueError('New output directory outside calculation results required')
    out.mkdir()
    project = QgsProject()
    project.setTitle('Komae A/B — '+METRIC)
    project.setCrs(QgsCoordinateReferenceSystem('EPSG:6677'))
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    bounds = None
    numeric = {}
    for site, (path, report) in zip(('A','B'), reports):
        group = project.layerTreeRoot().addGroup(site+' '+report['source_run'].replace('\\','/').split('/')[-1])
        numeric[site] = numeric_check(path, report)
        roi = report['grid']['projected_evaluation_ROI_bounds']
        x0,y0,x1,y1 = roi
        convert = QgsCoordinateTransform(project.crs(), QgsCoordinateReferenceSystem('EPSG:4326'), project)
        ring = []
        for x,y in ((x0,y0),(x0,y1),(x1,y1),(x1,y0),(x0,y0)):
            point = convert.transform(QgsPointXY(x,y))
            ring.append([point.x(),point.y()])
        geo = out/(site.lower()+'-evaluation-roi.geojson')
        geo.write_text(json.dumps(dict(type='FeatureCollection',features=[dict(type='Feature',properties={'site':site},
                            geometry=dict(type='Polygon',coordinates=[ring]))])),encoding='utf-8')
        outline = QgsVectorLayer(str(geo), site+' saved B1 evaluation ROI', 'ogr')
        outline.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#dc243a','outline_width':'0.45'}))
        project.addMapLayer(outline,False)
        group.addLayer(outline)
        for name,title,visible in (('observer_valid','Excluded observers (gray)',True),
                                    ('view_index',METRIC+' [dimensionless 0–1]',True),
                                    ('evaluation_view_index','Evaluation ROI extract [dimensionless 0–1]',False)):
            layer = QgsRasterLayer(str(path.parent/(name+'.tif')),site+' '+title,'gdal')
            if not layer.isValid():
                raise ValueError('QGIS raster invalid')
            invalid_renderer(layer) if name == 'observer_valid' else index_renderer(layer)
            project.addMapLayer(layer,False)
            node = group.addLayer(layer)
            node.setItemVisibilityChecked(visible)
            node.setExpanded(False)
        extent = QgsRectangle(*report['grid']['projected_domain_bounds'])
        if bounds is None: bounds = extent
        else: bounds.combineExtentWith(extent)
    bounds.scale(1.08)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(bounds,project.crs()))
    if not project.write(str(out/'project.qgz')):
        raise ValueError('QGIS project save failed')
    settings = QgsMapSettings()
    settings.setDestinationCrs(project.crs())
    settings.setLayers([n.layer() for n in project.layerTreeRoot().findLayers() if n.isVisible()])
    settings.setExtent(bounds)
    settings.setOutputSize(QSize(1400,900))
    settings.setBackgroundColor(QColor('white'))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    if not job.renderedImage().save(str(out/'overview.png')):
        raise ValueError('QGIS PNG render failed')
    unchanged(assets)
    receipt = dict(schema='ouem-b2-qgis-experiment/v0.1',metric=METRIC,qgis=Qgis.QGIS_VERSION,
                   python=sys.version,project_sha256=sha(out/'project.qgz'),
                   report_paths=[str(p) for p,_ in reports],
                   inputs={str(p):h for p,h in assets.items()}, numeric=numeric,
                   source_immutability='PASS',separate_process_reopen='NOT_VERIFIED',GUI='NOT_VERIFIED',
                   project_crs='EPSG:6677', data_crs='EPSG:4326',display_range=[0,1],
                   NoData='transparent index; gray invalid-observer overlay; white outside domains')
    (out/'project.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    settings.setLayers([])
    job = None
    project.clear()
    return receipt


def verify(paths, project_path):
    from qgis.core import QgsProject, Qgis
    reports, assets = inspect(paths)
    project_path = Path(project_path).resolve(strict=True)
    receipt = json.loads((project_path.parent/'project.json').read_text(encoding='utf-8'))
    if sha(project_path) != receipt['project_sha256']:
        raise ValueError('Project hash changed')
    project = QgsProject()
    if not project.read(str(project_path)) or project.crs().authid() != 'EPSG:6677':
        raise ValueError('Project reopen/CRS failed')
    nodes = project.layerTreeRoot().findLayers()
    if len(nodes) != 4*len(reports):
        raise ValueError('Unexpected B2 layer count')
    for i, (path, _) in enumerate(reports):
        group = nodes[4*i:4*i+4]
        for node, name in zip(group[1:], ('observer_valid','view_index','evaluation_view_index')):
            layer = node.layer()
            if (not layer.isValid() or Path(layer.source()).resolve() != path.parent/(name+'.tif')
                    or layer.crs().authid() != 'EPSG:4326' or node.itemVisibilityChecked() != (name != 'evaluation_view_index')):
                raise ValueError('Saved raster source/CRS/visibility mismatch')
            renderer = layer.renderer()
            provider = layer.dataProvider()
            bands = [b for b in range(1,provider.bandCount()+1)
                     if provider.colorInterpretation(b) == Qgis.RasterColorInterpretation.AlphaBand]
            if renderer.alphaBand() != (bands[0] if len(bands) == 1 else -1):
                raise ValueError('Saved provider alpha mismatch')
            if name == 'observer_valid':
                classes = renderer.classes()
                if [(c.value,c.color.alpha()) for c in classes] != [(0,255),(1,0)]:
                    raise ValueError('Saved invalid observer alpha mismatch')
            else:
                if renderer.classificationMin() != 0 or renderer.classificationMax() != 1:
                    raise ValueError('Saved index range mismatch')
                if [c.color.name() for c in renderer.shader().rasterShaderFunction().colorRampItemList()] != COLORS:
                    raise ValueError('Saved index ramp mismatch')
    unchanged(assets)
    project.clear()
    return dict(reopen='PASS',layers=len(nodes),qgis=Qgis.QGIS_VERSION,source_immutability='PASS',GUI='NOT_VERIFIED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', nargs=2, type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path)
    action.add_argument('--verify', type=Path)
    args = parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    os.environ['GDAL_PAM_ENABLED'] = 'NO'
    from qgis.core import QgsApplication
    with tempfile.TemporaryDirectory() as profile:
        app = QgsApplication([],False,profile)
        app.initQgis()
        try:
            result = verify(args.reports,args.verify) if args.verify else generate(args.reports,args.output)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        finally:
            app.exitQgis()


if __name__ == '__main__':
    main()
