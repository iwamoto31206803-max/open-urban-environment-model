"""Runtime-boundary checks for native GIS subprocess integrations."""

from __future__ import annotations

import os
from pathlib import Path
import sys


GIS_ENVIRONMENT_VARIABLES = (
    "OSGEO4W_ROOT",
    "QGIS_PREFIX_PATH",
    "QGIS_PLUGINPATH",
    "GDAL_DATA",
    "PROJ_LIB",
)


def gis_environment_leaks(environment: dict[str, str] | None = None) -> list[str]:
    """Return variables which show that a GIS runtime leaked into OUEM."""

    env = os.environ if environment is None else environment
    leaks = [name for name in GIS_ENVIRONMENT_VARIABLES if env.get(name)]
    for name in ("PYTHONHOME", "PYTHONPATH"):
        value = env.get(name, "")
        if "qgis" in value.lower() or "osgeo4w" in value.lower():
            leaks.append(name)
    return leaks


def validate_ouem_runtime(expected_python: str | Path) -> None:
    """Fail unless this is the requested clean, repository-local interpreter."""

    expected = Path(expected_python).resolve()
    actual = Path(sys.executable).resolve()
    if actual != expected:
        raise RuntimeError(f"OUEM interpreter mismatch: expected {expected}, got {actual}")
    leaks = gis_environment_leaks()
    if leaks:
        names = ", ".join(leaks)
        raise RuntimeError(
            "GIS runtime variables are present in the OUEM process "
            f"({names}). Run this stage from a new Windows cmd or VS Code terminal."
        )
