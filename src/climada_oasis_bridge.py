"""
CLIMADA and Oasis LMF Open Exposure Data (OED) Interoperability Bridge
Translates scrubbed Odisha exposure datasets into:
  1. Oasis LMF OED Standard Format (location.csv and account.csv)
  2. CLIMADA Exposures / Entity data format
"""
import pandas as pd
from pathlib import Path
from src.config import PROCESSED_DATA_DIR

def export_oasis_oed_files(df_clean: pd.DataFrame) -> dict:
    """
    Transforms the cleaned Odisha exposure dataset into Oasis LMF Open Exposure Data (OED) format:
    - location.csv (OED Location table)
    - account.csv (OED Account / Policy Terms table)
    """
    oasis_dir = PROCESSED_DATA_DIR / "oasis_oed"
    oasis_dir.mkdir(parents=True, exist_ok=True)

    # 1. Oasis OED location.csv
    oed_locations = []
    oed_accounts = []

    # Oasis construction mapping
    oasis_construction_map = {
        "RCC": 5000,       # Reinforced Concrete
        "MASONRY": 5100,  # Unreinforced / Confined Masonry
        "STEEL_PEB": 5200, # Steel / Metal Frame
        "TIN_ROOF": 5300,  # Light Metal / CGI Sheeting
        "KUTCHA": 5400     # Non-engineered Wood/Thatch
    }

    # Oasis occupancy mapping
    oasis_occupancy_map = {
        "RESIDENTIAL": 1050,
        "COMMERCIAL": 1110,
        "INDUSTRIAL": 1150,
        "AGRICULTURAL": 1200
    }

    for idx, row in df_clean.iterrows():
        loc_num = idx + 1
        pol_id = row["policy_id"]
        acc_id = row["account_id"]

        # OED Location record
        oed_locations.append({
            "PortNumber": 1,
            "AccNumber": acc_id,
            "LocNumber": loc_num,
            "LocName": row["location_name"],
            "LocPerilsCovered": "WTC", # Wind Tropical Cyclone
            "BuildingTIV": row["building_tiv"],
            "OtherTIV": 0.0,
            "ContentsTIV": row["contents_tiv"],
            "BITIV": row["bi_tiv"],
            "LocCurrency": "INR",
            "LocOccupancyCode": oasis_occupancy_map.get(row["occupancy_code"], 1050),
            "LocConstructionCode": oasis_construction_map.get(row["construction_code"], 5100),
            "YearBuilt": row["year_built"],
            "NumberOfStoreys": row["storeys"],
            "Latitude": row["latitude"],
            "Longitude": row["longitude"],
            "PostalCode": row["pincode"],
            "CountryCode": "IN"
        })

        # OED Account record
        oed_accounts.append({
            "PortNumber": 1,
            "AccNumber": acc_id,
            "PolNumber": pol_id,
            "LayerNumber": 1,
            "LayerParticipation": 1.0,
            "LayerAttachmentPoint": 0.0,
            "LayerLimit": row["policy_limit_inr"],
            "PolPeril": "WTC",
            "PolDed6Building": row["deductible_inr"],
            "PolDed6Contents": 0.0,
            "PolDed6BI": 0.0
        })

    df_oed_loc = pd.DataFrame(oed_locations)
    df_oed_acc = pd.DataFrame(oed_accounts)

    loc_path = oasis_dir / "location.csv"
    acc_path = oasis_dir / "account.csv"

    df_oed_loc.to_csv(loc_path, index=False)
    df_oed_acc.to_csv(acc_path, index=False)

    print(f"[Oasis Bridge] Exported Oasis LMF OED location.csv ({len(df_oed_loc)} rows) -> {loc_path}")
    print(f"[Oasis Bridge] Exported Oasis LMF OED account.csv ({len(df_oed_acc)} rows) -> {acc_path}")

    return {"location_csv": loc_path, "account_csv": acc_path}

def export_climada_exposure_file(df_clean: pd.DataFrame) -> Path:
    """
    Transforms exposure to CLIMADA standard Exposures DataFrame format:
    - latitude, longitude, value, ded, lim, category_id / if_TC
    """
    climada_df = pd.DataFrame()
    climada_df["latitude"] = df_clean["latitude"]
    climada_df["longitude"] = df_clean["longitude"]
    climada_df["value"] = df_clean["total_tiv"]
    climada_df["ded"] = df_clean["deductible_inr"]
    climada_df["lim"] = df_clean["policy_limit_inr"]
    climada_df["currency"] = "INR"

    # CLIMADA Impact Function ID (if_TC)
    c_to_if = {"RCC": 1, "MASONRY": 2, "STEEL_PEB": 3, "TIN_ROOF": 4, "KUTCHA": 5}
    climada_df["if_TC"] = df_clean["construction_code"].map(c_to_if)
    climada_df["impf_TC"] = climada_df["if_TC"]

    climada_csv = PROCESSED_DATA_DIR / "climada_exposures_odisha.csv"
    climada_df.to_csv(climada_csv, index=False)
    print(f"[CLIMADA Bridge] Exported CLIMADA native exposures dataset -> {climada_csv}")
    return climada_csv

if __name__ == "__main__":
    pass
