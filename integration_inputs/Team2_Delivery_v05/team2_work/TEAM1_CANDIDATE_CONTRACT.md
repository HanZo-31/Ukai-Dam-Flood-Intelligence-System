# Team 1 / Team 2 candidate contract — version 1.0.0

Date: 8 October 2026. Base package: `2ccf20b727ac4588a7f3ac39ba68b9ca`.

This contract covers the local Team 2 service. Reference endpoints remain the existing `/api/v1/prototypes/scenarios` namespace. Team 1 owns its frontend adapter; Team 2 owns this service and its tests. The service is separate from the baseline API and binds `127.0.0.1:8770`; reference resources continue through the existing app proxy on5174/API8766. Neither team edits the other's runtime or database.

Assembly clarification (no schema change): the implemented combined supervisor uses frontend/proxy5176, reference API8767 and separate PostgreSQL55434 by default. It routes the unchanged candidate contract through the same origin. Ports5174/8766 above remain the original baseline/development setup; use ASSEMBLY_AND_RUN_GUIDE.md for the combined launch profile. The actual Team1 frontend adapter/build still needs to be received and tested.

## Current capability and exact-plan decision

Only four physical scenarios are supplied. H01/H02/H03 share terrain, geometry, plan settings and a rounded fixed hydrograph shape, with peaks15000/20000/30000m³/s. Reconstructed2006 is a different hydrograph/duration and remains a reference, not another peak-only fit sample. H02 is stored under `part_a`, not `receipts/h02`.

The first diagnostic fits H01/H03 and holds out H02. It is a log-linear spatial regression, distinct from the linear-interpolation comparator. It does not generate extra hydraulic scenarios. The original plan requires two disjoint intermediate holdouts and independently defensible numerical gates before a surrogate is displayed. Only one is available, so `experimental_ml` stays disabled. Existing HEC-RAS reference exploration is the plan's permitted fallback. No alternate scientific acceptance criteria are introduced.

Do not display diagnostic weights as a supported new-scenario generator. The fit cannot infer flood expansion into endpoint nodata cells. Experimental evaluation evidence can be linked in Evidence with its domain limits.

## Endpoints

| Method/path | Behavior |
| --- | --- |
| GET `/api/v1/candidates/capabilities` | Supported modes, bounded family, available reference peaks, validation status and model unavailability reason. |
| POST `/api/v1/candidates/jobs` | Explicit stored-reference selection. Must say stored lookup, not compute a flood simulation. |
| GET `/api/v1/candidates/jobs/{job_id}` | Completed lookup identity/resources/timing;404 when absent. |

These are implemented by Team2 in this delivery; the baseline API does not already contain them. Separate-loopback-service routing is the initial connection. Final launcher/proxy wiring belongs to the final assembly and must be tested with the actual service.

## Request

```json
{
  "schema_version": "1.0.0",
  "request_id": "demo-request-001",
  "mode": "stored_reference",
  "input_family": "ukai-hyp-fixed-shape-v1",
  "peak_release_m3s": 20000,
  "allow_nearest_stored": false
}
```

Identifiers: lowercase letters/digits/underscore/hyphen,3..100 characters. Unknown fields, nonfinite values, unsupported family/mode and releases outside15000..30000 reject. With `allow_nearest_stored:false`, only15000/20000/30000 succeed. With true, return the nearest stored peak, resolving ties toward the lower peak, and prominently expose requested AND actual peak. No interpolation or ML is performed by this mode. Reusing a request ID with different content returns409; same content returns the saved job. Request bounds are a library-selection range, not evidence of calibrated intermediate predictions.

## Result

Required fields: schema_version,job_id,request_id,status,mode,input_family,requested_peak_release_m3s,actual_peak_release_m3s,cache_hit,computed,engine,scientifically_validated,calibration_status,warnings,elapsed_wall_seconds,source_scenario_id,source_run_id,reference_resources. Completed means all referenced source objects/hash checks passed. Stored lookup reports `computed:false`, `engine:HEC-RAS stored reference`, `scientifically_validated:false`, `calibration_status:uncalibrated`.

`reference_resources` contains relative URLs in the unchanged prototype namespace: detail,layers,impact,assumptions,quality_report. Team1 resolves these through its existing reference API adapter. It must use `source_scenario_id` and `source_run_id`, never derive a new scientific run from job ID. Timing is service lookup/validation time, not hydraulic model execution time or complete browser-ready latency. The final demo separately measures request→display latency.

Job states reserved for future computed modes are queued/running/completed/failed. Current stored lookup normally returns completed. UI fixtures may test all states but stay clearly labelled as fixtures; fixtures are never returned by the actual service as scientific candidates.

## Errors and independent frontend behavior

400 invalid selection;404 unknown job;409 conflicting request identity or busy service;422 schema/unsupported mode;503 source/resource validation unavailable. Errors use a safe reason code and no private path/credentials. Missing Team2 connection keeps Team1's reference pages operational, with an explicit candidate-service-unavailable state.

Team1 can implement its adapter and fixtures now using this version. Contract changes require a new version and a documented compatibility check; source/evaluation updates do not silently enable unsupported modes. A real ML mode requires a separate capability and acceptance decision supported by the plan's data/evaluation gates.

## Handoff to Claude

Give Claude this file and the exported `candidate-openapi-v1.json`, plus `candidate-examples.json` when generated. Copy these files manually through the agreed plain folders; no external message has been sent. Read capability flags before enabling a mode. Keep reference labels/units/unknown values unchanged.
