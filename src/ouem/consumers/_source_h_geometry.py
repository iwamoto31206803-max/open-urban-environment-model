"""Independent bounded ISO WKB Z reader and correspondence checks for consumers.

Does not call Standardizer map/write/reopen QA or transform H through PROJ.
"""
import math
import struct
import uuid

from pyproj import CRS, Proj
from shapely.geometry import Polygon, GeometryCollection, box

from ouem.native.building.source_h_geometry import open_readonly, require, quoted, counts

XY_TOLERANCE_M = 1e-7


class Reader:
    def __init__(self, blob):
        require(isinstance(blob, bytes) and 8 <= len(blob) <= 64*1024*1024,
                'geometry', 'missing/excessive BLOB')
        self.blob, self.pos, self.vertices = blob, 0, 1_000_000

    def read(self, fmt):
        n = struct.calcsize(fmt)
        require(self.pos+n <= len(self.blob), 'geometry', 'truncated BLOB')
        values = struct.unpack_from(fmt, self.blob, self.pos)
        self.pos += n
        return values

    def tree(self, depth=0):
        require(depth <= 32, 'geometry', 'nesting limit')
        endian, = self.read('B')
        require(endian in (0, 1), 'geometry', 'bad byte order')
        order = '<' if endian else '>'
        kind, n = self.read(order+'II')
        require(kind in (1003, 1006, 1007) and 0 < n <= self.vertices,
                'geometry', 'only nonempty ISO Polygon/MultiPolygon/polygon-only Collection Z')
        if kind == 1003:
            rings = []
            for _ in range(n):
                length, = self.read(order+'I')
                require(4 <= length <= self.vertices, 'geometry.ring', 'invalid ring length')
                self.vertices -= length
                ring = tuple(self.read(order+'ddd') for _ in range(length))
                require(all(math.isfinite(v) for p in ring for v in p), 'geometry.XYZ', 'nonfinite XYZ')
                require(ring[0] == ring[-1], 'geometry.ring', 'unclosed ring')
                rings.append(ring)
            return 'Polygon', tuple(rings)
        children = tuple(self.tree(depth+1) for _ in range(n))
        require(kind != 1006 or all(c[0] == 'Polygon' for c in children), 'geometry', 'invalid MultiPolygon child')
        return ('MultiPolygon' if kind == 1006 else 'GeometryCollection'), children


def decode(blob):
    r = Reader(blob)
    magic, version, flags = r.read('2sBB')
    # Candidate ISO Z subset: no envelope, empty, M or extended encoding.
    require(magic == b'GP' and version == 0 and flags in (0, 1), 'geometry.header', 'unsupported GPKG encoding')
    srid, = r.read(('<' if flags else '>')+'i')
    require(srid == 6677, 'geometry.srid', 'BLOB SRID must be6677')
    tree = r.tree()
    require(r.pos == len(blob), 'geometry', 'trailing bytes')
    return tree


def read_standard(path, layer):
    """Read actual metadata/attributes/BLOBs, independent of persisted QA."""
    require(layer == 'building', 'standard.layer', 'candidate layer must be building')
    features = {}
    all_xy = []
    with open_readonly(path) as conn:
        require(conn.execute('PRAGMA application_id').fetchone()[0] == 0x47504B47, 'GPKG', 'application_id')
        require(conn.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'GPKG', 'integrity_check')
        require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'GPKG', 'foreign_key_check')
        require(conn.execute('SELECT table_name,data_type,srs_id FROM gpkg_contents').fetchall()
                == [('building', 'features', 6677)], 'gpkg_contents', 'unexpected feature layer/CRS')
        columns = conn.execute('SELECT table_name,column_name,geometry_type_name,srs_id,z,m FROM gpkg_geometry_columns').fetchall()
        require(len(columns) == 1 and columns[0][:2] == ('building', 'geometry')
                and columns[0][3:] == (6677, 1, 0), 'gpkg_geometry_columns', 'CRS/Z/M/column mismatch')
        declared_type = columns[0][2]
        require(declared_type in ('POLYGON', 'MULTIPOLYGON', 'GEOMETRYCOLLECTION', 'GEOMETRY'), 'geometry.type', 'unsupported declaration')
        definitions = conn.execute('SELECT organization,organization_coordsys_id,definition,definition_12_063 FROM gpkg_spatial_ref_sys WHERE srs_id=6677').fetchall()
        crs = CRS.from_epsg(6677)
        require(len(definitions) == 1 and definitions[0][:2] == ('EPSG', 6677), 'gpkg_spatial_ref_sys', 'authority mismatch')
        # WKT1 cannot round-trip the parameter/axis definition exactly. Require
        # the candidate's generated WKT1 plus semantic WKT2, without relabelling.
        require(definitions[0][2] == crs.to_wkt('WKT1_GDAL')
                and CRS.from_wkt(definitions[0][3]).equals(crs), 'gpkg_spatial_ref_sys', 'WKT1/WKT2 mismatch')
        require(conn.execute('SELECT table_name,column_name,extension_name,definition,scope FROM gpkg_extensions').fetchall()
                == [('gpkg_spatial_ref_sys', 'definition_12_063', 'gpkg_crs_wkt',
                     'http://www.geopackage.org/spec/#extension_crs_wkt', 'read-write')], 'gpkg_extensions', 'WKT2 extension mismatch')
        names = {r[1] for r in conn.execute('PRAGMA table_info(building)')}
        require({'geometry','ouem_id','source_id','source_dataset','source_lod','measured_height'} <= names,
                'attributes', 'required column missing')
        seen = set()
        for blob, ouem_id, identifier, dataset, lod, height in conn.execute('SELECT geometry,ouem_id,source_id,source_dataset,source_lod,measured_height FROM building'):
            require(isinstance(identifier, str) and identifier.strip() and identifier not in features,
                    'source_id', 'NULL/blank/duplicate source ID')
            require(isinstance(ouem_id, str) and ouem_id and ouem_id not in seen, 'ouem_id', 'NULL/duplicate OUEM ID')
            expected_id = 'oub-'+str(uuid.uuid5(uuid.NAMESPACE_URL, 'ouem-standard-building-v0.1|PLATEAU CityGML|'+identifier))
            require(ouem_id == expected_id and dataset == 'PLATEAU CityGML', identifier, 'ID/dataset mapping mismatch')
            require(lod is None or isinstance(lod, str), identifier, 'source_lod must be text/null')
            require(height is None or (type(height) in (int, float) and math.isfinite(height)), identifier, 'invalid measured_height')
            tree = decode(blob)
            require(declared_type in ('GEOMETRY', tree[0].upper()), identifier, 'BLOB type vs metadata')
            features[identifier] = (tree, lod, height)
            def xy_values(node):
                if node[0] == 'Polygon':
                    return [p[:2] for ring in node[1] for p in ring]
                return [p for child in node[1] for p in xy_values(child)]
            all_xy.extend(xy_values(tree))
            seen.add(ouem_id)
            require(len(features) <= 100_000, 'features', 'feature limit exceeded')
        require(all_xy, 'gpkg_contents.bounds', 'missing vertices')
        actual_bounds=(min(p[0] for p in all_xy),min(p[1] for p in all_xy),max(p[0] for p in all_xy),max(p[1] for p in all_xy))
        require(conn.execute('SELECT min_x,min_y,max_x,max_y FROM gpkg_contents').fetchall()==[actual_bounds],
                'gpkg_contents.bounds', 'bounds do not match actual vertices')
    require(features, 'features', 'empty output')
    return features


def native_attributes(path, layer):
    with open_readonly(path) as conn:
        names = {r[1].casefold(): r[1] for r in conn.execute('PRAGMA table_info('+quoted(layer)+')')}
        lod = next((names[n] for n in ('source_lod','lod','lodtype','lod_type') if n in names), None)
        height = next((names[n] for n in ('measuredheight','measured_height') if n in names), None)
        fields = ','.join(quoted(f) if f else 'NULL' for f in ('id',lod,height))
        rows = conn.execute('SELECT '+fields+' FROM '+quoted(layer)).fetchall()
    result = {}
    for identifier, lod, height in rows:
        require(lod is None or str(lod) in ('2','2.0','lod2','LoD2'), identifier, 'Native LoD contradicts LoD2')
        require(height is None or (type(height) in (int,float) and math.isfinite(height)), identifier, 'invalid Native measuredHeight')
        result[identifier] = (str(lod) if lod is not None else None, height)
    return result


def project_native(tree, reference):
    if tree[0] == 'Polygon':
        rings = []
        for ring in tree[1]:
            values = []
            for lon, lat, h in ring:
                x, y = reference(lon, lat, errcheck=True)  # 2D only; H never passed
                require(all(map(math.isfinite, (x,y,h))), 'XYZ', 'nonfinite projection')
                values.append((x,y,h))
            rings.append(tuple(values))
        return 'Polygon', tuple(rings)
    return tree[0], tuple(project_native(c, reference) for c in tree[1])


def support(tree):
    if tree[0] == 'Polygon':
        return Polygon([p[:2] for p in tree[1][0]], [[p[:2] for p in r] for r in tree[1][1:]])
    return GeometryCollection([support(c) for c in tree[1]])


def compare_tree(expected, actual, identifier):
    require(expected[0] == actual[0] and len(expected[1]) == len(actual[1]), identifier, 'geometry type/structure changed')
    if expected[0] != 'Polygon':
        values = [compare_tree(a,b,identifier) for a,b in zip(expected[1],actual[1])]
        return sum(v[0] for v in values), max(v[1] for v in values)
    vertices, error = 0, 0.0
    for a,b in zip(expected[1],actual[1]):
        require(len(a) == len(b), identifier, 'ring/vertex count changed')
        for p,q in zip(a,b):
            require(struct.pack('<d', p[2]) == struct.pack('<d', q[2]), identifier, 'H binary64 mismatch')
            delta = max(abs(p[0]-q[0]), abs(p[1]-q[1]))
            require(delta <= XY_TOLERANCE_M, identifier, 'XY/order mismatch')
            error = max(error, delta)
            vertices += 1
    return vertices, error


def verify_geometry(native, native_path, actual, extent):
    reference = Proj(CRS.from_epsg(6677))
    transformed = {k:project_native(v,reference) for k,v in native.features.items()}
    boundary = box(*extent)
    selected = {k for k,v in transformed.items() if support(v).intersects(boundary)}
    require(selected == actual.keys(), 'selection', 'AOI-selected IDs differ from actual Standard')
    attributes = native_attributes(native_path,native.layer)
    vertices, max_error, buildings = 0, 0.0, {}
    for identifier in selected:
        tree, lod, height = actual[identifier]
        n, delta = compare_tree(transformed[identifier],tree,identifier)
        require((lod,height) == attributes[identifier], identifier, 'nullable attribute mismatch')
        vertices += n
        max_error = max(max_error,delta)
        buildings[identifier] = counts(tree)
    return {'selected':selected,'excluded':native.features.keys()-selected,'vertices':vertices,
            'max_xy_error_m':max_error,'buildings':buildings}
