# Step 4 — reliable local storage/downloads

Scope: the existing local-file object store and hardened Linux API, not S3/public
hosting. B1's schema, publication rules, immutable store API and scientific
contracts remain unchanged. No new public keys, accounts or external services.

## Resource policy

The supported large-file baseline uses 1 GiB private `/tmp` tmpfs and a 2 GiB API
memory limit; all capabilities stay dropped, root/object mounts stay read-only and
only loopback is published. Default maximum artifact: 512 MiB, verification budget:
60 seconds, scratch safety reserve: 8 MiB. Oversized objects, insufficient space,
an occupied admission lock or failed IO produce a safe 503 before response bytes.
This is fail-closed backpressure, not a guarantee that every simultaneous request
is admitted. Liveness and small requests remain independently usable.

| Setting | Default | Allowed range / purpose |
| --- | --- | --- |
| `B2_DOWNLOAD_MAX_BYTES` | 536870912 | 1 MiB–8 GiB per object, including HEAD/ranges/discovery |
| `B2_DOWNLOAD_VERIFY_SECONDS` | 60 | 1–300; cooperative deadline between local reads and after verification |
| `B2_DOWNLOAD_STREAM_SECONDS` | 300 | 1–3600; total ASGI response deadline, including blocked/slow sends |
| `B2_TMPFS_SIZE` | 1g | Compose scratch size; set with measured artifact/concurrency requirements |
| `B2_MEMORY_LIMIT` | 2g | Compose memory limit; tmpfs counts against it, so allow interpreter/IO headroom |
| `B2_SCRATCH_MIN_BYTES` | 8388608 | Shared download/readiness reserve, 1 MiB–1 GiB; forwarded by Compose |

Raising only the object limit does not provide enough scratch or RAM. Budget at
least simultaneous full verified representations plus reserve, with additional
memory for the interpreter and IO. Do not configure unsupported larger capacities
without repeating the rehearsal. Team A has confirmed files exceed 128 MiB, but
their exact maximum and agreed concurrency/SLA are still required for final sizing.

## Integrity and lifecycle

Every request rechecks B1 approval/mode scope and verifies the complete source SHA256
before publishing bytes. A response streams only its private disk-backed snapshot,
in 1 MiB chunks. A source changed during verification, missing/unreadable object,
hash mismatch, growth/truncation, short write/flush failure or exhausted verification
budget is rejected. A changed original cannot alter an already verified snapshot.

Linux uses directory-descriptor traversal with no-follow/nonblocking opens and
rejects special files, avoiding parent/final symlink swaps and blocking FIFOs.
Snapshot admission is serialized across workers through one private scratch lock;
`posix_fallocate` reserves real space, not sparse file length. Unsupported allocation
filesystems fail safely. Windows development has conservative per-process admission;
the multi-worker hardened release profile is Linux, not arbitrary Windows shares.

Snapshot cleanup runs even on ASGI send failure, cancellation before streaming
starts and client disconnect. EOF before declared length aborts the connection;
an async total streaming deadline also releases snapshots held by stalled clients.
once response headers are sent, it is impossible to replace a stream with JSON
503, so clients must treat truncated transfers as failed and verify checksum/length.
Slow transfers release catalogue dependencies before body streaming, preventing
idle database transactions from surviving for a download's entire lifetime.

HEAD, range and export discovery still verify/copy the entire artifact. This trades
extra IO for strict per-request integrity; it is not an optimized CDN/object-store
range adapter or a promise of interactive large-map latency. No cache hides tampering.
The verification deadline cannot interrupt a kernel IO syscall already stalled;
network filesystems/remote adapters are not covered by this local-file rehearsal.

## Realistic receiving rehearsal

Rebuild runtime and verification targets, then use a new output directory:

```powershell
.\.venv\Scripts\python.exe scripts/rehearse_b2_container.py --large-assets --output data/handoff/b2-step4-NEW
```

The probe generates three aligned, one-band 8192×8192 float32 COGs with units, CRS,
coverage and synthetic tags. Uncompressed tiled COGs with overviews exceed 300 MiB
each; these are real strict-valid COGs, not renamed blobs. The actual B1 CLI imports
them with its unchanged GIS inspector and an explicit pixel budget. The inspector
works block-wise and validates every raster. No real scientific approval is claimed.

The B1 import command now offers `--max-raster-pixels`; its default remains
20 million. A receiver expecting 8192×8192 assets can explicitly supply
`--max-raster-pixels 67108864` after agreeing the inspection budget. The CLI accepts
1–1,000,000,000 pixels; that bound is not an agreed scientific or performance limit.
It does not skip GIS checks or invent KML support.

The isolated probe checks full checksum downloads, HEAD, start/middle/end ranges,
invalid ranges, two simultaneous slow TCP readers, safe rejection of a third,
concurrent checksum integrity, database-connection release, three client aborts,
scratch recovery, missing/corrupt/truncated/unreadable objects and byte restoration.
The surrounding rehearsal retains readiness/outage/security/restart/shutdown tests,
records memory peak/OOM counters and validates B1 preservation/owned-resource cleanup.
Unit tests inject read/write/flush/disk/time/send faults and cross-worker lock/race
cases. Windows explicitly skips four Linux-only cases; Linux verifies them.

Completion requires passing **fresh** host, container and renewed exact-image
vulnerability evidence, not merely code creation or a previous Step 3 result.
Failed/intermediate rehearsals are retained; only generated temporary resources are
removed. The final evidence is summarized in the workspace Step 4 completion report.

Final local engineering evidence passed on 2026-10-06: 678 Windows tests (four
Linux-only skips), 681 Linux tests (one host-only exclusion), real 357,571,424-byte
COG downloads and failure recovery, complete scratch recovery and zero OOM events.
The ASGI harness also verifies a stalled-body-send timeout; real TCP checks cover
client aborts/concurrency and byte integrity. Exact final runtime:
`sha256:532d5f93799126b26a349b8f5d699c8033d6c6bf1e414ceb45b54338052dc30d`.
Its renewed unsuppressed vulnerability/applicability gate passed, preserving the
same scoped eight high OS advisory dispositions as Step 3. No next step started.
Final Team A size/concurrency/formats/SLA agreement remains outstanding.

References: [Python allocation and descriptor APIs](https://docs.python.org/3.13/library/os.html),
[FastAPI early dependency release](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#early-exit-and-scope),
[GDAL COG format](https://gdal.org/en/stable/drivers/raster/cog.html).
