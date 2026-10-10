# Ukai demonstration script and questions

Date: 2026-10-09 (Asia/Calcutta). Target: this computer, confirmed by the user. This is preparation, not evidence that two human rehearsals have occurred.

## 90-second introduction

“Ukai Flood Intelligence helps us explore and compare four stored HEC-RAS simulations. These are uncalibrated reference outputs, not observed flood truth. We can inspect depth, velocity, extent and elapsed arrival; compare recorded wet footprints and paired arrival differences; and explain coordinate zones needing review. Our What-if path selects existing references and shows the actual returned release, without pretending that a stored lookup is a fresh simulation. Every result links back to run identity, original assets and limitations. The application runs locally without public hosting or login.”

## 3–5 minute judge journey

| Approximate time | Action | Explain |
|---|---|---|
| 0:00–0:40 | Open H02 in Explore; show depth and arrival | Stored HEC-RAS simulation; shared scales; uncalibrated. |
| 0:40–1:20 | Timeline: 3 h, final hour, pause/reset | First depth above 0.1 m; hourly HEC-RAS arrival; elapsed model time. Maxima colouring is not time-varying water level. |
| 1:20–2:20 | Compare H01/H02, then swap; select zones | Candidate minus baseline; unmatched coverage is unknown, not dry. Zones support review, not evacuation. |
| 2:20–3:20 | What-if: 20000 exact, then 26000 with explicit nearest opt-in | The nearest result is 30000, not a new 26000 simulation. Name the displayed lookup timing scope and cache state. |
| 3:20–4:20 | Open H02 Evidence and original assets | Run IDs/checksums, units, missing exposure measurements and scientific limitations. |
| 4:20–5:00 | State next steps and fallback | Calibration, more independent scenarios and separately gated solver/ML work; show the offline screenshot backup if needed. |

Do not force a 5-minute runtime by inserting delays into a recording. These times are narration targets, not performance measurements.

## Questions and honest answers

- **Why HEC-RAS?** It provides the packaged hydraulic reference simulations. This does not make these inputs calibrated or independently validated.
- **Do you calculate a new flood when I enter a release?** No. This release demonstrates exact or opted-in nearest stored-reference selection. A new hydraulic computation is not enabled.
- **What changes between hypothetical scenarios?** The supplied hypothetical family varies release amplitude within its declared forcing assumptions. Peak alone does not define an arbitrary release policy.
- **What does arrival mean?** First depth above 0.1 m, recorded hourly, stored in minutes and displayed as elapsed hours since simulation start. It is not a confirmed historical timezone.
- **Is 2006 observed validation?** No. It is a reconstructed model replay with source uncertainties.
- **What does “candidate-only wet” mean?** Wet in the candidate but not recorded wet in the baseline; the baseline may have nodata. It is not proof of a dry-to-wet transition.
- **Can the system estimate people or roads affected?** Not with the delivered data. Those measurements stay unavailable, not zero.
- **Is the ML model ready?** An offline approximation diagnostic exists. Enabled prediction remains unavailable because the independent-data and acceptance gates are unmet.
- **Is this scientifically validated or suitable for evacuation decisions?** No. The interface supports review of simulated results; it does not issue operational recommendations.
- **Can it run without the internet?** The runtime, assets and application dependencies are packaged locally. Physical disconnected acceptance must be recorded on the final laptop before claiming that check complete.

## Rehearsal acceptance

- [ ] Operator performs the complete journey once in 3–5 minutes.
- [ ] Operator repeats it from a stopped, physically offline state.
- [ ] Operator demonstrates one planned failure and recovery without altering reference bytes.
- [ ] Record a normal-speed local video with readable engine labels, requested/actual release and timing scope.
- [ ] Play the video offline; keep a separate SSD copy and a local copy.

Automated browser smoke, unit tests and screenshots do not tick these operator/video boxes.
