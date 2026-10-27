"""Portable audit helper tests; no osgeo import or real PLATEAU processing."""

from pathlib import Path
import struct

import pytest

from ouem import gdal_citygml_feasibility as probe

FIXTURE = Path(__file__).parent / "fixtures/plateau_converter/two_buildings.gml"


def ring(z=10.0):
    return [(0, 0, z), (1, 0, z), (1, 1, z), (0, 0, z)]


def test_ring_comparison_ignores_start_direction_but_detects_z_changes():
    a = ring()
    b = [a[1], a[2], a[0], a[1]]
    assert probe.normalized_ring(a) == probe.normalized_ring(b[::-1])
    assert probe.normalized_ring(a) != probe.normalized_ring(ring(11))


def test_polygon_comparison_preserves_holes_and_duplicate_faces():
    p = [ring(), ring(20)]
    assert probe.signature([p]) != probe.signature([[ring()]])
    assert probe.signature([p, p]) != probe.signature([p])


def test_blob_srs_and_z_type_decode_little_and_big_endian():
    for flags, endian, order in [(1, '<', 1), (0, '>', 0)]:
        data = b'GP\x00' + bytes([flags]) + struct.pack(endian+'i', 6697)
        data += bytes([order]) + struct.pack(endian+'I', 1006)
        assert probe.blob_srs(data) == 6697
        assert probe.blob_wkb_type(data) == 1006


def test_fixture_reference_retains_every_lod2_face_ring_and_coordinate():
    reference = probe.source_reference(FIXTURE)
    assert len(reference) == 2
    assert len(reference['synthetic_tokyo'][2]) == 10
    assert sum(len(p) for p in reference['synthetic_tokyo'][2]) == 12
    rows = [{'attributes': {'gml_id': k}, 'polygons': v[2]} for k, v in reference.items()]
    result = probe.verify_rows(rows, reference, 2)
    assert result == {'ids_exact': True, 'all_xyz_rings_exact': True,
                      'polygon_count': 20, 'ring_count': 24, 'vertex_occurrences': 120}
    assert not probe.verify_rows(rows[:-1], reference, 2)['ids_exact']


def test_non_fixture_input_fails_before_a_generic_reader_is_assumed(tmp_path):
    source = tmp_path / 'other.gml'
    source.write_bytes(FIXTURE.read_bytes().replace(b'synthetic_tokyo', b'unknown_building'))
    with pytest.raises(ValueError, match='exact committed synthetic'):
        probe.source_reference(source)
