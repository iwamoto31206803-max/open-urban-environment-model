"""GIS-only acceptance check, intended for QGIS/OSGeo4W Python."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys


def main() -> int:
    ogr2ogr = shutil.which("ogr2ogr")
    if ogr2ogr is None:
        raise SystemExit("ogr2ogr is not on PATH; run this stage in OSGeo4W Shell")
    completed = subprocess.run(
        [ogr2ogr, "--version"], check=True, capture_output=True, text=True
    )
    from osgeo import gdal, ogr, osr  # noqa: F401

    print(f"GIS Python: {sys.executable} ({platform.python_version()})")
    print(f"ogr2ogr: {completed.stdout.strip()}")
    print(f"GDAL bindings: {gdal.VersionInfo('--version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
