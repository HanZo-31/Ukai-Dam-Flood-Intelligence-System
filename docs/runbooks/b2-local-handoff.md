# B2 refreshed local engineering handoff — readiness item 6

Current entry point, 2026-10-06. The earlier Step 19 archive remains historical
and is not overwritten. Item 6 refreshes source, setup instructions, evidence and
pending gates. It does not mean production/scientific acceptance or receipt.

## Backend scope

B2 is the read-only FastAPI layer under services/api, reusing B1's migrations,
models, repositories, publication verification and local object store. Public
schemas live in app/api_schemas, avoiding B1's app/schemas.py. Step 3's authorized
shared upgrade is included: FastAPI 0.142.2, Starlette 1.7.0 and required
opentelemetry-api 1.45.0, without an exporter. Step 4's B1 CLI supports an explicit
larger-raster inspection budget; its default is unchanged. Core B1 contracts,
scientific pins and working data were preserved, but do not claim no shared file
has ever changed.

The eight business GET endpoints cover health, scenario list/detail/layers/impact,
historical events, demo current status and registered export discovery. Supporting
asset/assumptions GET/HEAD routes provide verified downloads and single ranges.
See [API usage](b2-api-usage.md), [API candidate](../contracts/b2-api-v1-candidate.md)
and docs/contracts/b2-openapi-v1.json. Examples are synthetic, not approved science.
The operational /readyz is separate from the business contract.

## Contents and trust

- source/: current combined B1/B2 source using B1's existing allowlist, including
  migrations, API, tests, scripts, contracts and container files.
- evidence/: fresh item-6 Windows/source preservation and same-host Linux checks;
  prior item-5 raw performance/container/host records; exact-image security gate,
  unsuppressed OS findings, complete Python audits and independent quality evidence.
- manifest.json: SHA-256/size inventory, evidence_profile=refreshed and explicit
  separation of local checkpoints from unaccepted joint gates.
- README.md: receiving entry point and scope.

Private .env, live DB/backups/object data, virtual environments, caches, Git history
and key directories are excluded. .env.example contains public development defaults,
not deployment credentials. No image tar or real Team A dataset is included.
Python/Docker/dependency access must be separately provisioned: not an offline installer.
Hashes detect corruption, not sender authenticity. Obtain the archive SHA-256
through a trusted team channel and inspect the ZIP before extracting to a new folder.
Never execute an untrusted package merely to verify it. From an already trusted
installed project/environment:

```powershell
.\.venv\Scripts\python.exe scripts/package_b2_handoff.py --check "C:\receiving\B2-local-handoff-step6.zip"
```

## Evidence chronology

Step 18's clean-copy/new-Python-environment run passed 488 tests. That run
**predates Step 19** and later hardening; it is not a new-host receiving result
for this archive. Item 5 passed 712 Windows / 715 Linux tests with documented
platform exclusions and measured 19,017 requests. Its provisional local targets
passed: worst JSON p95 199.209 ms, mixed 341 MiB download 9.238 s, HEAD/range
1.103/1.063 s, zero unexpected errors/OOM. See [methodology](b2-performance-resource-testing.md).

Item 6 records fresh counts/source hashes in B2-step-6-test-evidence.json and
same-host Linux checks in B2-step-6-container-verification.json. These verify
the delivered source. After the quality follow-up changed runtime source, its new
image was required to have matching fresh performance/container/security evidence.
Evidence filenames are stable logical slots; inspect their timestamps and image
identities for the current run. Original item-5/6 files outside this new archive
remain historical and are not overwritten. The verifier compares source with
the exact current measured image, not an older image. The verification image is
not the deployable runtime. Packaging itself is not a new benchmark.

Raw OS findings remain included. Eight high advisories (44 package/advisory pairs)
have expiry-bound applicability dispositions; zero critical/Python findings were
reported. Not a vulnerability-free certificate. Re-review before 2026-11-06 or
earlier after changed code/profile/dependencies/base/advisories/exposure. A rebuilt
image requires testing/audit of its actual identity, not inherited approval.

## Receiving sequence

1. Review manifest, evidence chronology and [open gates](../b2-pending-items.md).
2. Follow [receiver setup](b2-receiver-setup.md) in a new folder. Do not test,
   migrate or seed production or silently reuse another B1 stack.
3. Choose Windows development or the hardened Linux container. Keep loopback.
   Liveness=200 alone does not establish readiness.
4. Run combined tests, dependency checks and OpenAPI freshness/conformance;
   repeat agreed container/storage/performance checks on the receiving profile.
5. Fill [receiver record](b2-receiver-acceptance.md) with actual package/image,
   environment, results and open gates. No receiver is pre-assigned or acknowledged.

## Rebuilding the refreshed package

Prepare a NEW evidence directory containing the filenames in
scripts/package_b2_handoff.py REFRESHED_EVIDENCE, except the current test report
generated below. Copy only named sanitized records, not private logs or a whole
workspace. Copy the fresh container report as B2-step-6-container-verification.json;
retain item-5 raw measurements with their original provenance. Never overwrite
the previous evidence. From a trusted current project:

```powershell
.\.venv\Scripts\python.exe scripts/verify_b2_handoff_source.py --evidence-dir "C:\receiving\evidence-NEW" --runtime-baseline "C:\trusted-evidence\B2-step-3-remediation-verification.json" "C:\trusted-evidence\B2-step-4-verification.json" --foundation-baseline "C:\trusted-evidence\B2-step-19-test-evidence.json"
.\.venv\Scripts\python.exe scripts/package_b2_handoff.py --profile refreshed --output "C:\receiving\B2-handoff-NEW" --evidence-dir "C:\receiving\evidence-NEW"
```

The verifier compares every shipped application file with the exact measured
image, checks chronological dependency/build baselines, runs complete host checks
and freezes source hashes. It requires Docker, but reads no image environment,
private settings or live objects. Packaging refuses
stale/failed/missing/changed evidence, changed release/benchmark identity, expired
applicability review, existing outputs, unsafe members and linked source. Output
must be outside the source project. The default historical profile is retained
only for Step 19 compatibility: use --profile refreshed for current delivery.
Neither operation approves data, writes publication records or signs an image.

## Acceptance boundary

Local correctness lint/gradual B2 type checks are now required independently;
see [scope and privacy](b2-local-quality.md). Step 17 Git/CI remains deferred. Step 18 formal
performance sign-off needs representative approved assets and owner-agreed targets.
Step 20 requires approved Team A outputs -> manifest -> B1 verification/catalogue
-> B2 JSON/downloads, joint acceptance and actual receipt. An agreed subset can
be tested before Team A finishes its entire project. Storage namespace/format
maxima/reviewer-identity policy and KML validation if required need coordination.

Local-only hosting is intentional: no login, public keys, public service or external
TLS was added. Those are later external-exposure decisions, not local merge
requirements. Demo status is not live; B2 does not compute hydraulics/exposure.
Item 6 closes the refreshed delivery task only when its archive checks pass,
not every external acceptance gate.
