# Current B1 local status

Updated 2026-10-06 for the combined B1/B2 local handoff. This supersedes older status claims;
`b1-readiness.md` remains a historical report.

Final audit/completion record: [B1 completion and B2 handoff](B1_COMPLETION_AND_B2_HANDOFF.md).

Historical B1-only verification on 2026-10-05: **262 tests passed** (19 final-audit cases added), no skips,
failures or warnings reported; Alembic check found no drift and pip check found
no broken requirements. Step 14 also runs the complete suite from copied source
against a fresh seeded database. See [handoff checklist](b1-handoff-checklist.md)
and [rehearsal runbook](runbooks/handoff-rehearsal.md); earlier step 11/13 evidence
is retained in [verification record](b1-verification-2026-10-05.md).
Current combined B1/B2 source, platform exclusions and delivery checks are recorded
in the verified handoff evidence. See [Team B local checklist](team-b-local-handoff-checklist.md).

## Implemented locally

Docker PostgreSQL/PostGIS; Alembic head `g05b8eab1001`; 16 application tables;
repeatable demo seed; repositories; candidate published manifest validation;
dataset/version provenance; historical events and supplied validation metrics;
run/asset/impact metadata; atomic published-bundle registration; approved-only
reads and revocation; query filters/paging; scenario/asset spatial metadata;
actual synthetic COG/GeoJSON inspection; immutable local files; executable
database/object backups and disposable restore verification.

Step 11 adds broader local acceptance regression coverage. Step 13 consolidates
operations, recovery, version policy, ownership and current limitations. No schema
change is needed for this batch. See [acceptance](b1-acceptance.md) and
[operations](runbooks/b1-operations.md).

## Actual working data, not test fixtures

The working database contains two scenarios, four scenario inputs, one run,
one result asset, one impact summary and one status reading. New dataset/event/
metric/publication/spatial catalogs remain empty. The object store contains 13
files: five earlier local demo files and eight synthetic GIS fixture files.
The GIS manifest remains DRAFT/pending review with no approver; generation does
not write database rows. Test approvals exist only in disposable environments.
Two original placeholder S3 references remain unresolved, not verified remote
objects. No S3 service, Supabase or Tiger Data is necessary for local testing.

## Deferred and external work

- Step 12: Git/CI deliberately deferred. No Git setup, commit, push or merge.
- Step 14: clean B1-only rehearsal completed; B2 HTTP integration is now implemented
  and tested. Team A scientific/joint integration sign-off remains separate.
- Team A: real data, hydraulic/GIS outputs, model validation and scientific approval.
- B2: read-only FastAPI, schemas/OpenAPI, safe assets and API tests are completed
  locally, including readiness/security/storage/performance/quality and packaging.
- Shared: candidate contract freeze, supported real GIS formats and joint acceptance.
- Later external deployment: deployment credentials and agreed identity policy,
  remote storage if chosen, backup scheduling and independent/off-host backup copy.

## Conclusion

Local B1 and B2 deliverables are implemented and verified for trusted-computer
handoff to Team A, excluding Git/CI. Python 3.13 is the confirmed local runtime.
No application login/public infrastructure is required for this scope. Real Team A
outputs, shared contract agreement, actual receiver verification and final combined
model/scientific acceptance remain pending; they are not unfinished B2 endpoints.
