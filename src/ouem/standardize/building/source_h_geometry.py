"""Experimental source-H Standard geometry IO; no GDAL/legacy worker changes."""
from contextlib import closing
import math
import sqlite3
import struct

from pyproj import CRS, Proj
from shapely import from_wkb
from shapely.geometry import Polygon, GeometryCollection, box

from ouem.native.building.source_h_geometry import open_readonly, require, counts
from . import deterministic_ouem_id, SOURCE_DATASET

XY_TOLERANCE_M = 1e-7  # floating-point computational budget, not survey accuracy


def map_xy(tree, transform):
    kind, parts = tree
    if kind == 'Polygon':
        rings = []
        for ring in parts:
            points = []
            for lon, lat, height in ring:
                x, y = transform(lon, lat)  # exactly TWO arguments; H never enters PROJ
                require(all(map(math.isfinite, (x, y, height))), 'XYZ', 'nonfinite coordinate')
                points.append((x, y, height))
            rings.append(tuple(points))
        return kind, tuple(rings)
    return kind, tuple(map_xy(child, transform) for child in parts)


def points(tree):
    if tree[0] == 'Polygon':
        return tuple(p for ring in tree[1] for p in ring)
    return tuple(p for child in tree[1] for p in points(child))


def as_shape(tree):
    if tree[0] == 'Polygon':
        return Polygon(tree[1][0], tree[1][1:])
    return GeometryCollection([as_shape(c) for c in tree[1]])


def intersects(tree, extent):
    # 2D intersection only; vertical faces may have degenerate XY projections.
    # Never repair/reorder/clip the original 3D geometry.
    return as_shape(tree).intersects(box(*extent))


def wkb(tree):
    kind, parts = tree
    code = {'Polygon': 1003, 'MultiPolygon': 1006, 'GeometryCollection': 1007}[kind]
    result = struct.pack('<BII', 1, code, len(parts))
    if kind == 'Polygon':
        return result + b''.join(struct.pack('<I', len(r)) + b''.join(struct.pack('<ddd', *p) for p in r) for r in parts)
    return result + b''.join(wkb(child) for child in parts)


def from_shape(shape):
    require(not shape.is_empty and shape.has_z, 'geometry', 'empty/2D geometry')
    if shape.geom_type == 'Polygon':
        result = ('Polygon', tuple(tuple(tuple(p) for p in r.coords) for r in (shape.exterior, *shape.interiors)))
    else:
        require(shape.geom_type in ('MultiPolygon', 'GeometryCollection'), 'geometry.type', 'unsupported geometry')
        result = (shape.geom_type, tuple(from_shape(c) for c in shape.geoms))
    require(all(len(p) == 3 and all(map(math.isfinite, p)) for p in points(result)), 'XYZ', 'invalid XYZ')
    return result


def read_attributes(path, layer):
    from ouem.native.building.source_h_geometry import quoted
    with open_readonly(path) as conn:
        fields = {r[1].casefold(): r[1] for r in conn.execute('PRAGMA table_info('+quoted(layer)+')')}
        lod = next((fields[x] for x in ('source_lod', 'lod', 'lodtype', 'lod_type') if x in fields), None)
        height = next((fields[x] for x in ('measuredheight', 'measured_height') if x in fields), None)
        selection = ','.join(quoted(f) if f else 'NULL' for f in ('id', lod, height))
        result = {}
        for identifier, lod_value, measured in conn.execute('SELECT '+selection+' FROM '+quoted(layer)):
            require(lod_value is None or str(lod_value) in ('2', '2.0', 'lod2', 'LoD2'), identifier, 'LoD attribute contradicts LoD2')
            require(measured is None or (isinstance(measured, (int, float)) and math.isfinite(measured)), identifier, 'nonfinite/non-numeric measuredHeight')
            result[identifier] = (str(lod_value) if lod_value is not None else None, measured)
        return result


def write_standard(path, features, attributes, timestamp):
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript('''
            PRAGMA application_id=1196444487;
            PRAGMA user_version=10300;
            CREATE TABLE gpkg_spatial_ref_sys(srs_name TEXT NOT NULL,srs_id INTEGER NOT NULL PRIMARY KEY,
                organization TEXT NOT NULL,organization_coordsys_id INTEGER NOT NULL,definition TEXT NOT NULL,description TEXT,
                definition_12_063 TEXT NOT NULL);
            CREATE TABLE gpkg_extensions(table_name TEXT,column_name TEXT,extension_name TEXT NOT NULL,
                definition TEXT NOT NULL,scope TEXT NOT NULL,UNIQUE(table_name,column_name,extension_name));
            CREATE TABLE gpkg_contents(table_name TEXT NOT NULL PRIMARY KEY,data_type TEXT NOT NULL,identifier TEXT UNIQUE,
                description TEXT DEFAULT '',last_change DATETIME NOT NULL,min_x DOUBLE,min_y DOUBLE,max_x DOUBLE,max_y DOUBLE,
                srs_id INTEGER,FOREIGN KEY(srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
            CREATE TABLE gpkg_geometry_columns(table_name TEXT NOT NULL,column_name TEXT NOT NULL,geometry_type_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL,z TINYINT NOT NULL,m TINYINT NOT NULL,PRIMARY KEY(table_name,column_name),
                FOREIGN KEY(table_name) REFERENCES gpkg_contents(table_name),FOREIGN KEY(srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
            CREATE TABLE building(fid INTEGER PRIMARY KEY AUTOINCREMENT,geometry BLOB NOT NULL,ouem_id TEXT NOT NULL UNIQUE,
                source_id TEXT NOT NULL UNIQUE,source_dataset TEXT NOT NULL,source_lod TEXT,measured_height REAL);
        ''')
        for name, code, org, orgcode, definition in (
            ('Undefined Cartesian SRS', -1, 'NONE', -1, 'undefined'),
            ('Undefined geographic SRS', 0, 'NONE', 0, 'undefined'),
            ('WGS 84', 4326, 'EPSG', 4326, CRS.from_epsg(4326).to_wkt('WKT1_GDAL')),
            ('JGD2011 / Japan Plane Rectangular CS IX', 6677, 'EPSG', 6677, CRS.from_epsg(6677).to_wkt('WKT1_GDAL'))):
            modern = CRS.from_epsg(code).to_wkt() if code > 0 else 'undefined'
            conn.execute('INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,NULL,?)', (name,code,org,orgcode,definition,modern))
        conn.execute('INSERT INTO gpkg_extensions VALUES(?,?,?,?,?)',
                     ('gpkg_spatial_ref_sys','definition_12_063','gpkg_crs_wkt','http://www.geopackage.org/spec/#extension_crs_wkt','read-write'))
        coords = [p for tree in features.values() for p in points(tree)]
        bounds = min(p[0] for p in coords), min(p[1] for p in coords), max(p[0] for p in coords), max(p[1] for p in coords)
        conn.execute('INSERT INTO gpkg_contents VALUES(?,?,?,?,?,?,?,?,?,?)', ('building','features','building','Experimental source-H',timestamp,*bounds,6677))
        types = {tree[0].upper() for tree in features.values()}
        declared = next(iter(types)) if len(types) == 1 else 'GEOMETRY'
        conn.execute('INSERT INTO gpkg_geometry_columns VALUES(?,?,?,?,?,?)', ('building','geometry',declared,6677,1,0))
        for identifier, tree in features.items():
            blob = b'GP\x00\x01'+struct.pack('<i',6677)+wkb(tree)
            conn.execute('INSERT INTO building(geometry,ouem_id,source_id,source_dataset,source_lod,measured_height) VALUES(?,?,?,?,?,?)',
                         (blob,deterministic_ouem_id(identifier),identifier,SOURCE_DATASET,*attributes[identifier]))
        conn.commit()


def audit_standard(path, source, expected, attributes):
    """Reopen with independent GEOS decoder and separately constructed Proj oracle."""
    reference = Proj(CRS.from_epsg(6677))  # geographic lon/lat -> projection, not Transformer pipeline
    result, max_xy = {}, 0.0
    with open_readonly(path) as conn:
        require(conn.execute('PRAGMA application_id').fetchone()[0] == 0x47504B47, 'GPKG', 'wrong application id')
        require(conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'GPKG', 'integrity failure')
        require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'GPKG', 'foreign-key failure')
        meta = conn.execute('SELECT table_name,column_name,geometry_type_name,srs_id,z,m FROM gpkg_geometry_columns').fetchall()
        require(len(meta) == 1 and meta[0][:2] == ('building','geometry') and meta[0][3:] == (6677,1,0), 'GPKG', 'geometry declaration')
        require(conn.execute('SELECT table_name,data_type,srs_id FROM gpkg_contents').fetchall() == [('building','features',6677)], 'GPKG', 'contents declaration')
        srs = conn.execute('SELECT organization,organization_coordsys_id,definition,definition_12_063 FROM gpkg_spatial_ref_sys WHERE srs_id=6677').fetchone()
        expected_crs = CRS.from_epsg(6677)
        require(srs and srs[:2] == ('EPSG',6677) and srs[2] == expected_crs.to_wkt('WKT1_GDAL')
                and CRS.from_wkt(srs[3]).equals(expected_crs), 'CRS', 'output WKT mismatch')
        require(conn.execute('SELECT table_name,column_name,extension_name,scope FROM gpkg_extensions').fetchall()
                == [('gpkg_spatial_ref_sys','definition_12_063','gpkg_crs_wkt','read-write')], 'CRS', 'WKT2 extension registration')
        for blob, ouem_id, identifier, dataset, lod, height in conn.execute('SELECT geometry,ouem_id,source_id,source_dataset,source_lod,measured_height FROM building'):
            require(blob[:4] == b'GP\x00\x01' and struct.unpack('<i',blob[4:8])[0] == 6677, identifier, 'BLOB SRID/header')
            tree = from_shape(from_wkb(blob[8:]))
            require(identifier in expected and identifier not in result and tree == expected[identifier], identifier, 'written type/order/XYZ differ')
            require(meta[0][2] in ('GEOMETRY',tree[0].upper()), identifier, 'declared geometry type mismatch')
            require((ouem_id,dataset,lod,height) == (deterministic_ouem_id(identifier),SOURCE_DATASET,*attributes[identifier]), identifier, 'attribute/ID mismatch')
            require(counts(tree) == counts(source[identifier]), identifier, 'structure/count mismatch')
            for a, b in zip(points(source[identifier]), points(tree)):
                require(struct.pack('<d',a[2]) == struct.pack('<d',b[2]), identifier, 'H not exactly preserved')
                x,y = reference(a[0],a[1],errcheck=True)
                delta = max(abs(x-b[0]),abs(y-b[1]))
                max_xy = max(max_xy, delta)
                require(delta <= XY_TOLERANCE_M, identifier, 'independent XY oracle mismatch')
            result[identifier] = counts(tree)
    require(result.keys() == expected.keys(), 'IDs', 'output ID set mismatch')
    return {'all_vertex_H_exact': 'PASS', 'structure_order_ids_attributes': 'PASS',
            'independent_XY': 'PASS', 'max_xy_error_m': max_xy, 'xy_tolerance_m': XY_TOLERANCE_M,
            'h_tolerance_m': 0, 'buildings': result}
