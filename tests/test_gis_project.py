"""Pure reference checks in OUEM; actual QGIS round trips in isolated GIS Python."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

FILE = Path(__file__).resolve().parents[1]/'src/ouem/gis_project.py'
spec = importlib.util.spec_from_file_location('gis_project', FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
GIS = importlib.util.find_spec('qgis') is not None


def fixture(root, gis=False):
    source = root/'inputs'; source.mkdir(parents=True)
    manifest = root/'manifest.json'
    grid = source/'grid.json'
    grid.write_text(json.dumps(dict(projected_reference_crs='EPSG:6677',
                                   projected_evaluation_ROI_bounds=[-23384,-40760,-23320,-40728])))
    def ref(path):
        return dict(path=os.path.relpath(path,root),sha256=m._hash(path),size_bytes=path.stat().st_size)
    sources = {'solar/grid.json':ref(grid)}
    layers = []
    for name in m.LAYERS:
        solar = name.startswith('solar_')
        stops = [dict(value=i,color='#000000' if i==0 else '#1b9e77',alpha=255 if solar or i==0 else 64,label=str(i))
                 for i in ([0,10] if solar else range(5) if name=='shadow_categories' else [0,1])]
        settings = dict(renderer='singlebandpseudocolor' if solar else 'paletted',stops=stops)
        if solar: settings.update(minimum=0,maximum=10)
        qml = root/(name+'.qml')
        tree = ET.Element('qgis',version='3.40.0',styleCategories='Symbology|Rendering')
        pipe = ET.SubElement(tree,'pipe')
        renderer = ET.SubElement(pipe,'rasterrenderer',type=settings['renderer'],band='1',opacity='1',alphaBand='-1',classificationMin='0',classificationMax='10')
        if solar:
            shader = ET.SubElement(renderer,'rastershader')
            palette = ET.SubElement(shader,'colorrampshader',colorRampType='INTERPOLATED',minimumValue='0',maximumValue='10')
            ET.SubElement(palette,'rampLegendSettings',suffix=' W/m²',useContinuousLegend='1')
        else: palette = ET.SubElement(renderer,'colorPalette')
        for stop in stops: ET.SubElement(palette,'item' if solar else 'paletteEntry',{k:str(v) for k,v in stop.items()})
        qml.write_bytes(ET.tostring(tree))
        raster = source/(name+'.tif')
        if gis:
            from osgeo import gdal,osr
            import numpy as np
            ds = gdal.GetDriverByName('GTiff').Create(str(raster),5,3,1,gdal.GDT_Float64 if solar else gdal.GDT_Byte)
            ds.SetGeoTransform((139.5755,.00001,.0000003,35.6332,.0000002,-.000009))
            crs = osr.SpatialReference(); crs.ImportFromEPSG(4326); ds.SetProjection(crs.ExportToWkt())
            band = ds.GetRasterBand(1)
            values = (np.arange(15).reshape(3,5)% (11 if solar else 5 if name=='shadow_categories' else 2)).astype(float if solar else 'uint8')
            if solar: values[0,0]=np.nan; band.SetNoDataValue(float('nan'))
            band.WriteArray(values); band=None; ds=None
        else: raster.write_bytes(b'authored hash fixture')
        sources['solar/'+name+'.tif'] = ref(raster)
        layers.append(dict(name=name,source='solar/'+name+'.tif',qml=ref(qml),style=settings))
    manifest.write_text(json.dumps(dict(schema='ouem-gis-visualization/v0.1',run_id='synthetic',
        validation=dict(saved_evidence_and_consumed_outputs='PASS'),sources=sources,layers=layers,
        spatial=dict(grid='solar/grid.json',crs='EPSG:4326'))))
    return manifest


class References(unittest.TestCase):
    def test_manifest_and_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest=fixture(Path(folder))
            self.assertEqual(len(m.inspect(manifest)[1]),7)
            (manifest.parent/'inputs/grid.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): m.inspect(manifest)

    def test_missing_absolute_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for path in ['/absolute.tif',r'\rooted.tif','C:/absolute.tif','https://host/x','missing.tif']:
                with self.assertRaises(ValueError): m._relative(root,path)
            (root/'bad.json').write_text('{"schema":1,"schema":2}')
            with self.assertRaisesRegex(ValueError,'Duplicate'): m._json(root/'bad.json')


@unittest.skipUnless(GIS,'Requires isolated existing QGIS Python')
class RoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['QT_QPA_PLATFORM']='offscreen'; os.environ['GDAL_PAM_ENABLED']='NO'
        from qgis.core import QgsApplication
        cls.profile=tempfile.TemporaryDirectory()
        cls.app=QgsApplication([],False,cls.profile.name); cls.app.initQgis()

    @classmethod
    def tearDownClass(cls):
        cls.app.exitQgis(); cls.profile.cleanup()

    def test_round_trip_separate_process_relocation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); manifest=fixture(root/'scene/visualization',True)
            before=m.inspect(manifest)[3]
            output=manifest.parent.parent/'project'
            receipt=m.generate(manifest,output); project=output/'project.qgz'
            self.assertEqual(receipt['source_immutability'],'PASS')
            self.assertEqual(m.verify(manifest,project)['roi_bounds'],[-23384,-40760,-23320,-40728])
            child=subprocess.run([sys.executable,str(FILE),'--manifest',str(manifest),'--verify',str(project)],capture_output=True,text=True)
            self.assertEqual(child.returncode,0,child.stderr)
            self.assertIn('"reopen": "PASS"',child.stdout)
            with zipfile.ZipFile(project) as archive:
                xml=ET.fromstring(archive.read(next(n for n in archive.namelist() if n.endswith('.qgs'))))
            self.assertTrue(all(n.text.startswith('../visualization/inputs/') for n in xml.findall('.//maplayer/datasource')))
            moved=root/'moved'; shutil.copytree(manifest.parent.parent,moved)
            self.assertEqual(m.verify(moved/'visualization/manifest.json',moved/'project/project.qgz')['reopen'],'PASS')
            orphan=root/'orphan.qgz'; shutil.copyfile(project,orphan)
            with self.assertRaisesRegex(ValueError,'Missing/invalid project raster'): m.verify(manifest,orphan)
            with self.assertRaisesRegex(ValueError,'no overwrite'): m.generate(manifest,output)
            m._unchanged(before)

    def test_saved_settings_and_missing_sources_fail(self):
        from qgis.core import QgsProject,QgsRectangle,QgsReferencedRectangle,QgsCoordinateReferenceSystem
        with tempfile.TemporaryDirectory() as folder:
            manifest=fixture(Path(folder)/'scene/visualization',True); output=manifest.parent.parent/'project'
            m.generate(manifest,output)
            for defect in ('alpha','opacity','visibility','extent','order','crs','band'):
                with self.subTest(defect=defect):
                    p=QgsProject(); p.read(str(output/'project.qgz')); nodes=p.layerTreeRoot().findLayers()
                    try:
                        if defect=='alpha': nodes[0].layer().renderer().setAlphaBand(-1)
                        elif defect=='opacity': nodes[0].layer().renderer().setOpacity(.5)
                        elif defect=='visibility': nodes[0].setItemVisibilityChecked(True)
                        elif defect=='extent': p.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(0,0,1,1),p.crs()))
                        elif defect=='crs': nodes[0].layer().setCrs(QgsCoordinateReferenceSystem('EPSG:6677'))
                        elif defect=='band':
                            nodes[0].layer().renderer().setInputBand(2)
                            self.assertEqual(nodes[0].layer().renderer().inputBand(),2)
                        else: nodes[0].layer().setCustomProperty('ouem/layer','wrong')
                        path=output/(defect+'.qgz'); self.assertTrue(p.write(str(path)))
                        with self.assertRaises(ValueError): m.verify(manifest,path)
                    finally:
                        p.clear()
            (manifest.parent/'inputs/roi_mask.tif').unlink()
            with self.assertRaisesRegex(ValueError,'Missing referenced file'): m.verify(manifest,output/'project.qgz')


if __name__=='__main__': unittest.main()
