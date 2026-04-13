import geopandas as gpd
import pandas as pd
import os

# Paths
processed_path = "data/processed"
master_csv = os.path.join(processed_path, "master_population_subzone.csv")
subzone_geojson = os.path.join(processed_path, "subzone_with_population.geojson")
electoral_2020 = os.path.join(processed_path, "electoral_boundaries_2020.geojson")
electoral_2025 = os.path.join(processed_path, "electoral_boundaries_2025.geojson")

def check_csv(csv_path):
    df = pd.read_csv(csv_path)
    print(f"\nChecking {csv_path}:")
    print(f"Shape: {df.shape}")
    missing = df.isnull().sum().sum()
    print(f"Total missing values: {missing}")
    if 'Number' in df.columns:
        duplicates = df['Number'].duplicated().sum()
        print(f"Duplicate subzone IDs in 'Number': {duplicates}")
    return df

def check_geojson(geojson_path, expected_crs="EPSG:4326"):
    gdf = gpd.read_file(geojson_path)
    print(f"\nChecking {geojson_path}:")
    print(f"Shape: {gdf.shape}")
    print(f"CRS: {gdf.crs}")
    print(f"Expected CRS: {expected_crs}")
    if '_feature_id' in gdf.columns:
        duplicates = gdf['_feature_id'].duplicated().sum()
        print(f"Duplicate _feature_id: {duplicates}")
    missing_pop = gdf['pop_total'].isnull().sum() if 'pop_total' in gdf.columns else 'N/A'
    print(f"Missing pop_total: {missing_pop}")
    return gdf

# Run checks
master_df = check_csv(master_csv)
subzone_gdf = check_geojson(subzone_geojson)
electoral_2020_gdf = check_geojson(electoral_2020)
electoral_2025_gdf = check_geojson(electoral_2025)