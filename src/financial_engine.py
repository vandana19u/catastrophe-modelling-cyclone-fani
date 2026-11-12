"""
Financial Engine for Catastrophe Risk Modeling
Calculates Ground-Up Loss (GUL), applies policy deductibles and limits to calculate
Gross Insured Loss, Insured Retained Loss, and portfolio-level actuarial metrics.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from src.config import RESULTS_DIR

def calculate_financial_losses(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes site-level and portfolio-level financial losses.
    Input must contain: building_tiv, contents_tiv, bi_tiv, deductible_inr, policy_limit_inr,
    mean_damage_ratio, contents_damage_ratio, bi_damage_ratio.
    """
    df = portfolio_df.copy()

    # 1. Ground-Up Loss (GUL) by coverage
    df["building_gul"] = np.round(df["building_tiv"] * df["mean_damage_ratio"], 2)
    df["contents_gul"] = np.round(df["contents_tiv"] * df["contents_damage_ratio"], 2)
    df["bi_gul"] = np.round(df["bi_tiv"] * df["bi_damage_ratio"], 2)
    df["total_ground_up_loss"] = np.round(df["building_gul"] + df["contents_gul"] + df["bi_gul"], 2)

    # 2. Application of Policy Deductibles and Limits (Gross Insured Loss)
    # Loss in excess of deductible: max(0, GUL - Deductible)
    loss_above_deductible = np.maximum(0.0, df["total_ground_up_loss"] - df["deductible_inr"])
    # Capped at Policy Limit: min(Limit, Loss above Deductible)
    df["gross_insured_loss"] = np.round(np.minimum(df["policy_limit_inr"], loss_above_deductible), 2)

    # 3. Policyholder Retained Loss (Deductible + Loss in excess of limit)
    df["retained_loss"] = np.round(df["total_ground_up_loss"] - df["gross_insured_loss"], 2)

    # 4. Site-level Loss Cost (% of TIV destroyed)
    df["site_loss_cost_pct"] = np.round((df["total_ground_up_loss"] / np.maximum(1.0, df["total_tiv"])) * 100.0, 3)

    return df

def generate_portfolio_loss_summary(df_loss: pd.DataFrame) -> dict:
    """
    Aggregates financial losses across the portfolio by district, construction, and occupancy.
    Returns a structured report dictionary.
    """
    total_portfolio_tiv = df_loss["total_tiv"].sum()
    total_ground_up = df_loss["total_ground_up_loss"].sum()
    total_gross = df_loss["gross_insured_loss"].sum()
    total_retained = df_loss["retained_loss"].sum()

    portfolio_loss_cost_pct = (total_ground_up / total_portfolio_tiv) * 100.0
    gross_loss_pct = (total_gross / total_portfolio_tiv) * 100.0

    # Summary by District
    district_summary = df_loss.groupby("district").agg(
        asset_count=("policy_id", "count"),
        total_tiv=("total_tiv", "sum"),
        mean_wind_kmh=("max_wind_kmh", "mean"),
        mean_mdr=("mean_damage_ratio", "mean"),
        total_gul=("total_ground_up_loss", "sum"),
        total_gross_loss=("gross_insured_loss", "sum")
    ).reset_index()
    district_summary["loss_cost_pct"] = (district_summary["total_gul"] / district_summary["total_tiv"]) * 100.0
    district_summary = district_summary.sort_values(by="total_gul", ascending=False)

    # Summary by Construction Type
    construction_summary = df_loss.groupby("construction_code").agg(
        asset_count=("policy_id", "count"),
        total_tiv=("total_tiv", "sum"),
        mean_mdr=("mean_damage_ratio", "mean"),
        total_gul=("total_ground_up_loss", "sum"),
        total_gross_loss=("gross_insured_loss", "sum")
    ).reset_index()
    construction_summary["loss_cost_pct"] = (construction_summary["total_gul"] / construction_summary["total_tiv"]) * 100.0
    construction_summary = construction_summary.sort_values(by="loss_cost_pct", ascending=False)

    # Summary by Occupancy Type
    occupancy_summary = df_loss.groupby("occupancy_code").agg(
        asset_count=("policy_id", "count"),
        total_tiv=("total_tiv", "sum"),
        mean_mdr=("mean_damage_ratio", "mean"),
        total_gul=("total_ground_up_loss", "sum"),
        total_gross_loss=("gross_insured_loss", "sum")
    ).reset_index()
    occupancy_summary["loss_cost_pct"] = (occupancy_summary["total_gul"] / occupancy_summary["total_tiv"]) * 100.0
    occupancy_summary = occupancy_summary.sort_values(by="total_gul", ascending=False)

    summary = {
        "portfolio_totals": {
            "num_assets": len(df_loss),
            "total_tiv_inr": round(total_portfolio_tiv, 2),
            "total_tiv_crores": round(total_portfolio_tiv / 1e7, 2),
            "total_ground_up_loss_inr": round(total_ground_up, 2),
            "total_ground_up_loss_crores": round(total_ground_up / 1e7, 2),
            "total_gross_insured_loss_inr": round(total_gross, 2),
            "total_gross_insured_loss_crores": round(total_gross / 1e7, 2),
            "total_retained_loss_inr": round(total_retained, 2),
            "total_retained_loss_crores": round(total_retained / 1e7, 2),
            "portfolio_loss_cost_pct": round(portfolio_loss_cost_pct, 2),
            "gross_loss_pct": round(gross_loss_pct, 2)
        },
        "by_district": district_summary,
        "by_construction": construction_summary,
        "by_occupancy": occupancy_summary
    }

    # Save summary tables to CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    district_summary.to_csv(RESULTS_DIR / "loss_summary_by_district.csv", index=False)
    construction_summary.to_csv(RESULTS_DIR / "loss_summary_by_construction.csv", index=False)
    occupancy_summary.to_csv(RESULTS_DIR / "loss_summary_by_occupancy.csv", index=False)
    print(f"[Financial Engine] Exported district, construction, and occupancy loss summaries to {RESULTS_DIR}")

    return summary

if __name__ == "__main__":
    pass
