"""
SQL Scrubbing and Data Hygiene Engine for Catastrophe Risk Exposure Data
Executes SQLite DDL, data validation queries, standardizes construction & occupancy codes,
cleans anomalous values, eliminates duplicates, and maintains an audit log.
"""
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import DB_PATH, SQL_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR

def run_sql_scrubbing(raw_csv_path: Path = None, db_path: Path = DB_PATH) -> dict:
    """
    Executes the end-to-end SQL scrubbing workflow.
    Returns audit metrics and record counts.
    """
    if raw_csv_path is None:
        raw_csv_path = RAW_DATA_DIR / "odisha_exposure_raw.csv"

    print(f"[SQL Scrubbing] Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Execute Schema Initialization
    schema_file = SQL_DIR / "01_schema.sql"
    with open(schema_file, "r") as f:
        cursor.executescript(f.read())
    conn.commit()

    # 2. Ingest Raw Exposure Data into SQLite
    print(f"[SQL Scrubbing] Ingesting raw CSV: {raw_csv_path}")
    df_raw = pd.read_csv(raw_csv_path)
    df_raw.to_sql("raw_exposure", conn, if_exists="append", index=False)
    conn.commit()

    total_raw_rows = cursor.execute("SELECT COUNT(*) FROM raw_exposure").fetchone()[0]
    print(f"[SQL Scrubbing] Loaded {total_raw_rows} records into 'raw_exposure'.")

    # 3. Execute Scrubbing Views Definition
    rules_file = SQL_DIR / "02_scrubbing_rules.sql"
    with open(rules_file, "r") as f:
        cursor.executescript(f.read())
    conn.commit()

    # -------------------------------------------------------------------------
    # 4. Scrubbing Step 1: Detect and Log Duplicate Policies
    # -------------------------------------------------------------------------
    cursor.execute("""
        SELECT policy_id, COUNT(*) 
        FROM raw_exposure 
        GROUP BY policy_id 
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    dup_count = len(duplicates)
    
    for pol_id, count in duplicates:
        cursor.execute("""
            INSERT INTO scrubbing_audit_log (policy_id, rule_name, field_name, original_value, cleaned_value, action_taken)
            VALUES (?, 'DEDUPLICATION', 'policy_id', ?, 'DE-DUPLICATED', ?)
        """, (pol_id, f"Count={count}", f"Retained single instance, purged {count-1} duplicate rows"))
    conn.commit()
    print(f"[SQL Scrubbing] Identified {dup_count} duplicate policy families. Audit logged.")

    # -------------------------------------------------------------------------
    # 5. Scrubbing Step 2: Build Clean Exposure Table with Deduplication & Rules
    # -------------------------------------------------------------------------
    # We select distinct policy_id (picking min row_id) with normalized construction & occupancy
    query_clean_base = """
    SELECT 
        r.policy_id,
        r.account_id,
        r.location_name,
        r.street_address,
        r.district,
        r.pincode,
        r.raw_latitude,
        r.raw_longitude,
        sc.standardized_construction_code AS construction_code,
        so.standardized_occupancy_code AS occupancy_code,
        COALESCE(r.year_built, 2005) AS year_built,
        COALESCE(r.number_of_storeys, 1) AS storeys,
        r.building_value_inr,
        r.contents_value_inr,
        r.bi_value_inr,
        r.deductible_inr,
        r.policy_limit_inr,
        cv.spatial_validation_status
    FROM raw_exposure r
    JOIN v_standardized_construction sc ON r.row_id = sc.row_id
    JOIN v_standardized_occupancy so ON r.row_id = so.row_id
    JOIN v_coordinate_validation cv ON r.row_id = cv.row_id
    WHERE r.row_id IN (
        SELECT MIN(row_id) FROM raw_exposure GROUP BY policy_id
    )
    """
    df_dedup = pd.read_sql_query(query_clean_base, conn)

    # -------------------------------------------------------------------------
    # 6. Scrubbing Step 3: Financial Hygiene (Impute / Cap Anomalies)
    # -------------------------------------------------------------------------
    # Calculate robust medians by district and occupancy for replacement values
    valid_mask = (df_dedup["building_value_inr"] > 100000) & (df_dedup["building_value_inr"] < 200000000)
    medians = df_dedup[valid_mask].groupby(["district", "occupancy_code"])["building_value_inr"].median().to_dict()
    global_median = df_dedup[valid_mask]["building_value_inr"].median()

    fixed_financials = 0
    for idx, row in df_dedup.iterrows():
        b_val = row["building_value_inr"]
        pol_id = row["policy_id"]
        
        # Check if building value is zero, negative, or extreme outlier
        if pd.isna(b_val) or b_val <= 0 or b_val > 500000000:
            key = (row["district"], row["occupancy_code"])
            imputed_val = medians.get(key, global_median)
            action = "IMPUTED_MEDIAN" if b_val <= 0 else "CAPPED_OUTLIER"
            
            cursor.execute("""
                INSERT INTO scrubbing_audit_log (policy_id, rule_name, field_name, original_value, cleaned_value, action_taken)
                VALUES (?, 'FINANCIAL_ANOMALY', 'building_value_inr', ?, ?, ?)
            """, (pol_id, str(b_val), f"{imputed_val:.2f}", action))
            
            df_dedup.at[idx, "building_value_inr"] = imputed_val
            # Adjust contents, deductible, and limit proportionally
            df_dedup.at[idx, "contents_value_inr"] = imputed_val * 0.30
            df_dedup.at[idx, "deductible_inr"] = max(25000.0, round(imputed_val * 0.02, -2))
            df_dedup.at[idx, "policy_limit_inr"] = imputed_val
            fixed_financials += 1
            
    conn.commit()
    print(f"[SQL Scrubbing] Repaired & audited {fixed_financials} anomalous financial records.")

    # Compute Total Insured Value (TIV)
    df_dedup["building_tiv"] = df_dedup["building_value_inr"].round(2)
    df_dedup["contents_tiv"] = df_dedup["contents_value_inr"].fillna(0).round(2)
    df_dedup["bi_tiv"] = df_dedup["bi_value_inr"].fillna(0).round(2)
    df_dedup["total_tiv"] = (df_dedup["building_tiv"] + df_dedup["contents_tiv"] + df_dedup["bi_tiv"]).round(2)

    # -------------------------------------------------------------------------
    # 7. Scrubbing Step 4: Spatial Validation & Quarantine Flagging
    # -------------------------------------------------------------------------
    # Flag which records have valid coordinates vs need geopy geocoding
    df_dedup["latitude"] = pd.to_numeric(df_dedup["raw_latitude"], errors="coerce")
    df_dedup["longitude"] = pd.to_numeric(df_dedup["raw_longitude"], errors="coerce")

    # Fix swapped lat/lon (e.g. lat around 85-87 and lon around 19-21)
    swapped_mask = (df_dedup["latitude"] > 80.0) & (df_dedup["longitude"] < 25.0)
    for idx in df_dedup[swapped_mask].index:
        pol_id = df_dedup.at[idx, "policy_id"]
        old_lat = df_dedup.at[idx, "latitude"]
        old_lon = df_dedup.at[idx, "longitude"]
        df_dedup.at[idx, "latitude"] = old_lon
        df_dedup.at[idx, "longitude"] = old_lat
        cursor.execute("""
            INSERT INTO scrubbing_audit_log (policy_id, rule_name, field_name, original_value, cleaned_value, action_taken)
            VALUES (?, 'COORDINATES_SWAPPED', 'lat_lon', ?, ?, 'Swapped inverted coordinates back to WGS84 Lat/Lon')
        """, (pol_id, f"lat={old_lat}, lon={old_lon}", f"lat={old_lon}, lon={old_lat}"))

    conn.commit()

    # Determine geocode source requirement
    valid_spatial = (
        (df_dedup["latitude"] >= 18.0) & (df_dedup["latitude"] <= 23.0) &
        (df_dedup["longitude"] >= 84.0) & (df_dedup["longitude"] <= 88.0)
    )
    df_dedup["geocode_source"] = "ORIGINAL"
    df_dedup.loc[~valid_spatial, "geocode_source"] = "PENDING_GEOCODE"
    df_dedup["quality_flag"] = "CLEAN"
    df_dedup.loc[~valid_spatial, "quality_flag"] = "NEEDS_GEOCODING"

    # Save to staging table in SQLite
    df_dedup.to_sql("exposure_scrubbed_stage", conn, if_exists="replace", index=False)
    conn.commit()

    pending_geo_count = (~valid_spatial).sum()
    clean_geo_count = valid_spatial.sum()
    print(f"[SQL Scrubbing] Clean spatial records: {clean_geo_count} | Pending Geocoding: {pending_geo_count}")

    # Export intermediate dataset for geocoding step
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    stage_csv = PROCESSED_DATA_DIR / "exposure_staged_for_geocoding.csv"
    df_dedup.to_csv(stage_csv, index=False)
    
    conn.close()

    metrics = {
        "total_raw": total_raw_rows,
        "duplicates_removed": dup_count,
        "financial_anomalies_cleaned": fixed_financials,
        "clean_spatial_records": int(clean_geo_count),
        "pending_geocoding": int(pending_geo_count),
        "total_cleaned_portfolio": len(df_dedup)
    }
    return metrics

if __name__ == "__main__":
    metrics = run_sql_scrubbing()
    print("Scrubbing Summary:", metrics)
