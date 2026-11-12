"""
QGIS Exporter & Cartographic Layer Generator
Exports catastrophe modeling results to GeoPackage (.gpkg) and GeoJSON formats,
generates wind swath contours, district-level loss choropleths, and QGIS project files (.qgs).
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString
from pathlib import Path
from src.config import GIS_DATA_DIR, RESULTS_DIR, CRS_WGS84
from src.hazard_fani import FANI_IBTRACS_TRACK

def export_qgis_exposure_layers(df_loss: pd.DataFrame):
    """
    Exports the asset-level exposure and loss dataset to GeoPackage (.gpkg) and GeoJSON.
    Includes geometry, TIV, max wind speed, MDR, ground-up loss, gross loss.
    """
    GIS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create GeoDataFrame
    geometry = [Point(xy) for xy in zip(df_loss["longitude"], df_loss["latitude"])]
    gdf = gpd.GeoDataFrame(df_loss, geometry=geometry, crs=CRS_WGS84)

    # Convert complex or timestamp fields if any
    export_cols = [
        "policy_id", "account_id", "location_name", "district", "pincode",
        "construction_code", "occupancy_code", "year_built", "storeys",
        "building_tiv", "contents_tiv", "bi_tiv", "total_tiv",
        "deductible_inr", "policy_limit_inr", "dist_to_coast_km",
        "max_wind_ms", "max_wind_kmh", "max_wind_kt", "hazard_category",
        "mean_damage_ratio", "total_ground_up_loss", "gross_insured_loss",
        "retained_loss", "site_loss_cost_pct", "geometry"
    ]
    gdf_sub = gdf[[c for c in export_cols if c in gdf.columns]]

    # 1. GeoPackage Export (Industry Standard for QGIS)
    gpkg_path = GIS_DATA_DIR / "odisha_exposure_loss.gpkg"
    gdf_sub.to_file(gpkg_path, driver="GPKG", layer="exposure_assets_loss")
    print(f"[QGIS Exporter] Exported GeoPackage layer -> {gpkg_path}")

    # 2. GeoJSON Export (Universal Web / GIS)
    geojson_path = GIS_DATA_DIR / "odisha_exposure_loss.geojson"
    gdf_sub.to_file(geojson_path, driver="GeoJSON")
    print(f"[QGIS Exporter] Exported GeoJSON layer -> {geojson_path}")

    return gdf_sub

def export_cyclone_track_layer():
    """
    Generates QGIS vector layers for Cyclone Fani IBTrACS track (Points & LineString).
    """
    points = []
    line_coords = []
    
    for pt in FANI_IBTRACS_TRACK:
        lon, lat = pt["lon"], pt["lat"]
        line_coords.append((lon, lat))
        points.append({
            "iso_time": pt["iso_time"],
            "stage": pt["stage"],
            "pressure_hpa": pt["pres_hpa"],
            "wind_speed_kt": pt["wspd_kt"],
            "wind_speed_kmh": round(pt["wspd_kt"] * 1.852, 1),
            "rmax_km": pt["rmax_km"],
            "geometry": Point(lon, lat)
        })

    gdf_pts = gpd.GeoDataFrame(points, crs=CRS_WGS84)
    pts_path = GIS_DATA_DIR / "cyclone_fani_track_points.geojson"
    gdf_pts.to_file(pts_path, driver="GeoJSON")

    # Track Line
    line_geom = LineString(line_coords)
    gdf_line = gpd.GeoDataFrame([{
        "storm_name": "Cyclone Fani (2019)",
        "peak_intensity": "Category 5 Equivalent (135 kt)",
        "landfall": "Puri, Odisha (May 3, 2019)",
        "geometry": line_geom
    }], crs=CRS_WGS84)
    line_path = GIS_DATA_DIR / "cyclone_fani_track_path.geojson"
    gdf_line.to_file(line_path, driver="GeoJSON")

    print(f"[QGIS Exporter] Exported Cyclone Fani track points and path to {GIS_DATA_DIR}")

def generate_district_loss_choropleth(df_loss: pd.DataFrame):
    """
    Generates convex/concave hull boundary polygons for each district in the portfolio,
    populated with aggregate TIV, aggregate loss, and mean damage ratio for choropleth thematic mapping.
    """
    # Group by district and compute polygon boundary from asset points
    district_features = []
    
    for district, group in df_loss.groupby("district"):
        coords = group[["longitude", "latitude"]].values
        # Create convex hull or bounding buffer
        pts = [Point(xy) for xy in coords]
        pts_gdf = gpd.GeoSeries(pts)
        hull = pts_gdf.unary_union.convex_hull.buffer(0.08) # Small buffer around assets

        tiv = group["total_tiv"].sum()
        gul = group["total_ground_up_loss"].sum()
        gross = group["gross_insured_loss"].sum()
        mean_mdr = group["mean_damage_ratio"].mean()
        mean_wind = group["max_wind_kmh"].mean()
        asset_count = len(group)

        district_features.append({
            "district": district,
            "asset_count": asset_count,
            "total_tiv_crores": round(tiv / 1e7, 2),
            "ground_up_loss_crores": round(gul / 1e7, 2),
            "gross_insured_loss_crores": round(gross / 1e7, 2),
            "loss_cost_pct": round((gul / tiv) * 100.0, 2),
            "mean_damage_ratio": round(mean_mdr, 4),
            "mean_max_wind_kmh": round(mean_wind, 1),
            "geometry": hull
        })

    gdf_districts = gpd.GeoDataFrame(district_features, crs=CRS_WGS84)
    dist_geojson_path = GIS_DATA_DIR / "district_loss_summary.geojson"
    gdf_districts.to_file(dist_geojson_path, driver="GeoJSON")
    print(f"[QGIS Exporter] Exported district loss summary choropleth layer -> {dist_geojson_path}")

def generate_qgis_project_file():
    """
    Generates a native QGIS Project file (.qgs) in XML format that automatically loads:
      1. Cyclone Fani Track Path
      2. Cyclone Fani Track Points
      3. Exposure Asset Losses (with graduated symbology recommendation)
      4. District Loss Summary Choropleth
    """
    qgs_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="Cyclone Fani Catastrophe Risk Model - Odisha" version="3.28.0">
  <title>Cyclone Fani (2019) Coastal Odisha Portfolio Impact</title>
  <layer-tree-group>
    <customproperties/>
    <layer-tree-layer id="fani_track_pts" name="Cyclone Fani Track Points (IBTrACS)" source="./cyclone_fani_track_points.geojson" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="fani_track_path" name="Cyclone Fani Track Path" source="./cyclone_fani_track_path.geojson" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="exposure_loss" name="Odisha Exposure Assets &amp; Losses" source="./odisha_exposure_loss.geojson" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="district_summary" name="District Loss Choropleth" source="./district_loss_summary.geojson" provider="ogr" expanded="1" checked="Qt::Checked"/>
  </layer-tree-group>
  <projectLayers>
    <maplayer id="fani_track_pts" type="vector">
      <id>fani_track_pts</id>
      <datasource>./cyclone_fani_track_points.geojson</datasource>
      <layername>Cyclone Fani Track Points (IBTrACS)</layername>
      <srs>
        <spatialrefsys><authid>EPSG:4326</authid></spatialrefsys>
      </srs>
    </maplayer>
    <maplayer id="fani_track_path" type="vector">
      <id>fani_track_path</id>
      <datasource>./cyclone_fani_track_path.geojson</datasource>
      <layername>Cyclone Fani Track Path</layername>
      <srs>
        <spatialrefsys><authid>EPSG:4326</authid></spatialrefsys>
      </srs>
    </maplayer>
    <maplayer id="exposure_loss" type="vector">
      <id>exposure_loss</id>
      <datasource>./odisha_exposure_loss.geojson</datasource>
      <layername>Odisha Exposure Assets &amp; Losses</layername>
      <srs>
        <spatialrefsys><authid>EPSG:4326</authid></spatialrefsys>
      </srs>
    </maplayer>
    <maplayer id="district_summary" type="vector">
      <id>district_summary</id>
      <datasource>./district_loss_summary.geojson</datasource>
      <layername>District Loss Choropleth</layername>
      <srs>
        <spatialrefsys><authid>EPSG:4326</authid></spatialrefsys>
      </srs>
    </maplayer>
  </projectLayers>
</qgis>
"""
    qgs_path = GIS_DATA_DIR / "odisha_fani_cat_model.qgs"
    with open(qgs_path, "w", encoding="utf-8") as f:
        f.write(qgs_content)
    print(f"[QGIS Exporter] Created native QGIS project file -> {qgs_path}")

def run_all_qgis_exports(df_loss: pd.DataFrame):
    """
    Executes full suite of GIS exports for QGIS mapping.
    """
    export_qgis_exposure_layers(df_loss)
    export_cyclone_track_layer()
    generate_district_loss_choropleth(df_loss)
    generate_qgis_project_file()
    print("[QGIS Exporter] All spatial layers and QGIS project successfully created!")

if __name__ == "__main__":
    pass
