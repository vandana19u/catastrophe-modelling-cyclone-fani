-- ============================================================================
-- Catastrophe Modeling: Exposure Database Schema (Odisha Portfolio)
-- ============================================================================

-- Drop existing tables if re-initializing
DROP TABLE IF EXISTS raw_exposure;
DROP TABLE IF EXISTS scrubbed_exposure;
DROP TABLE IF EXISTS scrubbing_audit_log;
DROP TABLE IF EXISTS district_metadata;

-- Raw Exposure Table (as ingested from insurance policy admin systems)
CREATE TABLE raw_exposure (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id TEXT,
    account_id TEXT,
    location_name TEXT,
    street_address TEXT,
    district TEXT,
    pincode TEXT,
    raw_latitude TEXT,
    raw_longitude TEXT,
    construction_type_raw TEXT,
    occupancy_type_raw TEXT,
    year_built INTEGER,
    number_of_storeys INTEGER,
    building_value_inr REAL,
    contents_value_inr REAL,
    bi_value_inr REAL, -- Business Interruption value
    deductible_inr REAL,
    policy_limit_inr REAL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Scrubbed & Cleansed Exposure Table (Production Cat Modeling format)
CREATE TABLE scrubbed_exposure (
    loc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    location_name TEXT,
    district TEXT NOT NULL,
    pincode TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    construction_code TEXT NOT NULL, -- Standardized: RCC, MASONRY, STEEL_PEB, TIN_ROOF, KUTCHA
    occupancy_code TEXT NOT NULL,    -- Standardized: RESIDENTIAL, COMMERCIAL, INDUSTRIAL, AGRICULTURAL
    year_built INTEGER,
    storeys INTEGER,
    building_tiv REAL NOT NULL,
    contents_tiv REAL NOT NULL,
    bi_tiv REAL NOT NULL,
    total_tiv REAL NOT NULL,
    deductible_inr REAL NOT NULL,
    policy_limit_inr REAL NOT NULL,
    geocode_source TEXT NOT NULL,    -- 'ORIGINAL', 'NOMINATIM', 'GAZETTEER_FALLBACK'
    quality_flag TEXT NOT NULL       -- 'CLEAN', 'IMPUTED', 'OUTLIER_ADJUSTED'
);

-- Audit Log Table tracking all scrubbing actions and data quality interventions
CREATE TABLE scrubbing_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id TEXT,
    rule_name TEXT,
    field_name TEXT,
    original_value TEXT,
    cleaned_value TEXT,
    action_taken TEXT,
    action_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- District Reference Metadata
CREATE TABLE district_metadata (
    district_name TEXT PRIMARY KEY,
    headquarters TEXT,
    centroid_lat REAL,
    centroid_lon REAL,
    coastal_exposure_tier TEXT, -- 'HIGH_COASTAL', 'MODERATE_INLAND', 'LOW_INLAND'
    vulnerability_factor REAL
);

-- Pre-populate Odisha Coastal District Reference Data
INSERT INTO district_metadata (district_name, headquarters, centroid_lat, centroid_lon, coastal_exposure_tier, vulnerability_factor) VALUES
('Puri', 'Puri', 19.8135, 85.8312, 'HIGH_COASTAL', 1.25),
('Khordha', 'Bhubaneswar', 20.2961, 85.8245, 'HIGH_COASTAL', 1.15),
('Cuttack', 'Cuttack', 20.4625, 85.8828, 'MODERATE_INLAND', 1.10),
('Jagatsinghpur', 'Jagatsinghpur', 20.2667, 86.1667, 'HIGH_COASTAL', 1.25),
('Kendrapara', 'Kendrapara', 20.5000, 86.4167, 'HIGH_COASTAL', 1.20),
('Ganjam', 'Berhampur', 19.3149, 84.7941, 'HIGH_COASTAL', 1.15),
('Bhadrak', 'Bhadrak', 21.0574, 86.5158, 'HIGH_COASTAL', 1.10),
('Balasore', 'Balasore', 21.4934, 86.9135, 'HIGH_COASTAL', 1.10);
