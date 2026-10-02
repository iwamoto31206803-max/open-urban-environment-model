# A1 Tokyo Reference End-to-End Pilot

This directory records the first small-area A1 Tokyo Reference end-to-end
experiment. The accepted building-input portion is:

```text
PLATEAU CityGML
→ PLATEAU GIS Converter GUI (manual, retain 3D)
→ Converter 3D GeoPackage
→ OUEM Native Building ingest and validation
→ QGIS 3D visual acceptance
→ OUEM Standard Building conversion and local acceptance
```

The local files for these stages belong under
`data/raw/building/plateau_komae/`,
`data/converted/building/plateau_komae/`, and `data/native/building/`
respectively. Converter output is converted input to OUEM, not the OUEM Native
Building dataset.

Direct GDAL/OGR conversion is not used because tested CityGML features became
`POLYHEDRALSURFACE Z EMPTY`; Converter output retained `MULTIPOLYGON Z` data.
The actual source and generated GeoPackages remain local and are not committed.
Native-to-Standard conversion now selects Komae extent intersections without
clipping and writes `data/standard/building/komae.gpkg`. Its formal input is
the accepted EPSG:4979 Native layer; it transforms only the EPSG:4326
horizontal component to EPSG:6677 and preserves the retained absolute T.P. Z.
VoxCity, terrain/canopy integration, and environmental analysis remain
subsequent work.

The completed Komae PoC produced `data/native/building/komae.gpkg` with layer
`building`: source and output Building counts both 3,637, 3D Multi Polygon
geometry in EPSG:4979 with Z retained, and preserved `measuredHeight` and
related attributes. Its required source feature identifier is the non-null
String field `id` inherited from the Converter `bldg:Building` layer; there is
no `gml_id` field. Standardization copies `id` to Standard `source_id` without
mutating the Native GeoPackage. QGIS 2D and 3D display succeeded using geometry Z without
added extrusion. The 3,637 count applies only to this acceptance Building
layer; other Converter GeoPackage layers are outside that comparison.

## Standard Building v0.1 local acceptance record

The Windows/QGIS-OSGeo local acceptance command
`scripts\work\plateau_komae_local_acceptance.cmd standard` was run against the
accepted Komae PLATEAU Native Building. It completed with the following result:

| Check | Result |
| --- | --- |
| Input features | 3,637 |
| Selected/output features | 111 |
| Input CRS | EPSG:4979 |
| Output CRS | EPSG:6677 |
| Geometry type / 3D | 3D Multi Polygon / True |
| Native source identifier | `id` |
| Required Standard metadata | PASS |
| Z preservation | PASS (maximum delta 0 m) |
| Deterministic IDs | PASS |
| Overall result | **PASS** |

The 111 output features are the buildings intersecting the configured Komae
study-area extent; 3,637 is the Native input count and is **not** the Standard
output count. Selected boundary buildings retain their complete geometry.

This result accepts the implemented Native-to-Standard conversion against the
current Standard Building v0.1 conditions for this Komae PLATEAU dataset. It
does not demonstrate compatibility with every PLATEAU municipality or dataset,
does not validate downstream VoxCity processing, and does not make the
provisional Standard Building v0.1 specification final.
