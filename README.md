# Catastrophe Risk Modeling: Cyclone Fani (2019) Coastal Odisha Portfolio Impact

An end-to-end catastrophe (Cat) risk modeling implementation simulating Tropical Cyclone Fani's landfall in coastal Odisha, India (May 2019), developed with open-source cat modeling principles (CLIMADA / Oasis LMF PiWind framework).

## Project Overview & Objectives
This project demonstrates the complete lifecycle of a professional catastrophe modeling workflow:
1. **Exposure Generation & Ingestion**: Synthetic yet realistic portfolio of ~3,500 residential, commercial, industrial, and infrastructure assets across coastal Odisha (Puri, Khordha/Bhubaneswar, Cuttack, Jagatsinghpur/Paradip, Kendrapara, Ganjam/Gopalpur, and Balasore).
2. **SQL Scrubbing & Data Hygiene**: Data cleansing in SQLite (`exposure.db`), validating Total Insured Value (TIV), construction codes, deduplication, occupancy mapping, and geocode validation flags.
3. **Geocoding & Spatial Enrichment**: Geocoding using `geopy` with geographic fallbacks to sub-district/pin-code centroids, coastal proximity calculation, and elevation sampling.
4. **Hazard Simulation (NOAA IBTrACS Cyclone Fani)**: Historical 3-hourly track extraction of Cyclone Fani (May 2019, Cat 4/5 equivalent, 932 hPa min pressure, landfall ~185–205 km/h near Puri), wind swath generation using the Holland (1980/2010) radial windfield profile, and CLIMADA TropicalCyclone hazard modeling.
5. **Vulnerability & Damage Modeling**: CLIMADA-aligned vulnerability functions (Eberenz et al. / Emanuel 2011 / Oasis LMF format) mapping 1-minute sustained wind speeds to Mean Damage Ratios (MDR) by construction type (Reinforced Concrete, Confined Masonry, Steel PEB, Thatched/Kutcha, etc.).
6. **Loss Calculation & Financial Engine**: Calculation of Ground Up Loss (GUL), site-level deductibles and policy limits, Gross Loss, and portfolio exceedance probability.
7. **Sensitivity Testing**: Quantifying loss elasticity with respect to:
   - Storm track shift (e.g. ±25 km / ±50 km east/west shift)
   - Central pressure drop & maximum sustained wind intensity (±10%)
   - Building vulnerability & retrofitting (upgraded roof / engineered construction)
   - Policy terms (varying deductible levels)
8. **QGIS Mapping & Spatial Reporting**: Exported layers (GeoPackage, GeoJSON, QGIS QML styles) for visual cartography of exposures, wind swaths, and loss density choropleths.
