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

The local files for these stages belong under
`data/raw/building/plateau_komae/`,
`data/converted/building/plateau_komae/`, and `data/native/building/`
respectively. Converter output is converted input to OUEM, not the OUEM Native
Building dataset.

Direct GDAL/OGR conversion is not used because tested CityGML features became
`POLYHEDRALSURFACE Z EMPTY`; Converter output retained `MULTIPOLYGON Z` data.
The actual source and generated GeoPackages remain local and are not committed.
Standardization, VoxCity, terrain/canopy integration, and environmental
analysis remain subsequent work.

The completed Komae PoC produced `data/native/building/komae.gpkg` with layer
`building`: source and output Building counts both 3,637, 3D Multi Polygon
geometry in EPSG:4979 with Z retained, and preserved `measuredHeight` and
related attributes. QGIS 2D and 3D display succeeded using geometry Z without
added extrusion. The 3,637 count applies only to this acceptance Building
layer; other Converter GeoPackage layers are outside that comparison.
