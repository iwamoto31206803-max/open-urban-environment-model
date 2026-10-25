# GEEKOM A6 Windows development and Codex Remote setup

Status: **LOCAL ENVIRONMENT ACCEPTED (scope-limited)**  
Recorded: 2026-10-25  
Scope: personal Windows development workstation for OUEM; not a Komae real-data acceptance or a portable environment guarantee.

## Purpose and boundaries

This record captures an observed, working development and remote-control setup. It does **not** replace OUEM's architecture, formal data contracts, or earlier Komae acceptance records. Software versions below are observations, not new minimum requirements. Source datasets will be downloaded afresh from public providers; no transfer from the company PC is planned.

## Host and repository

- Host: GEEKOM A6; Windows 11 Pro; AMD Ryzen 7 6800H; Radeon 680M; 32 GB RAM; 1 TB SSD.
- Repository: `iwamoto31206803-max/open-urban-environment-model`.
- Local checkout: `C:\dev\open-urban-environment-model`.
- Tools: Git for Windows, VS Code, Codex extension, ChatGPT/Codex desktop connection.
- Repository-local OUEM Python: **3.11.9**, in `.venv`; installed in editable mode with `pip install -e .`.
- Pinned external VoxCity: commit `fa212656305328a9a657973bae26f352bfe813bc`; do not change as part of workstation setup.

## Two-runtime boundary (existing architecture)

The separation documented in [Windows local acceptance helpers](../../scripts/work/README.md) remains authoritative:

| OUEM `.venv` | QGIS/OSGeo4W |
| --- | --- |
| OUEM orchestration, portable Python, GeoPandas/Rasterio, VoxCity, pytest | Native GDAL/OGR, `osgeo`, PDAL, QGIS |
| Python 3.11.9 | GIS Python 3.12.15 observed on this PC |

Do not install OUEM into GIS Python or `osgeo` into the OUEM venv. Do not launch `.venv\Scripts\python.exe` from OSGeo4W Shell. GIS Python is used where needed as a **child-process worker through a file/argument contract**; this is intentional separation, not an environment merge.

Observed GIS versions: QGIS Desktop **4.2.3**, GDAL/OGR **3.13.3**, PDAL **2.10.0**. QGIS GUI launch, `gdalinfo`, `ogrinfo`, `pdal --version`, and `from osgeo import gdal` were checked successfully.

### Capturing the GIS runtime

In **OSGeo4W Shell** (not VS Code PowerShell):

```cmd
cd /d C:\dev\open-urban-environment-model
scripts\work\plateau_komae_local_acceptance.cmd gis
```

Observed output: GIS Python 3.12.15, `ogr2ogr` GDAL 3.13.3, GDAL bindings 3.13.3; runtime snapshot written to `scripts\work\.runtime\plateau_komae_gis.json`. This snapshot is local/ignored and **must not be committed**.

The same `gis` command from ordinary VS Code PowerShell failed with `ERROR: ogr2ogr not found. Use OSGeo4W Shell.` This is expected when OSGeo4W's tools are not on that shell's PATH; it does not indicate broken GIS installation.

The subsequent `scripts\work\plateau_komae_local_acceptance.cmd ouem` stage was **not run on this PC** because it expects local PLATEAU real-data inputs. A successful GIS snapshot is not proof of end-to-end ingest.

## Local verification evidence

- Full OUEM test run on the new PC: **400 passed, 5 skipped, 0 failed**, 128 warnings.
- Normal VS Code PowerShell successfully launched `.venv\Scripts\python.exe`, reporting Python **3.11.9**.
- Codex local smoke test: repository and Git status read; temporary `data/work/codex-smoke-test/smoke.py` created, then removed; final `git status --short` was empty.
- The initial Codex **sandboxed** Python launch failed (exit code **103**). Diagnosis: sandbox access was denied to the base Python at `C:\Users\iwahi\AppData\Local\Programs\Python\Python311\python.exe`; the base Python and venv were confirmed present and working outside the sandbox. **Do not interpret this as a broken venv.**
- Codex then ran `.venv\Scripts\python.exe -m pytest -q tests/test_komae_preflight.py` with approval for execution outside the sandbox: **36 passed**, 24 Rasterio `PendingDeprecationWarning` warnings, exit code **0**, 21.21 s.
- Codex permission setting during successful workflow: **Approve for me**. Keep approval boundaries; **Full access is not required**. Inspect and approve privileged operations as needed. Do not bypass the sandbox silently.
- No source/config edits or commits were made by the smoke tests. Pytest cache creation was not separately audited.

## iPhone Codex Remote

The iPhone ChatGPT app's Codex **Connect computer** workflow was paired with GEEKOM A6. The device showed online (green indicator), and the local `open-urban-environment-model` project and existing Codex session were visible.

A read-only remote request returned:

1. Working directory: `C:\dev\open-urban-environment-model`.
2. `git status --short`: empty (clean).
3. `.venv/Scripts/python.exe`: exists.

The same result was obtained **over cellular data after restarting the PC and reopening the ChatGPT app**. This verifies remote read-only Codex command execution and reconnection in the observed conditions, not unrestricted remote desktop access.

Power/sleep settings were reviewed by the operator and reported suitable for remote operation. Long unattended uptime, wake from sleep, and **remote editing / pytest via iPhone** have not yet been separately accepted. The PC must be online and the remote host connection available.

## Operating practices

- Use VS Code/ordinary PowerShell for OUEM `.venv` commands, and OSGeo4W Shell for OSGeo4W-specific `gis` setup.
- Prefer GitHub-hosted source and documentation for code reviews; avoid dumping long README files to terminal.
- Keep local data, generated GIS artifacts, `.runtime` snapshots, credentials, pairing codes, and machine-specific secrets out of Git.
- Use Codex for controlled local changes and tests; review diffs before commit/PR/merge.
- A mobile Codex connection is **not** a general Windows GUI remote desktop and does not imply automated QGIS GUI access.
- When rebuilding on another machine, verify tool versions, interpreter paths, GIS snapshot, Python tests, and Codex approval behavior anew.

## Next phase (not yet accepted)

1. Inventory authoritative public sources, licenses, download URLs, and expected file layout for Komae inputs.
2. Download required open data directly from the providers to the new PC.
3. Run the documented real-data acceptance workflow only once prerequisites are present, and record new local evidence separately.
4. Optionally test a small remote **edit + pytest** task and unattended availability as distinct remote acceptance checks.

See also: [root README](../../README.md), [runtime architecture](../architecture.md), [Windows local acceptance helpers](../../scripts/work/README.md).
