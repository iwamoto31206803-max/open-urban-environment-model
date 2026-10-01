"""Capture the active GIS runtime for later OUEM child processes."""

import json
import locale
import os
import shutil
import sys
from pathlib import Path


def main(destination: str) -> int:
    ogr2ogr = shutil.which("ogr2ogr")
    ogrinfo = shutil.which("ogrinfo")
    if not ogr2ogr or not ogrinfo:
        print("ERROR: ogr2ogr and ogrinfo must both be available.", file=sys.stderr)
        return 2
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema": "ouem-gis-runtime/v0.1",
        "python": sys.executable,
        "ogr2ogr": ogr2ogr,
        "ogrinfo": ogrinfo,
        "output_encoding": locale.getpreferredencoding(False),
        "environment": dict(os.environ),
    }
    output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(f"GIS runtime snapshot written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
