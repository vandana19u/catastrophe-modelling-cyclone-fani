"""
Hazard Simulation Engine - Cyclone Fani (2019) from NOAA IBTrACS
Implements the Holland (1980/2010) parametric radial wind field model to compute
maximum sustained wind footprints across the coastal Odisha exposure portfolio.
Compatible with CLIMADA Hazard format and QGIS geospatial exports.
"""
import math
import numpy as np
import pandas as pd
from pathlib import Path
from src.config import HAZARD_DATA_DIR, FANI_LANDFALL_PURI

# Historical NOAA IBTrACS 3-Hourly Track for Cyclone FANI (2019026N03089 / Bay of Bengal)
# Covers intense approach, landfall at Puri (May 3 03:00 UTC), and inland tracking across Odisha
FANI_IBTRACS_TRACK = [
    {"iso_time": "2019-05-02 00:00:00", "lat": 16.00, "lon": 84.70, "pres_hpa": 932, "wspd_kt": 135, "rmax_km": 28.0, "stage": "Offshore Cat 4/5 Peak"},
    {"iso_time": "2019-05-02 06:00:00", "lat": 16.70, "lon": 84.80, "pres_hpa": 935, "wspd_kt": 130, "rmax_km": 28.0, "stage": "Approaching Andhra/Odisha"},
    {"iso_time": "2019-05-02 12:00:00", "lat": 17.50, "lon": 84.90, "pres_hpa": 935, "wspd_kt": 125, "rmax_km": 30.0, "stage": "Parallel to Ganjam Coast"},
    {"iso_time": "2019-05-02 18:00:00", "lat": 18.50, "lon": 85.20, "pres_hpa": 936, "wspd_kt": 120, "rmax_km": 30.0, "stage": "Offshore Chilika"},
    {"iso_time": "2019-05-03 00:00:00", "lat": 19.30, "lon": 85.50, "pres_hpa": 937, "wspd_kt": 115, "rmax_km": 32.0, "stage": "Pre-Landfall Eye Wall Near Puri"},
    {"iso_time": "2019-05-03 03:30:00", "lat": 19.80, "lon": 85.82, "pres_hpa": 938, "wspd_kt": 115, "rmax_km": 32.0, "stage": "LANDFALL AT PURI"},
    {"iso_time": "2019-05-03 06:00:00", "lat": 20.25, "lon": 85.83, "pres_hpa": 955, "wspd_kt": 95,  "rmax_km": 36.0, "stage": "Over Bhubaneswar / Khordha"},
    {"iso_time": "2019-05-03 09:00:00", "lat": 20.50, "lon": 85.95, "pres_hpa": 968, "wspd_kt": 80,  "rmax_km": 40.0, "stage": "Over Cuttack"},
    {"iso_time": "2019-05-03 12:00:00", "lat": 20.85, "lon": 86.30, "pres_hpa": 980, "wspd_kt": 65,  "rmax_km": 45.0, "stage": "Weakening Over Jajpur/Bhadrak"},
    {"iso_time": "2019-05-03 15:00:00", "lat": 21.20, "lon": 86.70, "pres_hpa": 988, "wspd_kt": 55,  "rmax_km": 50.0, "stage": "Over Balasore"},
    {"iso_time": "2019-05-03 18:00:00", "lat": 21.60, "lon": 87.20, "pres_hpa": 993, "wspd_kt": 45,  "rmax_km": 55.0, "stage": "Entering West Bengal Border"},
    {"iso_time": "2019-05-04 00:00:00", "lat": 22.50, "lon": 88.10, "pres_hpa": 998, "wspd_kt": 35,  "rmax_km": 60.0, "stage": "Dissipating Over Gangetic Delta"}
]

class HollandWindFieldModel:
    """
    Implements the Holland (1980 / 2010) Parametric Radial Wind Field Model:
    V(r) = sqrt( (B / rho) * (Rmax / r)^B * delta_P * exp(-(Rmax / r)^B) + (r * f / 2)^2 ) - (r * f / 2)
    Plus asymmetric forward motion vector and boundary layer surface friction adjustment.
    """
    def __init__(self, p_env_hpa: float = 1010.0, air_density: float = 1.15, default_b: float = 1.35):
        self.p_env_hpa = p_env_hpa  # Ambient environmental pressure (hPa)
        self.rho = air_density      # Air density (kg/m^3) at sea level in tropics
        self.default_b = default_b  # Holland shape parameter

    def haversine_distance_bearing(self, lat1, lon1, lat2, lon2):
        """
        Calculates distance (km) and bearing (degrees clockwise from North)
        from point 1 (eye) to point 2 (exposure location).
        """
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlam = np.radians(lon2 - lon1)

        # Distance
        a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0)**2
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        dist_km = 6371.0 * c

        # Bearing
        y = np.sin(dlam) * np.cos(phi2)
        x = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlam)
        bearing_rad = np.arctan2(y, x)
        bearing_deg = (np.degrees(bearing_rad) + 360.0) % 360.0

        return dist_km, bearing_deg

    def compute_wind_at_point(self, storm_lat: float, storm_lon: float, p_c: float,
                              r_max_km: float, b_param: float, trans_speed_ms: float,
                              trans_bearing_deg: float, exp_lat: float, exp_lon: float) -> float:
        """
        Computes 1-minute sustained 10m surface wind speed (m/s) at an exposure location.
        """
        r_km, bearing_to_point = self.haversine_distance_bearing(storm_lat, storm_lon, exp_lat, exp_lon)
        
        # Avoid division by zero at the exact center of the eye
        if r_km < 1.0:
            return 8.0 # Calm eye conditions

        r_m = r_km * 1000.0
        rmax_m = r_max_km * 1000.0
        delta_p_pa = max(500.0, (self.p_env_hpa - p_c) * 100.0) # Convert hPa to Pa

        # Coriolis parameter f = 2 * omega * sin(phi)
        omega = 7.2921e-5
        f_coriolis = 2.0 * omega * math.sin(math.radians(storm_lat))

        # Holland Gradient Wind Equation
        exp_term = math.exp(-((rmax_m / r_m) ** b_param))
        pressure_grad_term = (b_param / self.rho) * ((rmax_m / r_m) ** b_param) * delta_p_pa * exp_term
        coriolis_term = (r_m * f_coriolis / 2.0) ** 2

        v_gradient = math.sqrt(pressure_grad_term + coriolis_term) - (r_m * f_coriolis / 2.0)

        # Boundary layer 10m surface reduction factor (~0.80 - 0.85 over coastal land/water)
        surface_factor = 0.82
        v_surface = v_gradient * surface_factor

        # Asymmetric forward motion addition (higher winds in the right-forward quadrant in Northern Hemisphere)
        rel_angle = math.radians(bearing_to_point - trans_bearing_deg)
        asymmetry_factor = trans_speed_ms * 0.55 * math.cos(rel_angle)
        
        v_total_ms = max(0.0, v_surface + asymmetry_factor)
        return v_total_ms

def compute_fani_hazard_footprint(exposure_df: pd.DataFrame, track_points: list = None,
                                 track_shift_km_east: float = 0.0,
                                 intensity_scale: float = 1.0) -> pd.DataFrame:
    """
    Runs the full Cyclone Fani storm track across all exposure points.
    Computes the maximum sustained wind speed (m/s, km/h, kt) experienced by each location.
    
    Supports sensitivity parameters:
      - track_shift_km_east: Shifts the storm track laterally (e.g. +25km East or -25km West).
      - intensity_scale: Multiplies delta_P / max wind speed (e.g. 1.10 for +10% intense cyclone).
    """
    if track_points is None:
        track_points = FANI_IBTRACS_TRACK.copy()

    holland_model = HollandWindFieldModel()
    results_df = exposure_df.copy()

    # Apply track shift if requested (lateral longitude shift in degrees ~ km / (111 * cos(lat)))
    processed_track = []
    for i, pt in enumerate(track_points):
        pt_copy = pt.copy()
        
        # Scale central pressure drop delta_P
        orig_delta_p = 1010.0 - pt_copy["pres_hpa"]
        scaled_delta_p = orig_delta_p * intensity_scale
        pt_copy["pres_hpa"] = 1010.0 - scaled_delta_p
        pt_copy["wspd_kt"] = pt_copy["wspd_kt"] * intensity_scale

        if track_shift_km_east != 0.0:
            lon_shift_deg = track_shift_km_east / (111.32 * math.cos(math.radians(pt_copy["lat"])))
            pt_copy["lon"] += lon_shift_deg

        processed_track.append(pt_copy)

    # Compute forward translation speed and bearing between track steps
    for i in range(len(processed_track)):
        p_curr = processed_track[i]
        if i < len(processed_track) - 1:
            p_next = processed_track[i + 1]
            t1 = pd.to_datetime(p_curr["iso_time"])
            t2 = pd.to_datetime(p_next["iso_time"])
            dt_hours = (t2 - t1).total_seconds() / 3600.0
            dist_km, bearing = holland_model.haversine_distance_bearing(p_curr["lat"], p_curr["lon"], p_next["lat"], p_next["lon"])
            trans_speed_ms = (dist_km * 1000.0) / (dt_hours * 3600.0) if dt_hours > 0 else 5.0
            p_curr["trans_speed_ms"] = trans_speed_ms
            p_curr["trans_bearing"] = bearing
        else:
            p_curr["trans_speed_ms"] = processed_track[i - 1]["trans_speed_ms"]
            p_curr["trans_bearing"] = processed_track[i - 1]["trans_bearing"]

    # Vectorized computation of max sustained wind across all track timesteps
    exp_lats = results_df["latitude"].values
    exp_lons = results_df["longitude"].values
    n_assets = len(results_df)

    max_winds_ms = np.zeros(n_assets, dtype=np.float64)

    for step_idx, step in enumerate(processed_track):
        s_lat = step["lat"]
        s_lon = step["lon"]
        p_c = step["pres_hpa"]
        r_max = step["rmax_km"]
        b_val = 1.35
        v_trans = step["trans_speed_ms"]
        b_trans = step["trans_bearing"]

        # Calculate for each asset
        for i in range(n_assets):
            v_point = holland_model.compute_wind_at_point(
                storm_lat=s_lat, storm_lon=s_lon, p_c=p_c,
                r_max_km=r_max, b_param=b_val,
                trans_speed_ms=v_trans, trans_bearing_deg=b_trans,
                exp_lat=exp_lats[i], exp_lon=exp_lons[i]
            )
            if v_point > max_winds_ms[i]:
                max_winds_ms[i] = v_point

    results_df["max_wind_ms"] = np.round(max_winds_ms, 2)
    results_df["max_wind_kmh"] = np.round(max_winds_ms * 3.6, 2)
    results_df["max_wind_kt"] = np.round(max_winds_ms * 1.94384, 2)

    # Saffir-Simpson / IMD Cyclone Intensity Categorization
    def categorize_wind(v_kt):
        if v_kt >= 113: return "Category 4/5 (Extremely Severe / Super)"
        if v_kt >= 96:  return "Category 3 (Very Severe Cyclonic Storm)"
        if v_kt >= 83:  return "Category 2 (Severe Cyclonic Storm)"
        if v_kt >= 64:  return "Category 1 (Cyclonic Storm)"
        if v_kt >= 34:  return "Tropical Storm / Deep Depression"
        return "Below Gale Force (<34 kt)"

    results_df["hazard_category"] = results_df["max_wind_kt"].apply(categorize_wind)
    return results_df

def export_hazard_track_layers():
    """
    Exports NOAA IBTrACS Cyclone Fani track points and line to GeoJSON / CSV
    for QGIS visualization and cataloging.
    """
    HAZARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_track = pd.DataFrame(FANI_IBTRACS_TRACK)
    track_csv = HAZARD_DATA_DIR / "fani_ibtracs_track.csv"
    df_track.to_csv(track_csv, index=False)
    print(f"[Hazard] Exported Cyclone Fani IBTrACS track points -> {track_csv}")

    # Build GeoJSON FeatureCollection for QGIS
    features = []
    coords_line = []
    for pt in FANI_IBTRACS_TRACK:
        lon, lat = pt["lon"], pt["lat"]
        coords_line.append([lon, lat])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "iso_time": pt["iso_time"],
                "stage": pt["stage"],
                "pressure_hpa": pt["pres_hpa"],
                "wind_speed_kt": pt["wspd_kt"],
                "wind_speed_kmh": round(pt["wspd_kt"] * 1.852, 1),
                "rmax_km": pt["rmax_km"]
            }
        })

    # Line feature for storm path
    features.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords_line},
        "properties": {
            "storm_name": "Cyclone Fani",
            "season": 2019,
            "basin": "North Indian Ocean",
            "peak_category": "Category 5 Equivalent",
            "landfall_location": "Puri, Odisha"
        }
    })

    geojson_obj = {"type": "FeatureCollection", "features": features}
    track_geojson_path = HAZARD_DATA_DIR / "fani_ibtracs_track.geojson"
    import json
    with open(track_geojson_path, "w") as f:
        json.dump(geojson_obj, f, indent=2)
    print(f"[Hazard] Exported Cyclone Fani GeoJSON track -> {track_geojson_path}")

if __name__ == "__main__":
    export_hazard_track_layers()
