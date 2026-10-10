# A1 → A2 HANDOFF
## Ukai Dam & Lower Tapi Flood Intelligence System

### Project
Hackbios — Ukai Dam & Lower Tapi Flood Intelligence System

### Group A
A1 — Data, Research & Spatial Inputs
A2 — Hydraulic Modelling Specialist

---

# 1. A1 DELIVERY STATUS

A1 has completed the initial verified spatial-data and historical-data package.

All 11 required delivery files passed the final file-existence QA.

---

# 2. VERIFIED DELIVERY FILES

## Terrain

File:
A1_DELIVERY/terrain/verified_dem.tif

Type:
GeoTIFF DEM

Source:
SRTM 1 Arc-Second tiles

CRS:
EPSG:4326

Coverage:
72.0–74.00028 E
20.99972–22.0 N

Resolution:
1 arc-second

Status:
VERIFIED

Important:
This is the verified DEM/data-coverage area. It is NOT the final HEC-RAS computational terrain/domain.

---

## Tapi River

Files:

A1_DELIVERY/river/river_network.gpkg
A1_DELIVERY/river/river_network_wgs84.gpkg

Source:
CWC/NWDP river network

Status:
VERIFIED

Important:
The original source CRS is an unnamed/custom Lambert Conformal Conic CRS.

Do not invent an EPSG code for the original source.

river_network_wgs84.gpkg is the explicit EPSG:4326 version.

The selected source feature represents the Tapi River and is not automatically the final HEC-RAS modelling reach.

---

## CWC Gauges

File:

A1_DELIVERY/river/gauges.gpkg

Verified stations:

1. Ukai Dam
   Station code: 010217016
   River: Tapi
   Latitude: 21.2500
   Longitude: 73.5925

2. Ghala
   Station code: 010217018
   River: Tapi
   Latitude: 21.2972
   Longitude: 73.0253

3. Surat (Seasonal)
   Station code: 010217019
   River: Tapi
   Latitude: 21.1969
   Longitude: 72.8164

Status:
VERIFIED CWC station metadata

Important:
These are gauge locations, NOT complete time-series observations.

---

# 3. REFERENCE CORRIDOR

File:

A1_DELIVERY/river/ukai_surat_reference_corridor.gpkg

Route:

Ukai Dam → Ghala → Surat

CRS:
EPSG:4326

Status:
REFERENCE ONLY

Important:
This corridor was derived from verified CWC gauge coordinates.

It is NOT the final HEC-RAS computational domain.

A2 must determine the actual hydraulic modelling reach/domain.

---

# 4. STUDY BOUNDARY

File:

A1_DELIVERY/boundaries/study_boundary.gpkg

Basis:
Verified DEM extent

CRS:
EPSG:4326

Status:
VERIFIED SPATIAL COVERAGE

Important:
This represents the available A1 DEM/data coverage.

It is NOT the final HEC-RAS 2D computational boundary.

A2 must define the hydraulic domain according to modelling requirements.

---

# 5. HISTORICAL DATA

## 1998

File:

A1_DELIVERY/historical/event_1998.csv

Source:
CWC manual daily river discharge dataset

Status:
OBSERVED / VERIFIED

Contents:
40 verified CWC discharge records covering 15–24 September 1998 at Tapi-related stations.

Important:
This is discharge observation data.

It is NOT a complete hourly flood hydrograph.

Do not create missing hourly values from this file.

Do not label interpolated or synthetic values as observed CWC data.

---

## 2003

File:

A1_DELIVERY/historical/event_2003_reference.csv

Source:
Timbadiya et al. 2014 / existing project reference

Status:
PARTIAL / REFERENCE

Contains:
Event period and cited peak-discharge information.

Important:
Hourly observed stages and release series are NOT available in the verified A1 dataset.

Do not treat this file as a complete observed hydrograph.

---

## 2006

File:

A1_DELIVERY/historical/event_2006_reference.csv

Source:
Timbadiya et al. 2014

Status:
PARTIAL / REFERENCE

Contains:
Event period, peak release/discharge and Nehru Bridge level information.

Important:
Complete hourly series, rainfall and flood raster are NOT available.

Do not treat this file as a complete observed hydrograph.

---

# 6. LAND COVER

File:

A1_DELIVERY/landcover/lulc_bhuvan_retrieved_feature.gpkg

Source:
Bhuvan / NRSC

Layer:
GJ_LULC50K_0506

CRS:
EPSG:4326

Retrieved class:
Agriculture / Cropland

Status:
VERIFIED FEATURE — INCOMPLETE COVERAGE

Important:
Only one actual feature was retrieved.

This is NOT complete Lower Tapi LULC coverage.

Do not assume that this file represents the entire modelling domain.

Bulk WFS retrieval was unavailable/disabled during A1 acquisition.

---

# 7. METADATA

File:

A1_DELIVERY/metadata/data_dictionary.xlsx

Status:
VERIFIED

Contains:
Dataset path, source, CRS, status, description and limitations for the A1 delivery datasets.

---

# 8. WHAT A2 CAN USE DIRECTLY

A2 may use:

1. verified_dem.tif
2. river_network_wgs84.gpkg
3. gauges.gpkg
4. ukai_surat_reference_corridor.gpkg as a spatial reference
5. study_boundary.gpkg as DEM/data-coverage reference
6. event_1998.csv as observed discharge evidence
7. event_2003_reference.csv as partial/reference information
8. event_2006_reference.csv as partial/reference information

---

# 9. WHAT A2 MUST NOT ASSUME

A2 must NOT assume:

- the entire DEM extent is the final hydraulic domain
- the entire Tapi River layer is the modelling reach
- the reference corridor is the final HEC-RAS domain
- the 1998 CSV is a complete hourly hydrograph
- 2003 data is a complete observed dataset
- 2006 data is a complete observed dataset
- the retrieved LULC feature represents the entire Lower Tapi area
- missing historical values can be invented
- synthetic/reference values are observed measurements

---

# 10. A2 NEXT MODELLING TASKS

A2 should now perform:

1. Inspect verified_dem.tif
2. Define the hydraulic modelling reach
3. Clip/prepare terrain for the modelling domain
4. Establish the 2D flow area
5. Define the computational mesh
6. Identify river alignment and hydraulic structures
7. Assign appropriate Manning roughness zones
8. Define upstream/downstream boundary conditions
9. Prepare the dam-break/breach scenario
10. Use available 1998 observations for calibration where applicable
11. Use 2003/2006 reference information only within its documented limitations
12. Produce flood depth, velocity and inundation outputs
13. Export model results for the application/dashboard

---

# 11. A1 → A2 HANDOFF RULE

A1 provides:
DATA + SOURCES + SPATIAL INPUTS + DOCUMENTED LIMITATIONS

A2 provides:
HYDRAULIC MODEL + PARAMETERS + SIMULATION + CALIBRATION + FLOOD OUTPUTS

A1 does not invent hydraulic parameters.

A2 does not silently change the provenance/status of A1 data.

Any derived/interpolated/model-generated value must be explicitly labelled as derived/modelled.

---

# 12. FINAL A1 STATUS

A1 initial data package:
READY FOR A2 HANDOFF

File QA:
PASS — 11/11 files present

Data integrity rule:
NO FABRICATED OBSERVATIONS

End of A1 → A2 handoff.
