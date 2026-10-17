"""Export PR #42 candidate A (post-CRS make_valid) for read-only QGIS review.

Writes only a new diagnostic directory; never modifies the integration run.
"""
from pathlib import Path
import argparse
import json
import sys

import geopandas as gpd
import shapely
from shapely.geometry import shape

TARGET = "oub-21a29be1-9794-593f-b22c-e3639a7d9d45"


def main():
    parser = argparse.ArgumentParser(description="Export PR42 candidate A geometry for QGIS")
    parser.add_argument("run_id")
    parser.add_argument("--target", default=TARGET)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = root / "data" / "work" / "diagnostics" / f"{args.run_id}-repair-qgis"
    if output_dir.exists():
        raise RuntimeError(f"Diagnostic output already exists; refusing overwrite: {output_dir}")

    results = []
    for repeat in (1, 2):
        source = root / "data" / "work" / "integration" / args.run_id / f"repeat-{repeat}" / "adapter.geojson"
        if not source.is_file():
            raise FileNotFoundError(source)
        document = json.loads(source.read_text(encoding="utf-8"))
        matches = [f for f in document["features"] if f["properties"].get("ouem_id") == args.target]
        if len(matches) != 1:
            raise RuntimeError(f"repeat {repeat}: expected one target, found {len(matches)}")
        original = shape(matches[0]["geometry"])
        if original.is_valid:
            raise RuntimeError(f"repeat {repeat}: target is already valid")
        repaired = shapely.make_valid(original)  # PR #42 candidate A, after CRS conversion
        if not repaired.is_valid or repaired.geom_type != "MultiPolygon":
            raise RuntimeError(f"repeat {repeat}: unexpected repair: {repaired.geom_type}, valid={repaired.is_valid}")
        parts = list(repaired.geoms)
        if len(parts) != 2:
            raise RuntimeError(f"repeat {repeat}: expected two components, got {len(parts)}")
        results.append((repeat, repaired, parts))

    if results[0][1].wkb != results[1][1].wkb:
        raise RuntimeError("Repeat repair WKB mismatch; refusing export")

    output_dir.mkdir(parents=True)
    for repeat, repaired, parts in results:
        rows = []
        for index, polygon in enumerate(parts, 1):
            area = float(gpd.GeoSeries([polygon], crs="EPSG:4326").to_crs("EPSG:6677").area.iloc[0])
            rows.append({"ouem_id": args.target, "repeat": repeat, "part_index": index,
                         "area_m2": area, "geometry": polygon})
        frame = gpd.GeoDataFrame(rows, crs="EPSG:4326")
        output = output_dir / f"repeat-{repeat}-make-valid-parts.gpkg"
        frame.to_file(output, layer="repair_parts", driver="GPKG")
        print(f"QGIS: {output}")
        for row in rows:
            print(f"  Part {row['part_index']}: {row['area_m2']:.12g} m2")
    print("Repeat 1/2 repair WKB identical. Original E2E files unchanged.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
