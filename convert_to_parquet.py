import os
import glob
import geopandas as gpd

# Paths
input_dir = "data/Vector"
output_dir = "data/Vector_Parquet"

# Create output folder if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Find all GeoJSON files
geojson_files = glob.glob(os.path.join(input_dir, "*.geojson"))

print(f"Found {len(geojson_files)} GeoJSON files to convert...\n")

for filepath in geojson_files:
    filename = os.path.basename(filepath)
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}.parquet")
    
    print(f"Converting: {filename} -> {base_name}.parquet")
    
    # Read GeoJSON and save as GeoParquet
    gdf = gpd.read_file(filepath)
    gdf.to_parquet(output_path)

print("\nAll files successfully converted to GeoParquet!")