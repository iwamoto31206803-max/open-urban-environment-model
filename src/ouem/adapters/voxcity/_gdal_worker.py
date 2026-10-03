"""Standalone OSGeo worker for the VoxCity adapter (runs in captured GIS runtime)."""
import json, math, sys
from pathlib import Path
from osgeo import gdal, ogr

def points(geom):
    out=[]
    for i in range(geom.GetPointCount()): out.append(geom.GetPoint(i))
    for i in range(geom.GetGeometryCount()): out.extend(points(geom.GetGeometryRef(i)))
    return out

def run(job):
    source=ogr.Open(job["buildings"]); layer=source.GetLayerByName("building")
    if layer is None: raise RuntimeError("Standard Building layer 'building' not found")
    srs=layer.GetSpatialRef()
    if not srs or srs.GetAuthorityCode(None)!="6677": raise RuntimeError("Standard Building must be EPSG:6677")
    raster=gdal.Open(job["terrain"]); projection=raster.GetProjection()
    if "6677" not in projection: raise RuntimeError("Standard Terrain must be EPSG:6677")
    band=raster.GetRasterBand(1); nodata=band.GetNoDataValue(); gt=raster.GetGeoTransform()
    if gt[2] or gt[4]: raise RuntimeError("rotated Terrain grids are unsupported")
    records=[]; features=[]; warnings=[]
    extent=[float("inf"),float("inf"),float("-inf"),float("-inf")]
    for feature in layer:
        oid=feature.GetFieldAsString("ouem_id"); geom=feature.GetGeometryRef()
        if not oid or geom is None or geom.IsEmpty(): raise RuntimeError("invalid Standard Building ouem_id or geometry")
        envelope=geom.GetEnvelope(); extent=[min(extent[0],envelope[0]),min(extent[1],envelope[2]),max(extent[2],envelope[1]),max(extent[3],envelope[3])]
        x0=max(0,int(math.floor((envelope[0]-gt[0])/gt[1]))); x1=min(raster.RasterXSize-1,int(math.floor((envelope[1]-gt[0])/gt[1])))
        y0=max(0,int(math.floor((envelope[3]-gt[3])/gt[5]))); y1=min(raster.RasterYSize-1,int(math.floor((envelope[2]-gt[3])/gt[5])))
        samples=[]
        for y in range(min(y0,y1),max(y0,y1)+1):
            for x in range(x0,x1+1):
                px=gt[0]+(x+.5)*gt[1]; py=gt[3]+(y+.5)*gt[5]
                p=ogr.Geometry(ogr.wkbPoint); p.AddPoint_2D(px,py)
                if geom.Contains(p) or geom.Touches(p):
                    value=float(band.ReadAsArray(x,y,1,1)[0,0])
                    if math.isfinite(value) and (nodata is None or value!=nodata): samples.append(value)
        if not samples: raise RuntimeError("Terrain coverage missing for building "+oid)
        zs=[float(p[2]) for p in points(geom) if len(p)>=3 and math.isfinite(p[2])]
        top=max(zs); bottom=min(zs); ground=math.fsum(samples)/len(samples); height=top-ground
        if height<=0: raise RuntimeError("non-positive height for building "+oid)
        footprint=geom.Clone(); footprint.FlattenTo2D()
        record={"ouem_id":oid,"z_top_abs":top,"z_bottom_geom_abs":bottom,"ground_eff_abs":ground,"height":height,"min_height":0.0,
          "ground_sample_count":len(samples),"ground_sample_min_abs":min(samples),"ground_sample_max_abs":max(samples)}
        records.append(record); features.append({"type":"Feature","properties":{"ouem_id":oid},"geometry":json.loads(footprint.ExportToJson())})
    return {"records":records,"geojson":{"type":"FeatureCollection","name":"voxcity_buildings","crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::6677"}},"features":features},"aoi":job.get("aoi") or extent,"warnings":warnings}

try:
    job=json.loads(Path(sys.argv[1]).read_text()); result=run(job); Path(sys.argv[2]).write_text(json.dumps(result))
except Exception as exc:
    print(str(exc),file=sys.stderr); raise SystemExit(1)
