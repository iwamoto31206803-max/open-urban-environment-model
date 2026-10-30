# CI and runtime evidence

Checked 2026-10-30 against main `ab17b28` (PR #128 merged), for Cleanup Plan
[C02 / PR-B](../planning/OUEM_Repository_Cleanup_Plan_v0.1.md#c02--explicit-environment-and-ci-evidence-p1--pr-b).
This describes evidence visibility, with no dependency, Python support, scientific
condition, Acceptance or backlog change. The [runtime architecture](../architecture.md)
owns environment separation; the [Windows runbook](../../scripts/work/README.md#runtime-boundary)
owns operational instructions. The [Inventory](../planning/OUEM_Repository_Inventory_v0.1.md)
retains its dated baseline and Unknowns.

## CI execution and metadata

The [workflow](../../.github/workflows/pytest.yml) triggers pull requests to main
and manual workflow_dispatch with contents:read. Its unchanged matrix is
`ubuntu-latest` / `windows-latest`, Python 3.12, checkout@v4 and setup-python@v5.
Installation remains `python -m pip install . pytest`; testing remains
`python -m pytest -q -ra`. Pyproject selects `tests` with `src` on pythonpath.
These commands do not install QGIS or run the opt-in `tests/integration/run_*.py`
real-data launchers, which are not pytest's default test filename pattern.

Between installation and tests, `python -m ouem.runtime_evidence` emits JSON using
only the standard library and installed `importlib.metadata`:

- OS family and Python version, without hostname, OS build details or environment.
- Interpreter name under the literal `<python-prefix>/` placeholder. The actual
  executable directory is intentionally withheld, including on developer hosts;
  this is a diagnostic label, not proof of executable identity.
- Distribution versions for pip, NumPy, Rasterio, GeoPandas, Shapely, pyproj,
  SciPy, VoxCity, Numba, Matplotlib, affine, pandas and pytest. Pip version is
  distribution metadata, not a subprocess invocation. Nonstandard version strings
  (including local suffixes) are withheld as unavailable to bound output.
- VoxCity PEP 610 `direct_url.json`: only the exact public URL
  `https://github.com/kunifujiwara/VoxCity.git`, git VCS and a 40-hex commit are
  allowed. Unknown/private/credential-bearing origins are withheld, never echoed.
  Requested revision, filesystem paths, raw metadata, exceptions and tokens are
  not printed. Missing or malformed metadata is an explicit incomplete observation.

The collector imports no third-party package or simulator, does no network access,
and writes no files. It does not authenticate metadata, rehash installed sources,
verify the pin, or establish engine compatibility. Existing provenance guards
remain responsible for their own checks. An `observed` status means collection
succeeded, not that the environment or tests passed.

Missing/withheld fields produce `status: incomplete`, sanitized issues, a GitHub
warning and exit code 1. The reporting step alone has `continue-on-error: true`,
so its failure does not prevent pytest. Inspect the step's original outcome and
issues: a green job can contain an incomplete report. Unexpected collection errors
also yield a fixed warning without raw exception text. Installation failure still
blocks subsequent steps under existing Actions behavior. Pytest failure behavior
is unchanged. No full pip freeze, path dump or artifact upload is added.

To inspect the same report locally, run `.venv/Scripts/python.exe -m
ouem.runtime_evidence` from an ordinary Windows terminal (Cloud uses
`.venv/bin/python -m ouem.runtime_evidence`). Use the OUEM environment, not GIS
Python. The report deliberately omits private absolute executable paths; the
existing runtime checks own actual selected-interpreter validation.

## What test results mean

| Check / evidence | Scope and limitation |
|---|---|
| Ordinary pytest | Synthetic scenes, unit/contracts, saved-run authored fixtures and platform-specific launcher checks. Some CPU simulator tests execute small synthetic scenes; metadata collection itself does not. `-ra` records skip reasons. |
| GIS skips | `test_gis_display.py` has two `skipUnless` methods gated by `find_spec('osgeo')`; `test_gis_project.py` and `test_b2_gvi_qgis.py` gate actual round-trip classes on `find_spec('qgis')`. Pure reference/mocked tests in these files still run. Discovery is not an installation/health test; a broken discoverable GIS environment can fail rather than skip. |
| Other skips | Windows CMD tests skip on non-Windows; symlink checks can skip for missing Windows privileges. Some tests use importorskip for declared geospatial packages/versions. Report actual reasons per run; skip is not PASS coverage. |
| Isolated GIS Python | Existing standalone unittest files exercise GDAL cell lookup and QGIS save/reopen/relocation with synthetic rasters when run in the separately managed, already available GIS runtime. See [Solar GIS procedures/evidence](../experiments/real_komae_solar/README.md#qgz-project-generation) and [B2 usage](../experiments/b2_gvi/README.md). Ordinary CI does not supply that runtime. |
| QGIS GUI | Actual visual display, NoData, location and presentation checks require their own recorded GUI observations. Headless save/reopen tests do not establish GUI verification. |
| B1/B2 real-data Technical E2E | [B1 Closeout](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) and [B2 Closeout](../status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md) link frozen run/source/configuration/output evidence and observed GIS checks. Ordinary CI neither recomputes these datasets nor guarantees their availability. |
| Scientific validity / Formal Acceptance | CI success establishes neither physical accuracy, photo agreement, new Formal Acceptance nor closure of deferred questions. Existing [acceptance records](../acceptance/), Building pilot and B1/B2 backlogs retain their own scope and states. |

Run ordinary tests with the OUEM venv. Existing GIS files can be executed directly
as standalone unittest scripts using the already configured GIS Python, without
installing OUEM or pytest into it. Local GIS setup remains host-specific; consult
the [recorded Windows setup](OUEM_Windows_Development_and_Remote_Setup_20261025.md).
Its observed versions and the architecture's earlier versions describe different
dated environments, not a new minimum compatibility specification.

## Dependency observation, without declaration changes

AST inspection of tracked Python under src/scripts/tests identifies the following
external import roots. Local module/test imports are repository references, not
third-party dependencies. Static inspection does not resolve every dynamic plugin,
native-library or external Converter dependency.

| Classification | Imports / evidence |
|---|---|
| Standard library | Examples: importlib.metadata, json, pathlib, platform, sys, ast, subprocess, unittest, sqlite3, xml. No new external dependency for the report. |
| Declared direct runtime | numpy, rasterio, geopandas, shapely, pyproj, scipy, voxcity: the seven dependencies in [pyproject](../../pyproject.toml). Build-only setuptools>=68 is separate. VoxCity remains pinned at `fa212656305328a9a657973bae26f352bfe813bc`. |
| Currently transitive, imported by source | affine (rasterio and VoxCity metadata), matplotlib and numba (VoxCity metadata), pandas (GeoPandas and VoxCity metadata). pandas appears in canopy experiments/integration; Numba in CPU runners and synthetic tests. This observation is based on installed distribution Requires-Dist, not a guarantee of all future resolver outcomes. |
| GIS-only | osgeo, qgis: separate GDAL/QGIS workers, standalone helpers and conditional tests. Do not add them to OUEM requirements to remove skips. Rasterio's GDAL use does not imply osgeo Python bindings are available. |
| Test-only | pytest is explicitly installed by CI, not a project runtime declaration. trimesh is directly imported by a synthetic observer test and currently provided by VoxCity's metadata dependency. unittest/mock are stdlib. |
| Unknown | Undeclared dynamic/native/external-tool requirements, fresh-machine compatibility and lower-bound combinations were not exhaustively exercised. No missing-package defect is inferred from an undeclared direct import alone. |

Future dependency review may consider declaring actually used transitive packages
directly or documenting test requirements, after checking supported versions,
resolver conflicts and compatibility with the fixed VoxCity revision. Python>=3.10
is declared, but CI exercises only 3.12; the lower bound and later Python versions
are not certified by this matrix. Pins/lockfiles, wider Python coverage and GIS CI
remain separate decisions. No package declaration, version or matrix changes here.

## Remote observations and remaining Unknowns

Read-only Actions query on 2026-10-30 for PR #128 head `5d45ba3` found
[run 41018142771](https://github.com/iwamoto31206803-max/open-urban-environment-model/actions/runs/41018142771):
Both jobs completed successfully (Windows was still running at the initial
query). Retrieved logs record Ubuntu **1,062 passed, 28 skipped, 19 warnings,
187.40 s** and Windows **1,085 passed, 5 skipped, 39 warnings, 392.74 s**.
This is the pre-change PR #128 run, not this report's validation.
Job success does not imply zero skips. The connector filters
pull-request runs and returns
only the first page; this is not an exhaustive Actions history or main-merge
workflow result. The workflow has no push trigger. New PR results must be read
from that PR's own checks; these dated observations are not new-code validation.

Branch protections, external workflows, fresh GIS compatibility, clean-room
dependency resolution and full installed-source integrity remain unverified.
CI logs describe a specific checked-out revision, OS and resolved environment;
B1/B2 execution reports bind different dated real inputs and outputs. Neither
should be rewritten to imply the other's coverage. No historical evidence or
Inventory Unknown is marked resolved by this visibility work.
