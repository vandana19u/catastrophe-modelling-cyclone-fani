-- ============================================================================
-- SQL Scrubbing & Data Hygiene Transformations
-- ============================================================================

-- 1. View: Identify duplicate policy entries
CREATE VIEW IF NOT EXISTS v_duplicate_policies AS
SELECT policy_id, COUNT(*) AS occurence_count
FROM raw_exposure
GROUP BY policy_id
HAVING COUNT(*) > 1;

-- 2. View: Identify invalid or corrupted financial values (TIV <= 0 or extreme outliers)
CREATE VIEW IF NOT EXISTS v_anomalous_values AS
SELECT 
    row_id,
    policy_id,
    building_value_inr,
    contents_value_inr,
    bi_value_inr,
    (COALESCE(building_value_inr, 0) + COALESCE(contents_value_inr, 0) + COALESCE(bi_value_inr, 0)) AS computed_total_tiv,
    CASE 
        WHEN building_value_inr <= 0 THEN 'NEGATIVE_OR_ZERO_BUILDING_VALUE'
        WHEN building_value_inr > 500000000 THEN 'EXTREME_OUTLIER_BUILDING_VALUE'
        WHEN deductible_inr > building_value_inr THEN 'DEDUCTIBLE_EXCEEDS_VALUE'
        ELSE 'VALID'
    END AS financial_health_status
FROM raw_exposure;

-- 3. View: Standardized Construction Mapping
CREATE VIEW IF NOT EXISTS v_standardized_construction AS
SELECT 
    row_id,
    policy_id,
    construction_type_raw,
    CASE 
        WHEN LOWER(TRIM(construction_type_raw)) IN ('rcc', 'reinforced concrete', 'rc frame', 'r.c.c.', 'concrete') 
            THEN 'RCC'
        WHEN LOWER(TRIM(construction_type_raw)) IN ('masonry', 'brick', 'brick masonry', 'confined masonry', 'stone') 
            THEN 'MASONRY'
        WHEN LOWER(TRIM(construction_type_raw)) IN ('steel', 'peb', 'pre-engineered building', 'steel frame', 'metal') 
            THEN 'STEEL_PEB'
        WHEN LOWER(TRIM(construction_type_raw)) IN ('tin', 'tin roof', 'cgi', 'cgi sheet', 'asbestos', 'asbestos sheet', 'sheet roof') 
            THEN 'TIN_ROOF'
        WHEN LOWER(TRIM(construction_type_raw)) IN ('kutcha', 'thatch', 'thatched', 'straw', 'mud', 'bamboo') 
            THEN 'KUTCHA'
        ELSE 'MASONRY' -- Default conservative fallback
    END AS standardized_construction_code
FROM raw_exposure;

-- 4. View: Standardized Occupancy Mapping
CREATE VIEW IF NOT EXISTS v_standardized_occupancy AS
SELECT 
    row_id,
    policy_id,
    occupancy_type_raw,
    CASE 
        WHEN LOWER(TRIM(occupancy_type_raw)) LIKE '%res%' OR LOWER(TRIM(occupancy_type_raw)) IN ('home', 'apartment', 'housing') 
            THEN 'RESIDENTIAL'
        WHEN LOWER(TRIM(occupancy_type_raw)) LIKE '%com%' OR LOWER(TRIM(occupancy_type_raw)) IN ('shop', 'retail', 'office', 'hotel') 
            THEN 'COMMERCIAL'
        WHEN LOWER(TRIM(occupancy_type_raw)) LIKE '%ind%' OR LOWER(TRIM(occupancy_type_raw)) IN ('factory', 'plant', 'manufacturing') 
            THEN 'INDUSTRIAL'
        WHEN LOWER(TRIM(occupancy_type_raw)) LIKE '%agr%' OR LOWER(TRIM(occupancy_type_raw)) IN ('warehouse', 'godown', 'storage') 
            THEN 'AGRICULTURAL'
        ELSE 'RESIDENTIAL' -- Default fallback
    END AS standardized_occupancy_code
FROM raw_exposure;

-- 5. View: Coordinates Validation
CREATE VIEW IF NOT EXISTS v_coordinate_validation AS
SELECT 
    row_id,
    policy_id,
    district,
    raw_latitude,
    raw_longitude,
    CAST(raw_latitude AS REAL) AS numeric_lat,
    CAST(raw_longitude AS REAL) AS numeric_lon,
    CASE 
        WHEN raw_latitude IS NULL OR raw_longitude IS NULL OR raw_latitude = '' OR raw_longitude = '' 
            THEN 'MISSING_COORDINATES'
        WHEN CAST(raw_latitude AS REAL) < 18.0 OR CAST(raw_latitude AS REAL) > 23.0 
            OR CAST(raw_longitude AS REAL) < 83.0 OR CAST(raw_longitude AS REAL) > 89.0 
            THEN 'OUT_OF_BOUNDS_ODISHA'
        ELSE 'VALID_BOUNDS'
    END AS spatial_validation_status
FROM raw_exposure;
