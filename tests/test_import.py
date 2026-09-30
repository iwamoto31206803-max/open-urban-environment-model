"""Package-level smoke tests for the Phase A namespace scaffold."""

import importlib


PHASE_A_MODULES = (
    "ouem.acquire",
    "ouem.native.terrain",
    "ouem.native.building",
    "ouem.native.canopy",
    "ouem.standardize.terrain",
    "ouem.standardize.building",
    "ouem.standardize.canopy",
    "ouem.model.terrain",
    "ouem.model.building",
    "ouem.model.canopy",
    "ouem.adapters.voxcity",
)


def test_import_ouem() -> None:
    """The package skeleton can be imported."""
    import ouem

    assert ouem.__doc__


def test_phase_a_namespaces_import() -> None:
    """All architectural package boundaries can be imported."""
    for module_name in PHASE_A_MODULES:
        assert importlib.import_module(module_name).__name__ == module_name
