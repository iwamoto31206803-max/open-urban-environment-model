import json

import pytest

from ouem.adapters.voxcity import (
    VOXCITY_COMMIT, VOXCITY_VERSION, VoxCityAdapterError, canonical_json,
    check_vertical_compatibility, derive_attributes, numeric_id_mapping,
)


def test_version_is_exactly_pinned():
    assert VOXCITY_VERSION == "1.7.0"
    assert VOXCITY_COMMIT == "fa212656305328a9a657973bae26f352bfe813bc"


def test_id_mapping_is_positive_bijective_and_order_independent():
    expected = {"oub-a": 1, "oub-m": 2, "oub-z": 3}
    assert numeric_id_mapping(["oub-z", "oub-a", "oub-m"]) == expected
    assert numeric_id_mapping(["oub-m", "oub-z", "oub-a"]) == expected
    assert len(set(expected.values())) == len(expected)
    with pytest.raises(VoxCityAdapterError, match="duplicate"):
        numeric_id_mapping(["oub-a", "oub-a"])


def test_height_uses_absolute_top_and_effective_ground_not_bottom():
    values = derive_attributes([12.0, 31.0, 15.0], [10.0, 11.0, 12.0])
    assert values["z_top_abs"] == 31.0
    assert values["z_bottom_geom_abs"] == 12.0
    assert values["ground_eff_abs"] == 11.0
    assert values["height"] == 20.0
    assert values["min_height"] == 0.0


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
