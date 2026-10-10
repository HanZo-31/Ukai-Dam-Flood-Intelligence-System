# Claims sheet (Team 1) — claim → source → limit → allowed wording

| Claim | Source | Limit | Allowed wording |
|---|---|---|---|
| Four stored HEC-RAS reference scenarios can be explored | Package receipts and UI | Simulated, uncalibrated, not scientifically validated; 2006 is a reconstructed replay | "HEC-RAS provides the reference library." |
| The timeline shows the area reached by elapsed model time | Stored arrival_time.tif (minutes, hourly) | Model time, not a clock; timezone unverified; valid-arrival footprint differs slightly from the wet extent | "Area reached by elapsed model time." |
| Depth/velocity under the timeline are maximum-over-run | max_depth / max_velocity rasters | Not changing water levels | "Maximum values, revealed as each cell is reached." |
| Candidate flooding differs from baseline by X km² | compare-v1 on the stored rasters | Different hydrographs; wet = depth > 0.1 m; velocity not compared | "Newly flooded area in the candidate scenario, by this definition." |
| Zones are listed for review | zone-rule-v1 | 5 km coordinate squares, not districts; no population/buildings/roads; ordering is not an evacuation order | "Priority for review." |
| What-if selects a stored reference | Candidate service contract 1.0.0 | Not computed; not ML; not interpolated; lookup time ≠ model run time | "This looks up an existing HEC-RAS result." |
| Rapid model / ML prediction | NOT demonstrated | Acceptance gate closed (one intermediate holdout) | Do not claim a live engine, "seconds", or a validated surrogate. |
| Population, roads, buildings, villages | NOT available | No verified exposure data supplied | Say "not available". |
