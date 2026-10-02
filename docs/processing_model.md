# Processing model

Provider-native processing may require a vendor GIS runtime. On Windows it is
executed out of process; outputs cross into OUEM through the existing
RAW/NATIVE/STANDARD data boundaries, not through shared Python imports.

```text
clean cmd:  OUEM .venv orchestration ---- files/arguments ----+
                                                          process boundary
OSGeo4W:    ogr2ogr / QGIS Python / GDAL / future PDAL <-----+
```

Interactive acceptance mirrors that boundary with separate `gis` and `ouem`
invocations of the work helper. Closing OSGeo4W Shell before the OUEM stage is
required because QGIS environment variables can redirect even an explicitly
named `.venv\Scripts\python.exe` to QGIS's Python and standard library.
