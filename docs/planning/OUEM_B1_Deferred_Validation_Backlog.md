# B1 Deferred Validation Backlog

Recorded 2026-10-30 against main `53c5067d72c62631fdbfd949077faedaab604316`.
Owner: future verification planning; linked from the
[B1 technical closeout](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md).
**All work below is deferred**, not scheduled, approved for execution, or assigned
a new pass/fail threshold. Priorities express the order when relevant work resumes:
P1 before physical interpretation or a dependent B2 design decision; P2 targeted
validation/sensitivity; P3 scaling/performance work. They are not new Acceptance
gates or a requirement to finish all B1 science before B2 planning.

Evidence owners:
[PA: parameter audit](OUEM_B1_VoxCity_Parameter_Baseline_Audit_v0.1.md),
[S1: synthetic sanity](../experiments/real_komae_solar/B1_PHYSICAL_SANITY_PHASE1.md),
[G2: real geometry/observer diagnosis](../experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md),
[AB: configured real-data verification](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst).
Those records own the full numeric evidence and unchanged source identities.

| Issue ID / priority | Known fact | Unverified question | Candidate future method | Applicability | Reopen condition |
|---|---|---|---|---|---|
| B1-V01 / P1 — physical observation height | S1/G2: API requests 1.5 m above voxel surface; real valid ROI observers are about DEM+2–3 m | Desired pedestrian exposure plane, height above surveyed/effective ground and roof/water/excluded-point policy | Agree the physical definition first; compare exact observation coordinates with synthetic and surveyed controls, then separately authorized height sensitivity | **B1 and B2**; B2 viewpoint definition must be explicit | User-approved observer definition or a B2 design that needs viewpoint heights; obtain approval before changing scientific assumptions |
| B1-V02 / P1 — D0 and vertical rounding | G2: same-DEM near-coincident A/B observers can differ by about half a metre because the origin/rounding phase changes; within-run paired observers match | Effect on ray intersections and comparisons across domains, and appropriate absolute vertical reference for future use | Freeze inputs; isolate origin/rounding phase in geometric controls and authorized common-location comparisons; compare occupied prefixes and source/voxel H | **B1 and B2**, shared geometry | Cross-extent comparison or B2 geometry reuse needs common physical coordinates; separate approval for D0/placement changes |
| B1-V03 / P2 — voxel resolution | Nominal 1 m production scenes; S1's continuous ray/box oracle agrees for tested discrete boxes; earlier sensitivity replicated samples | Convergence for real sub-cell roofs/crowns and observation rays; finer grid is not automatically better data | Predesign geometric oracles and memory limits; compare separately authorized resolutions with consistent observers and source sampling, not just replicated coarse cells | **B1 and B2** | Resolution change is proposed and resources/expected comparisons are agreed |
| B1-V04 / P1 — canopy XY / CHM accuracy | G2: state=1 includes valid zero depth; CHMv2 is estimated, with abrupt spatial steps and candidates over buildings | Tree presence/absence, horizontal alignment, source age, roof false positives and local CHM bias | Compare existing candidate maps with appropriately dated independent vegetation/imagery/height observations; retain zero/NoData and temporal distinctions | **B1 and B2**, especially B2 vegetation attribution | Independent reference becomes available or a decision would treat TREE as measured vegetation; new acquisition requires authorization |
| B1-V05 / P2 — CR and crown bottom | Fixed CR=0.60 reproduces prepared Float32 Envelope; thin expansion, ground exclusions and Building priority explain saved occupancy | Ecological crown-bottom accuracy, suitable CR variability and representation of thin crowns | Review independent crown profiles; preregister CR/bottom sensitivity and geometric cases; distinguish pre-priority interval from surviving TREE | **B1 and B2** geometry | Crown geometry will be interpreted physically or modified; agree references and parameter scope first |
| B1-V06 / P1 — Building 2.5D and height | G2: source extrema/footprints agree, but grounded roof-max supports and surface rounding differ from source surfaces | Roof slopes, openings/overhangs, base/ground accuracy, data dates and true shadow/visibility fidelity | Compare selected source LoD2 surfaces and independent surveys/observations with current proxy; quantify representation error before proposing richer geometry | **B1 and B2**, shared obstruction | A use case requires more than the bounded 2.5D proxy; geometry/contract changes need approval |
| B1-V07 / P1 — k / LAD and cutoff | PA/S1: explicit defaults k=0.6, LAD=1.0 follow exp attenuation in tested boxes; T<0.01 becomes numeric zero | Local/species/season calibration, optical homogeneity and exact-cutoff boundary behavior | Independent optical/path-length controls near the cutoff; field-informed sensitivity only after experimental design; do not derive geometry CR from optical k/LAD | **B1** physics; **B2 applicability undecided**, depends on its visibility definition | Optical interpretation/parameter change is requested, or B2 proposes a transmission rule; do not copy B1 optics by default |
| B1-V08 / P1 — context / exterior occluders | AB/G2: isotropic 32 m known-height bound fails; conditional directional checks pass; finite-domain exterior sufficiency remains UNVERIFIED | Missing outside shadows, scene-height bounds and adequate context for each ray family | Authorized expanded-domain convergence at unchanged ROI/observers; retain source coverage/NoData guards and classify unknown exterior objects | **B1 and B2**; different ray directions need separate context reasoning | Boundary-sensitive interpretation, changed sun, taller objects or B2 all-direction views are proposed |
| B1-V09 / P2 — sun / temporal representativeness | PA: azimuth 135°, elevation 35°, DNI 800 are artificial required inputs, not dated weather/defaults | Representative date/time/timezone, actual DNI and seasonal/daily interpretation; global/annual results not established | Agree an external-condition dataset and API path; compare fixed geometry first, then separately scoped dated/weather runs | **B1**; **B2** source season/date relevance, not necessarily solar physics | A dated/weather-based or time-integrated assessment is requested |
| B1-V10 / P1 — measured radiation / shade | S1 supports numerical formula consistency; no independent real-city field accuracy is certified | Radiation bias, shade-edge position/time accuracy and uncertainty budgets | Design synchronized measured irradiance/shadow references, geometry/weather controls and a comparison protocol before choosing accuracy criteria | **B1**; B2 needs its own visibility reference, not this radiation test | Suitable measurements, purpose and study design are approved; no criteria are pre-approved here |
| B1-V11 / P2 — region/data transfer | AB confirms configured reuse of existing prepared data in adjacent rectangles, not nationwide/provider generality | New region/provider/datum/coverage behavior, independent geometry and provenance completeness | Start with coverage/CRS/height/provenance preflight, then separately authorized representative E2E cases and failure tests with new evidence IDs | **B1 and B2** | A new region, input identity or provider is actually requested; preserve existing formal contract boundaries |
| B1-V12 / P3 — runtime / wider application | AB records bounded CPU timings and shared array sizes; no broad scaling benchmark or national pipeline | Cold/warm JIT, memory growth, I/O, larger context/scene limits and B2 ray-count scaling | Benchmark explicitly defined workloads/backend/thread counts, peak memory and failure behavior; do not extrapolate B1 timings to B2 | **B1 and B2** runtime | A concrete scale/performance target is requested with resource budget and approved workloads |

## Interpretation and restart rules

- **Unverified is not failed.** Most rows are questions without independent
  reference truth. V08's particular isotropic-bound failure, historical PR #107
  capacity failure and initial test-oracle arithmetic failure remain the outcomes
  of those specified checks; none means every B1 result is invalid. Later technical
  completion does not relabel a past failure or supply missing field validation.
- A common translation of all observers/occluders does not change visibility;
  absolute endpoint residuals alone are not measured Solar error. Changes in
  relative geometry, sampling, quantization phase and optical paths require their
  own controlled comparison.
- Restart one purpose at a time: identify the issue IDs, evidence/run/source
  snapshots, physical hypothesis, external conditions, reference observations,
  comparison method and proposed criteria **before** execution. Obtain required
  authorization for real runs/acquisition, scientific changes, dependencies or
  formal contracts; none is provided by a row's candidate method.
- Use fresh output IDs, preserve old bytes/hashes and distinguish technical
  calculation, visible modeled effect, scientific accuracy and Acceptance.
  Keep outcomes in an owning experiment report and update this backlog by link.
  B2 shares geometry/provenance concerns but must define its own metric, viewpoint,
  masks and validation under the [Concept owners](../OUEM_Concept_Architecture_v0.2.md).
