"""STEP 3-A: synthetic planar roof Derived; no Standard or engine integration.

Coordinates are explicitly authored EPSG:6677 metres, including absolute Z in
an arbitrary synthetic vertical datum. No roof classification or triangulation.
"""
from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import json
from numbers import Real
from pathlib import Path
import platform

import numpy as np
from shapely.geometry import Point, Polygon, box, mapping
from shapely.ops import unary_union

from ouem.height_envelope import GridSpec

PROFILE = "ouem-synthetic-building-height-distribution/v0.1"
PLANAR_TOLERANCE_M = 1e-8  # synthetic numerical check, not a source accuracy claim
METHODS = ("centre", "cell_max")


@dataclass(frozen=True)
class Face:
    face_id: str
    rings: tuple  # closed XYZ exterior, then optional closed XYZ holes


@dataclass(frozen=True)
class Building:
    source_id: str
    footprint: Polygon  # independently authored XY building presence
    faces: tuple[Face, ...]
    provenance: str


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _face(face):
    """Validate a hand-authored planar face; return XY support and Z plane.

    Truly vertical planes are recorded as excluded, never projected as roofs.
    Nonplanarity, degeneracy and invalid projected roof topology are rejected.
    """
    _require(isinstance(face.face_id, str) and bool(face.face_id), "face identifier required")
    _require(bool(face.rings), "missing XYZ rings")
    rings = []
    for ring in face.rings:
        try:
            _require(all(isinstance(v, Real) and not isinstance(v, (bool, np.bool_))
                         for point in ring for v in point), "numeric XYZ coordinates required")
            p = np.array(ring, dtype=float, copy=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid XYZ ring") from exc
        _require(p.ndim == 2 and p.shape[1] == 3 and len(p) >= 4
                 and np.isfinite(p).all(), "finite closed XYZ ring required")
        _require(np.array_equal(p[0], p[-1]), "unclosed XYZ ring")
        rings.append(p)
    origin = rings[0][0]
    offsets = rings[0][:-1] - origin
    normal = max((np.cross(a, b) for a in offsets for b in offsets),
                 key=lambda v: float(np.linalg.norm(v)))
    length = float(np.linalg.norm(normal))
    _require(length > PLANAR_TOLERANCE_M, "degenerate 3D face")
    normal = normal / length
    _require(all(np.max(np.abs((p-origin) @ normal)) <= PLANAR_TOLERANCE_M
                 for p in rings), "nonplanar face unsupported")
    # Check ring topology on the best-conditioned plane, including vertical walls.
    drop = int(np.argmax(np.abs(normal)))
    projected = [np.delete(p, drop, axis=1) for p in rings]
    topology = Polygon(projected[0], projected[1:])
    _require(topology.is_valid and topology.area > 0, "invalid face shape")
    if abs(normal[2]) <= 1e-12:
        return None
    support = Polygon(rings[0][:, :2], [p[:, :2] for p in rings[1:]])
    _require(support.is_valid and support.area > 0, "invalid XY roof shape")
    a, b = -normal[:2] / normal[2]
    # Evaluate relative to origin to avoid cancellation at a large CRS offset.
    return support, (float(a), float(b), *map(float, origin))


def _z(plane, x, y):
    a, b, x0, y0, z0 = plane
    result = float(z0 + a*(x-x0) + b*(y-y0))
    _require(np.isfinite(result), "nonfinite calculated top Z")
    return result


def _vertices(geometry):
    if geometry.geom_type == "Polygon":
        yield from geometry.exterior.coords
        for ring in geometry.interiors:
            yield from ring.coords
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _vertices(part)


def sample_roofs(grid: GridSpec, buildings, *, method):
    """Geometry-only sampling; no dataset profile, datum or environment identity.

    Presence requires positive footprint-cell area. Boundary-only roof touches
    do not contribute. Centre uses closed-set covers, so a seam can yield two
    values. Max is the affine maximum on each clipped polygon's closure.
    """
    _require(method in METHODS, "unsupported sampling method")
    buildings = tuple(sorted(buildings, key=lambda b: b.source_id))
    _require(len({b.source_id for b in buildings}) == len(buildings), "duplicate source_id")
    prepared, sources, excluded = [], [], []
    for building in buildings:
        _require(isinstance(building.source_id, str) and bool(building.source_id)
                 and isinstance(building.provenance, str) and bool(building.provenance),
                 "source identifier and provenance required")
        fp = building.footprint
        _require(isinstance(fp, Polygon) and not fp.has_z and not fp.is_empty
                 and fp.is_valid and fp.area > 0
                 and np.isfinite(np.asarray(fp.exterior.coords)).all()
                 and all(np.isfinite(np.asarray(r.coords)).all() for r in fp.interiors),
                 "valid finite XY footprint required")
        faces = sorted(building.faces, key=lambda f: f.face_id)
        _require(len({f.face_id for f in faces}) == len(faces), "duplicate face_id within source")
        roofs = []
        for face in faces:
            parsed = _face(face)
            if parsed is None:
                excluded.append(dict(source_id=building.source_id, face_id=face.face_id,
                                     reason="VERTICAL_FACE_NOT_ROOF_SUPPORT"))
            else:
                support, plane = parsed
                roofs.append((face.face_id, support.intersection(fp), plane))
        prepared.append((building, roofs))
        sources.append(dict(source_id=building.source_id, provenance=building.provenance,
                            footprint=mapping(fp), faces=[dict(face_id=f.face_id, rings=f.rings)
                                                        for f in faces]))
    cells = []
    resolution = grid.resolution
    for row in range(grid.height):
        for col in range(grid.width):
            left = grid.bounds[0] + col*resolution
            top = grid.bounds[3] - row*resolution
            cell = box(left, top-resolution, left+resolution, top)
            centre = Point(left+resolution/2, top-resolution/2)
            records = []
            for building, roofs in prepared:
                occupied = building.footprint.intersection(cell)
                if occupied.area <= 0:
                    continue
                contributions, supports = [], []
                for face_id, support, plane in roofs:
                    clipped = support.intersection(cell)
                    if clipped.area <= 0:
                        continue
                    supports.append(clipped)
                    value = None
                    if method == "centre" and clipped.covers(centre):
                        value = _z(plane, centre.x, centre.y)
                    elif method == "cell_max":
                        value = max(_z(plane, x, y) for x, y in _vertices(clipped))
                    contributions.append(dict(source_id=building.source_id, face_id=face_id,
                                              cell_index=[row, col], absolute_top_z=value,
                                              valid=value is not None,
                                              state="KNOWN" if value is not None else "CENTRE_UNSUPPORTED",
                                              coverage_fraction=clipped.area/cell.area))
                values = [c["absolute_top_z"] for c in contributions if c["valid"]]
                coverage = unary_union(supports).area/cell.area if supports else 0.
                records.append(dict(source_id=building.source_id,
                                    state="KNOWN" if values else "TOP_UNKNOWN",
                                    valid=bool(values),
                                    # A per-building summary, never an owner or loss of contributors.
                                    absolute_top_z=max(values) if values else None,
                                    footprint_fraction=occupied.area/cell.area,
                                    coverage_fraction=coverage,
                                    partial_roof_coverage=0 < coverage < 1,
                                    contribution_count=len(contributions), contributions=contributions))
            cells.append(dict(cell_index=[row, col], centre_xy=[centre.x, centre.y],
                              state="BUILDING_PRESENT" if records else "NO_BUILDING",
                              building_count=len(records),
                              contribution_count=sum(r["contribution_count"] for r in records),
                              buildings=records))
    return cells, sources, excluded


def derive(grid: GridSpec, buildings, *, method):
    """Synthetic-only Derived wrapper around the unchanged geometric sampler."""
    cells, sources, excluded = sample_roofs(grid, buildings, method=method)
    resolution = grid.resolution
    metadata = grid.metadata()
    metadata.update(origin_xy=[grid.bounds[0], grid.bounds[3]],
                    column_axis=[resolution, 0.], row_axis=[0., -resolution],
                    horizontal_units="m", vertical_units="m", array_axes=["row", "column"],
                    sampling_location="centres identify cells; roof evaluation uses sampling_method",
                    boundary_rule="positive-area footprint presence; closed-set roof centre support")
    return dict(profile=PROFILE, status="COMPLETED_SYNTHETIC_ONLY", sampling_method=method,
                grid=metadata, grid_identity=_hash(metadata), cells=cells,
                source_provenance=sources, source_identity=_hash(sources), excluded_faces=excluded,
                procedure=dict(implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                               environment=dict(python=platform.python_version(), numpy=version("numpy"),
                                                shapely=version("shapely")),
                               planar_tolerance_m=PLANAR_TOLERANCE_M,
                               max_rule="affine maximum on clipped positive-area roof closure",
                               centre_rule="closed-set covers; boundary-only area excluded",
                               vertical_datum="arbitrary synthetic datum; not T.P.",
                               top_semantics="absolute Z, not ground-relative height"),
                terrain_integration_ready=False, scientific_validation="NOT_VERIFIED",
                formal_acceptance="NOT_VERIFIED")


def compare(centre, maximum):
    """Compare per-building cell tops, retaining differing support separately."""
    _require(centre["sampling_method"] == "centre" and maximum["sampling_method"] == "cell_max"
             and centre["grid_identity"] == maximum["grid_identity"]
             and centre["source_identity"] == maximum["source_identity"], "comparison identities differ")
    differences, support_differences, partial_differences = [], [], []
    for a, b in zip(centre["cells"], maximum["cells"], strict=True):
        for x, y in zip(a["buildings"], b["buildings"], strict=True):
            key = dict(cell_index=a["cell_index"], source_id=x["source_id"])
            if x["valid"] != y["valid"]:
                support_differences.append(key)
            elif x["valid"]:
                delta = y["absolute_top_z"] - x["absolute_top_z"]
                if abs(delta) > PLANAR_TOLERANCE_M:
                    differences.append(dict(**key, max_minus_centre_m=delta))
                    if y["partial_roof_coverage"]:
                        partial_differences.append(key)
    return dict(comparable_height_differences=differences,
                differing_cell_count=len({tuple(d["cell_index"]) for d in differences}),
                differing_building_cell_count=len(differences),
                maximum_absolute_difference_m=max((abs(d["max_minus_centre_m"]) for d in differences), default=0.),
                support_differences=support_differences,
                partial_coverage_height_differences=partial_differences)


def relative_to_ground(absolute_top_z, ground_z):
    """Explicit same-shape subtraction only; caller owns ground/anchor identity.

    NaN top remains unknown. Infinity or nonfinite ground is rejected. This is
    not a voxel conversion, owner-average DEM or inference of building bottom.
    """
    top, ground = np.asarray(absolute_top_z, dtype=float), np.asarray(ground_z, dtype=float)
    _require(top.shape == ground.shape and not np.isinf(top).any()
             and np.isfinite(ground).all(), "finite same-shape ground required")
    return top-ground


def demonstration():
    """Small reproducible comparison; representative absolute Z is authored.

    Representative values mimic a constant per-building source maximum; no
    existing representative-height model is called or replaced.
    """
    def face(name, bounds, a=0., b=0., c=10., holes=()):
        polygon = box(*bounds)
        rings = (polygon.exterior.coords, *holes)
        return Face(name, tuple(tuple((x,y,a*x+b*y+c) for x,y in ring) for ring in rings))

    cases = [
        ("flat", (0,0,2,2), [face("flat", (0,0,2,2))], 10.),
        ("slope", (0,0,2,2), [face("slope", (0,0,2,2),2,3)], 20.),
        ("step", (0,0,2,1), [face("low", (0,0,.75,1),c=4),
                                  face("high", (.75,0,2,1),c=9)], 9.),
        ("roof_hole", (0,0,3,3), [face("hole", (0,0,3,3),
                                    holes=(box(1,1,2,2).exterior.coords,))], 10.),
        ("thin_eave", (0,0,1,1), [face("eave", (0,0,.1,1),2,0)], 10.2),
        ("partial", (0,0,1,1), [face("partial", (0,0,.75,1),2,0)], 11.5),
    ]
    results = {}
    for name, bounds, faces, representative in cases:
        buildings = [Building("synthetic-"+name, box(*bounds), tuple(faces),
                              "hand-authored STEP 3-A demonstration; arbitrary synthetic datum")]
        a,b = (derive(GridSpec(bounds), buildings, method=m) for m in METHODS)
        def summary(result):
            rows = [r for cell in result["cells"] for r in cell["buildings"]]
            values = [r["absolute_top_z"] for r in rows if r["valid"]]
            return dict(known=len(values), unknown=len(rows)-len(values),
                        partial=sum(r["partial_roof_coverage"] for r in rows),
                        representative_minus_top_range_m=[min(representative-v for v in values),
                                                          max(representative-v for v in values)] if values else None)
        results[name] = dict(representative_absolute_z=representative,
                             centre=summary(a), cell_max=summary(b), comparison=compare(a,b),
                             derived_centre=a, derived_cell_max=b)
    return dict(profile=PROFILE, status="COMPLETED_SYNTHETIC_ONLY", cases=results)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new synthetic JSON file (never overwrite)")
    args = parser.parse_args()
    result = demonstration()
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
