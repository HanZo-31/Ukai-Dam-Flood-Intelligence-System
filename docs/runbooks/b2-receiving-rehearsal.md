# Step 18 - clean local B2 receiving and performance rehearsal

This is a reproducible same-host engineering rehearsal, not scientific or
production acceptance. Agreed performance targets and representative Team A
assets are still required for a performance sign-off. Git/CI/container work is
deferred; no final step 19 handoff is performed by this command.

## Reproduce safely

Use the verified Python 3.13 environment to orchestrate the rehearsal. The
existing local PostGIS service must be healthy and the trusted developer must
have permission to create/drop a disposable database. Choose a NEW output name:

```powershell
.\.venv\Scripts\python.exe scripts/rehearse_b2_receiving.py --output data/handoff/b2-receiving-NEW --samples 20 --concurrency 4 --io-mib 16
```

Do not run beside application writes. Before/after inventories must match,
including working rows, sequence state and original object hashes. The script
refuses an existing destination or a path outside data/handoff, accepts only
bounded workloads, and creates only an exact generated `b2_receive_<uuid>` DB.
Cleanup checks that identity again before removing that database, never the
working DB. No private .env is copied or stored in evidence; local credentials
are supplied to child processes in environment variables, not command arguments.
Inherited Python paths/home/virtual-environment selection are removed.

## Clean receiving checks

1. Copy B1's existing safe source allowlist, including B2 code, JSON examples,
   OpenAPI, development requirements and tests. No private configuration, live
   data, virtual environment, caches or Git history is transferred.
2. Create an independent Python 3.13 virtual environment without system site
   packages. Freshly install root runtime pins and B2 development requirements;
   check dependency consistency and record interpreter/package versions.
3. Create an empty database from template0, enable PostGIS, apply all migrations
   from the copy, check all 16 tables and model/schema parity.
4. Seed twice, proving identical rows, sequence values and object hashes in the
   receiving environment.
5. Run the entire B1+B2 test suite from the copy using the new interpreter.
   Disable bytecode/pytest caches; prove seeded baseline and copied source stay intact.
6. Check saved OpenAPI freshness/conformance from the receiving copy.
7. Use B1's actual GIS-aware registration CLI to import one clearly synthetic
   historical replay, three hypotheticals and a hidden draft. Include an actual
   explicit GeoJSON derivative; do not substitute extent links or invent KML.
8. Start the actual API on an owned loopback ephemeral TCP socket. Verify all
   eight endpoints, parameters/units/nullable impacts/provenance, paging, mode
   and publication rules, real artifact hashes, COG ranges/HEAD, assumptions,
   exports, historical replay links, persisted demo status and served docs parity.
9. Record bounded HTTP and adapter IO performance, proving read-only requests
   preserve the receiving database.
10. Test revocation and tampering only in the disposable fixture; issued links
    must fail safely. Restore deliberately altered fixture bytes.
11. Stop the owned API server, verify source integrity, remove only the generated
    database and prove working database/object preservation.

The test-only reviewer declaration proves engineering wiring, not human or
scientific approval. Four scenarios share synthetic GIS assets; they are not
four distinct validated hydraulic models.

## Performance method and acceptance boundary

Twelve HTTP workloads cover all eight JSON endpoints, full/range/HEAD COG reads
and GeoJSON export download. Each has three warmups, then 20 sequential samples
and 20 samples at concurrency 4 by default. Results include nearest-rank
p50/p95/p99/max latency, unexpected status count and bounded concurrent-batch
requests/second. Requests use actual localhost TCP and consume the response body;
they are not in-process TestClient timings. This is a warm-cache, same-machine,
small-sample baseline, not a sustained-load or production capacity test.

Tiny valid synthetic COGs support the HTTP fixture. A separate default 16 MiB
opaque synthetic blob measures verified local disk-snapshot IO without being
registered or described as a valid COG. One warmup and five recorded verifications
are used; each snapshot is streamed, hashed and closed. Throughput uses logical
source MiB divided by verification time, not total physical disk IO. Peak RSS,
peak temporary-disk use and real large-COG/network behavior are not measured.

No latency target is invented. `performance_signoff` stays pending until owners
agree p95 limits by workload, error budget, concurrent users, representative
catalog/COG sizes, cache assumptions, duration and infrastructure. Then rerun
the agreed workload against approved representative assets. KML GIS validation,
scientific quality thresholds, security/CORS and remote storage remain separate.

## Evidence and retained files

`receiving.json` records stages, fresh interpreter/package inventory, source
and object hashes, the copied-suite summary, preserved-working-data flag and
removed-disposable-database flag. `http-performance.json` records actual HTTP
acceptance and raw aggregate timing/throughput results, with explicit scope limits.
Check result=passed, every stage passed, source_copy_preserved=true,
working_data_preserved=true, disposable_database_removed=true and
http_performance.server_stopped=true before accepting the engineering run.

The receiving source copy, new virtual environment and synthetic objects are
retained under the chosen output folder for review. No private .env is included.
The recorded temporary DB has been removed; do not point a future run at it.
Choose a new folder to rerun. This is not an archive to deploy blindly on another
host, a Docker installation/build test, or the final handoff package.

Unit safety checks:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_receiving_rehearsal.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Receiving-test success does not authorize production deployment or complete
joint acceptance. Treat performance as measured-but-unapproved until targets
and real scientific assets are supplied by their owners.
