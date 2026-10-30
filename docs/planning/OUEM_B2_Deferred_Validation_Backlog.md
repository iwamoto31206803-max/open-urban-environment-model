# B2 Deferred Validation Backlog

2026-10-30. Status: **Deferred / Unverified**, except explicitly measured CPU
facts cited below. This is future technical verification planning, not execution
authorization, metric adoption, a new Acceptance gate or a finding of GPU error.

Evidence owners: [PR #123 static audit](OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md)
(sections 4–6, anchors R/U/H),
[CPU characterization](../experiments/b2_gvi/B2_CPU_GVI_Synthetic_Characterization_v0.1.md),
and [proposed decisions D01–D05](OUEM_B2_Minimal_Technical_E2E_Design_v0.1.md).
The [B1 backlog](OUEM_B1_Deferred_Validation_Backlog.md) is preserved; shared
B1-V01–V06/V08/V11/V12 remain applicable without being closed here.

| ID | Summary and evidence | Unconfirmed matters / future verification | State | B2 Technical E2E impact |
|---|---|---|---|---|
| B2-V01 | CPU/GPU TREE score: audit R:160–178 vs U:407–413 suggests CPU first-chord 1-T versus GPU ordinary hit=1; only CPU has now been executed | With separately authorized GPU environment, freeze matching synthetic voxels, origins, directions, targets, k/LAD, cutoff and sampling. Compare per-case analytic expectations and each backend's actual path before whole-map statistics. Do not assume equal metric definitions or assert measured differences today | Deferred / Unverified (execution comparison) | CPU-only technical characterization can proceed; GPU substitution/parity and metric naming cannot be inferred |
| B2-V02 | CPU/GPU starting cell/capacity: audit R includes start, U:398/464–515 has guard/skip logic; CPU inside-TREE half chord and out-of-Z finite zero measured | Future origin-in-TREE/Building/AIR, boundary and out-of-capacity controls using equal physical coordinates; check origin selection and valid masks separately from scores | Deferred / Unverified (backend comparison) | Require independent CPU observer/capacity checks before real E2E; do not share masks blindly |
| B2-V03 | Precision, axes and ray sampling: audit R Float64, U Float32, H/G differing direction conventions, possible sampling phase | Future matched explicit directions plus grid/Fibonacci cases, non-square asymmetric scenes, near ties and cutoff neighbourhood. Record device/dtypes/thread/runtime, absolute/relative errors and masking; thresholds need design before execution | Deferred / Unverified | No backend accuracy ranking or drop-in parity; future directional interpretation needs explicit local frame |
| B2-V04 | CPU fast/generic tangency: audit R tie handling predicted risk; CPU exact diagonal side-Building now gives generic 0 vs direct fast 0.506931308604760 | Extend independent hand-geometric cases to reversed axes, 3D corners and near ties; decide intended tangency policy before adopting a backend. Frequency/effect in real scenes unknown | Deferred / Unverified (scope/impact); specified synthetic discrepancy confirmed | Fast/generic are not interchangeable generally; D02 requires explicit review |
| B2-V05 | Public fast fallback: audit V catch-all risk; recorded NumPy/Numba environment raises 1D-mask TypingError and silently returns generic; shaped-mask direct fast diagnostic succeeds | Future separately approved upstream/runtime investigation and explicit path observability. Recheck uninstrumented public call and captured path in any changed environment; no engine/dependency modification authorized here | Deferred / Unverified (upstream resolution/portability); local failure confirmed | fast=True numeric agreement is not fast success. Declare actual execution path; generic proposal remains for review |
| B2-V06 | CPU cutoff and metric: audit R T<0.01; CPU k=4.6 gives 0.989948164255366, k=4.61 gives 0; deeper crown unchanged | Exact-cutoff/near-cutoff precision controls; review weighted first-chord versus Concept binary canopy fraction, optical meaning and suitable public API. Do not force binary scores by tuning k/LAD | Deferred / Unverified (threshold boundary/scientific definition) | D01 remains unresolved; no primary GVI definition adopted |
| B2-V07 | Domain/viewpoint/sampling validity: audit sections 3/5 and CPU height/escape/mask measurements | Separately authorize fixed-origin domain extension, sampling convergence, physical-height controls and independent photographic/field references. CPU finite zero outside Z and positive code 14 are not physical validity | Deferred / Unverified | D03–D05 and shared B1 geometry remain open; 32 m context is not certified for GVI |

Reopen a row with scope, engine/source identities, environment, independent
expectations, proposed tolerances and authorized resource/data boundaries.
Keep execution facts distinct from source inference and scientific validity.
No GPU/Taichi installation or execution, real-data GVI, or B1 evidence change
is authorized by this backlog. The current synthetic task does not decide the
transition to real-data Technical E2E.
