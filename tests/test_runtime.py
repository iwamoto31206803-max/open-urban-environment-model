from __future__ import annotations

import sys

import pytest

from ouem.runtime import gis_environment_leaks, validate_ouem_runtime


def test_gis_environment_leaks_detects_native_and_python_paths() -> None:
    environment = {
        "OSGEO4W_ROOT": r"C:\OSGeo4W",
        "PYTHONPATH": r"C:\Program Files\QGIS 4.2.3\apps\Python312",
    }
    assert gis_environment_leaks(environment) == ["OSGEO4W_ROOT", "PYTHONPATH"]


def test_validate_ouem_runtime_accepts_current_clean_interpreter(monkeypatch) -> None:
    for name in (
        "OSGEO4W_ROOT", "QGIS_PREFIX_PATH", "QGIS_PLUGINPATH", "GDAL_DATA",
        "PROJ_LIB", "PYTHONHOME", "PYTHONPATH",
    ):
        monkeypatch.delenv(name, raising=False)
    validate_ouem_runtime(sys.executable)


def test_validate_ouem_runtime_rejects_gis_environment(monkeypatch) -> None:
    monkeypatch.setenv("QGIS_PREFIX_PATH", r"C:\Program Files\QGIS 4.2.3")
    with pytest.raises(RuntimeError, match="QGIS_PREFIX_PATH"):
        validate_ouem_runtime(sys.executable)
