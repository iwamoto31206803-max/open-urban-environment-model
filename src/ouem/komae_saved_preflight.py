"""Check frozen PR #99 identities without opening rasters, databases or arrays.

Use a stable local snapshot mounted read-only for an authorized real run.
The inherited filesystem checks detect changes, but are not a sandbox
against concurrent replacement of directories by another process.
"""
import argparse
import json
from pathlib import Path, PureWindowsPath
import stat
import sys

from ouem.consumers.source_h_standard import Watch, digest_text
from ouem.native.building.source_h_geometry import GeometryValidationError, require
from ouem.real_komae_solar import BASE_REPORT_SHA, ENVELOPE_SHA

FINAL_REPORT_SHA = "0fb30cf5f500dd726a3b1032ce0a9fb51bb9d84488bdc417a63cf15bdeecbdc2"
FINAL_OUTPUTS = {
    "grid.json": "bfc9ed90daec82c1caccdd635adf45ea7e4c33114da70bc089036743a9e80b19",
    "current_voxels.npy": "c7ff44c47e3c85fd8b8c6908f1a9325bc0c81549eeb2a67069054fa66190728e",
    "no_canopy_voxels.npy": "015ba23186093d6fedc9f7ee7bd2b683965dfb4da7f1404d02adbb666aee0561",
}
ENGINE_COMMIT = "fa212656305328a9a657973bae26f352bfe813bc"


def check_component(path):
    info = path.lstat()
    require(not stat.S_ISLNK(info.st_mode)
            and not (getattr(info, "st_file_attributes", 0)
                     & stat.FILE_ATTRIBUTE_REPARSE_POINT),
            "path", "symlinks and reparse points are forbidden")
    return info


class FrozenWatch(Watch):
    """Keep Watch's descriptor and digest checks with stricter path rules."""

    def __init__(self, root):
        root = Path(root).absolute()
        require(".." not in root.parts, "root", "parent traversal forbidden")
        for component in (*reversed(root.parents), root):
            check_component(component)
        super().__init__(root)

    def resolve(self, locator):
        require(isinstance(locator, str), "path", "relative locator required")
        path = Path(locator)
        win = PureWindowsPath(locator)
        require(path.parts and not path.is_absolute() and not win.anchor
                and not any(character in locator for character in ("\\", ":", "\0"))
                and ".." not in path.parts, "path", "relative locator required")
        current = self.root
        for part in path.parts:
            current /= part
            info = check_component(current)
            if stat.S_ISREG(info.st_mode):
                self.stamp(info)
        return super().resolve(locator)

    @staticmethod
    def stamp(info):
        require(info.st_nlink == 1, "file", "hardlinks are forbidden")
        return Watch.stamp(info)


def child(parent, name):
    require(isinstance(name, str) and name not in ("", ".", "..")
            and not any(character in name for character in ("/", "\\", ":", "\0")),
            "output", "plain filename required")
    return (Path(parent).parent / name).as_posix()


def bind(watch, key, locator, ref, *, parse=False):
    digest_text(ref["sha256"], key)
    require(type(ref["size_bytes"]) is int, key, "size required")
    return watch.capture(key, locator, ref["sha256"], ref["size_bytes"], json_data=parse)


def _verify(root, report_locator, final_sha, base_sha, envelope_sha, output_pins):
    watch = FrozenWatch(root)
    report = watch.capture("final", report_locator, final_sha, json_data=True)
    require(report["status"] == "COMPLETED" and report["input_immutability"] == "PASS"
            and "run_config" not in report and report["preflight"]["status"] == "PASS",
            "final", "expected final historical run")
    inputs = report["input_artifacts"]
    base_ref, envelope_ref = inputs["PR98_report"], inputs["envelope_manifest"]
    require(base_ref["sha256"] == base_sha and envelope_ref["sha256"] == envelope_sha
            and report["preflight"]["source_model_report_sha256"] == base_sha,
            "chain", "unexpected model or Envelope identity")
    base = bind(watch, "base", base_ref["path"], base_ref, parse=True)
    envelope = bind(watch, "envelope", envelope_ref["path"], envelope_ref, parse=True)
    require(base["status"] == envelope["status"] == "COMPLETED"
            and base["consumer"]["technical_validation"] == "PASS"
            and base["input_immutability"] == "PASS"
            and envelope["schema"] == "ouem-height-envelope-poc/v0.1"
            and envelope["cr_model"]["parameters"]["cr"] == report["preflight"]["source_CR"] == .6,
            "chain", "invalid recorded evidence or CR")

    # Runtime code hashes describe the historical implementation. They do
    # not authorize reading or requiring that checkout's Python source.
    for key, ref in inputs.items():
        if key != "implementation":
            bind(watch, "input:" + key, ref["path"], ref)
    for key, ref in envelope["input_files"].items():
        recorded = inputs["envelope_input:" + key]
        require(recorded["sha256"] == ref["sha256"] and recorded["size_bytes"] == ref["bytes"],
                "chain", "Envelope input binding differs")
    require(envelope["input_files"]["terrain"]["sha256"] == base["input_artifacts"]["terrain"]["sha256"],
            "chain", "different recorded terrain")
    for key, ref in base["input_artifacts"].items():
        bind(watch, "base-input:" + key, ref["path"], ref)
    for name, ref in base["outputs"].items():
        bind(watch, "base-output:" + name, child(base_ref["path"], name), ref)
    for name, ref in envelope["outputs"].items():
        bind(watch, "envelope-output:" + name, child(envelope_ref["path"], name),
             {"sha256": ref["sha256"], "size_bytes": ref["bytes"]})

    outputs = report["outputs"]
    require(all(outputs[name]["sha256"] == sha for name, sha in output_pins.items()),
            "final", "unexpected output identities")
    for name, ref in outputs.items():
        bind(watch, "output:" + name, child(report_locator, name), ref)
    grid = bind(watch, "final-grid", child(report_locator, "grid.json"), outputs["grid.json"], parse=True)
    engine = report["environment"]["voxcity"]
    base_grid = base["model"]["grid"]
    require(grid == base_grid and grid["shape"] == [128, 128, 27]
            and grid["layout"] == "uv_m/SOUTH_UP"
            and grid["D0_effective_H_m"] == 19.586000442504883
            and type(base["model"]["numba"]) is bool
            and engine["version"] == "1.7.0" and engine["commit"] == ENGINE_COMMIT
            and engine["verified"] is True,
            "metadata", "grid, D0 or recorded engine differs")
    require(outputs["no_canopy_voxels.npy"]["sha256"] == base["outputs"]["voxels.npy"]["sha256"],
            "control", "expected saved base voxel identity")
    watch.unchanged()
    return {"status": "PASS", "scope": "saved_identity_only",
            "report_sha256": final_sha, "checks": len(watch.identities),
            "recorded_numba": base["model"]["numba"],
            "semantic_revalidation": "NOT_EXECUTED"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--final-report", required=True, help="POSIX path relative to artifact root")
    args = parser.parse_args(argv)
    try:
        require(sys.dont_write_bytecode, "runtime", "use python -B")
        result = _verify(args.artifact_root, args.final_report, FINAL_REPORT_SHA,
                         BASE_REPORT_SHA, ENVELOPE_SHA, FINAL_OUTPUTS)
    except (GeometryValidationError, OSError, ValueError, KeyError, TypeError) as exc:
        # Validator details can contain local paths and input values.
        print(json.dumps({"status": "BLOCKED", "error_type": type(exc).__name__,
                          "code": getattr(exc, "code", "INVALID_OR_UNAVAILABLE_INPUT")}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
