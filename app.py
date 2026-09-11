import io
import base64
from PIL import Image
import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import MeasureControl
from streamlit_folium import st_folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
from rasterio.crs import CRS
import numpy as np
import matplotlib.colors as mcolors
from branca.element import Element
from shapely.geometry import box

st.set_page_config(
    layout="wide",
    page_title="Syria Climate Hazard Explorer",
    page_icon="🌍",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { --primary-color: #1f78b4 !important; }
    div[data-baseweb="checkbox"] > div[aria-checked="true"],
    div[data-baseweb="checkbox"] div[aria-checked="true"],
    [data-testid="stCheckbox"] div[data-baseweb="checkbox"] > div {
        background-color: #1f78b4 !important;
        border-color: #1f78b4 !important;
    }
    div[data-baseweb="checkbox"]:hover > div[aria-checked="true"] {
        background-color: #1665a0 !important;
        border-color: #1665a0 !important;
        box-shadow: 0 0 0 3px rgba(31,120,180,0.28) !important;
    }
    div[data-baseweb="checkbox"] div[aria-checked="true"] svg,
    div[data-baseweb="checkbox"] div[aria-checked="true"] path {
        fill: white !important; stroke: white !important;
    }
    div[data-baseweb="radio"] div[aria-checked="true"] {
        background-color: #1f78b4 !important;
        border-color: #1f78b4 !important;
    }
    div[data-baseweb="radio"] div[aria-checked="true"] > div {
        background-color: #fff !important;
    }
    .block-container { padding-top: 1.2rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }
    h1 { color: #0f172a !important; font-weight: 700 !important; letter-spacing: -0.4px; margin-bottom: 0.2rem !important; }
    .developer-tag { font-size: 0.95rem; font-weight: 600; color: #1f78b4; margin-bottom: 0.4rem; }
    .subtitle { color: #64748b; font-size: 0.95rem; margin-bottom: 1.2rem; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stExpander {
        background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px;
    }
    iframe { border-radius: 12px !important; box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important; }
    .footer-note { color: #94a3b8; font-size: 0.8rem; margin-top: 0.8rem; }
</style>
""", unsafe_allow_html=True)

DEFAULT_BINS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
DUST_BINS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
FROST_BINS = [0, 0.1, 1, 5, 10, 20, 30, 50, 70, 100]

COLOR_SCHEMES = {
    "drought": [
        "#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c",
        "#fc4e2a", "#e31a1c", "#bd0026", "#800026", "#4a0018"
    ],
    "flood": [
        "#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a",
        "#ef3b2c", "#cb181d", "#a50f15", "#67000d", "#400008"
    ],
    "dust": [
        "#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8",
        "#fee090", "#fdae61", "#f46d43", "#d7191c", "#a50026"
    ],
    "windstorm": [
        "#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8",
        "#fee090", "#fdae61", "#f46d43", "#d7191c", "#a50026"
    ],
    "cropland_fire": [
        "#2b83ba", "#52b1b3", "#7fa2b6", "#abdda4", "#cbe6a3",
        "#ffffbf", "#fdae61", "#f46d43", "#d7191c", "#a50026"
    ],
    "forest_fire": [
        "#005a32", "#238b45", "#41ab5d", "#74c476", "#a1d99b",
        "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026", "#800026"
    ],
    "waterspout": [
        "#e5e7eb", "#2563eb", "#38bdf8", "#4ade80", "#a3e635",
        "#facc15", "#f97316", "#ef4444", "#dc2626", "#991b1b"
    ],
    "spring_heat": [
        "#ffffe5", "#fff7bc", "#fee391", "#fec44f", "#fe9929",
        "#ec7014", "#cc4c02", "#993404", "#662506", "#3f1503"
    ],
    "summer_heat": [
        "#ffffcc", "#ffeb99", "#ffcc66", "#ffaa33", "#ff8800",
        "#e65500", "#cc2200", "#990000", "#660000", "#400000"
    ],
    "spring_frost": [
        "#ffffcc", "#ffebaa", "#ffaa88", "#ff66aa", "#e633cc",
        "#b300ff", "#8800cc", "#550099", "#330066", "#1a0033"
    ]
}

HAZARD_METADATA = {
    "drought": {
        "title": "Meteorological Drought Hazard",
        "description": "Reflects climate-driven conditions of long-term precipitation deficit and high atmospheric evaporative demand.",
        "indicators": "Normalized SPI (Standardized Precipitation Index), LST-Derived TCI (Temperature Condition Index), PET Anomalies (Potential Evapotranspiration), precipitation decrease, temperature increase, and actual evaporation decrease.",
        "spatial": "Concentrated primarily in northeastern Syria (Al-Hasakeh) and northern zones (Aleppo), with moderate-to-high hazard pockets in central, western, and southern regions (Daraa, As-Sweida)."
    },
    "flood": {
        "title": "Flood Hazard",
        "description": "Measures physical susceptibility to riverine and flash flooding from short-duration, high-intensity rainfall.",
        "indicators": "JRC 100-year flood depth, river influence, Topographic Wetness Index (TWI), land cover flood susceptibility, flow accumulation, inverted slope, extreme daily rainfall (Rx1day), soil water content (0–15 cm), clay content, and projected changes in annual runoff/heavy precipitation.",
        "spatial": "High hazard areas are located along major river systems, low-lying lands, and flash-flood-prone semi-arid regions (including parts of the Badia)."
    },
    "spring_heat": {
        "title": "Spring Heatwave Hazard (March–April)",
        "description": "Evaluates early-season extreme heat during key phenological crop stages such as flowering and early grain filling.",
        "indicators": "Derived from ERA5-Land (2015–2025) and CMIP6 NEX-GDDP ACCESS-CM2 projections (SSP5-8.5, 2040–2060) relative to the 1981–2010 baseline.",
        "spatial": "Highest hazards occur in inland, northeastern regions, and northwestern Aleppo. Coastal and mountainous areas exhibit lower hazard levels."
    },
    "summer_heat": {
        "title": "Summer Heatwave Hazard (July–August)",
        "description": "Evaluates peak seasonal cumulative heat stress coinciding with the critical growth stages of summer irrigated crops.",
        "indicators": "Derived from ERA5-Land (2015–2025) and CMIP6 NEX-GDDP ACCESS-CM2 projections (SSP5-8.5, 2040–2060) relative to the 1981–2010 baseline.",
        "spatial": "Widespread high to very high hazard levels across northeastern and southern Syria (Daraa, As-Sweida, Rural Damascus), with moderate levels even along the coast."
    },
    "spring_frost": {
        "title": "Spring Frost Hazard (March–April)",
        "description": "Measures freezing temperature risk (minimum temperature ≤ 0°C) during sensitive crop emergence and flowering periods.",
        "indicators": "Derived from ERA5-Land (2015–2025) and CMIP6 NEX-GDDP ACCESS-CM2 projections (SSP5-8.5, 2040–2060) relative to the 1981–2010 baseline.",
        "spatial": "High hazard levels concentrate in elevated mountain terrains and inland valleys where cold air accumulates."
    },
    "dust": {
        "title": "Sand and Dust Storms Hazard",
        "description": "Captures severe wind-driven dust emission potential and transboundary atmospheric dust concentration.",
        "indicators": "Dust storm records, MODIS AOD, Sentinel-5P AAI, MERRA-2 dust, inverse NDVI, and ensemble wind frequency.",
        "spatial": "Highest hazard levels concentrate in eastern Syria (Deir Ezzor Governorate) extending into central regions."
    },
    "windstorm": {
        "title": "Windstorm Hazard",
        "description": "Identifies exposure to large-scale extreme wind speeds capable of causing structural damage and severe soil erosion.",
        "indicators": "Multi-model ensemble processing using ERA5, MERRA-2, FLDAS, and CFSv2 wind speed datasets through normalization.",
        "spatial": "Peak hazard centers around Al-Bishri Mountain (south of Ar-Raqqa and west of Deir Ezzor) and parts of southern Syria (As-Sweida and Rural Damascus)."
    },
    "waterspout": {
        "title": "Waterspout Hazard (Coastal Zone)",
        "description": "Evaluates localized marine wind-vortex hazards occurring along the Mediterranean shoreline.",
        "indicators": "GIS-based Euclidean distance analysis and terrain elevation derived from SRTM DEM (30 m) combined with recorded waterspout events.",
        "spatial": "Strictly confined to the immediate coastal strip of Latakia and Tartous Governorates, decreasing rapidly inland."
    },
    "cropland_fire": {
        "title": "Cropland Fire Hazard",
        "description": "Evaluates seasonal fire risk in agricultural fields (wheat and barley focus) during the summer harvest period (May–July).",
        "indicators": "Multi-factor analysis integrating LST, NDVI, Fire Weather Index (FWI), wind speed, proximity to roads and settlements, and cropland extent mask.",
        "spatial": "High susceptibility across major irrigation schemes in Aleppo, Ar-Raqqa, and Deir Ezzor, as well as rainfed fields in southern Al-Hasakeh, eastern Hama, and Homs."
    },
    "forest_fire": {
        "title": "Forest Fire Hazard",
        "description": "Assesses wildfire susceptibility within dense forested areas based on terrain, fuel load, and climate indicators.",
        "indicators": "Multi-criteria composite methodology integrating NDVI, LST, FWI, slope, canopy height, forest extent mask, wind speed, and proximity to urban areas.",
        "spatial": "Concentrated in interior mountainous zones of western Homs, western Hama, eastern Tartous, and northern Latakia."
    }
}


@st.cache_data
def load_data(filepath):
    return gpd.read_parquet(filepath)


@st.cache_data
def get_outside_mask(_syria_gdf):
    syria_4326 = _syria_gdf.to_crs(epsg=4326)
    syria_geom = syria_4326.geometry.union_all()
    
    outer_box = box(20.0, 20.0, 50.0, 50.0)
    outside_geom = outer_box.difference(syria_geom)
    
    return gpd.GeoDataFrame(geometry=[outside_geom], crs="EPSG:4326")


@st.cache_data
def load_raster_overlay(
    filepath,
    cmap_colors=("#ffffcc", "#ff9900", "#cc0000"),
    bins=None
):
    with rasterio.open(filepath) as src:
        dst_crs = CRS.from_epsg(4326)
        src_crs = src.crs

        nodata_val = src.nodata

        if src_crs != dst_crs:
            transform, width, height = calculate_default_transform(
                src_crs, dst_crs, src.width, src.height, *src.bounds
            )
            data = np.full((height, width), np.nan, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=data,
                src_transform=src.transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
                src_nodata=nodata_val,
                dst_nodata=np.nan
            )
            west, south, east, north = array_bounds(height, width, transform)
        else:
            data = src.read(1).astype(np.float32)
            if nodata_val is not None:
                data[data == nodata_val] = np.nan
            west, south, east, north = array_bounds(data.shape[0], data.shape[1], src.transform)

        bounds = [[south, west], [north, east]]

    nan_mask = np.isnan(data)

    palette_rgb = [mcolors.to_rgba(c) for c in cmap_colors]
    palette_uint8 = (np.array(palette_rgb) * 255).astype(np.uint8)

    active_bins = bins if bins is not None else DEFAULT_BINS
    binned = np.digitize(data, active_bins) - 1
    binned = np.clip(binned, 0, len(cmap_colors) - 1)

    colored_uint8 = palette_uint8[binned]
    colored_uint8[nan_mask] = [0, 0, 0, 0]

    img = Image.fromarray(colored_uint8, mode='RGBA')
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=6)
    png_data = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')

    return png_data, bounds


def get_name_field(gdf):
    candidates = [
        "NAME", "name", "Name", "NAME_EN", "name_en", "NAME_1", "NAME_2", "NAME_3",
        "ADM1_EN", "ADM2_EN", "ADM3_EN", "ADM1_NAME", "ADM2_NAME", "ADM3_NAME",
        "admin_name", "ADMIN_NAME", "governorate", "district", "subdistrict",
        "NAME_AR", "name_ar"
    ]
    for c in candidates:
        if c in gdf.columns:
            return c
    for c in gdf.columns:
        if c.lower() == "geometry":
            continue
        if gdf[c].dtype == object or str(gdf[c].dtype).startswith("string"):
            return c
    return None


def add_named_geojson(m, gdf, layer_name, style_fn, marker=None, show_name=True):
    name_field = get_name_field(gdf) if show_name else None
    tooltip = popup = None
    if name_field:
        tooltip = folium.GeoJsonTooltip(
            fields=[name_field], aliases=[""], sticky=True,
            style=("background:white;color:#1e293b;font-family:sans-serif;"
                   "font-size:13px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;")
        )
        popup = folium.GeoJsonPopup(
            fields=[name_field], aliases=["Name"], labels=True,
            style="font-family:sans-serif;font-size:13px;"
        )
    kwargs = dict(name=layer_name, style_function=style_fn, tooltip=tooltip, popup=popup)
    if marker is not None:
        kwargs["marker"] = marker
    folium.GeoJson(gdf, **kwargs).add_to(m)


def classify_water_bodies(gdf):
    text_cols = [c for c in gdf.columns if c.lower() in (
        "type", "category", "class", "name", "name_en", "hydro_type",
        "wat_type", "water_type", "featurecla", "fclass", "descriptio",
        "descript", "remark", "notes"
    ) or "type" in c.lower() or "name" in c.lower() or "class" in c.lower()]
    if not text_cols:
        return gdf.copy(), gdf.iloc[0:0].copy()
    def is_sabkha_row(row):
        parts = []
        for c in text_cols:
            val = row.get(c)
            if val is not None and str(val).strip() and str(val).lower() != "nan":
                parts.append(str(val).lower())
        joined = " ".join(parts)
        return any(k in joined for k in (
            "sabkha", "sabkhat", "sabkhah", "sebkha", "sebkah",
            "salt lake", "salt flat", "salt pan", "playa", "saline"
        ))
    mask_series = gdf.apply(is_sabkha_row, axis=1)
    return gdf[~mask_series].copy(), gdf[mask_series].copy()


def generate_discrete_legend(title, colors, opacity):
    color_blocks = "".join([
        f'<div style="background:{c}; height:13px; width:18px;"></div>'
        for c in reversed(colors)
    ])
    total_height = len(colors) * 13

    return f"""
        <div style="margin-bottom: 16px;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 8px; font-size: 12px;">{title}</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="display: flex; flex-direction: column; border: 1px solid #94a3b8; border-radius: 3px; overflow: hidden;">
                    {color_blocks}
                </div>
                <div style="display: flex; flex-direction: column; justify-content: space-between; height: {total_height}px; font-size: 11px; font-weight: 600; color: #334155;">
                    <div>↑ High</div>
                    <div style="font-size: 10px; color: #64748b; font-weight: normal;">▲ Increase</div>
                    <div>↓ Low</div>
                </div>
            </div>
            <div style="margin-top: 6px; font-size: 10px; color: #94a3b8;">Opacity: {int(opacity * 100)}%</div>
        </div>
    """


st.title("Syria Climate Hazard Explorer")
st.markdown('<div class="developer-tag">Developed by Khaled Haider (FAOSY)</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Classified climate-hazard maps for Syria: <b>meteorological drought</b>, <b>flood</b>, '
    '<b>sand and dust storms</b>, <b>windstorm</b>, <b>cropland fire</b>, <b>forest fire</b>, <b>waterspout</b>, and <b>temperature extremes</b> (spring/summer heatwaves and spring frost). '
    'Use the <b>ruler tool</b> (top-left on the map) to measure distances.</p>',
    unsafe_allow_html=True
)

syria_boundary = load_data("data/Vector_Parquet/Syria_Admin0_National-Level.parquet")

with st.sidebar:
    st.markdown("### 🎛️ Controls")
    st.caption("👤 **Developer:** Khaled Haider (FAOSY)")

    with st.expander("🌡️ Climate Hazard", expanded=True):
        st.caption("Select climate hazard layers to display:")
        show_drought = st.checkbox("**Meteorological Drought Hazard**", value=True)
        show_flood = st.checkbox("**Flood Hazard**", value=False)
        show_dust = st.checkbox("**Sand and Dust Storms Hazard**", value=False)
        show_windstorm = st.checkbox("**Windstorm Hazard**", value=False)
        show_cropland_fire = st.checkbox("**Cropland Fire Hazard**", value=False)
        show_forest_fire = st.checkbox("**Forest Fire Hazard**", value=False)
        show_waterspout = st.checkbox("**Waterspout Hazard**", value=False)
        show_spring_heat = st.checkbox("**Spring Heatwave (Mar–Apr)**", value=False)
        show_summer_heat = st.checkbox("**Summer Heatwave (Jul–Aug)**", value=False)
        show_spring_frost = st.checkbox("**Spring Frost (Mar–Apr)**", value=False)

        st.markdown("---")
        with st.expander("🎚️ Adjust Opacities", expanded=False):
            drought_opacity = st.slider("Drought opacity", 0.1, 1.0, 0.95, 0.05, key="drought_opacity")
            flood_opacity = st.slider("Flood opacity", 0.1, 1.0, 0.95, 0.05, key="flood_opacity")
            dust_opacity = st.slider("Dust hazard opacity", 0.1, 1.0, 0.95, 0.05, key="dust_opacity")
            windstorm_opacity = st.slider("Windstorm opacity", 0.1, 1.0, 0.95, 0.05, key="windstorm_opacity")
            cropland_fire_opacity = st.slider("Cropland fire opacity", 0.1, 1.0, 0.95, 0.05, key="cropland_fire_opacity")
            forest_fire_opacity = st.slider("Forest fire opacity", 0.1, 1.0, 0.95, 0.05, key="forest_fire_opacity")
            waterspout_opacity = st.slider("Waterspout opacity", 0.1, 1.0, 0.95, 0.05, key="waterspout_opacity")
            spring_heat_opacity = st.slider("Spring heatwave opacity", 0.1, 1.0, 0.95, 0.05, key="spring_heat_opacity")
            summer_heat_opacity = st.slider("Summer heatwave opacity", 0.1, 1.0, 0.95, 0.05, key="summer_heat_opacity")
            spring_frost_opacity = st.slider("Spring frost opacity", 0.1, 1.0, 0.95, 0.05, key="spring_frost_opacity")

    with st.expander("🗺️ Administrative Boundaries", expanded=True):
        show_poly_l0 = st.checkbox("National Boundary (L0)", value=True)
        show_poly_l1 = st.checkbox("Governorates (L1)", value=True)
        show_poly_l2 = st.checkbox("Districts (L2)", value=False)
        show_poly_l3 = st.checkbox("Subdistricts (L3)", value=False)

    with st.expander("📍 Administrative Centers", expanded=False):
        show_center_l1 = st.checkbox("Governorate Centers (L1)", value=True)
        show_center_l2 = st.checkbox("District Centers (L2)", value=False)
        show_center_l3 = st.checkbox("Subdistrict Centers (L3)", value=False)

    with st.expander("💧 Hydrology", expanded=True):
        show_rivers = st.checkbox("Main Rivers", value=False)
        show_water_bodies = st.checkbox("Water Bodies (Reservoirs + Sabkha)", value=False)

    with st.expander("🖼️ Base Map", expanded=False):
        basemap_option = st.radio(
            "Select base layer",
            ["None", "OpenStreetMap", "Google Maps", "Google Satellite"],
            index=0
        )

m = folium.Map(
    location=[34.8021, 38.9968],
    zoom_start=7,
    tiles=None,
    control_scale=True,
    prefer_canvas=True,
    zoom_control=True
)

MeasureControl(
    position="topleft",
    primary_length_unit="kilometers",
    secondary_length_unit="meters",
    primary_area_unit="sqkilometers",
    secondary_area_unit="hectares",
).add_to(m)

if basemap_option == "OpenStreetMap":
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", control=True).add_to(m)
elif basemap_option == "Google Maps":
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps", name="Google Maps", control=True
    ).add_to(m)
elif basemap_option == "Google Satellite":
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite", name="Google Satellite", control=True
    ).add_to(m)

poly_paths = {
    "L0": "data/Vector_Parquet/Syria_Admin0_National-Level.parquet",
    "L1": "data/Vector_Parquet/Syria_Admin1_Governorate-Level.parquet",
    "L2": "data/Vector_Parquet/Syria_Admin2_District-Level.parquet",
    "L3": "data/Vector_Parquet/Syria_Admin3_Subdistrict-Level.parquet",
}
center_paths = {
    "L1": "data/Vector_Parquet/Syria_Admin1_Governorate-Center.parquet",
    "L2": "data/Vector_Parquet/Syria_Admin2_District-Center.parquet",
    "L3": "data/Vector_Parquet/Syria_Admin3_Subdistrict-Center.parquet",
}

legend_blocks = []
active_hazards = []

# --- Raster Hazard Layers ---
if show_drought:
    active_hazards.append("drought")
    drought_img, drought_bounds = load_raster_overlay(
        "data/Raster/Drought_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["drought"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=drought_img, bounds=drought_bounds, opacity=drought_opacity,
        name="<b>Meteorological Drought Hazard</b>", interactive=False, zindex=1
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Meteorological Drought", COLOR_SCHEMES["drought"], drought_opacity)
    )

if show_flood:
    active_hazards.append("flood")
    flood_img, flood_bounds = load_raster_overlay(
        "data/Raster/Flood_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["flood"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=flood_img, bounds=flood_bounds, opacity=flood_opacity,
        name="<b>Flood Hazard</b>", interactive=False, zindex=2
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Flood Hazard", COLOR_SCHEMES["flood"], flood_opacity)
    )

if show_dust:
    active_hazards.append("dust")
    dust_img, dust_bounds = load_raster_overlay(
        "data/Raster/Dust_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["dust"],
        bins=DUST_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=dust_img, bounds=dust_bounds, opacity=dust_opacity,
        name="<b>Sand & Dust Storms Hazard</b>", interactive=False, zindex=3
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Sand & Dust Storms", COLOR_SCHEMES["dust"], dust_opacity)
    )

if show_windstorm:
    active_hazards.append("windstorm")
    windstorm_img, windstorm_bounds = load_raster_overlay(
        "data/Raster/Ensemble_Wind_Index.tif",
        cmap_colors=COLOR_SCHEMES["windstorm"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=windstorm_img, bounds=windstorm_bounds, opacity=windstorm_opacity,
        name="<b>Windstorm Hazard</b>", interactive=False, zindex=4
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Windstorm Hazard", COLOR_SCHEMES["windstorm"], windstorm_opacity)
    )

if show_cropland_fire:
    active_hazards.append("cropland_fire")
    cropland_fire_img, cropland_fire_bounds = load_raster_overlay(
        "data/Raster/Fire_Hazard_for_Cropland.tif",
        cmap_colors=COLOR_SCHEMES["cropland_fire"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=cropland_fire_img, bounds=cropland_fire_bounds, opacity=cropland_fire_opacity,
        name="<b>Cropland Fire Hazard</b>", interactive=False, zindex=5
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Cropland Fire Hazard", COLOR_SCHEMES["cropland_fire"], cropland_fire_opacity)
    )

if show_forest_fire:
    active_hazards.append("forest_fire")
    forest_fire_img, forest_fire_bounds = load_raster_overlay(
        "data/Raster/Fire_Hazard_for_Forest_land.tif",
        cmap_colors=COLOR_SCHEMES["forest_fire"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=forest_fire_img, bounds=forest_fire_bounds, opacity=forest_fire_opacity,
        name="<b>Forest Fire Hazard</b>", interactive=False, zindex=6
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Forest Fire Hazard", COLOR_SCHEMES["forest_fire"], forest_fire_opacity)
    )
    m.fit_bounds(forest_fire_bounds)

if show_waterspout:
    active_hazards.append("waterspout")
    waterspout_img, waterspout_bounds = load_raster_overlay(
        "data/Raster/Waterspout_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["waterspout"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=waterspout_img, bounds=waterspout_bounds, opacity=waterspout_opacity,
        name="<b>Waterspout Hazard</b>", interactive=False, zindex=7
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Waterspout Hazard", COLOR_SCHEMES["waterspout"], waterspout_opacity)
    )
    m.fit_bounds(waterspout_bounds)

if show_spring_heat:
    active_hazards.append("spring_heat")
    spring_heat_img, spring_heat_bounds = load_raster_overlay(
        "data/Raster/Spring_Hot_Day_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["spring_heat"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=spring_heat_img, bounds=spring_heat_bounds, opacity=spring_heat_opacity,
        name="<b>Spring Heatwave (Mar–Apr)</b>", interactive=False, zindex=8
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Spring Heatwave", COLOR_SCHEMES["spring_heat"], spring_heat_opacity)
    )

if show_summer_heat:
    active_hazards.append("summer_heat")
    summer_heat_img, summer_heat_bounds = load_raster_overlay(
        "data/Raster/Summer_Hot_Day_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["summer_heat"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=summer_heat_img, bounds=summer_heat_bounds, opacity=summer_heat_opacity,
        name="<b>Summer Heatwave (Jul–Aug)</b>", interactive=False, zindex=9
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Summer Heatwave", COLOR_SCHEMES["summer_heat"], summer_heat_opacity)
    )

if show_spring_frost:
    active_hazards.append("spring_frost")
    spring_frost_img, spring_frost_bounds = load_raster_overlay(
        "data/Raster/Spring_Frost_Day_Hazard.tif",
        cmap_colors=COLOR_SCHEMES["spring_frost"],
        bins=FROST_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=spring_frost_img, bounds=spring_frost_bounds, opacity=spring_frost_opacity,
        name="<b>Spring Frost (Mar–Apr)</b>", interactive=False, zindex=10
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Spring Frost", COLOR_SCHEMES["spring_frost"], spring_frost_opacity)
    )

# --- Outside Display Mask (Covers areas outside Syria) ---
outside_mask_gdf = get_outside_mask(syria_boundary)
folium.GeoJson(
    outside_mask_gdf,
    name="Outside Mask",
    style_function=lambda x: {
        "fillColor": "#ffffff",
        "color": "none",
        "fillOpacity": 1.0,
        "weight": 0
    },
    tooltip=None,
    popup=None
).add_to(m)

# --- Administrative & Hydrology Boundaries ---
if show_poly_l0:
    add_named_geojson(
        m, syria_boundary, "National Boundary (L0)",
        lambda x: {"fillColor": "transparent", "color": "#0f172a", "weight": 2.6,
                   "fillOpacity": 0, "opacity": 1.0},
        show_name=False
    )
if show_poly_l3:
    add_named_geojson(
        m, load_data(poly_paths["L3"]), "Subdistricts (L3)",
        lambda x: {"fillColor": "transparent", "color": "#94a3b8", "weight": 0.55,
                   "fillOpacity": 0, "opacity": 0.85}
    )
if show_poly_l2:
    add_named_geojson(
        m, load_data(poly_paths["L2"]), "Districts (L2)",
        lambda x: {"fillColor": "transparent", "color": "#64748b", "weight": 1.0,
                   "fillOpacity": 0, "opacity": 0.9}
    )
if show_poly_l1:
    add_named_geojson(
        m, load_data(poly_paths["L1"]), "Governorates (L1)",
        lambda x: {"fillColor": "transparent", "color": "#334155", "weight": 1.6,
                   "fillOpacity": 0, "opacity": 0.95}
    )

if show_rivers:
    add_named_geojson(
        m, load_data("data/Vector_Parquet/Main_Rivers.parquet"), "Main Rivers",
        lambda x: {"color": "#2563eb", "weight": 1.2, "opacity": 0.95}
    )

if show_water_bodies:
    STYLE_RESERVOIR = lambda x: {
        "fillColor": "#3b82f6", "color": "#1d4ed8", "weight": 1.3,
        "fillOpacity": 0.60, "opacity": 0.95
    }
    STYLE_SABKHA = lambda x: {
        "fillColor": "#d1d5db", "color": "#6b7280", "weight": 1.0,
        "fillOpacity": 0.70, "opacity": 0.9
    }
    gdf_wb = load_data("data/Vector_Parquet/Water_Bodies.parquet")
    gdf_res, gdf_sab = classify_water_bodies(gdf_wb)
    if len(gdf_res) > 0:
        add_named_geojson(m, gdf_res, "Reservoirs / Lakes", STYLE_RESERVOIR)
    if len(gdf_sab) > 0:
        add_named_geojson(m, gdf_sab, "Sabkha / Salt Lakes", STYLE_SABKHA)

if show_center_l3:
    add_named_geojson(
        m, load_data(center_paths["L3"]), "Subdistrict Centers (L3)", lambda x: {},
        marker=folium.CircleMarker(radius=3, color="#be185d", fill=True,
                                   fill_color="#ec4899", fill_opacity=0.9, weight=1)
    )
if show_center_l2:
    add_named_geojson(
        m, load_data(center_paths["L2"]), "District Centers (L2)", lambda x: {},
        marker=folium.CircleMarker(radius=4, color="#5b21b6", fill=True,
                                   fill_color="#8b5cf6", fill_opacity=0.9, weight=1)
    )
if show_center_l1:
    add_named_geojson(
        m, load_data(center_paths["L1"]), "Governorate Centers (L1)", lambda x: {},
        marker=folium.CircleMarker(radius=5.5, color="#c2410c", fill=True,
                                   fill_color="#f59e0b", fill_opacity=0.95, weight=1.5)
    )

# --- Floating Continuous Vertical Ramp Legend ---
if legend_blocks:
    combined_legend = f"""
    <div style="
        position: fixed; bottom: 26px; right: 26px; width: 180px; max-height: 70vh; overflow-y: auto;
        background: rgba(255,255,255,0.97); z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12px; border: 1px solid #cbd5e1; border-radius: 10px;
        padding: 14px 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    ">
        {"".join(legend_blocks)}
    </div>
    """
    m.get_root().html.add_child(Element(combined_legend))

folium.LayerControl(position="topright", collapsed=True).add_to(m)

# --- Layout Rendering ---
map_col, info_col = st.columns([4.2, 1.2], gap="medium")
with map_col:
    st_folium(
        m, width="100%", height=680,
        use_container_width=True
    )

with info_col:
    st.markdown("#### ℹ️ Hazard Layer Metadata")
    if not active_hazards:
        st.caption("No climate hazard layer currently selected.")
    else:
        for key in active_hazards:
            meta = HAZARD_METADATA[key]
            with st.expander(f"**{meta['title']}**", expanded=False):
                st.markdown(f"**Description:** {meta['description']}")
                st.markdown(f"**Indicators / Methodology:** {meta['indicators']}")
                st.markdown(f"**Spatial Highlights:** {meta['spatial']}")

st.markdown(
    '<p class="footer-note">'
    '<b>Syria Climate Hazard Explorer</b> | Developed by <b>Khaled Haider (FAOSY)</b> | '
    'Classified Hazards: Meteorological Drought, Flood, Sand & Dust Storms, Windstorm, Cropland Fire, Forest Fire, Waterspout, '
    'Spring Heatwave, Summer Heatwave, and Spring Frost.'
    '</p>',
    unsafe_allow_html=True
)
