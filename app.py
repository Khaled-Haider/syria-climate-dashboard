import streamlit as st
import geopandas as gpd
import pydeck as pdk

# 1. Page Setup
st.set_page_config(layout="wide", page_title="Syria Climate Hazard Dashboard")

st.title("Syria Multi-Hazard Climate Dashboard")
st.markdown("Interactive GPU-accelerated map displaying Syria's administrative boundaries and baseline hydrology.")

# 2. Fast Memory Caching for GeoParquet Files
@st.cache_data
def load_data(filepath):
    return gpd.read_parquet(filepath)

# 3. Sidebar Controls
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

# 4. Parquet File Paths
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

# 5. Build PyDeck WebGL Layers List
layers = []

# Admin Polygons Layer
if admin_poly != "None" and admin_poly in poly_paths:
    gdf_poly = load_data(poly_paths[admin_poly])
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            gdf_poly,
            id="admin-polygons",
            opacity=0.4,
            stroked=True,
            filled=True,
            get_fill_color=[49, 134, 204, 60],
            get_line_color=[0, 0, 0, 200],
            get_line_width=150,
            pickable=True
        )
    )

# Admin Centers Layer
if admin_center != "None" and admin_center in center_paths:
    gdf_center = load_data(center_paths[admin_center])
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            gdf_center,
            id="admin-centers",
            pickable=True,
            filled=True,
            get_fill_color=[230, 25, 75, 255],
            get_point_radius=3000,
            point_radius_min_pixels=4
        )
    )

# Hydrology: Water Bodies
if show_water_bodies:
    gdf_water = load_data("data/Vector_Parquet/Water_Bodies.parquet")
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            gdf_water,
            id="water-bodies",
            opacity=0.6,
            stroked=True,
            filled=True,
            get_fill_color=[166, 206, 227, 180],
            get_line_color=[31, 120, 180, 255],
            get_line_width=100,
            pickable=True
        )
    )

# Hydrology: Main Rivers
if show_rivers:
    gdf_rivers = load_data("data/Vector_Parquet/Main_Rivers.parquet")
    layers.append(
        pdk.Layer(
            "GeoJsonLayer",
            gdf_rivers,
            id="main-rivers",
            stroked=True,
            filled=False,
            get_line_color=[31, 120, 180, 255],
            get_line_width=300,
            line_width_min_pixels=2,
            pickable=True
        )
    )

# 6. Set Camera Viewport Centered over Syria
view_state = pdk.ViewState(
    latitude=34.8021,
    longitude=38.9968,
    zoom=6.5,
    pitch=0
)

# 7. Render PyDeck WebGL Chart
st.pydeck_chart(
    pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip={"html": "<b>Feature Attributes:</b><br/>{properties}"}
    )
)