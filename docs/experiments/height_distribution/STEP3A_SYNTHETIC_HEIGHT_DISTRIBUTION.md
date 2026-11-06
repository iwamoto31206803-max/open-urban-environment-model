# STEP 3-A — Synthetic Building Height Distribution PoC

2026-11-06. **COMPLETED_SYNTHETIC_ONLY / EXPERIMENTAL** for the bounded
geometry/numerical checks below. Scientific validation and formal acceptance:
**NOT_VERIFIED**; `terrain_integration_ready=false`. No engine connection or
real-data accuracy is established. The PR's Windows/Ubuntu CI results are
recorded in its description, separately from this local experiment.

## Baseline and audit

Base: main `2864c61cfbf9fa0a993fdc67abe7cedf7a528be3`, PR #161 merged;
[its pytest run](https://github.com/iwamoto31206803-max/open-urban-environment-model/actions/runs/42149343003)
completed successfully before this branch was created.

Reviewed [Concept v0.2 §4.2](../../OUEM_Concept_Architecture_v0.2.md),
[H0 audit](../../planning/OUEM_H0_Height_Distribution_Design_Audit_v0.1.md),
[T4-B1](../../../src/ouem/candidate_b_t4b1.py),
[T4-B2](../../../src/ouem/candidate_b_t4b2.py),
[T5](../../../src/ouem/candidate_b_t5.py),
[real voxel ground/occupancy audit](../../../src/ouem/real_komae_voxel.py),
[Mixed-LoD standardizer](../../../src/ouem/standardize/building/mixed_lod.py)
and their authored synthetic tests. The Standard preserves source face/ring XYZ;
the existing downstream path derives representative heights against owner-cell
mean ground, then checks segments and quantized occupancy. None of these paths
is replaced. The H0 stage table has historical local numbering: this experiment
is the **current STEP 3-A**, not H0's old STEP 2-B or its real-PLATEAU STEP 3-A.

## Implemented boundary and Derived meaning

[Implementation](../../../src/ouem/synthetic_height_distribution.py) accepts
only explicitly authored planar XYZ polygon faces and independent valid XY
Polygon footprints. No file reader, automatic roof classification, triangulation,
planarity repair or missing-height interpolation is provided. Nonfinite/missing
or nonnumeric XYZ, unclosed/degenerate/nonplanar faces, self-intersection and bad
holes are rejected. Valid vertical walls are recorded as excluded. Numerical
planarity distance tolerance is `1e-8 m`; normalized `|normal_z| <= 1e-12` is the
vertical exclusion threshold. These are synthetic numerical constraints, not
physical accuracy budgets. Near-vertical real geometry is outside verification.

The existing `height_envelope.GridSpec` supplies EPSG:6677 north-up, resolution-
aligned bounds, centres and Affine. The experiment records top-left origin,
eastward column vector, southward row vector, shape, units and a grid identity.
It deliberately inherits that helper's restricted grid: arbitrary rotation,
non-aligned origins, other CRSs and anisotropic cells are unsupported. No new
grid framework or dependency was added. The imported Envelope helper is not run
as a CHM/Terrain pipeline.

Each cell retains **all** intersecting buildings and positive-area roof-face
contributions, each with source/face identifiers, cell index, absolute top Z,
validity/state and coverage fraction. Input geometry/provenance, canonical source
SHA, implementation SHA, environment and sampling method are recorded. Per-building
maximum summaries accompany the complete contribution list; there is no single
cell owner. Lower overlapping faces and buildings are retained.

| Field / condition | Meaning |
|---|---|
| `NO_BUILDING` | No positive-area footprint intersection; no fabricated Z |
| `BUILDING_PRESENT` | One or more footprint intersections, including missing roof support |
| `KNOWN` / `valid=true` | Top is numerically determined for this method; 0 and negative synthetic absolute Z are valid |
| `TOP_UNKNOWN` / `valid=false` | Footprint exists but this method has no supported top; JSON `null`, never zero |
| Face `CENTRE_UNSUPPORTED` | Positive-area roof contribution exists but does not cover the centre |
| `building_count`, `contribution_count` | Explicit multiplicity before any owner decision |
| `footprint_fraction` | Building-footprint intersection area / full cell area |
| `coverage_fraction` | Roof-support **union** area / full cell area; overlapping faces are not double-counted |
| `partial_roof_coverage` | `0 < coverage_fraction < 1`; known partial support does not establish a complete roof |

Per-face coverage is its clipped area / full cell area; sums may exceed one under
overlap, while the union summary does not. Roof support is explicitly clipped to
the independently authored footprint and cell. All original faces remain in
source provenance, including excluded walls and outside-footprint portions.
No inference about cavities, overhang solids or bottoms follows from this top.

**A, centre:** evaluate each positive-area clipped face whose closed support covers
the exact cell centre. A centre on a seam can have two face values; retain both.
**B, cell maximum:** evaluate the affine Z plane at vertices of the clipped roof
polygons, including disconnected parts and holes. A linear function's maximum
on the compact polygon closure is at a vertex. Boundary-only line/point touches
do not create building/roof contributions. B is not the maximum over the whole
cell when only a small part is covered. Neither method is formally selected.

## Executed synthetic comparison

Windows OUEM `.venv/Scripts/python.exe`: Python 3.11.9, NumPy 2.4.6,
Shapely 2.2.0; existing environment, no dependency changes. The following runs
write new files exclusively and never overwrite an existing path:

```powershell
.venv/Scripts/python.exe -m ouem.synthetic_height_distribution --output data/work/step3a-synthetic/comparison-final-a.json
.venv/Scripts/python.exe -m ouem.synthetic_height_distribution --output data/work/step3a-synthetic/comparison-final-b.json
```

Both independent invocations produced byte-identical JSON with full Derived
records and comparisons. SHA256:
`b924247829ab1559693b178a2fc18fb45bbfe8d61823607fac8a8b2bb7b2ca8f`.
Implementation SHA256:
`43bc89a67a4b6a29e34315ac882e20ad21d1a072589c118619e40a3b6601271d`.
These local generated artifacts remain ignored, not committed; rerun the small
authored demonstration to inspect them. Byte identity is verified on this
environment, not asserted across OS/package versions (environment is recorded).

Representative comparison uses an explicitly authored per-building constant
absolute top (the source roof maximum), mimicking the representative baseline
numerically without calling or replacing the existing model. All demo cells are
1 m. Counts below are cells; each demonstration has one building.

| Roof / representative Z (m) | A known / unknown | B known / unknown | Numeric differing cells / max B−A (m) | Support differences | Partial cells |
|---|---:|---:|---:|---:|---:|
| Flat / 10 | 4 / 0 | 4 / 0 | 0 / 0 | 0 | 0 |
| `Z=10+2x+3y`, 2×2 m / 20 | 4 / 0 | 4 / 0 | 4 / 2.5 | 0 | 0 |
| Step at `x=.75`, Z=4 or 9 / 9 | 2 / 0 | 2 / 0 | 1 / 5 | 0 | 0 |
| 3×3 roof, central 1×1 hole / 10 | 8 / 1 | 8 / 1 | 0 / 0 | 0 | 0 |
| Thin support `x=0..0.1`, `Z=10+2x` / 10.2 | 0 / 1 | 1 / 0 | not comparable | 1 | 1 |
| Partial support `x=0..0.75`, `Z=10+2x` / 11.5 | 1 / 0 | 1 / 0 | 1 / .5 | 0 | 1 |

For the sloped roof, north-to-south row-major A Z is
`[15.5,17.5,12.5,14.5]`; B Z is `[18,20,15,17]`.
Representative-minus-A ranges 2.5–7.5 m; representative-minus-B ranges 0–5 m.
For the step, A is `[4,9]`, B `[9,9]`, representative-minus-A 0–5 m and
representative-minus-B 0. The thin eave is a support/validity difference, not a
numerical zero difference; its B top is 10.2, not the full-cell extrapolated 12.
Partial coverage explains some differences, but full-coverage slopes/steps also
differ. Numeric counts compare only mutually known building-cell pairs; separate
support-difference lists prevent unknown values from disappearing into zeros.

Absolute Z is not height. With flat ground Z=2, slope A relative values are
`[13.5,15.5,10.5,12.5]`. With ground `Z=2+x` at the explicit **cell centres**,
they are `[13,14,10,11]`; B-minus-centre-ground is `[15.5,16.5,12.5,13.5]`.
The latter is explicitly not the maximum of local roof-minus-ground height.
The subtraction helper preserves NaN unknowns, rejects infinite top/nonfinite
ground and never changes D0, ownership, ground or voxel rounding. All datum
values are arbitrary synthetic elevations, with no T.P. inheritance claim.

## Verification and protection

[Self-contained pytest](../../../tests/test_synthetic_height_distribution.py)
contains 25 cases, with hand-calculated/analytic expected values rather than
sampling the implementation to generate expectations. Coverage includes flat,
slope, seam/step, roof and footprint holes, thin/partial support, vertical walls,
disconnected clipped support, negative slope/Z and valid zero, multiple buildings
and faces, invalid XYZ/shape, translated 2 m grid, unchanged inputs, order stability
and repeated-run identity. It imports no fixtures from older tests.

Focused final command:

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_synthetic_height_distribution.py tests/test_candidate_b_t4b1.py tests/test_candidate_b_t4b2.py tests/test_height_envelope.py -k "not test_height_envelope or exact_komae_grid_centres or invalid_constant_cr or replaceable_spatial_cr_model"
```

**44 passed, 33 deselected, 8 warnings, 2.33 s**. Warnings are existing Rasterio
Affine multiplication PendingDeprecationWarnings. No skips/failures in this run.
An earlier broad related run stopped producing output during the legacy Envelope
bundle tests and was interrupted (exit 1, no completed summary); it is not counted
as PASS. Those tests obtain repository-wide Git status in their provenance path;
the full Envelope suite is left to the unchanged CI gate rather than repeatedly
running that path in this large local workspace. Full local regression was not
run. The original Windows/Ubuntu full-suite CI, pip cache and `--durations=30`
remain unchanged, with no weakened tests or assertions.

Only new synthetic files and documentation change in this PR. No real PLATEAU
was read; no saved T5/STEP 2 input was loaded or changed, and no Terrain/Canopy,
VoxCity voxelization, Solar or GVI was executed by this experiment. Standard,
Adapter, representative-height implementation, pinned engine and dependencies
remain unchanged. Existing CI still runs its original synthetic engine tests.

## STEP 3-B handoff and unresolved decisions

STEP 3-B may consume these explicit absolute-Z, coverage/state and many-to-many
contribution records in **new synthetic tests**. Before any connection, establish
ground sampling identity/anchor, D0, surface-vs-building index convention,
rounding, capacity and owner/segment correspondence independently. Preserve the
representative baseline; do not flatten owner-conditioned ground implicitly.

Centre/max adoption, missing-support policy, conflicting source ownership,
eaves/solid interpretation and physically meaningful tolerances remain unresolved.
Top-only information cannot establish occupied intervals or cavities. Arbitrary
nonplanar roofs, real PLATEAU/GSI processing, CRS transformations, formal Derived
schema and scientific accuracy remain **NOT_VERIFIED / NOT_IMPLEMENTED** as
applicable. STEP 3-B is not executed or accepted by this PR.
