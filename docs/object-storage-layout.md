# Object-storage layout

Current B2 scope (2026-10-06) is local files only. The S3 layout below describes
future logical storage possibilities, not a configured backend or a requirement
to add buckets/keys now. For Step 5's proposed portable local key/reference
convention and pending team decisions, see
[the storage/input-output agreement candidate](contracts/b2-storage-io-agreement-candidate.md).
No existing files/URIs are moved by that proposal.

Use a bucket per environment, for example `ukai-demo` and `ukai-production`. Keys are append-only and use the scenario ID as the boundary:

```text
s3://<bucket>/reference/<dataset-version>/...
s3://<bucket>/scenarios/<scenario-id>/manifest.json
s3://<bucket>/scenarios/<scenario-id>/inputs/<input-name>
s3://<bucket>/scenarios/<scenario-id>/runs/<run-id>/logs/<name>.log
s3://<bucket>/scenarios/<scenario-id>/runs/<run-id>/outputs/<asset-name>
```

`scenario_inputs.storage_uri` must point to an immutable input key. `result_assets.storage_uri` must point to the final output key. `processing_runs.log_uri` may point to a run log. Registered inputs/outputs need verified `sha256:<hex>` checksums supplied by the publishing/importing team. B2 reads precomputed approved outputs.

Do not put access keys, personal data, or mutable `latest` aliases in the database. Readers should receive scoped, time-limited object-store access outside this schema.

## Verified local demo mode

Published imports use an explicit trusted bundle root within this store.
Inputs may refer to separately registered `datasets/<dataset-id>/<version>/`
keys. Outputs, assumptions and quality reports must be checksummed; import
never overwrites files. See `docs/contracts/published-registry.md` for the
local-byte gate, production GIS hook and approved-only reads. B2 must convert
internal file URIs to safe served links, not return raw paths.

`LocalObjectStore` implements the same relative key layout under
`data/object-store/` (or `OBJECT_STORAGE_ROOT`). Its persisted URIs are absolute
`file://` references. Objects are atomically published and immutable: the same
bytes can be published again, while changed bytes under an existing key fail.
Registration requires every input to exist and match its SHA-256 checksum.
Output registration performs the same checks before changing database state.

`scripts/seed_db.py` publishes two synthetic CSV inputs, assumptions, one
synthetic CSV output, and the canonical manifest for `demo-monsoon-local-002`.
It computes actual checksums and refuses inconsistent existing records.
These are contract fixtures, not computed flood predictions.

An S3 bucket/backend and credentials have not been provided. S3 URI syntax can
be parsed, but the local adapter explicitly refuses to claim remote objects are
verified. A production S3 adapter, bucket versioning, access controls, and remote
recovery checks are separate deployment acceptance requirements.
