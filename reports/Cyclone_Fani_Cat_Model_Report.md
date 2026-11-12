# Catastrophe Risk Modeling Technical Report: Cyclone Fani (2019) Coastal Odisha Portfolio

**Platform Framework**: ETH Zurich CLIMADA & Oasis LMF Architecture  
**Hazard Peril**: Tropical Cyclone (Wind & Gust)  
**Historical Event**: Cyclone Fani (May 2019, Bay of Bengal, Landfall near Puri, Odisha)  
**Exposure Scope**: 3,500 Risk Locations Across Coastal Odisha  
**Currency**: Indian Rupee (INR)

---

## 1. Executive Summary & Headline Actuarial Metrics

Tropical Cyclone Fani (May 2019) was an Extremely Severe Cyclonic Storm (Category 4/5 equivalent on the Saffir-Simpson Hurricane Wind Scale) with peak sustained 1-minute surface winds of 115–135 knots (215–250 km/h) and a minimum central pressure of 932–937 hPa. The storm made landfall on May 3, 2019 near Puri, Odisha, tracking directly through Khordha (including the capital city Bhubaneswar) and Cuttack before traversing the northern coastal districts into West Bengal.

| Metric | Portfolio Value (INR) | Normalized Value |
| :--- | :--- | :--- |
| **Total Insured Value (TIV)** | ₹11,095.49 Crores | 100.00% |
| **Total Ground-Up Loss (GUL)** | ₹968.62 Crores | **8.73% Loss Cost** |
| **Total Gross Insured Loss** | ₹728.48 Crores | **6.57% of TIV** (75.2% of GUL) |
| **Policyholder Retained Loss** | ₹240.14 Crores | **2.16% of TIV** (24.8% of GUL) |
| **Peak Portfolio Sustained Wind** | 187.2 km/h | Category 3/4 Eye-wall Peak |
| **Mean Portfolio Damage Ratio** | 9.70% | Non-linear composite damage |

---

## 2. Exposure scrubbing & SQL Hygiene (`sql/` & `src/sql_scrubber.py`)

A synthetic portfolio of 3,545 records representing real-world commercial, residential, industrial, and agricultural properties across coastal Odisha was ingested into SQLite (`data/exposure.db`). 

### Data Cleansing Interventions:
1. **Deduplication**: 45 duplicate policy entries were detected and purged, logging retention rationale to `scrubbing_audit_log`.
2. **Financial Value Scrubbing**: 30 records with invalid values (negative, zero, or erroneous ₹99 Cr outliers) were identified. Outliers were imputed using robust district/occupancy medians.
3. **Construction Standardization**: Messy colloquial strings (`r.c.c.`, `tin roof`, `cgi sheet`, `straw thatch`, `peb`, `brick`) were standardized to CRESTA/CLIMADA/Oasis codes:
   - `RCC` (Engineered Reinforced Concrete Frame)
   - `MASONRY` (Confined Brick Masonry)
   - `STEEL_PEB` (Pre-Engineered Metal Buildings)
   - `TIN_ROOF` (Unreinforced Masonry with CGI/Asbestos Sheet Roof)
   - `KUTCHA` (Non-Engineered Thatched/Mud/Wood Construction)
4. **Spatial Quarantine**: 139 records with missing or inverted coordinates were flagged for geocoding resolution.

---

## 3. Spatial Geocoding & Coastal Proximity (`src/geocoder.py`)

Geocoding was performed using `geopy` (Nominatim API) with an embedded high-resolution administrative gazetteer for Odisha pin codes and district centroids:
- **100% Coordinate Resolution**: All 139 quarantined records were successfully positioned with WGS84 coordinates.
- **Coastal Proximity**: Distance-to-coast was calculated for each asset using Haversine projection against Odisha's coastal boundary. 
- Over 62% of portfolio value sits within 25 km of the Bay of Bengal coastline, highlighting high exposure vulnerability.

---

## 4. Hazard Modeling: NOAA IBTrACS & Holland (1980/2010) Radial Wind Field

Historical 3-hourly waypoint data for Cyclone Fani was obtained from NOAA's IBTrACS dataset (May 2–4, 2019):
- **Holland Parametric Radial Profile**:
  $$V(r) = \sqrt{\frac{B}{\rho_{air}} \left(\frac{R_{max}}{r}\right)^B \Delta P \exp\left(-\left(\frac{R_{max}}{r}\right)^B\right) + \left(\frac{r f}{2}\right)^2} - \frac{r f}{2}$$
- **Asymmetric Vector Addition**: Forward storm translation velocity was added, capturing the intensified right-front quadrant.
- **Surface Reduction Factor**: 10m surface roughness reduction factor (0.82) was applied.

---

## 5. Loss Summaries by District & Construction Type

### A. District Breakdown
| District | Asset Count | Total TIV (₹ Cr) | Mean Wind (km/h) | Mean MDR | Ground-Up Loss (₹ Cr) | Loss Cost (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Khordha** | 988 | ₹3,082.21 | 158.7 | 15.04% | **₹440.16** | **14.28%** |
| **Puri** | 768 | ₹2,246.13 | 155.6 | 13.78% | **₹313.11** | **13.94%** |
| **Cuttack** | 540 | ₹1,531.21 | 142.1 | 7.44% | **₹123.59** | **8.07%** |
| **Jagatsinghpur** | 417 | ₹1,468.16 | 126.4 | 5.19% | **₹40.55** | **2.76%** |
| **Kendrapara** | 291 | ₹1,207.10 | 116.2 | 3.32% | **₹30.33** | **2.51%** |
| **Ganjam** | 195 | ₹530.74 | 129.2 | 5.29% | **₹16.49** | **3.11%** |
| **Bhadrak** | 154 | ₹580.79 | 107.0 | 1.20% | **₹2.52** | **0.43%** |
| **Balasore** | 147 | ₹449.17 | 98.3 | 0.89% | **₹1.88** | **0.42%** |

*Key Insight*: Khordha (Bhubaneswar) and Puri bore 77.8% of the entire portfolio loss due to direct eye-wall traversal and high asset concentration.

### B. Building Construction Vulnerability Breakdown
| Construction Code | Asset Count | Total TIV (₹ Cr) | Mean MDR | Ground-Up Loss (₹ Cr) | Loss Cost (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **KUTCHA** (Thatched/Mud) | 118 | ₹272.10 | 60.88% | ₹165.53 | **60.83%** |
| **TIN_ROOF** (CGI/Asbestos) | 358 | ₹1,070.27 | 33.35% | ₹398.18 | **37.20%** |
| **STEEL_PEB** (Metal Sheds) | 207 | ₹650.40 | 12.49% | ₹54.14 | **8.32%** |
| **MASONRY** (Brick) | 1,807 | ₹5,729.93 | 6.16% | ₹316.42 | **5.52%** |
| **RCC** (Reinforced Concrete) | 1,010 | ₹3,372.79 | 1.09% | ₹34.34 | **1.02%** |

---

## 6. Sensitivity Analysis Findings

Catastrophe risk models exhibit sharp non-linear behavior when input parameters change:

### 1. Storm Track Spatial Shift
- **50 km Westward Shift**: Moves the cyclone eye over Chilika lake and rural Ganjam, dropping portfolio losses by **-50.25%** (to ₹481.86 Cr).
- **25 km Eastward Shift**: Places maximum right-quadrant winds across dense commercial centers of Bhubaneswar and Cuttack, increasing portfolio losses by **+3.42%** (to ₹1,001.75 Cr).

### 2. Hazard Intensity Scaling (Climate Intensification)
- **-10% Intensity**: Reduces portfolio loss by **-23.97%** (to ₹736.47 Cr).
- **+10% Intensity**: Amplifies portfolio loss by **+27.44%** (to ₹1,234.38 Cr).
- **Elasticity**: Loss elasticity $\approx 2.74$, demonstrating that loss grows nearly cubic relative to wind speed.

### 3. Proactive Building Retrofitting (Mitigation)
- Retrofitting 50% of vulnerable structures (hurricane straps, roof ties, storm shutters) avoids **₹319.91 Crores** in damage (-33.0% loss reduction).
- 100% retrofitting avoids **₹637.90 Crores** (-65.9% loss reduction).

### 4. Policy Deductibles (Risk Transfer)
- A 2% deductible shifts 17.5% of loss to policyholders (insurer pays ₹799.25 Cr).
- A 10% deductible shifts 38.3% of loss to policyholders (insurer pays ₹597.41 Cr).

---

## 7. QGIS & Oasis LMF Interoperability Guide

- **QGIS Project File**: Double-click [odisha_fani_cat_model.qgs](file:///e:/Project%20Vandana/data/gis/odisha_fani_cat_model.qgs) to open pre-configured thematic maps in QGIS.
- **Layers Available**:
  - `odisha_exposure_loss.gpkg` (Assets styled by Loss Cost & Max Wind)
  - `cyclone_fani_track_path.geojson` & `cyclone_fani_track_points.geojson`
  - `district_loss_summary.geojson` (District choropleth)
- **Oasis LMF OED**: Standard [location.csv](file:///e:/Project%20Vandana/data/processed/oasis_oed/location.csv) and [account.csv](file:///e:/Project%20Vandana/data/processed/oasis_oed/account.csv) ready for ingestion into Oasis LMF / PiWind.
- **CLIMADA Native**: [climada_exposures_odisha.csv](file:///e:/Project%20Vandana/data/processed/climada_exposures_odisha.csv) compatible with `climada.entity.Exposures`.
