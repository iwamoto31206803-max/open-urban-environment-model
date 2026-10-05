import json
import inspect
from pathlib import Path

import pytest

from ouem.adapters.voxcity import (
    VOXCITY_COMMIT, VOXCITY_PRECISE_RASTERIZATION, VOXCITY_VERSION,
    VoxCityAdapterError, canonical_json,
    check_vertical_compatibility, derive_attributes, grid_ground_samples,
    interface_id_properties, numeric_id_mapping, build_normalized_footprint,
    _set_normalized_footprints, _to_voxcity_building_crs,
)
import ouem.adapters.voxcity as adapter


def test_version_is_exactly_pinned():
    assert VOXCITY_VERSION == "1.7.0"
    assert VOXCITY_COMMIT == "fa212656305328a9a657973bae26f352bfe813bc"
    assert VOXCITY_PRECISE_RASTERIZATION is True


def test_a3_has_no_external_gis_worker_runtime_boundary():
    signature = inspect.signature(adapter.adapt_standard_to_voxcity)
    assert "runtime" not in signature.parameters
    package = Path(adapter.__file__).parent
    assert not (package / "_gdal_worker.py").exists()
    source = Path(adapter.__file__).read_text(encoding="utf-8")
    assert "subprocess.run" not in source
    assert "load_gis_runtime" not in source


def test_acceptance_uses_complete_mapping_not_stale_fixture_id():
    acceptance = Path("scripts/work/voxcity_komae_a3_acceptance.py").read_text(
        encoding="utf-8"
    )
    assert "REGRESSION_OUEM_ID" not in acceptance
    assert "oub-589ee7e2-c016-5b74-b199-af2e052e0ff1" not in acceptance
    assert '"no_unexplained_loss": present == expected' in acceptance


def test_id_mapping_is_positive_bijective_and_order_independent():
    expected = {"oub-a": 1, "oub-m": 2, "oub-z": 3}
    assert numeric_id_mapping(["oub-z", "oub-a", "oub-m"]) == expected
    assert numeric_id_mapping(["oub-m", "oub-z", "oub-a"]) == expected
    assert len(set(expected.values())) == len(expected)
    with pytest.raises(VoxCityAdapterError, match="duplicate"):
        numeric_id_mapping(["oub-a", "oub-a"])


def test_interface_id_is_the_positive_voxcity_consumed_id():
    mapping = numeric_id_mapping(["oub-z", "oub-a"])
    assert interface_id_properties("oub-z", mapping) == {
        "ouem_id": "oub-z", "voxcity_id": 2, "id": 2,
    }
    with pytest.raises(VoxCityAdapterError, match="zero is background"):
        interface_id_properties("oub-a", {"oub-a": 0})


def test_height_uses_absolute_top_and_effective_ground_not_bottom():
    ids = [[0, 7, 7], [3, 7, 0]]
    dem = [[99.0, 10.0, 11.0], [2.0, 12.0, 99.0]]
    samples = grid_ground_samples(ids, dem, 7)
    values = derive_attributes([12.0, 31.0, 15.0], samples)
    assert values["z_top_abs"] == 31.0
    assert values["z_bottom_geom_abs"] == 12.0
    assert values["ground_eff_abs"] == 11.0
    assert values["height"] == 20.0
    assert values["min_height"] == 0.0


def test_grid_ground_rejects_building_without_assigned_cell():
    with pytest.raises(VoxCityAdapterError, match="no VoxCity grid cell"):
        grid_ground_samples([[0, 0], [0, 0]], [[1.0, 1.0], [1.0, 1.0]], 4)


def test_vertical_gate_accepts_declared_tp_and_rejects_unresolved():
    check_vertical_compatibility("absolute T.P. elevation in metres",
                                 {"status": "source-declared", "name": "T.P."})
    with pytest.raises(VoxCityAdapterError, match="not resolved"):
        check_vertical_compatibility("absolute T.P.", {"status": "unresolved", "name": None})
    with pytest.raises(VoxCityAdapterError, match="incompatible"):
        check_vertical_compatibility("absolute T.P.", {"status": "verified", "name": "ellipsoidal"})


def test_canonical_serialization_is_deterministic():
    first = canonical_json({"z": [2, 1], "a": "日本語"})
    second = canonical_json(json.loads(first))
    assert first == second
    assert first.endswith(b"\n")


def test_shell_surfaces_form_valid_footprint_and_discard_vertical_walls():
    shapely = pytest.importorskip("shapely", minversion="2.0")
    from shapely.geometry import MultiPolygon, Polygon
    roof = Polygon([(0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10)])
    floor = Polygon([(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)])
    wall = Polygon([(0, 0, 0), (10, 0, 0), (10, 0, 10), (0, 0, 10)])
    footprint, diagnostic = build_normalized_footprint(
        MultiPolygon([roof, floor, wall]), "oub-shell"
    )
    assert footprint.is_valid and footprint.geom_type == "Polygon"
    assert footprint.area == pytest.approx(100.0)
    assert diagnostic["source_surface_part_count"] == 3
    assert diagnostic["projected_discarded_zero_area_part_count"] == 1


def test_all_positive_projected_parts_are_unioned_and_order_independent():
    pytest.importorskip("shapely", minversion="2.0")
    from shapely.geometry import MultiPolygon, Polygon
    left = Polygon([(0, 0, 5), (2, 0, 5), (2, 2, 5), (0, 2, 5)])
    right = Polygon([(4, 0, 6), (7, 0, 6), (7, 2, 6), (4, 2, 6)])
    first, diagnostic = build_normalized_footprint(MultiPolygon([left, right]), "oub-parts")
    second, _ = build_normalized_footprint(MultiPolygon([right, left]), "oub-parts")
    assert first.area == pytest.approx(10.0)
    assert diagnostic["projected_positive_area_part_count"] == 2
    assert first.wkb == second.wkb


def test_only_degenerate_projected_surfaces_fail_fast():
    pytest.importorskip("shapely", minversion="2.0")
    from shapely.geometry import MultiPolygon, Polygon
    wall = Polygon([(0, 0, 0), (2, 0, 0), (2, 0, 3), (0, 0, 3)])
    with pytest.raises(VoxCityAdapterError, match="oub-degenerate"):
        build_normalized_footprint(MultiPolygon([wall]), "oub-degenerate")


def test_normalized_footprint_assignment_preserves_source_crs():
    gpd = pytest.importorskip("geopandas", minversion="1.0")
    pytest.importorskip("shapely", minversion="2.0")
    from shapely.geometry import Polygon
    source = gpd.GeoDataFrame(
        {"ouem_id": ["oub-a"]},
        geometry=gpd.GeoSeries(
            [Polygon([(0, 0, 1), (2, 0, 1), (2, 2, 1), (0, 2, 1)])],
            crs="EPSG:6677",
        ),
    )
    footprint = build_normalized_footprint(source.geometry.iloc[0], "oub-a")
    result = _set_normalized_footprints(source, {"oub-a": footprint})
    assert result.crs == source.crs
    assert result.geometry.crs == source.geometry.crs
    transformed = result.to_crs(4326)
    assert transformed.crs.to_epsg() == 4326


def test_voxcity_boundary_transforms_footprints_and_preserves_attributes():
    gpd = pytest.importorskip("geopandas", minversion="1.0")
    pytest.importorskip("shapely", minversion="2.0")
    from shapely.geometry import Polygon
    source = gpd.GeoDataFrame(
        {"ouem_id": ["oub-a"], "voxcity_id": [1], "id": [1],
         "height": [12.5], "min_height": [0.0]},
        geometry=gpd.GeoSeries(
            [Polygon([(-30000, -40000), (-29998, -40000),
                      (-29998, -39998), (-30000, -39998)])],
            crs="EPSG:6677",
        ),
    )
    result = _to_voxcity_building_crs(source)
    assert source.crs.to_epsg() == 6677
    assert result.crs.to_epsg() == 4326
    assert result[["ouem_id", "voxcity_id", "id", "height", "min_height"]].to_dict("records") == [
        {"ouem_id": "oub-a", "voxcity_id": 1, "id": 1,
         "height": 12.5, "min_height": 0.0}
    ]
