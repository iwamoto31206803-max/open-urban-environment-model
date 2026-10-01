# Runtime architecture

## Windows native GIS boundary

OUEM uses a process boundary between two independently managed runtimes:

| Runtime | Responsibilities |
| --- | --- |
| OSGeo4W / QGIS | `ogr2ogr`, GDAL/OGR and `osgeo`, and future GIS-native tools such as PDAL |
| Repository `.venv` | OUEM orchestration, validation, provider selection, and portable Python logic |

These environments are intentionally not merged. OUEM is not installed into
QGIS Python, and QGIS/GDAL Python bindings are not installed into the OUEM
venv. Different compatible minor versions are expected: the accepted local
combination includes QGIS 4.2.3 / GDAL 3.13.3 / GIS Python 3.12.14 alongside
OUEM Python 3.11.9.

An OUEM provider may invoke a native GIS executable or a selected GIS Python
(`--gis-python`) only as a child-process worker. The bridge must use an explicit
executable, a narrow argument/file or serialization contract, and separate
error reporting. It must never activate OSGeo4W in the OUEM parent process or
reinterpret the GIS Python as OUEM's interpreter. This policy applies equally
to PLATEAU, CHM, LiDAR, GDAL, and PDAL providers and does not alter Standard
Building or any other provider-independent data contract.
