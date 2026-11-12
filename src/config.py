"""
Catastrophe Risk Modeling Configuration - Cyclone Fani (2019) Odisha Project
"""
import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
HAZARD_DATA_DIR = DATA_DIR / "hazard"
GIS_DATA_DIR = DATA_DIR / "gis"
SQL_DIR = PROJECT_ROOT / "sql"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

# Database Path
DB_PATH = DATA_DIR / "exposure.db"

# Coordinate Reference Systems
CRS_WGS84 = "EPSG:4326"
CRS_METRIC = "EPSG:3857"  # Pseudo-Mercator for distance calculations

# Odisha Coastal Geographic Bounds (Lat: 19.0 to 22.0 N, Lon: 84.5 to 87.5 E)
ODISHA_BOUNDS = {
    "min_lat": 19.0,
    "max_lat": 22.0,
    "min_lon": 84.5,
    "max_lon": 87.5
}

# Cyclone Fani Historical Constants (Landfall May 3, 2019 near Puri, Odisha)
FANI_LANDFALL_PURI = {
    "name": "Puri, Odisha",
    "lat": 19.80,
    "lon": 85.82,
    "landfall_time_utc": "2019-05-03 03:30:00",
    "central_pressure_mb": 937.0,  # At landfall (~932 hPa at peak offshore)
    "max_sustained_wind_kt": 115.0,  # ~215 km/h (1-min sustained)
    "max_gust_kmh": 240.0,
    "rmax_km": 32.0,  # Radius of maximum winds
    "holland_b": 1.35  # Holland shape parameter
}

# Currency formatting constant (Indian Rupee INR)
CURRENCY_SYMBOL = "INR"
