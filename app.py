import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Syria Climate Hazard Dashboard")

st.title("Syria Multi-Hazard Climate Dashboard")
st.markdown("Interactive map displaying Syria's administrative boundaries and baseline hydrology.")

# 2. Fast Caching for GeoParquet Files
@st.cache_data
def load_data(filepath):
    return gpd.read_parquet(filepath)

# 3. Sidebar Controls
st.sidebar.header("Map Layers")

# Administrative Polygons Control
st.sidebar.subheader("Administrative Polygons")
admin_poly = st.sidebar.radio(
    "Select Polygon Boundary Level",
    ["None", "National (L0)", "Governorate (L1)", "District (L2)", "Subdistrict (L3)"]
)

# Administrative Centroids Control
st.sidebar.subheader("Administrative Centers")
admin_center = st.sidebar.radio(
    "Select Center Point Level",
    ["None", "Governorate Centers (L1)", "District Centers (L2)", "Subdistrict Centers (L3)"]
)

# Hydrology Overlays
st.sidebar.subheader("Hydrology Layers")
show_rivers = st.sidebar.checkbox("Main Rivers", value=True)
show_water_bodies = st.sidebar.checkbox("Water Bodies", value=True)

# 4. Initialize Folium Map centered on Syria
m = folium.Map(location=[34.8021, 38.9968], zoom_start=7, tiles="CartoDB positron")

# 5. GeoParquet Data File Paths
poly_paths = {
    "National (L0)": "data/Vector_Parquet/Syria_Admin0_National-Level.parquet",
    "Governorate (L1)": "data/Vector_Parquet/Syria_Admin1_Governorate-Level.parquet",
    "District (L2)": "data/Vector_Parquet/Syria_Admin2_District-Level.parquet",
    "Subdistrict (L3)": "data/Vector_Parquet/Syria_Admin3_Subdistrict-Level.parquet",
}

center_paths = {
    "Governorate Centers (L1)": "data/Vector_Parquet/Syria_Admin1_Governorate-Center.parquet",
    "District Centers (L2)": "data/Vector_Parquet/Syria_Admin2_District-Center.parquet",
    "Subdistrict Centers (L3)": "data/Vector_Parquet/Syria_Admin3_Subdistrict-Center.parquet",
}

# 6. Render Layers on Map
# Add Selected Polygon Layer
if admin_poly != "None" and admin_poly in poly_paths:
    gdf_poly = load_data(poly_paths[admin_poly])
    folium.GeoJson(
        gdf_poly,
        name=admin_poly,
        style_function=lambda x: {
            "fillColor": "#3186cc",
            "color": "#000000",
            "weight": 1.5,
            "fillOpacity": 0.1,
        }
    ).add_to(m)

# Add Selected Center Layer
if admin_center != "None" and admin_center in center_paths:
    gdf_center = load_data(center_paths[admin_center])
    folium.GeoJson(
        gdf_center,
        name=admin_center,
        marker=folium.CircleMarker(radius=4, color="red", fill=True, fill_color="red")
    ).add_to(m)

# Add Hydrology Layers
if show_rivers:
    gdf_rivers = load_data("data/Vector_Parquet/Main_Rivers.parquet")
    folium.GeoJson(
        gdf_rivers,
        name="Main Rivers",
        style_function=lambda x: {"color": "#1f78b4", "weight": 2}
    ).add_to(m)

if show_water_bodies:
    gdf_water = load_data("data/Vector_Parquet/Water_Bodies.parquet")
    folium.GeoJson(
        gdf_water,
        name="Water Bodies",
        style_function=lambda x: {"fillColor": "#a6cee3", "color": "#1f78b4", "weight": 1, "fillOpacity": 0.6}
    ).add_to(m)

# 7. Display Map in Streamlit
st_folium(m, width="100%", height=650, returned_objects=[])