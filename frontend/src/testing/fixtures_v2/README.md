# SYNTHETIC engineering fixtures — not simulations

These small 4×4 grids are HAND-DESIGNED TEST DATA. No solver ran. They do not depict actual Ukai flooding. extent.geojson is a projection-test bounding polygon, NOT a real depth-derived wet outline. Synthetic Result's computed=true/timing/provenance fields exercise a future response schema only.

TIFF: float32, one band, EPSG:32643, 100 m cells, upper-left (270000,2360000), nodata=-9999, classic little-endian tiled256 Deflate predictor1. Four files are independently decoded by the CURRENT browser-compatible TypeScript reader. Arrays and hand-authored oracle are in arrays-and-oracle.json; independent NumPy enumeration checks the counts/statistics before delivery.

Each cell is 10,000 m² =0.01 km². Threshold is depth>0.1. Confirmed gained/lost cells require known validity in BOTH depth grids. Recorded-only footprints include unmatched wet coverage and must be displayed separately. Paired arrival values are minutes. Four paired cells are deliberately below the 50-pair timing-rank gate, so this small example MUST show unavailable timing priority. Claude must add a larger independent test case for eligible timing ranks.

The fixture is not the operational H02 grid. The v2 schema allows small dimensions for isolated tests; operational packaging/consumer guards must require exact reference metadata. Do not allow this synthetic config/fixture to enable a real service capability. Route-to-file mappings in a test transport follow contract/examples.json; never derive filesystem paths from unvalidated caller URLs.
