"""Komae A3 real-data and pinned-VoxCity acceptance runner.

Run inside an environment containing VoxCity 1.7.0 at the pinned commit,
GeoPandas, Rasterio and NumPy after producing the adapter GeoJSON.  This keeps
the heavyweight engine an explicit acceptance dependency rather than an OUEM
runtime dependency.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

PIN = "fa212656305328a9a657973bae26f352bfe813bc"

def digest(array):
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument("adapter_geojson"); p.add_argument("terrain")
    p.add_argument("--meshsize",type=float,required=True); p.add_argument("--expected",type=int,default=111)
    p.add_argument("--report",required=True); args=p.parse_args()
    import geopandas as gpd
    import voxcity
    from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon
    gdf=gpd.read_file(args.adapter_geojson)
    if getattr(voxcity,"__version__",None)!="1.7.0": raise RuntimeError("VoxCity 1.7.0 is required")
    if len(gdf)!=args.expected: raise RuntimeError(f"expected {args.expected} buildings, got {len(gdf)}")
    bounds=gdf.total_bounds; rectangle=[(bounds[0],bounds[1]),(bounds[0],bounds[3]),(bounds[2],bounds[3]),(bounds[2],bounds[1])]
    def once(): return create_building_height_grid_from_gdf_polygon(gdf,args.meshsize,rectangle)
    h,m,ids,filtered=once(); h2,m2,ids2,filtered2=once()
    present={int(x) for x in ids.flat if int(x)>0}; expected=set(map(int,gdf.voxcity_id))
    report={"voxcity_version":"1.7.0","voxcity_commit":PIN,"input_buildings":len(gdf),
      "filtered_buildings":len(filtered),"building_id_grid_produced":bool(ids.size),
      "voxelization_ready":bool((h>0).any()),"ids_present":sorted(present),"ids_expected":sorted(expected),
      "no_unexplained_loss":present==expected,"deterministic":digest(h)==digest(h2) and digest(ids)==digest(ids2)}
    if not all((report["building_id_grid_produced"],report["voxelization_ready"],report["no_unexplained_loss"],report["deterministic"])):
        raise RuntimeError("VoxCity acceptance failed: "+json.dumps(report))
    Path(args.report).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
