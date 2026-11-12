"""
Synthetic Exposure Generator for Coastal Odisha Catastrophe Modeling
Simulates ~3,500 real-world insurance policy risk locations across cyclone-prone districts.
Includes deliberate real-world data imperfections for SQL scrubbing & geopy geocoding.
"""
import random
import numpy as np
import pandas as pd
from pathlib import Path
from src.config import RAW_DATA_DIR, PROJECT_ROOT

# Ensure reproducible generation
np.random.seed(42)
random.seed(42)

# Odisha Coastal Districts and Key Localities
DISTRICT_LOCALITIES = {
    "Puri": [
        {"locality": "Puri Town Beach Road", "pincode": "752001", "lat": 19.7983, "lon": 85.8249},
        {"locality": "Grand Road Jagannath Colony", "pincode": "752001", "lat": 19.8048, "lon": 85.8179},
        {"locality": "Konark Marine Drive", "pincode": "752111", "lat": 19.8876, "lon": 86.0945},
        {"locality": "Pipili Market Square", "pincode": "752104", "lat": 20.1130, "lon": 85.8340},
        {"locality": "Brahmagiri Chilika Gate", "pincode": "752011", "lat": 19.8010, "lon": 85.6420},
        {"locality": "Nimapada Rural Sector", "pincode": "752106", "lat": 20.0610, "lon": 86.0150},
        {"locality": "Satyabadi Sakhigopal", "pincode": "752014", "lat": 19.9530, "lon": 85.8270},
        {"locality": "Astaranga Coastal Fishery", "pincode": "752109", "lat": 19.9820, "lon": 86.2650}
    ],
    "Khordha": [
        {"locality": "Bhubaneswar Jayadev Vihar", "pincode": "751013", "lat": 20.3015, "lon": 85.8245},
        {"locality": "Bhubaneswar Patia IT Hub", "pincode": "751024", "lat": 20.3588, "lon": 85.8160},
        {"locality": "Bhubaneswar Old Town Lingaraj", "pincode": "751002", "lat": 20.2410, "lon": 85.8330},
        {"locality": "Bhubaneswar Rasulgarh Industrial", "pincode": "751010", "lat": 20.2980, "lon": 85.8670},
        {"locality": "Bhubaneswar Khandagiri Enclave", "pincode": "751030", "lat": 20.2570, "lon": 85.7870},
        {"locality": "Jatani Railway Junction", "pincode": "752050", "lat": 20.1650, "lon": 85.7070},
        {"locality": "Khordha Industrial Estate", "pincode": "752055", "lat": 20.1820, "lon": 85.6170},
        {"locality": "Balipatna Rural Belt", "pincode": "752102", "lat": 20.1700, "lon": 85.9500}
    ],
    "Cuttack": [
        {"locality": "Cuttack Badambadi Bus Stand", "pincode": "753012", "lat": 20.4570, "lon": 85.8730},
        {"locality": "Cuttack Choudwar Industrial", "pincode": "754025", "lat": 20.5360, "lon": 85.8970},
        {"locality": "Cuttack CDA Sector 9", "pincode": "753014", "lat": 20.4780, "lon": 85.8320},
        {"locality": "Cuttack Jagatpur Industrial Park", "pincode": "754021", "lat": 20.4980, "lon": 85.9150},
        {"locality": "Banki Subdivisional Town", "pincode": "754008", "lat": 20.3780, "lon": 85.5320},
        {"locality": "Salepur Market Yard", "pincode": "754202", "lat": 20.4850, "lon": 86.1150}
    ],
    "Jagatsinghpur": [
        {"locality": "Paradip Port Port Area", "pincode": "754142", "lat": 20.2644, "lon": 86.6690},
        {"locality": "Paradip Refinery Complex", "pincode": "754141", "lat": 20.2910, "lon": 86.6210},
        {"locality": "Jagatsinghpur Town Square", "pincode": "754103", "lat": 20.2570, "lon": 86.1710},
        {"locality": "Erasama Cyclone Shelter Area", "pincode": "754139", "lat": 20.1760, "lon": 86.4420},
        {"locality": "Kujang Coastal Block", "pincode": "754141", "lat": 20.3080, "lon": 86.5450},
        {"locality": "Balikuda Fishery Hamlet", "pincode": "754108", "lat": 20.0890, "lon": 86.3210}
    ],
    "Kendrapara": [
        {"locality": "Kendrapara Town Canal Road", "pincode": "754211", "lat": 20.4980, "lon": 86.4220},
        {"locality": "Pattamundai Rice Mill Zone", "pincode": "754215", "lat": 20.5730, "lon": 86.5680},
        {"locality": "Rajnagar Mangrove Buffer", "pincode": "754225", "lat": 20.5840, "lon": 86.7320},
        {"locality": "Mahakalapada Riverine Belt", "pincode": "754224", "lat": 20.4320, "lon": 86.6020},
        {"locality": "Aul Agricultural Zone", "pincode": "754219", "lat": 20.6720, "lon": 86.6380}
    ],
    "Ganjam": [
        {"locality": "Gopalpur on Sea Beachfront", "pincode": "761002", "lat": 19.2600, "lon": 84.9080},
        {"locality": "Berhampur Commercial Market", "pincode": "760001", "lat": 19.3149, "lon": 84.7941},
        {"locality": "Chatrapur District HQ", "pincode": "761020", "lat": 19.3550, "lon": 84.9920},
        {"locality": "Ganjam Salt Pans & Coast", "pincode": "761026", "lat": 19.3820, "lon": 85.0510},
        {"locality": "Aska Sugar Factory Zone", "pincode": "761110", "lat": 19.6100, "lon": 84.6540}
    ],
    "Bhadrak": [
        {"locality": "Bhadrak Charampa Market", "pincode": "756101", "lat": 21.0574, "lon": 86.5158},
        {"locality": "Dhamra Port Logistics Terminal", "pincode": "756171", "lat": 20.8260, "lon": 86.9580},
        {"locality": "Chandbali Ferry Ghat", "pincode": "756133", "lat": 20.7780, "lon": 86.7420},
        {"locality": "Basudevpur Coastal Plain", "pincode": "756125", "lat": 21.1390, "lon": 86.7450}
    ],
    "Balasore": [
        {"locality": "Balasore OT Road Business", "pincode": "756001", "lat": 21.4934, "lon": 86.9135},
        {"locality": "Chandipur Beach Defense Road", "pincode": "756025", "lat": 21.4680, "lon": 87.0160},
        {"locality": "Remuna Handloom Cluster", "pincode": "756019", "lat": 21.5280, "lon": 86.8720},
        {"locality": "Jaleswar Bengal Border", "pincode": "756032", "lat": 21.8020, "lon": 87.2180},
        {"locality": "Soro Agro Industry", "pincode": "756045", "lat": 21.2890, "lon": 86.6870}
    ]
}

# Real-world dirty input strings for construction and occupancy
CONSTRUCTION_NOISE = {
    "RCC": ["RCC", "rc frame", "Reinforced Concrete", "R.C.C.", "concrete structure", "RCC Roof"],
    "MASONRY": ["Masonry", "brick masonry", "Confined Brick", "brick", "Stone Masonry", "MASONRY"],
    "STEEL_PEB": ["Steel", "PEB", "Pre-Engineered Building", "industrial steel frame", "metal shed"],
    "TIN_ROOF": ["Tin Roof", "CGI Sheet", "Asbestos Sheet", "tin", "sheet roof", "CGI_ROOF"],
    "KUTCHA": ["Kutcha", "Thatch", "thatched roof", "straw", "mud wall thatch", "bamboo thatch"]
}

OCCUPANCY_NOISE = {
    "RESIDENTIAL": ["Residential", "RES", "Home", "Single Family", "Apartment", "residence"],
    "COMMERCIAL": ["Commercial", "COMM", "Shop", "Office Complex", "Retail", "Hotel"],
    "INDUSTRIAL": ["Industrial", "IND", "Manufacturing Plant", "Factory", "Chemical Storage"],
    "AGRICULTURAL": ["Agricultural", "AGR", "Grain Warehouse", "Godown", "Cold Storage"]
}

def generate_exposure_records(n_records: int = 3500) -> pd.DataFrame:
    """
    Generates realistic exposure records across coastal Odisha.
    Simulates property characteristics, replacement values, insurance terms,
    and deliberate data hygiene issues.
    """
    records = []
    policy_counter = 100000
    
    # District weights representing exposure concentration (Khordha/Bhubaneswar & Puri highest)
    districts = list(DISTRICT_LOCALITIES.keys())
    weights = [0.22, 0.28, 0.16, 0.12, 0.08, 0.06, 0.04, 0.04]
    
    construction_keys = ["RCC", "MASONRY", "STEEL_PEB", "TIN_ROOF", "KUTCHA"]
    construction_probs = [0.42, 0.28, 0.10, 0.13, 0.07]
    
    occupancy_keys = ["RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "AGRICULTURAL"]
    occupancy_probs = [0.65, 0.22, 0.08, 0.05]
    
    for i in range(n_records):
        policy_counter += 1
        pol_id = f"POL-ODI-{policy_counter:07d}"
        acc_id = f"ACC-{(i % 450) + 101:05d}"
        
        district = np.random.choice(districts, p=weights)
        locality_info = random.choice(DISTRICT_LOCALITIES[district])
        
        # Add small spatial jitter (~100m to 1.5km) around locality centroid
        lat = locality_info["lat"] + np.random.normal(0, 0.008)
        lon = locality_info["lon"] + np.random.normal(0, 0.008)
        
        c_base = np.random.choice(construction_keys, p=construction_probs)
        o_base = np.random.choice(occupancy_keys, p=occupancy_probs)
        
        # Injected noise in string fields
        c_raw = random.choice(CONSTRUCTION_NOISE[c_base])
        o_raw = random.choice(OCCUPANCY_NOISE[o_base])
        
        # Financial values based on occupancy & construction (INR in Lakhs/Crores)
        if o_base == "RESIDENTIAL":
            b_val = float(np.random.lognormal(mean=15.1, sigma=0.55)) # ~INR 25L - 80L
            c_val = b_val * np.random.uniform(0.20, 0.35)
            bi_val = 0.0
            deductible = max(25000.0, round(b_val * 0.02, -2))
            limit = b_val * 1.0
            storeys = random.choice([1, 1, 2, 2, 3, 4])
        elif o_base == "COMMERCIAL":
            b_val = float(np.random.lognormal(mean=16.5, sigma=0.75)) # ~INR 1 Cr - 4 Cr
            c_val = b_val * np.random.uniform(0.40, 0.70)
            bi_val = b_val * np.random.uniform(0.15, 0.30)
            deductible = max(100000.0, round(b_val * 0.05, -3))
            limit = b_val * 1.0
            storeys = random.choice([2, 3, 4, 5, 7])
        elif o_base == "INDUSTRIAL":
            b_val = float(np.random.lognormal(mean=18.0, sigma=0.85)) # ~INR 5 Cr - 25 Cr
            c_val = b_val * np.random.uniform(0.80, 1.50)
            bi_val = b_val * np.random.uniform(0.30, 0.60)
            deductible = max(250000.0, round(b_val * 0.05, -4))
            limit = b_val * 1.0
            storeys = random.choice([1, 2, 3])
        else: # AGRICULTURAL
            b_val = float(np.random.lognormal(mean=14.8, sigma=0.60)) # ~INR 20L - 60L
            c_val = b_val * np.random.uniform(0.60, 1.20)
            bi_val = b_val * np.random.uniform(0.10, 0.20)
            deductible = max(50000.0, round(b_val * 0.03, -2))
            limit = b_val * 1.0
            storeys = 1

        year_built = int(np.random.randint(1985, 2018))
        
        # Round financial numbers cleanly
        b_val = round(b_val, 2)
        c_val = round(c_val, 2)
        bi_val = round(bi_val, 2)
        
        loc_name = f"{locality_info['locality']} Plot #{random.randint(10, 999)}"
        street = f"{random.randint(1, 25)} Main St, {locality_info['locality']}"
        pincode = locality_info["pincode"]
        
        # Form raw record
        record = {
            "policy_id": pol_id,
            "account_id": acc_id,
            "location_name": loc_name,
            "street_address": street,
            "district": district,
            "pincode": pincode,
            "raw_latitude": f"{lat:.6f}",
            "raw_longitude": f"{lon:.6f}",
            "construction_type_raw": c_raw,
            "occupancy_type_raw": o_raw,
            "year_built": year_built,
            "number_of_storeys": storeys,
            "building_value_inr": b_val,
            "contents_value_inr": c_val,
            "bi_value_inr": bi_val,
            "deductible_inr": deductible,
            "policy_limit_inr": limit
        }
        records.append(record)

    df = pd.DataFrame(records)

    # -------------------------------------------------------------------------
    # Deliberate Data Imperfections Injection (for SQL Scrubbing & Geocoding)
    # -------------------------------------------------------------------------
    # 1. Duplicate policies (45 records duplicated)
    dup_indices = np.random.choice(df.index, size=45, replace=False)
    df_dups = df.loc[dup_indices].copy()
    
    # 2. Missing or blank coordinates (140 records need geopy geocoding)
    missing_geo_indices = np.random.choice(df.index, size=140, replace=False)
    for idx in missing_geo_indices:
        df.at[idx, "raw_latitude"] = ""
        df.at[idx, "raw_longitude"] = ""
        # Sometimes pincode is also slightly malformed or missing
        if random.random() < 0.2:
            df.at[idx, "pincode"] = "UNKNOWN"
            
    # 3. Swapped or out-of-bounds coordinates (25 records)
    swapped_geo_indices = np.random.choice(df.index, size=25, replace=False)
    for idx in swapped_geo_indices:
        lat_val = df.at[idx, "raw_latitude"]
        lon_val = df.at[idx, "raw_longitude"]
        if lat_val and lon_val:
            df.at[idx, "raw_latitude"] = lon_val  # Swapped!
            df.at[idx, "raw_longitude"] = lat_val
            
    # 4. Outlier / Corrupted values (30 records: negative or absurd 999999999)
    outlier_indices = np.random.choice(df.index, size=30, replace=False)
    for i, idx in enumerate(outlier_indices):
        if i % 3 == 0:
            df.at[idx, "building_value_inr"] = -50000.0  # Negative!
        elif i % 3 == 1:
            df.at[idx, "building_value_inr"] = 0.0       # Zero!
        else:
            df.at[idx, "building_value_inr"] = 999999999.0 # Extreme erroneous outlier

    # Append the duplicate rows to create realistic duplicate policy conflicts
    df = pd.concat([df, df_dups], ignore_index=True)
    # Shuffle dataframe
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    return df

def main():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_csv_path = RAW_DATA_DIR / "odisha_exposure_raw.csv"
    print(f"Generating synthetic coastal Odisha exposure portfolio...")
    df_raw = generate_exposure_records(n_records=3500)
    df_raw.to_csv(raw_csv_path, index=False)
    print(f"Successfully generated {len(df_raw)} raw exposure records -> {raw_csv_path}")

if __name__ == "__main__":
    main()
