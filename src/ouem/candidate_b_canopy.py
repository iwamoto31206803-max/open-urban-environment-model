"""STEP 2-B canopy input audit and narrow adapter to the existing B1 integrator."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from pyproj import Transformer
import rasterio
from shapely.geometry import box

from ouem.compatibility_probe import inspect, load_candidate
from ouem.consumers.source_h_standard import Watch
from ouem.height_envelope import sample_raster, validate_sources
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require
from ouem.real_komae_solar import sample_canopy, integrate_canopy
from ouem.candidate_b_shadow import T5_SHA
from ouem.terrain_candidate_b_preflight import digest

ENVELOPE_SHA = "6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68"


def integrate(arrays, metadata, segments, sampled, envelope, *, source_dem_sha256, building_height_grid):
    """Map a checked Candidate B snapshot to B1's unchanged TREE placement."""
    engine=voxcity_provenance()
    require(engine["verified"],"engine","fixed VoxCity installation required")
    require(envelope["quantity"]=="absolute_elevation_m" and envelope["vertical_reference"]=="T.P."
            and envelope["source_dem_sha256"]==source_dem_sha256,
            "canopy.vertical","explicit absolute T.P. and identical source DEM binding required")
    require(metadata["canopy"]=="NONE","canopy.base","base must have no TREE")
    inspect(**arrays,metadata=metadata)
    shape=arrays["voxels"].shape[:2]
    for key in ("state","missing","outside","valid","candidate","top","bottom"):
        require(sampled[key].shape==shape,"canopy.shape","sample grids differ from model")
    missing,outside=sampled["missing"],sampled["outside"]
    require(missing.dtype==outside.dtype==bool,"canopy.masks","boolean missing/outside required")
    finite=np.isfinite(sampled["top"])&np.isfinite(sampled["bottom"])&np.isfinite(sampled["state"])
    valid=~missing & ~outside & finite & (sampled["state"]==1)
    require(np.array_equal(valid,sampled["valid"]),"canopy.valid","sample validity differs from state/masks")
    ground=arrays["ground_abs"]
    # B1 stores the first air/building index; Candidate B's surface is one lower.
    surface=np.argmax(arrays["voxels"]==1,axis=2)
    a=dict(building_ids=arrays["ids"],building_heights=building_height_grid,
           terrain_H=arrays["raw_dem"],effective_ground_H=ground,
           effective_dem=ground-metadata["d0_effective_abs_m"],ground_indices=surface+1)
    current,absent,tree,high,low,qa=integrate_canopy(
        arrays["voxels"],a,segments,sampled,metadata["d0_effective_abs_m"],numba=metadata["numba"])
    qa.update(missing_inside_columns=int((missing&~outside).sum()),outside_columns=int(outside.sum()),
              invalid_state_inside_columns=int((~missing&~outside&(sampled["state"]!=1)).sum()),
              nonfinite_inside_columns=int((~missing&~outside&~finite).sum()),
              building_candidate_columns=int((sampled["candidate"]&(arrays["ids"]>0)).sum()),
              terrain_integration_ready=False,presence="ESTIMATED / NOT_OBSERVED",
              source_dem_sha256=source_dem_sha256,engine=engine)
    return current,absent,tree,high,low,qa


def audit(source, envelope_manifest, output, *, envelope_sha256=ENVELOPE_SHA):
    """Read-only audit of the existing B1 envelope, never real-model integration."""
    source=Path(source).resolve(strict=True)
    manifest_path=Path(envelope_manifest).resolve(strict=True)
    output=Path(output).resolve()
    for root in (source,manifest_path.parent):
        require(not output.is_relative_to(root) and not root.is_relative_to(output),
                "canopy.output","audit must use a new directory outside the input bundles")
    output.mkdir()
    report=dict(profile="ouem-candidate-b-step2b-input-audit/v0.1",status="BLOCKED",
                real_canopy_integration="NOT_VERIFIED",terrain_integration_ready=False)
    try:
        engine=voxcity_provenance()
        require(engine["verified"],"engine","fixed VoxCity installation required")
        arrays,metadata,probe,t5,model_watch=load_candidate(source,T5_SHA,observer_height=0.)
        envelope_watch=Watch(manifest_path.parent)
        record=envelope_watch.capture("manifest",manifest_path.name,envelope_sha256,json_data=True)
        require(record["status"]=="COMPLETED" and record["schema"]=="ouem-height-envelope-poc/v0.1",
                "canopy.manifest","completed Height Envelope required")
        artifact_root=Path(__file__).resolve().parents[2]
        upstream=Watch(artifact_root)
        for key,ref in record["input_files"].items():
            upstream.capture(key,Path(ref["path"]).resolve().relative_to(artifact_root).as_posix(),ref["sha256"],ref["bytes"])
        inputs=record["input_files"]
        semantics=validate_sources(*(inputs[k]["path"] for k in
            ("chm","acquisition_record","chm_evidence","terrain","terrain_manifest","terrain_acceptance")))
        paths=[manifest_path.parent/name for name in
               ("canopy_top_z.tif","canopy_bottom_z.tif","height_envelope_state.tif")]
        rasters=[]
        for path in paths:
            ref=record["outputs"][path.name]
            envelope_watch.capture(path.name,path.name,ref["sha256"],ref["bytes"])
            with rasterio.open(path) as ds:
                state=path.name=="height_envelope_state.tif"
                require(ds.count==1 and ds.crs.to_epsg()==6677 and ds.shape==
                        (record["grid_spec"]["height"],record["grid_spec"]["width"])
                        and list(ds.transform)[:6]==record["grid_spec"]["transform"]
                        and ds.nodata==(None if state else record["float_nodata"])
                        and ds.units==((None,) if state else ("m",)),
                        "canopy.grid","raster and envelope grid differ")
                require(ds.tags().get("VERTICAL_REFERENCE")==semantics["vertical_reference"]["name"]
                        and ds.tags().get("VERTICAL_QUANTITY")==
                        ("height_validity_flags" if state else "absolute_elevation_m"),
                        "canopy.vertical","raster and source vertical declaration differ")
                rasters.append(dict(file=path.name,bounds=list(ds.bounds),crs=ds.crs.to_string(),
                                    nodata=ds.nodata,tags=ds.tags(),dtype=ds.dtypes[0]))
        sampled=sample_canopy(paths,arrays["centres_xy"][...,0],arrays["centres_xy"][...,1])
        acquisition=json.loads(Path(inputs["acquisition_record"]["path"]).read_bytes())
        evidence_path=Path(inputs["chm_evidence"]["path"])
        review=json.loads(evidence_path.read_bytes())["compatibility_review"]
        approval=(evidence_path.parent/review["approval_record_path"]).resolve()
        upstream.capture("limited_review",approval.relative_to(artifact_root).as_posix(),
                         review["approval_record_sha256"])
        raw=[]
        for tile in acquisition["tiles"]:
            path=Path(tile["path"]).resolve()
            upstream.capture("raw:"+tile["quadkey"],path.relative_to(artifact_root).as_posix(),tile["sha256"],tile["bytes"])
            with rasterio.open(path) as ds:
                x,y=Transformer.from_crs(6677,ds.crs,always_xy=True).transform(
                    arrays["centres_xy"][...,0],arrays["centres_xy"][...,1],errcheck=True)
                bounds=ds.bounds
                inside=(x>=bounds.left)&(x<bounds.right)&(y>=bounds.bottom)&(y<bounds.top)
                crs=ds.crs.to_string()
            grid=SimpleNamespace(height=inside.shape[0],width=inside.shape[1],epsg=6677,
                                 centres=lambda:(arrays["centres_xy"][...,0],arrays["centres_xy"][...,1]))
            sample=sample_raster(path,grid)
            native_valid=~sample.missing & ~sample.outside & np.isfinite(sample.values) & (sample.values>=0)
            raw.append(dict(quadkey=tile["quadkey"],sha256=tile["sha256"],crs=crs,
                            model_centres_inside_extent=int(inside.sum()),cells=int(inside.size),
                            valid_nearest_samples=int(native_valid.sum()),
                            valid_zero_samples=int((native_valid&(sample.values==0)).sum()),
                            limitation="raw HAG samples only; no Candidate B Height Envelope generated"))
        source_dem=inputs["terrain"]["sha256"]
        target_dem=t5["outputs"]["t5-2/terrain.tif"]
        reasons=[]
        if not sampled["valid"].all():
            reasons.append("INCOMPLETE_CANDIDATE_B_ENVELOPE_COVERAGE")
        if source_dem!=target_dem:
            reasons.append("ENVELOPE_SOURCE_DEM_DIFFERS_FROM_T5")
        report.update(status="COMPLETED",engine=engine,candidate_probe=probe,
                      model_inputs=model_watch.identities,envelope_inputs=envelope_watch.identities,
                      upstream_inputs=upstream.identities,implementation_sha256=digest(Path(__file__)),
                      source_grid=record["grid_spec"],domain=metadata["domain_bounds"],
                      envelope_cr_model=record["cr_model"],state_encoding=record["state_encoding"],
                      source_semantics=semantics,rasters=rasters,raw_chm_extent_review=raw,
                      coverage=dict(model_cells=int(sampled["valid"].size),valid=int(sampled["valid"].sum()),
                                    outside=int(sampled["outside"].sum()),
                                    missing_inside=int((sampled["missing"]&~sampled["outside"]).sum())),
                      envelope_intersects_domain=box(*record["grid_spec"]["bounds"]).intersects(
                          box(*metadata["domain_bounds"])),
                      source_dem_sha256=source_dem,target_dem_sha256=target_dem,
                      source_dem_matches_model=source_dem==target_dem,
                      reasons=reasons,
                      source_immutability="PASS")
        model_watch.unchanged()
        envelope_watch.unchanged()
        upstream.unchanged()
    except Exception as exc:
        report.update(status="BLOCKED",error=f"{type(exc).__name__}: {exc}",source_immutability="NOT_VERIFIED")
    with (output/"report.json").open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
        stream.write("\n")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run",type=Path,required=True)
    parser.add_argument("--envelope-manifest",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    report=audit(args.source_run,args.envelope_manifest,args.output_dir)
    print(report["status"],report.get("error",report.get("coverage")))
    return int(report["status"]!="COMPLETED")


if __name__=="__main__":
    raise SystemExit(main())
