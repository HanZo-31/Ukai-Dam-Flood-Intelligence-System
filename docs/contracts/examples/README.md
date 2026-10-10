# Contract example scope

`published-scenario-demo.json` is **metadata only**. Its numeric values, dates,
reviewer, licence label and repeated-digit checksums are invented schema
examples. The referenced rasters, vectors, quality report and source artifact
are not provided by this example. The checksum strings demonstrate syntax;
they are not asserted to match real file bytes.

`status: approved` and the named reviewer only exercise the approved-state
validation branch. They do not assert team sign-off or scientific approval.
`data_mode: demo` and `data_kind: demo` prevent presenting this example as real
hydraulic output. Nullable exposure values remain unavailable rather than zero.

The schema-only CLI accepts its metadata while stating that files are not
verified and nothing is registered. A later real asset-verification gate must
reject it until a genuine checksummed bundle exists. The existing local demo
with actual CSV bytes remains separate and unchanged. Creating tiny valid GIS
assets and a registerable published fixture is a later checklist step.
