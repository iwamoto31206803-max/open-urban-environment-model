"""Opt-in contained-building PoC selection, not a change to A1 or its contract."""
from __future__ import annotations

import math
import os
from pathlib import Path

SELECTED = 92
EXCLUDED = 19


class PocBlocked(ValueError):
    """The explicitly scoped PoC prerequisites are not met."""


def select(frame, area):
    from shapely.geometry import box
    from ouem.adapters.voxcity import build_normalized_footprint
    if area.epsg != 6677 or not all(math.isfinite(v) for v in area.extent):
        raise PocBlocked("contained PoC requires finite EPSG:6677 Study Area")
    if frame.crs is None or frame.crs.to_epsg() != 6677:
        raise PocBlocked("contained PoC requires EPSG:6677 Standard Building")
    if frame.ouem_id.isna().any() or frame.ouem_id.duplicated().any():
        raise PocBlocked("contained PoC requires unique non-null building IDs")
    study = box(*area.extent)
    selected, excluded, outside, touching = [], [], [], []
    for row in frame.itertuples():
        footprint, _ = build_normalized_footprint(row.geometry, row.ouem_id)
        if study.covers(footprint):
            selected.append(row.ouem_id)
        else:
            excluded.append(row.ouem_id)
            if not study.intersects(footprint):
                outside.append(row.ouem_id)
            elif study.touches(footprint):
                touching.append(row.ouem_id)
    evidence = {"rule": "study.covers(normalized 2D footprint)",
                "study_area_epsg": area.epsg, "study_area_extent": list(area.extent),
                "source_count": len(frame), "selected_count": len(selected),
                "excluded_count": len(excluded), "selected_ids": sorted(selected),
                "excluded_ids": sorted(excluded), "outside_ids": sorted(outside),
                "touch_only_ids": sorted(touching), "geometry_operation": "whole-feature selection; no clipping",
                "scope": "CONTAINED_BUILDING_POC_ONLY_NOT_FORMAL_ACCEPTANCE"}
    return frame.loc[frame.ouem_id.isin(selected)].sort_values('ouem_id').copy(), evidence


def validate_selection(evidence):
    if (evidence['selected_count'] != SELECTED or evidence['excluded_count'] != EXCLUDED
            or evidence['source_count'] != SELECTED + EXCLUDED
            or evidence['outside_ids'] or evidence['touch_only_ids']):
        raise PocBlocked(f"PoC requires {SELECTED} contained / {EXCLUDED} crossing / 0 outside or touch-only; "
                         f"observed {evidence['selected_count']} / {evidence['excluded_count']}, "
                         f"outside={len(evidence['outside_ids'])}, touch-only={len(evidence['touch_only_ids'])}")


def write_subset(frame, target, parent, evidence, *, guard):
    """Write only new isolated outputs; preserve XYZ and Standard metadata exactly."""
    from ouem.komae_integration import adjacent, building_frame_semantics, building_semantics, canonical, fingerprint, read_json
    target, parent = Path(target), Path(parent)
    guard()
    if any(os.path.lexists(p) for p in (target, adjacent(target))):
        raise PocBlocked("PoC subset output already exists; no overwrite allowed")
    expected = building_frame_semantics(frame)
    frame.to_file(target, layer='building', driver='GPKG')
    guard()
    if building_semantics(target) != expected:
        raise PocBlocked("subset serialization changed Standard XYZ geometry or metadata")
    original = read_json(adjacent(parent))
    manifest = {"schema": "ouem-standard-building-manifest/v0.1",
                "status": "POC_DERIVED_NOT_ACCEPTED", "z_reference": original.get('z_reference', ''),
                "standard_output": str(target.absolute()), "selection": evidence,
                "parent": {"building": fingerprint(parent), "manifest": fingerprint(adjacent(parent))},
                "validation": {"output_features": len(frame), "unmodified_selected_features": True,
                               "output_crs": "EPSG:6677"},
                "note": "Selection evidence only; original A1 validation remains in the parent manifest."}
    with adjacent(target).open('xb') as stream:
        stream.write(canonical(manifest))
    guard()
    return expected
