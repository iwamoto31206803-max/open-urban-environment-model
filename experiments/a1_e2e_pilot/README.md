# A1 Tokyo Reference End-to-End Pilot

This directory records the first small-area A1 Tokyo Reference end-to-end
experiment. The accepted building-input portion is:

```text
PLATEAU CityGML
→ PLATEAU GIS Converter GUI (manual, retain 3D)
→ Converter 3D GeoPackage
→ OUEM Native Building ingest and validation
→ QGIS 3D visual acceptance
```

Direct GDAL/OGR conversion is not used because tested CityGML features became
`POLYHEDRALSURFACE Z EMPTY`; Converter output retained `MULTIPOLYGON Z` data.
The actual source and generated GeoPackages remain local and are not committed.
Standardization, VoxCity, terrain/canopy integration, and environmental
analysis remain subsequent work.
