import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Syria Climate Hazard Dashboard")

st.title("Syria Multi-Hazard Climate Dashboard")
st.markdown("Interactive map displaying Syria's administrative boundaries and baseline hydrology.")

# Sidebar Controls
st.sidebar.header("Map Layers")

st.sidebar.subheader("Administrative Polygons")
admin_poly = st.sidebar.radio(
    "Select Polygon Boundary Level",
    ["None", "National (L0)", "Governorate (L1)", "District (L2)", "Subdistrict (L3)"]
)

st.sidebar.subheader("Administrative Centers")
admin_center = st.sidebar.radio(
    "Select Center Point Level",
    ["None", "Governorate Centers (L1)", "District Centers (L2)", "Subdistrict Centers (L3)"]
)

st.sidebar.subheader("Hydrology Layers")
show_rivers = st.sidebar.checkbox("Main Rivers", value=True)
show_water_bodies = st.sidebar.checkbox("Water Bodies", value=True)

# Map Initialization
m = folium.Map(location=[34.8021, 38.9968], zoom_start=7, tiles="CartoDB positron")

poly_paths = {
    "National (L0)": "data/Vector/Syria_Admin0_National-Level.geojson",
    "Governorate (L1)": "data/Vector/Syria_Admin1_Governorate-Level.geojson",
    "District (L2)": "data/Vector/Syria_Admin2_District-Level.geojson",
    "Subdistrict (L3)": "data/Vector/Syria_Admin3_Subdistrict-Level.geojson",
}

center_paths = {
    "Governorate Centers (L1)": "data/Vector/Syria_Admin1_Governorate-Center.geojson",
    "District Centers (L2)": "data/Vector/Syria_Admin2_District-Center.geojson",
    "Subdistrict Centers (L3)": "data/Vector/Syria_Admin3_Subdistrict-Center.geojson",
}

if admin_poly != "None" and admin_poly in poly_paths:
    gdf_poly = gpd.read_file(poly_paths[admin_poly])
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

if admin_center != "None" and admin_center in center_paths:
    gdf_center = gpd.read_file(center_paths[admin_center])
    folium.GeoJson(
        gdf_center,
        name=admin_center,
        marker=folium.CircleMarker(radius=4, color="red", fill=True, fill_color="red")
    ).add_to(m)

if show_rivers:
    gdf_rivers = gpd.read_file("data/Vector/Main_Rivers.geojson")
    folium.GeoJson(
        gdf_rivers,
        name="Main Rivers",
        style_function=lambda x: {"color": "#1f78b4", "weight": 2}
    ).add_to(m)

if show_water_bodies:
    gdf_water = gpd.read_file("data/Vector/Water_Bodies.geojson")
    folium.GeoJson(
        gdf_water,
        name="Water Bodies",
        style_function=lambda x: {"fillColor": "#a6cee3", "color": "#1f78b4", "weight": 1, "fillOpacity": 0.6}
    ).add_to(m)

st_folium(m, width="100%", height=650)