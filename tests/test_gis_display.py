import importlib.util,sys,unittest,tempfile,math
from pathlib import Path
from unittest.mock import Mock,patch
spec=importlib.util.spec_from_file_location('gis_display',Path(__file__).resolve().parents[1]/'src/ouem/gis_display.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
GIS=importlib.util.find_spec('osgeo') is not None
class Checks(unittest.TestCase):
 def test_rotated_translated_non_square(self):
  for c,f in [(0,0),(10,-20)]:
   gt=(c,2,.25,f,.5,-3)
   for r in range(3):
    for col in range(5):
     x=c+(col+.5)*2+(r+.5)*.25;y=f+(col+.5)*.5-(r+.5)*3
     self.assertEqual(m.pixel(gt,5,3,x,y),(r,col))
 def test_edges_outside(self):
  self.assertEqual(m.pixel((0,1,0,0,0,1),5,3,1,1),(1,1))
  for x,y in [(-.01,0),(5,1),(1,3),(float('nan'),1)]:
   with self.assertRaises(ValueError):m.pixel((0,1,0,0,0,1),5,3,x,y)
 def test_alpha_policy(self):
  with tempfile.NamedTemporaryFile() as file:
   for bands,default,expected in [([0,9],2,2),([9,0],1,1),([0],-1,-1)]:
    layer=Mock();layer.isValid.return_value=True;p=layer.dataProvider.return_value;p.bandCount.return_value=len(bands);p.colorInterpretation.side_effect=lambda i:bands[i-1]
    r=layer.renderer.return_value;r.alphaBand.side_effect=[default,-1];layer.loadNamedStyle.return_value=('',True)
    with patch.dict(sys.modules,{'qgis.core':Mock(Qgis=Mock(RasterColorInterpretation=Mock(AlphaBand=9)))}):
     result=m.apply_qml(layer,file.name)
    self.assertEqual(result['alpha_after'],expected)
 @unittest.skipUnless(GIS,'Requires isolated existing GIS Python')
 def test_actual_gdal_lookup(self):
  from osgeo import gdal,osr
  import numpy as np
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'authored.tif';ds=gdal.GetDriverByName('GTiff').Create(str(path),5,3,1,gdal.GDT_Float64);gt=(139,0.00002,0.000003,35,0.000004,-0.00003);ds.SetGeoTransform(gt);crs=osr.SpatialReference();crs.ImportFromEPSG(4326);ds.SetProjection(crs.ExportToWkt());a=np.arange(15,dtype=float).reshape(3,5);a[0,:3]=[0,-9999,np.nan];ds.GetRasterBand(1).SetNoDataValue(-9999);ds.GetRasterBand(1).WriteArray(a);ds=None
   for r in range(3):
    for c in range(5):
     x,y=gdal.ApplyGeoTransform(gt,c+.5,r+.5);v=m.lookup(path,x,y,uv=True)
     self.assertEqual((v['row'],v['col']),(r,c));self.assertEqual(v['uv'],[2-r,c])
     self.assertEqual(v['status'],'nan' if np.isnan(a[r,c]) else 'nodata' if a[r,c]==-9999 else 'valid')
   src=osr.SpatialReference();src.ImportFromEPSG(4326);src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);dst=osr.SpatialReference();dst.ImportFromEPSG(6677);dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
   x,y=gdal.ApplyGeoTransform(gt,4.5,2.5);x,y,_=osr.CoordinateTransformation(src,dst).TransformPoint(x,y);self.assertEqual(m.lookup(path,x,y,epsg=6677)['value'],14)
if __name__=='__main__':unittest.main()
