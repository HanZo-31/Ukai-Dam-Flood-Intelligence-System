# Prototype preview HTTP contract — Stage 2 design

Version 1.0.0, 7 October 2026. This defines planned Stage 9 models/routes; it is not an enabled service, generated live schema or receiver/scientific acceptance. The executable OpenAPI design is prototype-preview-api-v1.design.json; existing b2-openapi-v1.json is unchanged.

| Method | Path below /api/v1/prototypes/scenarios | Response |
| --- | --- | --- |
| GET | empty suffix | PrototypeList, pagination default20/max100/nonnegative offset |
| GET | /{scenario_id} | PrototypeDetail with provenance/engine/timing/nulls/reasons |
| GET | /{scenario_id}/layers | PrototypeLayers with supported exact-run maps and safe links |
| GET | /{scenario_id}/impact | PrototypeImpact, unchanged registered metrics/nulls/reasons |
| GET/HEAD | /{scenario_id}/assets/{asset_type} | Verified registered supported map bytes |
| GET/HEAD | /{scenario_id}/assumptions | Verified context JSON, <=64 KiB |
| GET/HEAD | /{scenario_id}/quality-report | Verified registered QA artifact; not approval |

Every JSON identity envelope explicitly includes draft, pending, null approved_by/approved_at, production/simulated, uncalibrated, prototype:true, scientifically_validated:false, schema/version/scenario/run/model/input identities, label "Uncalibrated prototype — simulated" and fixed warnings uncalibrated/not_scientifically_validated/simulated. Do not inherit an approved summary model or pass default. List entries contain the same warning identity envelope; list wrapper contains items/pagination.

Detail adds parameters/units, registered impacts, dataset provenance without storage URLs, coverage/run times, explicit engine and source/derivative identities, public timing/arrival meanings, textual limitations/assumptions, unavailable reasons and prototype-only links. Original raw paths/evidence refs/private manifest snapshots are not included in JSON responses. Context/QA downloads remain explicit protected resources. Source provenance references never authorize arbitrary file serving.

Layers include role/format/CRS/unit/nodata/checksum/coverage and prototype URL. Support existing map roles only; never advertise WSE/KML/export-generation/model-running. Initial Part A delivery has four required core roles. Optional existing roles need actual corresponding input evidence, inspection and consistent unavailable-product metadata; none is invented by this design.

All routes require enabled local profile, loopback peer, bounded current admission, registered exact identity/hash, coherent draft/pending production/simulated completed bundle, null approvals, valid verified context and appropriate GIS evidence. Disabled preview returns404 and is excluded from default OpenAPI. Enabled implementation will generate a separate preview-inclusive artifact and must conform to this design; Stage 2 does not change default runtime routing.

Use existing problem+json for404/422/416/500/503. Downloads share full/range/HEAD/If-Range snapshots, deadlines/admission/cleanup, no-store, ETag and correct content types/filenames. Successful downloads carry X-Ukai-Prototype:true and X-Ukai-Scientific-Validation:not_validated. Layer MIME is TIFF or GeoJSON; assumptions is application/json; QA content uses its registered safe content policy. OpenAPI's asset/report binary bodies are transport descriptions, not invented file conversions.

Future tests cover default/enabled schema consistency, all eligibility negatives, path/privacy isolation, pagination bounds, exact-run assets, bytes/hash/context binding, range/HEAD/failure/close behavior and real H02 roundtrip separately from honest mocks. Windows local launcher must bind127.0.0.1 without trusting proxy headers. No frontend is added.
