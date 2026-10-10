# Ukai: 20-hour offline hackathon work order

Prepared 8 October 2026. The clock starts after the current SSD migration checks and baseline signoff. This is an implementation plan; its unchecked tasks are future work, not completed features or scientific acceptance.

**Demonstrated question:** How do additional release conditions change flood extent, arrival time, and the zones that need earlier review?

Build on the existing Explore, Compare and Evidence interface. H01, H02, H03 and the reconstructed 2006 scenario have already completed genuine import and preview integration. The existing selector, metrics, limitations, shared scales and synchronized comparison maps are the starting point. Earlier working-laptop visual checks were reported for 16 map-layer combinations; the portable copy has independently passed all 24 download-resource checks. Its automated screenshot test is blocked by the restricted browser environment, so complete the receiving-device visual check in the SSD guide. The earlier B-01 → Team A H02 context/tags → Team B import dependency has already been completed; do not spend the opening hours repeating it.

## Fixed model story

| Layer | Role and required label | Evidence boundary |
| --- | --- | --- |
| HEC-RAS | Reference scenario library; uncalibrated simulations | These packaged scenarios are reference outputs, not observed flood truth. Reconstructed 2006 is a model replay with source uncertainties. |
| Fast solver | Rapid what-if engine **under evaluation**; experimental preview | Its purpose is speed. Compare its outputs with the HEC-RAS reference and report differences. Do not claim scientific superiority or observed-event validation. |
| Optional surrogate | Bounded approximation for intermediate releases; identify surrogate/version/training range | Compare against held-out **fast-solver** runs, disjoint from training and tuning. Agreement with the solver is approximation evidence, not real-world accuracy or validated confidence. |
| Decision layer | Scenario comparison and transparent priorities for review | Explain changed area and timing using available data. Priorities support review; they are not optimal release decisions or evacuation orders. |

Default demo wording:

> HEC-RAS provides the reference library. Our rapid model lets planners explore additional release conditions, while showing model differences and where evidence is limited.

Use the requested wording “in seconds” only after the demonstrated path has measured end-to-end latency that supports it. Name that path: fresh solver run, stored result lookup, or bounded surrogate. A stored result lookup does not establish a fresh simulation time. Show an elapsed-time badge and disclose whether a result is computed or precomputed.

### Evidence that determines the scope

- `C:\Ukai\Ukai\part_a_handoff\PART_A_FOR_TEAM_B_REVIEW\FAST_SOLVER_STATUS.md` reports earlier laptop solver runs of 74–129 seconds. The later evaluation reports diagnostic runs of 132–205 seconds on a different two-core workspace. Grid construction, packaging, import and display overhead were not included. Current evidence supports minutes for a solver run, not a fresh result in seconds on the demo machine.
- `C:\Ukai\Ukai\part_a_handoff\integration_work\2026-10-07_v1\FAST_SOLVER_EVALUATION.md` is the later interpretation. H02 was used to fit Manning n = 0.025. H01, H03 and reconstructed 2006 are comparisons with the same unvalidated HEC-RAS model family, not independent observational validation.
- `ARRIVAL_METRICS_RECONCILIATION.md` in that directory separates signed bias from mean absolute difference. The like-for-like hourly-ceiling comparison has arrival MAE 2.09–4.07 hours across the four scenarios; H02 is 2.50 hours. Denominator: pixels with valid arrival in both engines. Report this mask and unit. Do not present the smaller signed bias as typical error.
- HEC-RAS maximum velocity magnitude and the solver's maximum face-normal velocity component have different definitions and resolutions. Direct differences require this caveat; do not rank safety from their raw velocity difference.
- The evaluation update dated 8 October records bounded Froude-cap sensitivity on H02 only, from 1.0 to 2.0, within the stated thresholds. Other parameters and scenarios remain untested. Volume accounting is numerical bookkeeping, not scientific validation.
- Fast-solver WSE and duration products are unavailable. Terrain lacks bathymetry and the vertical datum is unresolved. Actual producing-run time/timezone and input permissions remain unknown where recorded as unknown.
- The original fast-solver status includes an old backup statement. Inspect the actual source/results/runtime inventory and verify a copy; do not infer a complete solver backup from the presence of an older `E:\Ukai\part_a_handoff\fast_solver` folder.

## Offline operating rules and ownership

The prepared distribution is `E:\Ukai\Ukai_SSD_Ready` on the current SSD. On another machine the drive letter may differ. Follow the SSD setup guide shipped beside this plan. Preserve that distribution and its checksum manifest as the baseline; develop in machine-local working copies with separate runtime state. Check `evidence/SSD_FINAL_VERIFICATION.md` for the final seal and any device-specific acceptance still outstanding.

| Owner | Owns | Delivers to the other team |
| --- | --- | --- |
| Team A, machine A | Hydraulic assumptions, solver inputs/build/run wrapper, result arrays, GIS packaging, model comparison evidence | Versioned engine/result folders, checksums, compatible manifest/context, limitations, measurements and acceptance record |
| Team B, machine B | Existing frontend, API integration, arrival display, comparison UI, zones/priorities display, local launch and demo capture | Versioned application source/build, request/result contract, consumer checks and screenshots |
| Demo/evidence owner, assigned at hour 0 | Story, claims register, decision log, recordings and Q&A | A short prepared demo and traceable evidence alongside every milestone |

Agree the file owners before editing. Team A and Team B must not edit the same source file or delivery folder simultaneously. For a shared contract change, the owner sends a small draft, the consumer acknowledges it, then the owner publishes a new version. No Git, CI or ZIP is needed. Exchange **plain versioned folders** on the SSD.

Suggested new work layout outside the preserved distribution:

```text
<SSD root>\hackathon_work\
  exchanges\team_a\A-W01-<date>-v01\
  exchanges\team_b\B-W01-<date>-v01\
  integrated\I-W01-<date>-v01\
  demo_evidence\
```

Each delivery contains `DELIVERY.md` (owner, delivery ID, base package ID, changes, exact commands/entry point, known failures), a relative-path SHA-256 manifest, the changed files/results, and evidence. A receiver checks hashes, acknowledges the delivery ID, and copies into their local work area before integration. A correction creates `v02`; do not overwrite an acknowledged `v01`. Keep private configuration and mutable database/runtime state on the machine. Do not transfer a live database directory or assume a copied virtual environment is portable. Transfer registered assets and portable receipts; use the existing receiver/import process.

All required runtimes, native solver dependencies, wheels, frontend packages, outputs, guides and demo assets must already be available locally. Test with the network disconnected. Use no remote tiles, external data/API calls, runtime model downloads or internet-dependent AI. AI assistance is a preparation/build aid; the product runs locally without it. Keep tasks narrow, give an assistant the relevant contract/files, and review the patch once. Prefer one focused implementation plus one reviewer over multiple agents rewriting the same files.

## Interfaces to preserve and extend

The current UI uses `/api/v1/prototypes/scenarios`, `/{scenario_id}`, `/{scenario_id}/layers`, `/{scenario_id}/impact`, assumptions and quality-report links. The current manifest asset roles are `extent_geojson`, `max_depth_cog`, `max_velocity_cog`, and `arrival_time_cog`. Keep existing HEC-RAS IDs, bytes and provenance unchanged. Existing prototype admission remains draft/pending, uncalibrated and not scientifically validated.

The current arrival COG is stored in minutes and displayed in hours; convert exactly once. Preserve nodata and valid cells. The origin is simulation start, threshold is first depth > 0.1 m, and HEC-RAS arrival resolution is hourly. A nominal UTC coverage index does not establish a real historical timezone. Use elapsed model time in the product; retain unknown timezone/producing-run reasons in Evidence.

Agree these **new interfaces before implementation**; they are proposed work, not existing endpoints:

| Interface | Minimum fields and behavior |
| --- | --- |
| Release request | Request ID; base forcing/configuration identity; peak release in m³/s; hydrograph shape/interval/unit; model start and elapsed-time convention; immutable input checksums; engine/configuration version. Only one control varies; preserve the declared shape and other parameters. Bound requests to the explicitly evaluated input range. |
| Local job status | Request/run ID; queued/running/completed/failed; timestamps; elapsed wall-clock duration; cache/computed/surrogate identity; bounded safe failure reason. Completion means the exact assets are packaged, checked and available, not merely that the executable exited. |
| Candidate result folder | New scenario/run IDs; manifest/context/checksums; engine/configuration/input identity; release definition; native grid and transformation method; units/nodata/coverage; measured timings; available roles; missing-product reasons; numerical diagnostics and comparison report. Preserve native results as well as registered derivatives. |
| Difference result | Baseline and candidate IDs/checksums; comparison grid/CRS; threshold; both-valid mask and each-only counts; difference direction; units; nodata/coverage; resampling method. Never interpolate missing data as zero. |
| Zone result | Zone ID/geometry source; pair of run IDs; zone area and valid coverage; baseline/candidate/newly wet/lost-wet area; arrival statistics and both-valid denominator; priority ordering/rule version; limitations and unavailable fields. |

The current context schema has HEC-RAS-specific arrival conversion assumptions (`original_unit=h`, conversion factor 60). Do not make solver seconds or surrogate outputs fit by changing their identity. Team A and Team B must agree a narrow, versioned candidate extension if needed, with unit/identity checks and regression of existing HEC-RAS receipts. If this does not fit the timebox, show separate clearly labelled candidate previews from a verified local result folder instead of mutating the reference bundle or claiming import support.

## 20-hour sequence

The intervals below are elapsed time for the whole team, with work in parallel. At the end of each interval spend at most 10 minutes on a checkpoint: one demonstrated action, relevant acceptance evidence, one limitations update, and one acknowledged plain-folder exchange. Write down pass/fail and the chosen fallback. Preparation happens inside every interval, not after product development.

| Time | Main result | Preparation in parallel | Gate/fallback |
| --- | --- | --- | --- |
| 0–2 h | Baseline signoff, evidence/engine/input/label gate, frozen user journey | Inventory offline assets; claims sheet and 90-second story | No intact solver setup by h2: proceed with HEC-RAS timeline/comparison while Team A resolves a candidate preview |
| 2–5 h | Arrival timeline/scrubber on the existing arrival grid | Capture timeline explanation and test points | At h5 keep manual elapsed-hour reveal if playback is unstable |
| 5–8 h | Stronger scenario comparison, difference views and readable context | Prepare before/after screenshots and model-limit answers | At h8 keep extent-only differences if depth/arrival masks cannot be justified |
| 8–11 h | Fast-engine wrapper and candidate-result pipeline | Record reproducible run procedure and measured timing | At h11 use verified precomputed solver candidates if a fresh pipeline fails |
| 11–14 h | Measured what-if release control; optional bounded surrogate only after its own gate | Record live/cached timing and prepare honest fallback narration | Decide by h12 whether surrogate work is feasible; freeze the demonstrated path at h14 |
| 14–16 h | Changed-zone ordering and response-review explanation | Prepare three explainable zone examples | At h16 retain explicit changed-area table if rankings cannot be reproduced |
| 16–18 h | Polish, stable offline launch, loading/error handling and demo states | Assemble recording, pitch, checksums and launch card | Feature freeze at h18; only demo-blocking fixes afterward |
| 18–20 h | Rehearsal, backup recording and judge-question preparation | Practice answers and recovery on actual target machines | Sign off a local demo and backup; disclose any untested second-machine path |

### 0–2 h: gate the baseline and choose the demonstrated question

- [ ] Team B records the final SSD package ID/hash and the current passing migration/browser evidence. Preserve previous failed attempts as history; a stale `FRONTEND_STATUS.md` or older `COMPLETION.json` is not the current frontend status.
- [ ] Team B confirms one short opening journey in the existing UI: choose H02 → compare H01/H03 → inspect Evidence. Use existing verified checks; repeat only the launch/essential smoke needed on the actual demo machine.
- [ ] Team A inventories source, tuned/native results, required terrain/geometry/flow files, compiler/native runtime and relative folder expectations. Back up missing solver essentials in a versioned delivery and hash them. Do not start long reruns just to refresh old evidence.
- [ ] Team A defines the bounded release control: vary peak amplitude of one declared hydrograph shape; hold timing, terrain and boundaries fixed. A peak alone does not define a general release policy. Start with 15,000–30,000 m³/s as the existing hypothetical range, and label intermediate conditions as unevaluated until checked.
- [ ] Both teams agree candidate-result units/identity, output availability, uncertainty wording and ownership. Assign the demo/evidence owner.
- [ ] Preparation: make `demo_evidence/CLAIMS.md` with claim → source → limit → allowed wording; save a 90-second script and a local inventory of required packages/assets.

**Acceptance:** the baseline opens offline with its four unchanged references; the evidence index resolves; all unavailable impacts remain unavailable; the solver is visibly under evaluation. The inventory identifies which machine can run the solver and which native dependencies are missing. Decide the product's single question and record one immutable baseline ID. If the solver setup is incomplete at h2, protect the timeline/comparison track and keep the rapid-engine track optional.

### 2–5 h: arrival-time timeline on existing data

- [ ] Team B adds an elapsed-hour slider, current-time label, reset and optional play/pause within Explore; retain the current map layout and controls.
- [ ] Reveal only pixels with valid arrival time <= selected elapsed time. Derive slider limits from metadata/valid range, not hard-coded dates. Use hour steps for HEC-RAS.
- [ ] Label the view “Area reached by elapsed model time.” If maximum depth/velocity is shown under the reveal mask, label it as maximum-over-run data revealed by arrival; it is **not** time-varying hydraulics, current water level or recession.
- [ ] Team A supplies a few exact coordinate/value samples and preserved nodata samples from each arrival grid. Keep the existing aligned conversion and original bytes.
- [ ] Preparation: capture three frames (early, middle, late); prepare the explanation of hourly resolution, the 0.1 m threshold and the unknown actual timezone.

**Acceptance:** for an independently sampled cell with arrival 180 minutes, the reveal excludes it at 2 hours and includes it at 3 hours; use an equivalent real sample if 180 is absent. At start, show only truly valid arrivals at/before start; nodata never appears as zero or safe land. Advancing time cannot remove reached pixels. At the valid final hour, the mask equals the valid-arrival footprint, which may differ from maximum-depth wet extent; explain that difference. Switching scenarios resets/clamps time and cannot leave the previous grid displayed. Test pause/reset and one unavailable-layer case. At h5 drop playback if necessary and keep the reliable manual scrubber.

### 5–8 h: strengthen comparison and readable context

- [ ] Team B extends the working Compare page with explicit baseline/candidate naming, metric deltas and unchanged shared legends/view synchronization. Preserve scenario/engine badges and missing-value reasons.
- [ ] Team A/Team B compute new-wet, common-wet and baseline-only areas using depth > 0.1 m and a documented common valid grid. For aligned HEC-RAS scenarios use native pixel edges. For engine comparisons, state the native 100 m solver grid, mapping choice and valid domain.
- [ ] Add one toggle for difference display. Extent differences are first priority; optional depth/arrival differences use both-valid masks and explicit direction “candidate minus baseline.” Arrival differences compare equivalent definitions/resolution and disclose engine timing disagreement.
- [ ] Show coverage differences separately. Maximum values at different places are not paired local differences. Do not subtract incompatible velocity definitions as if the quantities were identical.
- [ ] Preparation: capture H01/H02/H03 comparisons; prepare the reason for HEC-RAS references, H02 tuning and shared color scales.

**Acceptance:** H02 versus itself gives zero new/lost area and zero paired differences; nodata remains excluded. Swapping a pair reverses signed differences and swaps new/lost areas. Independently counted valid wet pixels × pixel area reproduce reported km² to stated rounding. Pan/zoom and layer changes still synchronize; legends do not rescale per scenario. A missing comparison input yields an explicit unavailable state. At h8 keep extent categories and metric deltas if more detailed differences remain unreliable.

### 8–11 h: fast-engine wrapper and candidate pipeline

- [ ] Team A creates a local wrapper around the existing solver using immutable inputs, explicit run/configuration IDs and a separate result folder. Confirm build/runtime compatibility on the actual solver machine; a `-march=native` binary from a different CPU is not portability evidence.
- [ ] Run one representative bounded request on the demo hardware. Measure request → input/grid preparation → solver → packaging/checks → import/availability → browser-ready result. Record cold/warm/cache states and all stage times separately.
- [ ] Preserve maximum depth, native arrival and native velocity diagnostics, numerical checks and source checksums. Package only real supported products. Give each experimental result a new engine/scenario/run identity.
- [ ] Team B integrates bounded local job status and a candidate preview path with the agreed interface. Allow one active job; avoid accidental resubmission during slider drag. The backend running the candidate remains loopback/local and returns safe errors.
- [ ] Preparation: record the one-run procedure, resource use and actual hardware/configuration; save a labelled precomputed result for recovery.

**Acceptance:** one release request produces traceable assets and a labelled preview; repeating it cannot overwrite the reference or cross-wire run IDs. Invalid/out-of-range input fails before running. A solver/package failure displays failed status and cannot expose partial results. Original reference checksums remain identical. Report measured stage and end-to-end times, not the older laptop benchmark. At h11 select a verified precomputed experimental candidate if a fresh pipeline is not usable; retain the measured attempt and failure reason.

### 11–14 h: measured what-if control and optional surrogate gate

- [ ] Team B adds release control within the existing interface, constrained to the declared hydrograph shape/range. Show chosen peak, units, engine, computed/precomputed state and a deliberate Run action.
- [ ] Team A evaluates at least one intermediate condition disjoint from the existing H02 tuning case. Keep the reference selection visible while a job runs. Do not extrapolate agreement from four peaks to arbitrary shapes or beyond the evaluated range.
- [ ] Measure at least three complete interactions on the actual demo machine, including one fresh result where supported. Save the durations, input IDs and displayed result IDs. Describe the observed range; three runs do not justify a robust percentile/SLA claim.
- [ ] By h12 decide whether an optional surrogate is feasible. Continue only if local verified fast-solver runs cover the bounded family, a training/tuning split and at least two disjoint intermediate held-out peaks can be maintained, and the evaluation can finish before h14. Two holdouts are a minimum hackathon gate, not a statistical confidence guarantee. Four existing scenarios alone are insufficient evidence for a general learned release model.
- [ ] If proceeding, freeze split IDs and evaluation criteria before fitting: extent IoU, area difference, both-wet depth MAE, both-valid arrival MAE and each-only coverage counts, all against held-out solver outputs. Agree numerical pass/fail limits appropriate to the demo before examining held-out results; if no defensible limits can be agreed, omit the surrogate. Keep raw metrics and no-data behavior. Do not imply that surrogate agreement validates HEC-RAS or real floods.
- [ ] Preparation: record the honest demo path and fallback narration. A stored-result selector must say “precomputed experimental runs”; a nearest stored release must show the actual returned peak rather than pretending to compute the requested value.

**Acceptance:** for each displayed candidate, request/run/result IDs and requested/actual peak agree; cache hits are labelled; release bounds are enforced; the last successful map remains identifiable during failure/loading. A fresh solver run, lookup and surrogate cannot share a misleading latency label. A surrogate is displayed only inside its evaluated range, carries its version/split/checksums and held-out metrics, and declines unsupported inputs. At h14 freeze one demonstrated path: measured live solver, labelled stored candidates, or gated bounded surrogate. If none works, retain HEC-RAS scenario exploration and state that additional-release computation remains pending.

### 14–16 h: changed-zone ranking and response-review explanation

- [ ] Team A/Team B use actual supplied administrative/exposure polygons only if their provenance/coverage is established. Otherwise create fixed coordinate grid zones in the projected CRS and label them “coordinate review zones”; never give them fabricated village names or exposure counts.
- [ ] Calculate valid area, newly flooded area and earlier-arrival statistics per zone from the documented comparison masks. Pixel area is `abs(a*e - b*d)` for affine raster coefficients; convert m² to km². Clip/count partial zone overlaps consistently. Do not use pixel counts from different resolutions as area.
- [ ] Use a transparent review order rather than an opaque weighted safety score: zones with new flooded area first (descending new area), then other zones with earlier arrival (descending median paired arrival advance), with deterministic zone-ID ties. Display all underlying metrics and identify incomplete coverage. Require enough paired coverage for an arrival statistic; otherwise show unavailable and avoid a timing-based rank for that zone.
- [ ] Explain each selected zone in plain language: how much new area, whether paired arrival is earlier/later, valid coverage, engine/model limitation and why it appears in the review order.
- [ ] Preparation: save three examples, including one with missing arrival. Prepare the answer that there are no population/road/shelter impacts or evacuation routes without those actual inputs.

**Acceptance:** the sum of a complete, non-overlapping zone partition reproduces new-wet/lost-wet area within documented numeric rounding; sample zones match an independent raster calculation. Same-scenario comparison yields no changed-zone priority. Repeated results have the same order. Nodata and absent exposure values stay unavailable, never zero. The page states “priority for review” and cannot claim an optimal dam operation, route or emergency action. At h16 keep the transparent changed-area table if reliable arrival rankings cannot be completed.

### 16–18 h: polish, launch and offline demo states

- [ ] Team B improves readable labels, spacing, keyboard operation, loading/status text, empty states and recovery within the established design. Use visible simulation/engine labels across Explore, Compare, What-if and Evidence.
- [ ] Check scenario switching during load, backend interruption/recovery, missing candidate results and no WebGL. Keep a clear evidence/download path; unavailable map rendering is disclosed and the tabular comparison remains usable.
- [ ] Integrate only acknowledged folder versions into a new application delivery, leaving the signed-off baseline intact. Use the SSD guide for separate local state, start/stop and offline launch.
- [ ] Preparation: capture final screenshots/short recording, update claims, prepare a one-page launch/recovery card and save the final feature list. Keep a baseline-only fallback recording too.

**Acceptance:** on the actual target machine with network disabled, cold launch reaches the reference catalog and the frozen demonstrated path without a remote request. Perform the affected UI smoke and targeted tests/build appropriate to changed files; run the complete integration/regression suite once on the final integrated candidate, with the baseline isolated. Record skips/failures honestly. Verify package hashes and clean stop/restart. If a second machine has not been tested, mark that explicitly instead of claiming universal portability. At h18 freeze features and use the last acknowledged passing delivery for rehearsal.

### 18–20 h: rehearsal, backup recording and Q&A

- [ ] Rehearse the actual 3–5 minute judge journey twice: question → HEC-RAS reference → arrival reveal → comparison → additional-release path and timing → changed zones → Evidence/limitations.
- [ ] Run one rehearsal from a stopped offline state. Recover once from a planned interrupted backend or failed candidate without changing reference files. Fix only demo-blocking issues and repeat the affected step.
- [ ] Save a local backup recording with visible engine labels, input values, result IDs and measured elapsed time; save screenshots and the script alongside it. Do not speed up video without a visible disclosure.
- [ ] Verify the final plain-folder delivery/checksum manifest and baseline recovery path; keep one local machine copy and one SSD copy of demo materials. Do not leave the only recording on a working runtime folder.
- [ ] Prepare concise answers: Why HEC-RAS? Why a fast solver? Which inputs changed? What does arrival mean? Is 2006 observed? What was tuned? What are the timing/velocity differences? What does the surrogate approximate? Is this validated? Can it run offline? What data would enable exposure/evacuation analysis?

**Acceptance:** the operator can complete the journey, state the actual latency and evidence limits, open the backup recording offline, and restore the baseline without assistance. The final claims sheet matches what is demonstrated. Stop at h20 with the signed-off package ID, passing checks, limitations, frozen fallback and next steps recorded; do not conceal unfinished candidate work.

## Test/evidence discipline

Use meaningful focused checks for new behavior: timeline threshold/nodata and stale-scenario handling; same-pair/swapped-pair differences; request bounds/identity/failure isolation; zone area/order/coverage; and surrogate held-out evaluation if attempted. A screenshot does not replace numerical checks, and synthetic tests do not establish real model agreement. Use the existing baseline evidence for unchanged features.

Keep short checkpoint records under `demo_evidence/` containing delivery IDs, actual checks/results, chosen fallback and changes to allowable claims. Run a full suite again only after new changes, failures or unresolved concerns justify it. Preserve failed results; do not repeatedly run the same broad suite merely to make the record look stronger.

The final handoff contains the reference package ID, new application/engine delivery IDs, input/result checksums, target-machine launch evidence, end-to-end latency measurements, comparison masks/units, any surrogate split/evaluation, zone rule/coverage, final script, backup recording and honest limitations. This traceability is the foundation of the AI-plus-physics story.
