"""
Master Pipeline Orchestrator - Odisha Cyclone Fani Catastrophe Risk Model
Executes the full end-to-end cat modeling workflow:
  Exposure Generation -> SQL Scrubbing -> Geopy Geocoding -> Hazard Simulation ->
  Vulnerability Curves -> Financial Engine -> Sensitivity Testing -> QGIS Exports
"""
import time
import pandas as pd
import matplotlib
matplotlib.use("Agg") # Non-interactive headless backend
import matplotlib.pyplot as plt
from pathlib import Path
from src.config import RESULTS_DIR, REPORTS_DIR, RAW_DATA_DIR
from src.exposure_generator import main as generate_raw_exposure
from src.sql_scrubber import run_sql_scrubbing
from src.geocoder import geocode_exposure_portfolio
from src.hazard_fani import compute_fani_hazard_footprint, export_hazard_track_layers
from src.vulnerability import apply_vulnerability_to_portfolio, generate_vulnerability_lookup_table
from src.financial_engine import calculate_financial_losses, generate_portfolio_loss_summary
from src.sensitivity import execute_all_sensitivity_experiments
from src.qgis_exporter import run_all_qgis_exports
from src.climada_oasis_bridge import export_oasis_oed_files, export_climada_exposure_file

def generate_visual_analytics(df_loss: pd.DataFrame, sensitivity_results: dict):
    """
    Generates high-resolution analytics plots for technical reporting.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. Plot: Spatial Exposure and Wind Speed vs Loss Cost
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Wind speed vs Loss Cost scatter
    scatter = axes[0].scatter(
        df_loss["max_wind_kmh"], 
        df_loss["site_loss_cost_pct"],
        c=df_loss["mean_damage_ratio"], 
        cmap="YlOrRd", 
        alpha=0.6, 
        edgecolors="none",
        s=25
    )
    axes[0].set_title("Cyclone Fani: Sustained Wind Speed vs. Site Loss Cost", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Peak 1-Min Sustained Wind Speed (km/h)", fontsize=11)
    axes[0].set_ylabel("Ground Up Loss Cost (% of TIV)", fontsize=11)
    cbar = plt.colorbar(scatter, ax=axes[0])
    cbar.set_label("Mean Damage Ratio (MDR)", fontsize=10)

    # Losses by Construction Type
    c_summary = df_loss.groupby("construction_code")["total_ground_up_loss"].sum() / 1e7
    c_summary = c_summary.sort_values(ascending=False)
    axes[1].bar(c_summary.index, c_summary.values, color=["#d95f02", "#e7298a", "#7570b3", "#1b9e77", "#66a61e"])
    axes[1].set_title("Ground-Up Losses by Building Construction Type", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Construction Code", fontsize=11)
    axes[1].set_ylabel("Total Ground-Up Loss (Crores INR)", fontsize=11)
    for i, v in enumerate(c_summary.values):
        axes[1].text(i, v + 2, f"INR {v:.1f} Cr", ha="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    chart1_path = REPORTS_DIR / "cat_model_wind_and_construction_losses.png"
    plt.savefig(chart1_path, dpi=200)
    plt.close()
    print(f"[Analytics] Saved wind and construction loss chart -> {chart1_path}")

    # 2. Plot: Sensitivity Experiments
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # A. Track Shift Sensitivity
    df_ts = sensitivity_results["track_shift"]
    axes[0, 0].plot(df_ts["parameter_value"], df_ts["ground_up_loss_crores"], marker="o", color="#b2182b", linewidth=2.5)
    axes[0, 0].axvline(0, color="gray", linestyle="--", alpha=0.7, label="Baseline Landfall (Puri)")
    axes[0, 0].set_title("Sensitivity: Lateral Track Shift vs Portfolio Loss", fontsize=11, fontweight="bold")
    axes[0, 0].set_xlabel("Track Shift (km East / West)", fontsize=10)
    axes[0, 0].set_ylabel("Ground Up Loss (Crores INR)", fontsize=10)
    axes[0, 0].legend()

    # B. Intensity Scaling Sensitivity
    df_intens = sensitivity_results["intensity"]
    axes[0, 1].bar(df_intens["scenario_label"], df_intens["ground_up_loss_crores"], color="#2166ac")
    axes[0, 1].set_title("Sensitivity: Cyclone Intensity Scaling (Central Pressure & Wind)", fontsize=11, fontweight="bold")
    axes[0, 1].set_xlabel("Intensity Delta", fontsize=10)
    axes[0, 1].set_ylabel("Ground Up Loss (Crores INR)", fontsize=10)

    # C. Vulnerability Retrofitting Sensitivity
    df_mit = sensitivity_results["mitigation"]
    axes[1, 0].plot(df_mit["parameter_value"] * 100, df_mit["ground_up_loss_crores"], marker="s", color="#1a9850", linewidth=2.5)
    axes[1, 0].set_title("Sensitivity: Proactive Building Retrofitting (Mitigation)", fontsize=11, fontweight="bold")
    axes[1, 0].set_xlabel("% of Portfolio Retrofitted with Cyclone Clips & Shutters", fontsize=10)
    axes[1, 0].set_ylabel("Ground Up Loss (Crores INR)", fontsize=10)

    # D. Deductible Structure Sensitivity
    df_ded = sensitivity_results["deductible"]
    bar_width = 0.35
    x = range(len(df_ded))
    axes[1, 1].bar([i - bar_width/2 for i in x], df_ded["gross_insured_loss_crores"], width=bar_width, label="Insurer Gross Loss", color="#4393c3")
    axes[1, 1].bar([i + bar_width/2 for i in x], df_ded["retained_by_policyholder_crores"], width=bar_width, label="Insured Retained Loss", color="#f4a582")
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(df_ded["deductible_rate_pct"])
    axes[1, 1].set_title("Sensitivity: Policy Deductible Loss Sharing", fontsize=11, fontweight="bold")
    axes[1, 1].set_xlabel("Deductible Rate (% of Building Value)", fontsize=10)
    axes[1, 1].set_ylabel("Loss Amount (Crores INR)", fontsize=10)
    axes[1, 1].legend()

    plt.tight_layout()
    chart2_path = REPORTS_DIR / "cat_model_sensitivity_suite.png"
    plt.savefig(chart2_path, dpi=200)
    plt.close()
    print(f"[Analytics] Saved sensitivity suite charts -> {chart2_path}")

def run_full_pipeline():
    """
    Executes the comprehensive catastrophe risk modeling project.
    """
    start_time = time.time()
    print("=" * 80)
    print("CATASTROPHE RISK MODELING: CYCLONE FANI (2019) ODISHA PORTFOLIO")
    print("ETH Zurich CLIMADA & Oasis LMF Framework Architecture")
    print("=" * 80)

    # Step 1: Exposure Generation
    print("\n--- STEP 1: EXPOSURE PORTFOLIO SIMULATION ---")
    generate_raw_exposure()

    # Step 2: SQL Scrubbing & Data Hygiene in SQLite
    print("\n--- STEP 2: SQL DATA SCRUBBING & HYGIENE IN SQLITE ---")
    scrubbing_metrics = run_sql_scrubbing()

    # Step 3: Spatial Geocoding with geopy & Gazetteer
    print("\n--- STEP 3: SPATIAL GEOCODING & COASTAL PROXIMITY (geopy) ---")
    df_clean = geocode_exposure_portfolio()

    # Step 4: NOAA IBTrACS Hazard Track & Holland Windfield
    print("\n--- STEP 4: HAZARD SIMULATION (NOAA IBTrACS CYCLONE FANI) ---")
    export_hazard_track_layers()
    df_hazard = compute_fani_hazard_footprint(df_clean)

    # Step 5: CLIMADA Vulnerability Damage Functions
    print("\n--- STEP 5: VULNERABILITY & DAMAGE MODELING ---")
    generate_vulnerability_lookup_table()
    df_vuln = apply_vulnerability_to_portfolio(df_hazard)

    # Step 6: Catastrophe Financial Engine (GUL, Gross, Retained)
    print("\n--- STEP 6: FINANCIAL ENGINE & ACTUARIAL LOSS ESTIMATION ---")
    df_loss = calculate_financial_losses(df_vuln)
    loss_summary = generate_portfolio_loss_summary(df_loss)

    # Step 7: Sensitivity Analysis
    print("\n--- STEP 7: SENSITIVITY TESTING EXPERIMENTS ---")
    sensitivity_results = execute_all_sensitivity_experiments(df_clean, df_loss)

    # Step 8: QGIS Geospatial Layer Generation
    print("\n--- STEP 8: QGIS CARTOGRAPHIC LAYERS & PROJECT EXPORT ---")
    run_all_qgis_exports(df_loss)

    # Step 9: Oasis LMF OED & CLIMADA Interoperability Bridges
    print("\n--- STEP 9: OASIS LMF OED & CLIMADA EXPORT ---")
    export_oasis_oed_files(df_clean)
    export_climada_exposure_file(df_clean)

    # Step 10: Visual Analytics & Reporting
    print("\n--- STEP 10: ANALYTIC CHARTS & REPORT GENERATION ---")
    generate_visual_analytics(df_loss, sensitivity_results)

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    print(f"Total Portfolio TIV: INR {loss_summary['portfolio_totals']['total_tiv_crores']:.2f} Crores")
    print(f"Total Ground-Up Loss: INR {loss_summary['portfolio_totals']['total_ground_up_loss_crores']:.2f} Crores")
    print(f"Total Gross Insured Loss: INR {loss_summary['portfolio_totals']['total_gross_insured_loss_crores']:.2f} Crores")
    print(f"Overall Portfolio Loss Cost: {loss_summary['portfolio_totals']['portfolio_loss_cost_pct']:.2f}%")
    print("=" * 80)

    return loss_summary

if __name__ == "__main__":
    run_full_pipeline()
