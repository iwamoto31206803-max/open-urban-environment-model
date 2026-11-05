"""Read saved B1 and Candidate B runs without invoking an evaluation kernel."""
import argparse
import json
from pathlib import Path

import numpy as np

from ouem import b2_gvi
from ouem.compatibility_probe import inspect
from ouem.consumers.source_h_standard import Watch
from ouem.komae_integration import voxcity_provenance
from ouem.native.building.source_h_geometry import require


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b1-run",required=True,type=Path)
    parser.add_argument("--candidate-run",required=True,type=Path)
    parser.add_argument("--candidate-report-sha256",required=True)
    args=parser.parse_args()
    engine=voxcity_provenance()
    require(engine["verified"],"engine","fixed VoxCity installation required")
    saved=b2_gvi.load_run(args.b1_run)
    def b1_array(name):
        return np.load(saved["root"]/"voxel"/(name+".npy"),allow_pickle=False,mmap_mode="r")
    g=saved["grid"]
    model=json.loads((saved["root"]/"voxel/report.json").read_bytes())["model"]
    xy=np.stack((b1_array("centre_x"),b1_array("centre_y")),axis=-1)
    meta=dict(shape=g["shape"],axes=["north","east","up"],mesh_m=g["nominal_voxel_size_m"],xy_epsg=6677,
              canopy="ESTIMATED",d0_effective_abs_m=g["D0_effective_H_m"],
              numba=model["numba"],
              origin_lonlat=g["origin_lonlat"],u_step_lonlat=g["u_step_lonlat"],v_step_lonlat=g["v_step_lonlat"],
              domain_bounds=g["projected_domain_bounds"],evaluation_bounds=g["projected_evaluation_ROI_bounds"],
              observer_height_m=1.5,
              source_id_by_numeric_id={str(r["id"]):r["source_id"] for r in model["selected_buildings"]})
    xyz=np.concatenate((xy,(meta["d0_effective_abs_m"]+saved["index"]+.5)[...,None]),axis=-1)
    left=inspect(saved["current"],b1_array("building_ids"),b1_array("terrain_H"),b1_array("effective_ground_H"),
                 xy,saved["roi"],meta,saved["index"],saved["valid"],xyz)
    watch=Watch(args.candidate_run.resolve())
    report=watch.capture("report","report.json",args.candidate_report_sha256,json_data=True)
    require(report["profile"]=="ouem-candidate-b-t5-23/v0.1" and report["gate1"]==report["gate2"]=="PASS",
            "candidate","completed T5-2/T5-3 required")
    for key,sha in report["outputs"].items():
        watch.capture(key,key,sha)
    def candidate(name):
        return np.load(watch.resolve(name+".npy"),allow_pickle=False,mmap_mode="r")
    voxels=candidate("t5-3/voxels")
    xy=candidate("t5-2/centres_xy")
    index,valid,_=b2_gvi.observers(voxels)
    grid=report["grid"]["engine_grid"]
    meta=dict(shape=list(voxels.shape),axes=["north","east","up"],mesh_m=grid["meshsize_m"],xy_epsg=6677,
              canopy="NONE",d0_effective_abs_m=report["voxels"]["z_reference_abs_m"],
              numba=report["voxels"]["numba"],origin_lonlat=grid["origin"],
              u_step_lonlat=(np.array(grid["u_vec"])*grid["adj_mesh"][0]).tolist(),
              v_step_lonlat=(np.array(grid["v_vec"])*grid["adj_mesh"][1]).tolist(),
              domain_bounds=report["domain"],evaluation_bounds=report["evaluation_aoi"],observer_height_m=1.5,
              source_id_by_numeric_id={str(r["id"]):r["source_id"] for r in report["grid"]["buildings"]})
    xyz=np.concatenate((xy,(meta["d0_effective_abs_m"]+index+.5)[...,None]),axis=-1)
    right=inspect(voxels,candidate("t5-2/building_ids"),candidate("t5-2/dem"),candidate("t5-3/effective_dem_abs"),
                  xy,candidate("t5-2/evaluation_mask"),meta,index,valid,xyz)
    right["saved_observer_contract"]="NOT_VERIFIED; recomputed using B2 observer definition"
    b2_gvi.unchanged(saved)
    watch.unchanged()
    print(json.dumps(dict(engine=engine,b1=left,candidate=right,
                          b1_inputs=b2_gvi.provenance(saved),candidate_inputs=watch.identities,
                          input_immutability="PASS"),indent=2))


if __name__=="__main__":
    main()
