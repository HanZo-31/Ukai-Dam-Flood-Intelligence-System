# Published-result contract changelog

## 1.0.0 candidate — 5 October 2026

Final B1 audit: revalidated legacy input/completion objects at write boundaries;
added internal completion savepoint, supported 150-character run IDs and failure
state checks; recognized feature-level synthetic GIS markers; sanitized internal
CLI failures; hardened source packaging and backup metadata rejection; restricted
the local DB port and bounded IPv4 connections. Candidate published schema and
applied migration revisions remain unchanged. See ../../docs/b1-handoff-checklist.md.

- Preserve the blueprint's published `status`, `assets`, `summary`, `quality`
  and assumptions fields.
- Define schema version, producing-run identity/time, scientific data labels,
  explicit units, dataset provenance, asset coverage and SHA-256 metadata.
- Support bundle-relative paths and immutable file/S3 references.
- Define approved-state validation and non-publishable draft/rejected states.
- Provide generated JSON Schema, executable semantic validation, metadata-only
  synthetic example, CLI, and acceptance/rejection regression tests.
- Additive compatibility: no changes to existing input-manifest/run contracts,
  registry behavior, database rows, seeds or applied migrations.

This is a local candidate pending joint Part A/B1/B2 review. It is not a frozen
API or signed scientific approval. The local database importer and GIS checks
are implemented in subsequent batches without changing schema version 1.0.0;
the local handoff rehearsal is documented in ../runbooks/handoff-rehearsal.md. Future breaking
changes need a reviewed version change, migration/compatibility notes and tests.
