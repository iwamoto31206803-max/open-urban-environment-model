"""Read-only CityGML-to-Adapter Z and height provenance diagnosis."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np

from ouem import komae_geometry_provenance as provenance
from ouem import komae_integration as runner
from ouem.adapters.voxcity import _z_values
from ouem.komae_repair_qgis_export import _guard_output, _new_directory
from ouem.standardize.building import deterministic_ouem_id

GML = "http://www.opengis.net/gml"
CITY = "http://www.opengis.net/citygml/building/2.0"
ID = f"{{{GML}}}id"
DEFAULT_GML = Path("data/raw/building/plateau_komae/53393465_bldg_6697_op.gml")


def require(condition, message):
    if not condition:
        raise provenance.Inconclusive(message)


def height_value(value):
    """PLATEAU -9999 denotes missing height, never a measured building height."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def missing_sentinel(value):
    try:
        return float(value) == -9999
    except (TypeError, ValueError):
        return False


def z_summary(values):
    numbers = np.asarray(values, dtype="<f8")
    require(numbers.size > 0 and np.isfinite(numbers).all(), "missing or nonfinite 3D vertices")
    return {"vertex_count": int(numbers.size), "z_min_m": float(numbers.min()),
            "z_max_m": float(numbers.max()),
            "sorted_z_sha256": hashlib.sha256(np.sort(numbers).tobytes()).hexdigest()}


def citygml_buildings(path, source_ids, *, require_all=True):
    """Stream complete Building elements; report unsupported coordinates explicitly."""
    from pyproj import CRS
    wanted, found = set(source_ids), {}
    crs_stack = []
    envelope_crs = set()
    for event, element in ET.iterparse(path, events=("start", "end")):
        if event == "start":
            crs_stack.append(element.attrib.get("srsName") or (crs_stack[-1] if crs_stack else None))
            if element.tag == f"{{{GML}}}Envelope" and element.get("srsName"):
                envelope_crs.add(element.get("srsName"))
            continue
        if element.tag == f"{{{CITY}}}Building" and element.get(ID) in wanted:
            identifier = element.get(ID)
            require(identifier not in found, f"duplicate CityGML gml:id: {identifier}")
            crs_names = {name for node in element.iter() if (name := node.get("srsName"))}
            if crs_stack[-1]:
                crs_names.add(crs_stack[-1])
            if not crs_names:
                crs_names.update(envelope_crs)
            crs_values = [CRS.from_user_input(name) for name in crs_names]
            require(crs_values and all(crs == crs_values[0] for crs in crs_values),
                    f"missing or mixed CityGML CRS for {identifier}: {sorted(crs_names)}")
            crs = crs_values[0]
            require(crs.to_epsg() == 6697, f"CityGML {identifier} is not declared EPSG:6697")
            positions, unsupported = [], []
            for node in element.iter():
                if node.tag not in (f"{{{GML}}}posList", f"{{{GML}}}pos"):
                    if node.tag == f"{{{GML}}}coordinates" or any(key.endswith("}href") for key in node.attrib):
                        unsupported.append(node.tag)
                    continue
                tokens = (node.text or "").split()
                dimension = node.get("srsDimension") or node.get("dimension")
                if dimension is not None and dimension != "3":
                    unsupported.append(f"{node.tag}: dimension={dimension}")
                    continue
                if not tokens or len(tokens) % 3:
                    unsupported.append(f"{node.tag}: incomplete XYZ tuples")
                    continue
                try:
                    triples = [tuple(map(float, tokens[i:i + 3])) for i in range(0, len(tokens), 3)]
                except ValueError:
                    unsupported.append(f"{node.tag}: nonnumeric coordinates")
                    continue
                if not all(math.isfinite(value) for point in triples for value in point):
                    unsupported.append(f"{node.tag}: nonfinite XYZ coordinates")
                    continue
                positions.extend(triples)
            require(not unsupported, f"unsupported CityGML geometry for {identifier}: {unsupported}")
            measured = [node.text for node in element.findall(f"{{{CITY}}}measuredHeight")]
            require(len(measured) <= 1, f"ambiguous measuredHeight for {identifier}")
            values = z_summary([point[2] for point in positions])
            found[identifier] = {**values, "gml_id": identifier, "crs": crs.to_string(),
                                 "axis_order": [axis.direction for axis in crs.axis_info],
                                 "measured_height_raw": measured[0] if measured else None,
                                 "measured_height_m": height_value(measured[0]) if measured else None,
                                 "first_xyz": list(positions[0])}
        if element.tag == f"{{{CITY}}}Building":
            element.clear()
        crs_stack.pop()
    if require_all:
        require(set(found) == wanted, f"CityGML gml:id missing: {sorted(wanted - set(found))}")
    return found


def _feature(path, layer, field, value):
    from pyproj import CRS
    row, geometry = provenance.read_feature(path, layer, field, value, native=(field == "id"))
    require(geometry[1] is not None, f"missing CRS: {path}")
    crs = CRS.from_user_input(geometry[1])
    summary = z_summary(_z_values(geometry[0]))
    measured_field = next((key for key in row.index if key.casefold() in ("measuredheight", "measured_height")), None)
    measured = row[measured_field] if measured_field else None
    return {**summary, "path": str(path), "crs": crs.to_string(),
            "crs_axis_order": [axis.direction for axis in crs.axis_info],
            "geometry_coordinate_order": "GeoPackage geometry XY(Z); axis metadata is listed separately",
            "measured_height_raw": None if measured is None else str(measured),
            "measured_height_m": height_value(measured)}


def _select(frame, source_prefix, extra_ids, contained_ids):
    source = frame["source_id"].astype(str)
    matches = frame.loc[source.str.startswith(source_prefix)]
    require(len(matches) == 1, f"source_id prefix {source_prefix!r} has {len(matches)} Standard matches")
    target = str(matches.iloc[0].source_id)
    selected = [(target, "target")]
    for value in extra_ids:
        require((source == value).sum() == 1, f"extra source_id {value!r} is not unique in Standard")
        if value != target:
            selected.append((value, "requested_representative"))
    for role in ("low_measured_height", "high_measured_height", "measured_height_minus_9999"):
        for preferred in (True, False):
            remaining = frame.loc[~source.isin([item[0] for item in selected])].copy()
            if preferred:
                remaining = remaining.loc[remaining.ouem_id.isin(contained_ids)]
            remaining["valid_height"] = remaining["measured_height"].map(height_value)
            if role == "measured_height_minus_9999":
                choices = remaining.loc[remaining.measured_height.map(missing_sentinel)].sort_values("source_id")
            else:
                choices = remaining.loc[remaining.valid_height.notna()].sort_values(["valid_height", "source_id"])
            if len(choices):
                row = choices.iloc[-1] if role == "high_measured_height" else choices.iloc[0]
                selected.append((str(row.source_id), role))
                break
    return selected


def _z_transition(left, right):
    if left is None or right is None:
        return {"status": "NOT_CHECKED"}
    return {"status": "CHECKED", "delta_min_m": right["z_min_m"] - left["z_min_m"],
            "delta_max_m": right["z_max_m"] - left["z_max_m"],
            "same_z_multiset": left["vertex_count"] == right["vertex_count"] and
                               left["sorted_z_sha256"] == right["sorted_z_sha256"]}


def _classify(stages, adapter_record, city_link_verified):
    names = ("citygml", "converter", "native", "standard")
    transitions = {f"{a}_to_{b}": _z_transition(stages.get(a), stages.get(b))
                   for a, b in zip(names, names[1:])}
    first_extrema = next((key for key, value in transitions.items()
                          if value["status"] == "CHECKED" and
                          (abs(value["delta_min_m"]) > 1e-6 or abs(value["delta_max_m"]) > 1e-6)), None)
    first = next((key for key, value in transitions.items()
                  if value["status"] == "CHECKED" and abs(value["delta_max_m"]) > 1e-6), None)
    complete = all(name in stages for name in names) and adapter_record is not None
    if not complete:
        level, reason = "UNRESOLVED", "one or more saved stages or Adapter records are unavailable"
    elif first:
        level = "CONFIRMED" if first != "citygml_to_converter" or city_link_verified else "LIKELY"
        reason = f"first observed Z maximum change is {first}; source-to-Converter file provenance is not recorded" if first == "citygml_to_converter" else f"first observed Z maximum change is {first}"
    else:
        level, reason = "UNRESOLVED", "no saved-stage Z maximum change; inspect the complete CityGML geometry/LOD and vertical reference against independent source evidence"
    return {"level": level, "first_z_extrema_change": first_extrema or "NONE_OBSERVED",
            "first_z_max_change": first or "NONE_OBSERVED",
            "reason": reason, "transitions": transitions,
            "meaning": "CONFIRMED locates an observed numerical transition only; it does not prove the final cause of an anomalous building height."}


def diagnose_run(root, citygml, source_prefix, extra_ids=()):
    import geopandas as gpd
    evidence = provenance.Evidence(root)
    citygml = evidence.protect(citygml)
    a1 = provenance.command(evidence.report, 1, "a1")
    full = evidence.artifact(provenance.option(a1, "--output"))
    full_manifest = evidence.manifest(full)
    a3 = provenance.command(evidence.report, 1, "a3")
    subset = evidence.artifact(a3[2])
    native = evidence.input("native_building")
    native_manifest = evidence.document(evidence.input("native_building_manifest"))
    source_record = native_manifest["source"]
    converter = evidence.protect(source_record["file"], source_record)
    converter_layer = source_record["layer_resolved"]
    frame = gpd.read_file(full, layer=full_manifest["validation"]["output_layer"])
    require(frame.crs is not None and frame.crs.to_epsg() == 6677, "Standard CRS differs")
    contained = gpd.read_file(subset, layer=full_manifest["validation"]["output_layer"])
    selected = _select(frame, source_prefix, extra_ids, set(contained.ouem_id))
    gml = citygml_buildings(citygml, [source_id for source_id, _ in selected], require_all=False)
    require(selected[0][0] in gml, f"target gml:id {selected[0][0]!r} is absent from supplied CityGML")
    rows = []
    for source_id, role in selected:
        ouem_id = deterministic_ouem_id(source_id)
        stages = ({"citygml": {**gml[source_id], "path": str(citygml)}} if source_id in gml else {})
        issues = [] if source_id in gml else ["representative gml:id is absent from supplied CityGML tile"]
        try:
            stages["converter"] = _feature(converter, converter_layer, "id", source_id)
            stages["native"] = _feature(native, native_manifest["parameters"]["output_layer"], "id", source_id)
        except (provenance.Inconclusive, KeyError, ValueError) as exc:
            issues.append(f"{type(exc).__name__}: {exc}")
        repeats = []
        for number in (1, 2):
            trace = provenance.diagnose_repeat(evidence, number, ouem_id)
            command = provenance.command(evidence.report, number, "a1")
            standard = evidence.artifact(provenance.option(command, "--output"))
            manifest = evidence.manifest(standard)
            item = {"repeat": number, "lineage_issues": trace["issues"]}
            standard_stage = _feature(standard, manifest["validation"]["output_layer"], "ouem_id", ouem_id)
            item["standard"] = standard_stage
            if number == 1:
                stages["standard"] = standard_stage
            if not trace["issues"]:
                a3 = provenance.command(evidence.report, number, "a3")
                adapter_path = evidence.artifact(provenance.option(a3, "--adapter-output"))
                adapter_manifest = evidence.manifest(adapter_path)
                records = [value for value in adapter_manifest["buildings"] if value["ouem_id"] == ouem_id]
                require(len(records) == 1, f"missing/duplicate Adapter ID {ouem_id}")
                record = records[0]
                item["adapter"] = {key: record[key] for key in ("voxcity_id", "z_top_abs", "ground_eff_abs",
                    "ground_sample_min_abs", "ground_sample_max_abs", "ground_sample_count", "height",
                    "z_bottom_geom_abs")}
                item["adapter"].update(crs=adapter_manifest["crs"]["target"],
                    geometry_coordinate_order="GeoJSON longitude, latitude; output geometry is 2D")
                item["adapter_consistent"] = (math.isclose(record["z_top_abs"], standard_stage["z_max_m"], abs_tol=1e-6) and
                    math.isclose(record["height"], record["z_top_abs"] - record["ground_eff_abs"], abs_tol=1e-6))
            repeats.append(item)
        adapter_record = repeats[0].get("adapter")
        verdict = _classify(stages, adapter_record, city_link_verified=False)
        repeat_consistent = (all(not item["lineage_issues"] and item.get("adapter_consistent") for item in repeats)
                             and repeats[0].get("standard", {}).get("sorted_z_sha256") ==
                             repeats[1].get("standard", {}).get("sorted_z_sha256")
                             and repeats[0].get("adapter") == repeats[1].get("adapter"))
        if not repeat_consistent:
            verdict.update(level="UNRESOLVED", reason="saved lineage, Adapter formula, or independent repeats differ")
        if adapter_record:
            verdict["citygml_max_minus_ground_m"] = (stages["citygml"]["z_max_m"] - adapter_record["ground_eff_abs"]
                if "citygml" in stages else None)
            verdict["standard_max_minus_ground_m"] = stages["standard"]["z_max_m"] - adapter_record["ground_eff_abs"]
            verdict["adapter_minus_measured_height_m"] = (adapter_record["height"] - stages["citygml"]["measured_height_m"]
                if "citygml" in stages and stages["citygml"]["measured_height_m"] is not None else None)
        rows.append({"role": role, "source_id": source_id, "gml_id": gml[source_id]["gml_id"] if source_id in gml else None,
                     "ouem_id": ouem_id, "stages": stages, "repeats": repeats,
                     "repeat_consistent": repeat_consistent,
                     "classification": verdict, "issues": issues})
    integrity = evidence.finish()
    return {"schema": "ouem-komae-building-vertical-diagnosis/v0.1", "scope": "DIAGNOSTIC_NOT_ACCEPTANCE",
            "run": str(root), "command": ["python", "-m", "ouem.komae_vertical_provenance",
                str(Path(root).name), source_prefix, "--citygml", str(citygml)],
            "source_gml_to_converter_provenance": "NOT_VERIFIED: manual Converter receipt records its GeoPackage, not the source CityGML SHA-256",
            "inputs_sha256": {path: record["sha256"] for path, record in sorted(evidence.before.items())},
            "input_integrity": integrity, "buildings": rows,
            "limitations": ["This diagnostic alone does not establish formal real-data acceptance.",
                "A numeric Z transition identifies its first observed interval, not the reason for that change.",
                "Source-to-Converter identity cannot be confirmed without independently recorded CityGML provenance.",
                "measuredHeight=-9999 is missing, never a valid height; measuredHeight is diagnostic, not a replacement for the Adapter contract."]}


def markdown(report):
    lines = ["# Komae building vertical-geometry diagnosis", "", f"Run: `{report['run']}`", "",
             "Diagnostic only; no data conversion, repair, or acceptance.", "",
             "| Role | source_id / gml:id | CityGML Z min/max | Converter Z min/max | Native Z min/max | Standard Z min/max | Ground | Adapter height | First Z-max change | Classification |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for row in report["buildings"]:
        stage = row["stages"]
        def span(name):
            value = stage.get(name)
            return f"{value['z_min_m']:.3f}/{value['z_max_m']:.3f}" if value else "NOT_CHECKED"
        adapter = row["repeats"][0].get("adapter") or {}
        lines.append(f"| {row['role']} | {row['source_id']} | {span('citygml')} | {span('converter')} | "
                     f"{span('native')} | {span('standard')} | {adapter.get('ground_eff_abs', 'NOT_CHECKED')} | "
                     f"{adapter.get('height', 'NOT_CHECKED')} | {row['classification']['first_z_max_change']} | "
                     f"{row['classification']['level']} |")
    lines += ["", "`CONFIRMED` locates an observed numerical transition only, not the final cause.",
              "CityGML-to-Converter file identity requires independent provenance review.",
              "Review the JSON for full-vertex hashes, measuredHeight, both repeats, lineage, and SHA-256.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="existing integration run ID")
    parser.add_argument("source_id_prefix", help="unique Standard source_id prefix matching CityGML gml:id")
    parser.add_argument("--citygml", type=Path, default=DEFAULT_GML)
    parser.add_argument("--extra-source-id", action="append", default=[])
    parser.add_argument("--output-base", type=Path, help="new independent diagnosis directory; default prints JSON")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("run ID must be a portable directory name of at most 64 characters")
    root = runner.REPOSITORY / "data/work/integration" / args.run_id
    citygml = args.citygml if args.citygml.is_absolute() else runner.REPOSITORY / args.citygml
    try:
        report = diagnose_run(root, citygml, args.source_id_prefix, args.extra_source_id)
        if args.output_base:
            output_base = args.output_base if args.output_base.is_absolute() else runner.REPOSITORY / args.output_base
            directory, identity = _new_directory(output_base, root, args.run_id)
            for filename, content in (("diagnosis.json", json.dumps(report, indent=2, ensure_ascii=False,
                                                                       allow_nan=False) + "\n"),
                                      ("summary.md", markdown(report))):
                _guard_output(directory.parent, directory, identity)
                with (directory / filename).open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(content)
            print(directory)
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if all(row["classification"]["level"] != "UNRESOLVED" for row in report["buildings"]) else 2
    except Exception as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
