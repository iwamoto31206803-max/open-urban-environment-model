"""Bounded read-only GeoPackage/WKB audit; no GDAL or geometry repair."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import sqlite3
import struct

from pyproj import CRS
from pyproj.exceptions import CRSError


class GeometryValidationError(ValueError):
    def __init__(self, code, field, reason):
        self.code, self.field, self.reason = code, field, reason
        super().__init__(f"{code}: {field}: {reason}")


def require(condition, field, reason, code="GEOMETRY_INVALID"):
    if not condition:
        raise GeometryValidationError(code, field, reason)


def quoted(name):
    require(isinstance(name, str) and name and "\x00" not in name, "identifier", "invalid SQL identifier")
    return '"' + name.replace('"', '""') + '"'


@contextmanager
def open_readonly(path):
    path = Path(path).resolve(strict=True)
    require(not any(Path(str(path)+suffix).exists() for suffix in ("-wal", "-shm", "-journal")),
            str(path), "live SQLite sidecars are not a frozen input")
    conn = sqlite3.connect(path.as_uri()+"?mode=ro&immutable=1", uri=True)
    try:
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("PRAGMA query_only=ON")
        yield conn
    finally:
        conn.close()


class _WKB:
    def __init__(self, blob, max_vertices):
        require(isinstance(blob, bytes) and len(blob) <= 64*1024*1024, "geometry", "BLOB missing or exceeds 64 MiB")
        self.blob, self.pos, self.remaining = blob, 0, max_vertices

    def read(self, fmt):
        size = struct.calcsize(fmt)
        require(self.pos+size <= len(self.blob), "geometry", "truncated geometry")
        values = struct.unpack_from(fmt, self.blob, self.pos)
        self.pos += size
        return values

    def geometry(self, depth=0):
        require(depth <= 32, "geometry", "nesting limit exceeded")
        endian, = self.read("B")
        require(endian in (0, 1), "geometry", "invalid WKB endian marker")
        order = "<" if endian else ">"
        kind, = self.read(order+"I")
        require(kind in (1003, 1006, 1007), "geometry.type", "only ISO Polygon Z, MultiPolygon Z, polygon-only GeometryCollection Z supported")
        count, = self.read(order+"I")
        require(0 < count <= self.remaining, "geometry", "empty or excessive geometry count")
        if kind == 1003:
            rings = []
            for _ in range(count):
                n, = self.read(order+"I")
                require(4 <= n <= self.remaining, "geometry.ring", "short/excessive ring")
                self.remaining -= n
                points = tuple(self.read(order+"ddd") for _ in range(n))
                require(all(math.isfinite(v) for p in points for v in p), "geometry.XYZ", "all vertices must be finite")
                require(points[0] == points[-1], "geometry.ring", "ring must close exactly")
                require(all(-180 <= p[0] <= 180 and -90 <= p[1] <= 90 for p in points),
                        "geometry.XY", "outside geographic coordinate domain", "AXIS_MISMATCH")
                rings.append(points)
            return ("Polygon", tuple(rings))
        children = tuple(self.geometry(depth+1) for _ in range(count))
        if kind == 1006:
            require(all(c[0] == "Polygon" for c in children), "geometry.type", "MultiPolygon child must be Polygon")
        return ("MultiPolygon" if kind == 1006 else "GeometryCollection", children)


def decode_geometry(blob, *, max_vertices=1_000_000):
    reader = _WKB(blob, max_vertices)
    magic, version, flags = reader.read("2sBB")
    require(magic == b"GP" and version == 0 and flags & 0xF0 == 0,
            "geometry.header", "invalid, empty or extended GPKG header")
    order = "<" if flags & 1 else ">"
    srid, = reader.read(order+"i")
    require(srid == 6697, "geometry.header.srs_id", "BLOB must declare 6697", "CRS_INCONSISTENT")
    envelope = (flags >> 1) & 7
    require(envelope in (0, 1, 2), "geometry.header", "unsupported envelope/m dimension")
    if envelope:
        bounds = reader.read(order+"d"*(4 if envelope == 1 else 6))
        require(all(map(math.isfinite, bounds)), "geometry.header", "nonfinite envelope")
    tree = reader.geometry()
    require(reader.pos == len(blob), "geometry", "unexpected trailing bytes")
    return tree


def polygons(tree):
    if tree[0] == "Polygon":
        return (tree[1],)
    return tuple(p for child in tree[1] for p in polygons(child))


def counts(tree):
    parts = polygons(tree)
    return {"geometry_type": tree[0], "faces": len(parts), "exterior_rings": len(parts),
            "interior_rings": sum(len(p)-1 for p in parts),
            "vertices": sum(len(r) for p in parts for r in p)}


@dataclass(frozen=True)
class GpkgSnapshot:
    layer: str
    geometry_column: str
    features: dict
    geometry_hashes: dict

    def summary(self):
        return {"layer": self.layer, "feature_count": len(self.features),
                "buildings": {k: counts(v) for k, v in self.features.items()},
                "geometry_blob_sha256": self.geometry_hashes}


def inspect_geopackage(path, layer):
    """Audit every feature; semantic H/LoD/source correspondence are separate."""
    try:
        with open_readonly(path) as conn:
            require(conn.execute("PRAGMA application_id").fetchone()[0] == 0x47504B47,
                    "database.application_id", "GeoPackage application ID required", "GPKG_INVALID")
            require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "database", "SQLite integrity failure")
            require(not conn.execute("PRAGMA foreign_key_check").fetchall(), "database", "foreign key violation")
            contents = conn.execute("SELECT data_type,srs_id FROM gpkg_contents WHERE table_name=?", (layer,)).fetchall()
            require(contents == [("features", 6697)], "gpkg_contents", "one feature layer declaration with 6697 required", "CRS_INCONSISTENT")
            columns = conn.execute("SELECT column_name,geometry_type_name,srs_id,z,m FROM gpkg_geometry_columns WHERE table_name=?", (layer,)).fetchall()
            require(len(columns) == 1, "gpkg_geometry_columns", "one geometry column required")
            column, declared_type, srid, z, m = columns[0]
            require(srid == 6697 and z == 1 and m == 0, "gpkg_geometry_columns", "mandatory Z, no M and 6697 required", "CRS_INCONSISTENT")
            require(declared_type in ("POLYGON", "MULTIPOLYGON", "GEOMETRYCOLLECTION", "GEOMETRY"), "geometry.type", "unsupported layer type")
            srs = conn.execute("SELECT organization,organization_coordsys_id,definition FROM gpkg_spatial_ref_sys WHERE srs_id=6697").fetchall()
            require(len(srs) == 1 and srs[0][:2] == ("EPSG", 6697), "gpkg_spatial_ref_sys", "6697 authority/code required", "CRS_INCONSISTENT")
            definitions = [srs[0][2]]
            srs_columns = [r[1] for r in conn.execute("PRAGMA table_info(gpkg_spatial_ref_sys)")]
            if "definition_12_063" in srs_columns:
                definitions += [conn.execute("SELECT definition_12_063 FROM gpkg_spatial_ref_sys WHERE srs_id=6697").fetchone()[0]]
            for wkt in definitions:
                try:
                    equal = CRS.from_wkt(wkt).equals(CRS.from_epsg(6697), ignore_axis_order=True)
                except (CRSError, ValueError, TypeError):
                    equal = False
                require(equal, "gpkg_spatial_ref_sys.definition", "WKT must match compound EPSG:6697", "CRS_INCONSISTENT")
            names = [r[1] for r in conn.execute("PRAGMA table_info("+quoted(layer)+")")]
            require("id" in names and "measuredHeight" in names, "attributes", "id and measuredHeight columns required")
            features, hashes = {}, {}
            for identifier, blob in conn.execute("SELECT id,"+quoted(column)+" FROM "+quoted(layer)):
                require(isinstance(identifier, str) and identifier.strip() and identifier not in features,
                        "building.id", "ID must be nonempty, non-NULL, unique text", "IDENTITY_MISMATCH")
                tree = decode_geometry(blob)
                require(declared_type == "GEOMETRY" or tree[0].upper() == declared_type,
                        identifier, "WKB and declared geometry type disagree")
                features[identifier] = tree
                hashes[identifier] = hashlib.sha256(blob).hexdigest()
                require(len(features) <= 100_000, "layer", "feature resource budget exceeded")
            require(features, "layer", "no buildings")
            return GpkgSnapshot(layer, column, features, hashes)
    except sqlite3.Error as exc:
        raise GeometryValidationError("GPKG_INVALID", str(path), str(exc)) from exc


def compare_snapshots(source, native):
    require(source.features.keys() == native.features.keys(), "building.id", "input/output ID set differs", "IDENTITY_MISMATCH")
    for identifier, tree in source.features.items():
        require(tree == native.features[identifier], identifier,
                "type, face/ring/vertex order or exact XYZ changed", "XYZ_MISMATCH")
        require(source.geometry_hashes[identifier] == native.geometry_hashes[identifier], identifier,
                "geometry BLOB bytes changed; no serialization difference permitted", "XYZ_MISMATCH")
    return {"building_id_preservation": "PASS", "all_vertex_xyz_preservation": "PASS",
            "geometry_structure_and_order": "PASS", "geometry_blob_preservation": "PASS",
            "summary": native.summary()}
