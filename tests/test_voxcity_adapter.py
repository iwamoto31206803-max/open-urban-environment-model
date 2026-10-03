import json
import inspect
from pathlib import Path

import pytest

from ouem.adapters.voxcity import (
    VOXCITY_COMMIT, VOXCITY_VERSION, VoxCityAdapterError, canonical_json,
    check_vertical_compatibility, derive_attributes, grid_ground_samples,
    interface_id_properties, numeric_id_mapping,
)
import ouem.adapters.voxcity as adapter


def test_version_is_exactly_pinned():
    assert VOXCITY_VERSION == "1.7.0"
    assert VOXCITY_COMMIT == "fa212656305328a9a657973bae26f352bfe813bc"


def test_a3_has_no_external_gis_worker_runtime_boundary():
    signature = inspect.signature(adapter.adapt_standard_to_voxcity)
    assert "runtime" not in signature.parameters
    package = Path(adapter.__file__).parent
    assert not (package / "_gdal_worker.py").exists()
    source = Path(adapter.__file__).read_text(encoding="utf-8")
    assert "subprocess.run" not in source
    assert "load_gis_runtime" not in source


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
