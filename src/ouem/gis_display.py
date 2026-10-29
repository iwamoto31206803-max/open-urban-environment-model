"""Standalone GIS-Python helpers; load this file directly, without importing OUEM.

These inspect original files, not QGIS's virtual display grid. No model calls.
"""
import argparse
import json
import math
from pathlib import Path


def apply_qml(layer, qml):
    """Load a style while preserving a verified provider alpha interpretation."""
    from qgis.core import Qgis
    if not layer.isValid():
        raise ValueError('Invalid raster layer')
    provider = layer.dataProvider()
    candidates = [i for i in range(1, provider.bandCount()+1)
                  if provider.colorInterpretation(i) == Qgis.RasterColorInterpretation.AlphaBand]
    before = layer.renderer().alphaBand()
    if before in candidates:
        alpha = before
    elif len(candidates) == 1:
        alpha = candidates[0]
    elif not candidates:
        alpha = -1
    else:
        raise ValueError('Ambiguous provider alpha bands')
    message, ok = layer.loadNamedStyle(str(Path(qml).resolve(strict=True)))
    if not ok:
        raise ValueError('QML load failed: '+message)
    styled = layer.renderer().alphaBand()
    if styled != alpha:
        layer.renderer().setAlphaBand(alpha)
    layer.triggerRepaint()
    return dict(alpha_before=before, alpha_from_qml=styled, alpha_after=alpha,
                provider_alpha_bands=candidates)


def pixel(geotransform, width, height, x, y):
    """Containing original pixel, half-open bounds; no tolerance/silent snapping."""
    if not all(math.isfinite(v) for v in (*geotransform, x, y)):
        raise ValueError('Finite coordinates and geotransform required')
    c,a,b,f,d,e = geotransform
    determinant = a*e-b*d
    if determinant == 0:
        raise ValueError('Singular geotransform')
    col = (e*(x-c)-b*(y-f))/determinant
    row = (-d*(x-c)+a*(y-f))/determinant
    if not (0 <= col < width and 0 <= row < height):
        raise ValueError('Coordinate outside original raster')
    return math.floor(row), math.floor(col)


def lookup(path, x, y, *, epsg=4326, uv=False):
    """Read original band 1; uv=True explicitly selects OUEM reversed-u mapping.

    Never called through the QGIS provider. Pixel boundaries use floor in the
    original grid; projected round trips at exact edges can have floating error.
    """
    from osgeo import gdal, osr
    if epsg not in (4326, 6677) or not all(math.isfinite(v) for v in (x,y)):
        raise ValueError('Finite XY and EPSG:4326 or EPSG:6677 required')
    with gdal.config_option('GDAL_PAM_ENABLED', 'NO'):
        ds = gdal.OpenEx(str(Path(path).resolve(strict=True)), gdal.OF_RASTER | gdal.OF_READONLY)
        if ds is None or ds.GetDriver().ShortName != 'GTiff' or ds.RasterCount != 1:
            raise ValueError('Original single-band GeoTIFF required')
        target = ds.GetSpatialRef()
        if target is None:
            raise ValueError('Missing source CRS')
        source = osr.SpatialReference();source.ImportFromEPSG(epsg)
        for crs in (source,target):
            crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        tx,ty,_ = osr.CoordinateTransformation(source,target).TransformPoint(x,y)
        row,col = pixel(ds.GetGeoTransform(), ds.RasterXSize, ds.RasterYSize, tx,ty)
        band = ds.GetRasterBand(1)
        value = band.ReadAsArray(col,row,1,1)[0,0].item()
        nodata = band.GetNoDataValue()
        nan = isinstance(value,float) and math.isnan(value)
        masked = int(band.GetMaskBand().ReadAsArray(col,row,1,1)[0,0]) == 0
        status = 'nan' if nan else 'nodata' if masked or (nodata is not None and value == nodata) else 'valid'
        result = dict(row=row,col=col,value=None if nan else value,status=status,
                      is_nodata=masked or (nodata is not None and (nan if math.isnan(nodata) else value==nodata)),
                      reference='original GeoTIFF band 1; not QGIS Identify')
        if uv:
            result['uv'] = [ds.RasterYSize-1-row,col]
        ds = None
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raster',type=Path,required=True)
    parser.add_argument('--x',type=float,required=True);parser.add_argument('--y',type=float,required=True)
    parser.add_argument('--epsg',type=int,choices=(4326,6677),default=4326)
    parser.add_argument('--ouem-uv',action='store_true')
    args = parser.parse_args()
    print(json.dumps(lookup(args.raster,args.x,args.y,epsg=args.epsg,uv=args.ouem_uv),allow_nan=False))


if __name__ == '__main__':
    main()
