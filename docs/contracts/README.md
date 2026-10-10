# Published scenario contract — candidate V1

Status: **implemented candidate for Part A/B1/B2 review**, not a jointly frozen
contract. Contract validation, local published-bundle registration and
approval-aware repositories are implemented. See
[registry contract](published-registry.md) for provenance, trust and production
GIS gates. No numerical model or FastAPI route is introduced here.

Files:

- `published-scenario.schema.json`: generated JSON Schema (Draft 2020-12).
- `published-scenario-v1.md`: field meanings, units, references and acceptance gates.
- `examples/published-scenario-demo.json`: metadata-only synthetic example.
- `CHANGELOG.md`: contract changes and compatibility notes.
- Executable validation: `services/api/app/published_contract.py`.

The candidate preserves the blueprint's `assets` role-to-path dictionary,
`summary`, `status`, and `quality` blocks. Additions make the blueprint's shared
requirements explicit: checksums, units, dataset provenance, run timestamp,
temporal coverage, data labels and contract version. The bare blueprint example
is illustrative and does not contain all these additions; do not register its
placeholder zeroes as scientific values.

Run metadata validation:

```powershell
.\.venv\Scripts\python.exe scripts\validate_published_manifest.py docs\contracts\examples\published-scenario-demo.json
.\.venv\Scripts\python.exe -m pytest tests\test_published_contract.py -q
```

The command checks schema and semantic rules and explicitly does not open or
verify asset bytes, register database rows, authenticate an approver, or claim
scientific validity. Later registration must perform those acceptance checks.
`--allow-draft` enables review of draft/rejected metadata without publishing it.

Regenerate the checked-in schema after a reviewed contract change:

```powershell
.\.venv\Scripts\python.exe scripts\export_published_schema.py
```

Tests detect divergence between the JSON Schema and typed contract. General
JSON Schema tools catch field/type rules and the approved-state condition;
the executable validator also checks cross-field semantics listed in the spec.

## Existing interfaces

`ScenarioManifest` and `scripts/register_scenario.py` currently describe the
legacy input/demo registration flow. They have not been silently switched to
this published-result contract. The separate `PublishedScenarioManifest`
provides the implemented candidate precomputed-result boundary. Existing run CLI
behavior does not define B2's role: B2 owns the read-only FastAPI service.

## Review and adoption

Part A reviews scientific units, provenance and completeness; B1 reviews
catalog/asset validation; B2 reviews API read requirements. Open questions are
recorded in the spec rather than silently presented as agreed decisions.
There is currently no configured Git repository/remote, so no shared-contract
pull request can be created here yet. These local artifacts are ready to form
that review once the repository is established. Implementation is additive;
applied migrations and existing demo contracts are untouched.
