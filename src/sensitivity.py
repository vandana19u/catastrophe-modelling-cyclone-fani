"""
Catastrophe Sensitivity Analysis Engine - Cyclone Fani (Odisha)
Tests how changing one input parameter shifts portfolio loss:
  1. Track Spatial Shift (±25 km, ±50 km East/West)
  2. Storm Intensity Scaling (±5%, ±10% central pressure drop / wind speed)
  3. Building Vulnerability Retrofitting (0%, 25%, 50%, 75%, 100% retrofitted)
  4. Policy Deductibles (0%, 2%, 5%, 10%)
"""
import numpy as np
import pandas as pd
from pathlib import Path
from src.config import RESULTS_DIR
from src.hazard_fani import compute_fani_hazard_footprint
from src.vulnerability import apply_vulnerability_to_portfolio
from src.financial_engine import calculate_financial_losses

def run_track_shift_sensitivity(clean_exposure_df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates loss elasticity when shifting the storm track laterally
    by -50 km (West towards Ganjam), -25 km, 0 km (Baseline Puri),
    +25 km, +50 km (East towards Jagatsinghpur/Paradip).
    """
    print("[Sensitivity] Running Track Shift Experiment (-50km to +50km)...")
    shifts = [-50, -25, 0, 25, 50]
    results = []

    for shift in shifts:
        # 1. Compute wind footprint with track shift
        df_hazard = compute_fani_hazard_footprint(clean_exposure_df, track_shift_km_east=shift)
        # 2. Apply vulnerability
        df_vuln = apply_vulnerability_to_portfolio(df_hazard)
        # 3. Calculate losses
        df_loss = calculate_financial_losses(df_vuln)

        total_gul = df_loss["total_ground_up_loss"].sum()
        total_gross = df_loss["gross_insured_loss"].sum()
        tiv = df_loss["total_tiv"].sum()
        mean_mdr = df_loss["mean_damage_ratio"].mean()

        label = f"{abs(shift)} km {'West' if shift < 0 else ('East' if shift > 0 else 'Baseline (Puri)')}"
        results.append({
            "experiment": "Track Displacement",
            "parameter_value": shift,
            "scenario_label": label,
            "mean_portfolio_mdr": round(mean_mdr, 4),
            "ground_up_loss_inr": round(total_gul, 2),
            "ground_up_loss_crores": round(total_gul / 1e7, 2),
            "gross_insured_loss_crores": round(total_gross / 1e7, 2),
            "loss_cost_pct": round((total_gul / tiv) * 100.0, 2)
        })

    df_res = pd.DataFrame(results)
    baseline_loss = df_res.loc[df_res["parameter_value"] == 0, "ground_up_loss_inr"].values[0]
    df_res["delta_loss_pct"] = np.round(((df_res["ground_up_loss_inr"] - baseline_loss) / baseline_loss) * 100.0, 2)
    return df_res

def run_intensity_scaling_sensitivity(clean_exposure_df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates loss elasticity when scaling storm intensity (central pressure drop & max wind speed)
    by -10%, -5%, 0% (Baseline), +5%, +10% (Climate change / intensification).
    """
    print("[Sensitivity] Running Hazard Intensity Scaling Experiment (-10% to +10%)...")
    scales = [0.90, 0.95, 1.00, 1.05, 1.10]
    results = []

    for s in scales:
        df_hazard = compute_fani_hazard_footprint(clean_exposure_df, intensity_scale=s)
        df_vuln = apply_vulnerability_to_portfolio(df_hazard)
        df_loss = calculate_financial_losses(df_vuln)

        total_gul = df_loss["total_ground_up_loss"].sum()
        total_gross = df_loss["gross_insured_loss"].sum()
        tiv = df_loss["total_tiv"].sum()
        mean_mdr = df_loss["mean_damage_ratio"].mean()
        mean_wind = df_loss["max_wind_kmh"].mean()

        pct_label = f"{(s - 1.0) * 100:+.0f}%" if s != 1.0 else "Baseline (1.0x)"
        results.append({
            "experiment": "Intensity Scaling",
            "parameter_value": s,
            "scenario_label": pct_label,
            "mean_wind_speed_kmh": round(mean_wind, 1),
            "mean_portfolio_mdr": round(mean_mdr, 4),
            "ground_up_loss_crores": round(total_gul / 1e7, 2),
            "gross_insured_loss_crores": round(total_gross / 1e7, 2),
            "loss_cost_pct": round((total_gul / tiv) * 100.0, 2),
            "ground_up_loss_inr": total_gul
        })

    df_res = pd.DataFrame(results)
    baseline_loss = df_res.loc[df_res["parameter_value"] == 1.0, "ground_up_loss_inr"].values[0]
    df_res["delta_loss_pct"] = np.round(((df_res["ground_up_loss_inr"] - baseline_loss) / baseline_loss) * 100.0, 2)
    return df_res

def run_vulnerability_mitigation_sensitivity(clean_exposure_df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates loss reduction under proactive building retrofitting
    (upgrading roofs, storm ties, hurricane shutters on 0%, 25%, 50%, 75%, 100% of buildings).
    """
    print("[Sensitivity] Running Vulnerability Retrofitting Experiment (0% to 100%)...")
    retrofit_ratios = [0.0, 0.25, 0.50, 0.75, 1.00]
    results = []

    # Baseline hazard footprint
    df_hazard = compute_fani_hazard_footprint(clean_exposure_df)

    for r in retrofit_ratios:
        df_vuln = apply_vulnerability_to_portfolio(df_hazard, retrofit_ratio=r)
        df_loss = calculate_financial_losses(df_vuln)

        total_gul = df_loss["total_ground_up_loss"].sum()
        tiv = df_loss["total_tiv"].sum()
        mean_mdr = df_loss["mean_damage_ratio"].mean()

        results.append({
            "experiment": "Vulnerability Retrofitting",
            "parameter_value": r,
            "scenario_label": f"{int(r * 100)}% Retrofitted",
            "mean_portfolio_mdr": round(mean_mdr, 4),
            "ground_up_loss_crores": round(total_gul / 1e7, 2),
            "loss_cost_pct": round((total_gul / tiv) * 100.0, 2),
            "ground_up_loss_inr": total_gul
        })

    df_res = pd.DataFrame(results)
    baseline_loss = df_res.loc[df_res["parameter_value"] == 0.0, "ground_up_loss_inr"].values[0]
    df_res["avoided_loss_crores"] = np.round((baseline_loss - df_res["ground_up_loss_inr"]) / 1e7, 2)
    df_res["loss_reduction_pct"] = np.round(((baseline_loss - df_res["ground_up_loss_inr"]) / baseline_loss) * 100.0, 2)
    return df_res

def run_deductible_structure_sensitivity(baseline_loss_df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates net insurer loss vs retained loss under varying deductible regimes (0%, 2%, 5%, 10%).
    """
    print("[Sensitivity] Running Policy Deductible Experiment (0% to 10%)...")
    deductible_pcts = [0.00, 0.02, 0.05, 0.10]
    results = []

    tiv = baseline_loss_df["total_tiv"].sum()
    total_gul = baseline_loss_df["total_ground_up_loss"].sum()

    for d_pct in deductible_pcts:
        df_temp = baseline_loss_df.copy()
        # Set deductible to specified % of building value
        df_temp["deductible_inr"] = np.round(df_temp["building_tiv"] * d_pct, 2)
        loss_above_ded = np.maximum(0.0, df_temp["total_ground_up_loss"] - df_temp["deductible_inr"])
        df_temp["gross_insured_loss"] = np.minimum(df_temp["policy_limit_inr"], loss_above_ded)
        df_temp["retained_loss"] = df_temp["total_ground_up_loss"] - df_temp["gross_insured_loss"]

        gross_sum = df_temp["gross_insured_loss"].sum()
        retained_sum = df_temp["retained_loss"].sum()

        results.append({
            "experiment": "Deductible Sensitivity",
            "deductible_rate_pct": f"{int(d_pct * 100)}%",
            "total_gul_crores": round(total_gul / 1e7, 2),
            "gross_insured_loss_crores": round(gross_sum / 1e7, 2),
            "retained_by_policyholder_crores": round(retained_sum / 1e7, 2),
            "insurer_share_pct": round((gross_sum / total_gul) * 100.0, 2),
            "policyholder_share_pct": round((retained_sum / total_gul) * 100.0, 2)
        })

    return pd.DataFrame(results)

def execute_all_sensitivity_experiments(clean_exposure_df: pd.DataFrame,
                                        baseline_loss_df: pd.DataFrame) -> dict:
    """
    Runs all 4 sensitivity experiments and exports consolidated tables.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df_track = run_track_shift_sensitivity(clean_exposure_df)
    df_intensity = run_intensity_scaling_sensitivity(clean_exposure_df)
    df_mitigation = run_vulnerability_mitigation_sensitivity(clean_exposure_df)
    df_deductible = run_deductible_structure_sensitivity(baseline_loss_df)

    df_track.to_csv(RESULTS_DIR / "sensitivity_track_shift.csv", index=False)
    df_intensity.to_csv(RESULTS_DIR / "sensitivity_intensity_scaling.csv", index=False)
    df_mitigation.to_csv(RESULTS_DIR / "sensitivity_vulnerability_mitigation.csv", index=False)
    df_deductible.to_csv(RESULTS_DIR / "sensitivity_deductibles.csv", index=False)

    print(f"[Sensitivity] Successfully completed all sensitivity analyses and saved tables -> {RESULTS_DIR}")

    return {
        "track_shift": df_track,
        "intensity": df_intensity,
        "mitigation": df_mitigation,
        "deductible": df_deductible
    }

if __name__ == "__main__":
    pass
