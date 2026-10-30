"""Standalone GIS-runtime tests; direct execution uses existing QGIS Python."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('b2_gvi_qgis', Path(__file__).resolve().parents[1]/'src/ouem/b2_gvi_qgis.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
GIS = importlib.util.find_spec('qgis') is not None


class ReferenceChecks(unittest.TestCase):
    def test_incomplete_report_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            path.write_text(json.dumps(dict(schema='wrong')),encoding='utf-8')
            with self.assertRaises(ValueError):
                m.inspect([path])

    def test_changed_output_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root/'array.npy'
            file.write_bytes(b'unchanged')
            report = dict(schema='ouem-b2-cpu-gvi-experiment/v0.1',status='COMPLETED',
                          input_immutability='PASS',metric=m.METRIC,
                          outputs={'array.npy':dict(sha256=m.sha(file),size_bytes=file.stat().st_size)})
            path = root/'report.json'
            path.write_text(json.dumps(report),encoding='utf-8')
            self.assertEqual(len(m.inspect([path])[1]),2)
            file.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                m.inspect([path])


@unittest.skipUnless(GIS, 'Requires isolated existing QGIS Python')
class GISChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        os.environ['GDAL_PAM_ENABLED'] = 'NO'
        from qgis.core import QgsApplication
        cls.app = QgsApplication.instance()
        if cls.app is None:
            cls.app = QgsApplication([],False)
            cls.app.initQgis()

    def test_non_square_save_reopen_and_exact_cells(self):
        import numpy as np
        from osgeo import gdal, osr
        from qgis.core import QgsProject
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = []
            for site,shift in (('a',0.),('b',.002)):
                out = root/site
                out.mkdir()
                values = np.arange(15,dtype=float).reshape(3,5)/20
                values[0,0] = np.nan
                values[0,1] = 0
                arrays = dict(view_index=values, evaluation_view_index=values[1:3,2:5],
                              observer_valid=np.isfinite(values),roi_mask=np.ones((3,5),bool))
                affine = [1e-5,-1e-8,139.575+shift,2e-8,-9e-6,35.633]
                a,b,c,d,e,f = affine
                crop_affine = [a,b,c+2*a,d,e,f+2*d]
                srs = osr.SpatialReference()
                srs.ImportFromEPSG(4326)
                for name,array in arrays.items():
                    np.save(out/(name+'.npy'),array)
                    ds = gdal.GetDriverByName('GTiff').Create(str(out/(name+'.tif')),array.shape[1],array.shape[0],1,
                                                             gdal.GDT_Byte if array.dtype==bool else gdal.GDT_Float64)
                    ds.SetProjection(srs.ExportToWkt())
                    aa,bb,cc,dd,ee,ff = crop_affine if name.startswith('evaluation') else affine
                    ds.SetGeoTransform((cc,aa,bb,ff,dd,ee))
                    ds.GetRasterBand(1).WriteArray(array[::-1].astype('uint8') if array.dtype==bool else array[::-1])
                    if array.dtype.kind == 'f': ds.GetRasterBand(1).SetNoDataValue(float('nan'))
                    ds = None
                report = dict(schema='ouem-b2-cpu-gvi-experiment/v0.1',status='COMPLETED',metric=m.METRIC,
                              input_immutability='PASS',source_run=site,
                              outputs={p.name:dict(sha256=m.sha(p),size_bytes=p.stat().st_size) for p in out.iterdir()},
                              spatial=dict(full_affine=affine,evaluation_affine=crop_affine),
                              grid=dict(projected_evaluation_ROI_bounds=[-23320,-40760,-23256,-40696],
                                        projected_domain_bounds=[-23352,-40792,-23224,-40664]))
                path = out/'report.json'
                path.write_text(json.dumps(report),encoding='utf-8')
                paths.append(path)
            receipt = m.generate(paths,root/'qgis')
            self.assertEqual(receipt['numeric']['A']['view_index']['all_cells'],'PASS')
            self.assertTrue((root/'qgis/overview.png').is_file())
            self.assertEqual(m.verify(paths,root/'qgis/project.qgz')['reopen'],'PASS')
            # Verify failure on a saved style change, while retaining receipt hash.
            project = QgsProject()
            project.read(str(root/'qgis/project.qgz'))
            layer = project.layerTreeRoot().findLayers()[2].layer()
            layer.renderer().setClassificationMax(.5)
            project.write(str(root/'qgis/project.qgz'))
            with self.assertRaises(ValueError):
                m.verify(paths,root/'qgis/project.qgz')
            layer = None
            project.clear()


if __name__ == '__main__':
    unittest.main()
