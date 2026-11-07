# P1-0 audit log — 2026-11-07

Publication note: the following describes the completed audit, not the later report-only Git submission. Findings and decisions are unchanged. Absolute locators/full snapshots were omitted from the public evidence; original local reports remain unchanged.

Read-only scope: local formal documents and STEP 4-0/A/B1/B2/C records; file hashes; AST; package METADATA/RECORD; XML identifier/semantic labels; SQLite attributes and raw geometry BLOB fingerprints. No geometry decoding, triangulation, watertight checks, voxelization, Solar/GVI, pytest, install, pip invocation, or Git mutation.

1. Read Concept v0.2, Development Principles and relevant Standard Building/Terrain/Adapter clauses; SHA index in evidence/audit_summary.json. Formal A3 gates were not replaced by experimental semantics.
2. External source Git HEAD independently equals 19628c033b1cbbbdee80fe781f516672765d1eee; porcelain output empty. OUEM local HEAD b261f1d749b6fcda42f795e7052b73f26557ee2a; tracked status empty. No fetch/checkout/branch/commit/push/PR.
3. Followed 4-C document manifest pin through stored inputs. Stage manifests: 4-0 14498ba3..., 4-A f73e6507..., B1 5f1b0e1c..., B2 9f564e7d..., 4-C 82488e28.... Verified 429 unique files, mismatch 0, then size/mtime unchanged at end. Full hashes and repository-relative/logical locators in evidence/input_chain.json.
4. Read saved audit correspondence, extracted member XML IDs and all polygon IDs; queried immutable read-only GPKGs. No shape processing. Four IDs and ouem_ids match. Both Native and Standard have 31 LoD1 / 32 LoD2. Archived transformation/planarity results are inherited by byte identity, not recomputed.
5. Existing Python 3.11.9 metadata confirms VoxCity 1.7.0 pinned PEP610 commit fa212656305328a9a657973bae26f352bfe813bc. 136 source RECORD entries match. Existing environment inventory unchanged. VoxCityGML and MeshLib not installed there; mapbox-earcut absent.
6. Isolated Python 3.11.9 has pip24.0 and setuptools65.5.0 only. No dependency import test or binary ABI test. The dry-run is a plan, not proof of installed/resolved runtime behavior.
7. AST scanned VoxCityGML source without importing it: 15 VoxCity import sites, no unresolved symbol/module in installed source. VoxCityPipeline.assemble_voxcity signature matches call keyword names; aliases such as public water flattener exist. This is static compatibility only.
8. Inspected no-MeshLib fallback and defaults at exact commit. Source header saying auto hull conflicts with actual auto list: actual code excludes hull. Legacy repair path still can alter detail, perform voxel marching/fill sealed shells. Hole-triangulation failure explicitly falls back to exterior-only. No experiment was performed to quantify these effects.
9. Inspected DEM replacement/re-anchor; None/CityGML Terrain branch avoids anchor; missing terrain returns zeros. Explicit raster fallback is converted to WGS84 terrain triangles and interpolated. Default named-source auto-selection/land-cover/canopy downloads, input-adjacent parse cache and water flattening must be controlled in a future minimal run.
10. Dry-run JSON decoded as UTF-8 bytes, 211 rows. No licence field/classifier: 67. Forty-seven have additional same-version installed SPDX expressions (evidence is not proof of identical planned wheel). VoxCityGML MIT verified in source pyproject/LICENSE; VoxCity MIT in installed primary metadata/notices. The remaining 20 without recovered installed expression are listed below; the first (VoxCityGML) has source MIT evidence. Full wheel/native-library notices were not exhaustively audited.
11. Copyleft/compound notices need per-use review; no blanket commercial prohibition inferred. Metadata omission is an evidence gap, not a licence denial. 173 planned package versions have some same-version installed metadata/notice evidence. Source ZIP README and resource CSV re-read without extraction; SHA matches stored audit. README licence choices and acquisition-policy summary differ; retained as CONDITIONAL.
12. Draft search was scoped to specified repo/docs, source/docs, preflight; no matching OUEM P1 architecture/spec draft found. No assumptions imported from absent drafts.

## Read attempts and limits

- External Git read initially hit sandbox Permission denied; authorized read escalation resolved it. No Git setting/security change.
- One PowerShell brace-style path pattern was invalid; corrected to explicit paths.
- A default CP932 JSON read failed; read_bytes/UTF-8 decoding corrected the inspection. No input changed.
- Upstream raw LICENSE URLs at the two pinned commits returned web Cache miss. Online retrieval was not verified; licence findings use local primary pinned source / installed metadata. No upstream repository content was downloaded.
- No runtime tests were run because this task excludes implementation and 3D execution. Existing technical PASS and figures are prior archived evidence only.

## Packages without recovered same-version installed expression

- voxcitygml==0.3.0
- ipython==9.18.1
- overturemaps==2.1.0
- pyvista==0.49.2
- click==8.5.1
- llvmlite==0.50.0
- narwhals==2.28.0
- pyarrow==26.0.1
- pydantic==2.14.3
- pydantic_core==2.50.4
- python-dateutil==4.0.0
- scooby==0.12.1
- threadpoolctl==3.8.0
- python-box==8.0.0
- platformdirs==4.14.5
- typing-inspection==0.4.5
- jupyter_builder==1.2.4
- opentelemetry-api==1.45.2
- anyio==4.16.0
- pyzmq==27.3.0

This list is not a commercial-use blacklist. Several may carry licence text/files or valid SPDX in their actual wheel/source; further notice review is required if adopted.

All output files were newly created with exclusive creation in the user-named new subdirectory. Existing dependency-plan.json, data, environments, repository files and old reports were not overwritten.

## Public evidence index

[Summary](P1-0_REPORT.md), [input SHA chain](evidence/input_chain.json), [source identity](evidence/source_identity.json), [static compatibility](evidence/static_compatibility.json), [license table](evidence/dependency_licenses.csv), [audit/environment summary](evidence/audit_summary.json). Evidence projections intentionally omit raw geometry, full environment/package inventory, download URLs and local absolute paths.
