# Prototype context field guide — 1.0.0

Written 7 October 2026; Stage 2 verification/delivery completed on the date recorded in its evidence. The JSON schema and pure Python contract are authoritative together; JSON Schema alone does not express every semantic/binding rule.

| Group | Fields / required meaning |
| --- | --- |
| Identity | schema_version=1.0.0; exact derivative scenario_id, run_id, model_version, input_dataset_version, time_coverage; explicit scenario_family |
| Status | calibration_status=uncalibrated; scientific_validation_status=not_validated; prototype is strict boolean true |
| engine | name, software_version, nullable build/source_checksum and corresponding unavailable reasons; a reason is present exactly when its value is missing |
| original | original draft status, original type, not_validated, original scenario ID, portable manifest_reference, raw manifest_checksum and nonempty source asset_checksums keyed by portable original file references |
| forcing | hypothetical_assumption or reconstructed_historical; assumed source label; description, exact dataset_id/version list, provenance references and uncertainties |
| arrival | min, simulation_start, reference_timestamp matching coverage start, threshold_m=0.1, positive temporal_resolution_minutes, original_unit=h, conversion_factor=60, valid_cells_times_60_nodata_preserved, original_reference/checksum, evidence references |
| timing | time_step_meaning=result_output_interval; positive integer result_output_interval_minutes matching manifest timestep; computation_step_seconds, forcing_interval_minutes and mapping_interval_minutes separately nullable with exact missing reasons; coverage_clock_kind, timezone_convention and evidence references |
| limitations | explicit calibration, terrain_bathymetry, vertical_datum and exposure text plus nonempty source_uncertainties |
| assumptions | nonempty bounded plain-text list, never fabricated science |
| unavailable_products | supported product/measurement keys with reasons; nullable summary/breach values need reasons and measured values cannot simultaneously be called unavailable |
| preserved_wse | null if absent; otherwise portable original reference/checksum, unknown vertical datum and reason_not_registered; source checksum must match original inventory and WSE needs an unavailable-product reason |
| derivation | processor/version, exact source and derivative scenario/run identities, unique named operations (including arrival conversion and window alignment), parameters/method text and evidence references |

All objects forbid extra fields. Lists/strings/maps are bounded by the actual schema; plain text rejects markup/control characters. Evidence/source references are relative POSIX keys, not URLs/Windows paths, and are not automatically fetched or served. Context bytes <=64 KiB. Manifest/context checker permits manifest <=1 MiB as an operational checker limit, not a changed PublishedScenarioManifest schema.

Portable original/evidence references describe the companion handoff layout: keep original and evidence files alongside the derivative as agreed with A2, with no traversal. The metadata checker verifies string structure and source/hash cross-links only; it does not open those original/evidence files or prove their truth. Real receipt checks verify them independently.

Prototype metadata binding requires four core map roles and permits optional existing duration/hazard/exposure roles only with corresponding actual manifest metadata and consistent availability reasons. It rejects KML/WSE/export roles for this preview profile, without changing the underlying published contract's allowed roles.

The default checker requires production/simulated draft/pending with null approvals. Forcing dataset references must match manifest entries labelled assumed for this delivery's hypothetical/reconstructed forcing. Other input datasets retain their actual source labels. Hypothetical time coverage is model_clock. No clock, run time, licence, configuration or interval is inferred from filenames or file timestamps.

The synthetic demo example is usable only with --synthetic-example. It retains demo labels, placeholders for unavailable source/GIS hashes and clearly synthetic engine/provenance text. Only its context-byte checksum is real. It is metadata-only and cannot be admitted or imported as actual Part A output. Do not copy its facts, fictional evidence refs or numbers into a real manifest.

Neither schema parsing nor a checker success grants DB import, preview admission, GIS approval or scientific acceptance. Actual preview later must use the default genuine profile, trusted verified snapshots, structured GIS evidence and exact operator admission.
