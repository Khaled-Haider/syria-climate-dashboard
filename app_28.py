import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import MeasureControl
from streamlit_folium import st_folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
from rasterio.crs import CRS
from rasterio.mask import mask
import numpy as np
import matplotlib.colors as mcolors
from branca.element import Element

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
    .subtitle { color: #64748b; font-size: 0.95rem; margin-bottom: 1.2rem; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stExpander {
        background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px;
    }
    iframe { border-radius: 12px !important; box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important; }
    .info-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 16px 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); min-height: 120px;
    }
    .info-card h4 { margin: 0 0 8px 0; color: #0f172a; font-size: 0.95rem; }
    .info-card p { margin: 0; color: #475569; font-size: 0.9rem; line-height: 1.45; }
    .info-empty { color: #94a3b8; font-style: italic; }
    .footer-note { color: #94a3b8; font-size: 0.8rem; margin-top: 0.8rem; }
</style>
""", unsafe_allow_html=True)

DEFAULT_BINS = [0, 20, 40, 60, 80, 100]
DUST_BINS = [0, 20, 40, 60, 80, 100]

HAZARD_LABELS = ["Very Low (0–20)", "Low (20–40)", "Moderate (40–60)", "High (60–80)", "Very High (80–100)"]

COLOR_SCHEMES = {
    "drought": ["#ffffcc", "#ffc266", "#ff9900", "#e63900", "#990000"],
    "flood": ["#fee5d9", "#fcae91", "#fb6a4a", "#de2d26", "#a50f15"],
    "spring_heat": ["#ffffcc", "#ffcc66", "#ff9933", "#cc6600", "#8B4513"],
    "summer_heat": ["#ffff99", "#ffcc66", "#ff6600", "#cc0000", "#800000"],
    "spring_frost": ["#ffff99", "#ffcc33", "#ff6699", "#cc33ff", "#330099"],
    "dust": ["#2c7bb6", "#abd9e9", "#ffffbf", "#fdae61", "#d7191c"]
}


@st.cache_data
def load_data(filepath):
    return gpd.read_parquet(filepath)


@st.cache_data
def load_raster_overlay(
    filepath,
    _mask_gdf,
    cmap_colors=("#ffffcc", "#ff9900", "#cc0000"),
    bins=None
):
    """
    Load, clip using boundary mask, reproject to EPSG:4326, and apply discrete class binning.
    """
    with rasterio.open(filepath) as src:
        dst_crs = CRS.from_epsg(4326)
        src_crs = src.crs

        # Ensure vector boundary matches raster CRS before masking
        mask_gdf_proj = _mask_gdf.to_crs(src_crs)
        shapes = [geom for geom in mask_gdf_proj.geometry if geom is not None and not geom.is_empty]

        # Use raster's existing nodata value, or default to 0 for integer datasets
        nodata_val = src.nodata if src.nodata is not None else 0

        out_image, out_transform = mask(
            src, 
            shapes, 
            crop=True, 
            filled=True, 
            nodata=nodata_val
        )
        
        # Cast array to float32 so NaN values can be assigned for out-of-bounds pixels
        data = out_image[0].astype(np.float32)
        if nodata_val is not None:
            data[out_image[0] == nodata_val] = np.nan

        if src_crs != dst_crs:
            transform, width, height = calculate_default_transform(
                src_crs, dst_crs, data.shape[1], data.shape[0],
                *rasterio.transform.array_bounds(data.shape[0], data.shape[1], out_transform)
            )
            data_reprojected = np.full((height, width), np.nan, dtype=np.float32)
            reproject(
                source=data,
                destination=data_reprojected,
                src_transform=out_transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
                src_nodata=np.nan,
                dst_nodata=np.nan
            )
            data = data_reprojected
            west, south, east, north = array_bounds(height, width, transform)
        else:
            west, south, east, north = array_bounds(data.shape[0], data.shape[1], out_transform)

        bounds = [[south, west], [north, east]]

    # Isolate valid data pixels from NaN background mask
    nan_mask = np.isnan(data)

    cmap = mcolors.ListedColormap(cmap_colors)
    active_bins = bins if bins is not None else DEFAULT_BINS
    
    # Classify raster values
    binned = np.digitize(data, active_bins) - 1
    binned = np.clip(binned, 0, len(cmap_colors) - 1)

    # Convert to RGBA
    colored = cmap(binned)

    # Force alpha=0 for background/clipped out pixels
    colored[nan_mask] = [0.0, 0.0, 0.0, 0.0]

    return colored, bounds


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


def generate_discrete_legend(title, colors, labels, opacity):
    items_html = "".join([
        f'<div style="display:flex; align-items:center; margin-bottom: 3px;">'
        f'<span style="background:{c}; width:14px; height:14px; display:inline-block; margin-right:8px; border-radius:2px; border: 1px solid #94a3b8;"></span>'
        f'<span style="color:#334155; font-size:11px;">{lbl}</span>'
        f'</div>'
        for c, lbl in zip(reversed(colors), reversed(labels))
    ])
    return f"""
        <div style="margin-bottom: 14px;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px; font-size: 12.5px;">{title}</div>
            {items_html}
            <div style="margin-top: 4px; font-size: 10.5px; color: #94a3b8;">Opacity: {int(opacity * 100)}%</div>
        </div>
    """


st.title("Syria Climate Hazard Explorer")
st.markdown(
    '<p class="subtitle">Classified climate-hazard maps for Syria: <b>meteorological drought</b>, <b>flood</b>, '
    '<b>sand and dust storms</b>, and <b>temperature extremes</b> (spring/summer heatwaves and spring frost). '
    'Use the <b>ruler tool</b> (top-left on the map) to measure distances. Click features for names.</p>',
    unsafe_allow_html=True
)

syria_boundary = load_data("data/Vector_Parquet/Syria_Admin0_National-Level.parquet")

with st.sidebar:
    st.markdown("### 🎛️ Controls")

    with st.expander("🌡️ Climate Hazard", expanded=True):
        st.caption("Composite hazards classified into discrete risk intervals (0–100).")
        show_drought = st.checkbox("**Meteorological Drought Hazard**", value=True)
        drought_opacity = st.slider("Drought opacity", 0.1, 1.0, 0.90, 0.05, key="drought_opacity")

        st.markdown("")
        show_flood = st.checkbox("**Flood Hazard**", value=False)
        flood_opacity = st.slider("Flood opacity", 0.1, 1.0, 1.00, 0.05, key="flood_opacity")

    with st.expander("🌪️ Sand and Dust Storms", expanded=True):
        st.caption("Environmental hazard driven by dry soil, low vegetation, and wind regimes.")
        show_dust = st.checkbox("**Sand and Dust Storms Hazard**", value=False)
        dust_opacity = st.slider("Dust hazard opacity", 0.1, 1.0, 0.90, 0.05, key="dust_opacity")

    with st.expander("🔥 Temperature Extremes", expanded=True):
        st.caption("Seasonal temperature hazard maps categorized into discrete classes.")
        show_spring_heat = st.checkbox("**Spring Heatwave (Mar–Apr)**", value=False)
        spring_heat_opacity = st.slider("Spring heatwave opacity", 0.1, 1.0, 0.90, 0.05, key="spring_heat_opacity")

        st.markdown("")
        show_summer_heat = st.checkbox("**Summer Heatwave (Jul–Aug)**", value=False)
        summer_heat_opacity = st.slider("Summer heatwave opacity", 0.1, 1.0, 0.90, 0.05, key="summer_heat_opacity")

        st.markdown("")
        show_spring_frost = st.checkbox("**Spring Frost (Mar–Apr)**", value=False)
        spring_frost_opacity = st.slider("Spring frost opacity", 0.1, 1.0, 0.90, 0.05, key="spring_frost_opacity")

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

if show_drought:
    drought_img, drought_bounds = load_raster_overlay(
        "data/Raster/Drought_Hazard.tif",
        _mask_gdf=syria_boundary,
        cmap_colors=COLOR_SCHEMES["drought"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=drought_img, bounds=drought_bounds, opacity=drought_opacity,
        name="<b>Meteorological Drought Hazard</b>", interactive=False, zindex=1
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Meteorological Drought", COLOR_SCHEMES["drought"], HAZARD_LABELS, drought_opacity)
    )

if show_flood:
    flood_img, flood_bounds = load_raster_overlay(
        "data/Raster/Flood_Hazard.tif",
        _mask_gdf=syria_boundary,
        cmap_colors=COLOR_SCHEMES["flood"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=flood_img, bounds=flood_bounds, opacity=flood_opacity,
        name="<b>Flood Hazard</b>", interactive=False, zindex=2
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Flood Hazard", COLOR_SCHEMES["flood"], HAZARD_LABELS, flood_opacity)
    )

if show_dust:
    dust_img, dust_bounds = load_raster_overlay(
        "data/Raster/Dust_Hazard.tif",
        _mask_gdf=syria_boundary,
        cmap_colors=COLOR_SCHEMES["dust"],
        bins=DUST_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=dust_img, bounds=dust_bounds, opacity=dust_opacity,
        name="<b>Sand & Dust Storms Hazard</b>", interactive=False, zindex=3
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Sand & Dust Storms", COLOR_SCHEMES["dust"], HAZARD_LABELS, dust_opacity)
    )

if show_spring_heat:
    spring_heat_img, spring_heat_bounds = load_raster_overlay(
        "data/Raster/Spring_Hot_Day_Hazard.tif",
        _mask_gdf=syria_boundary,
        cmap_colors=COLOR_SCHEMES["spring_heat"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=spring_heat_img, bounds=spring_heat_bounds, opacity=spring_heat_opacity,
        name="<b>Spring Heatwave (Mar–Apr)</b>", interactive=False, zindex=4
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Spring Heatwave", COLOR_SCHEMES["spring_heat"], HAZARD_LABELS, spring_heat_opacity)
    )

if show_summer_heat:
    summer_heat_img, summer_heat_bounds = load_raster_overlay(
        "data/Raster/Summer_Hot_Day_Hazard.tif",
        _mask_gdf=syria_boundary,
        cmap_colors=COLOR_SCHEMES["summer_heat"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=summer_heat_img, bounds=summer_heat_bounds, opacity=summer_heat_opacity,
        name="<b>Summer Heatwave (Jul–Aug)</b>", interactive=False, zindex=5
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Summer Heatwave", COLOR_SCHEMES["summer_heat"], HAZARD_LABELS, summer_heat_opacity)
    )

if show_spring_frost:
    spring_frost_img, spring_frost_bounds = load_raster_overlay(
        "data/Raster/Spring_Frost_Day_Hazard.tif",
        _mask_gdf=syria_boundary,
        cmap_colors=COLOR_SCHEMES["spring_frost"],
        bins=DEFAULT_BINS
    )
    folium.raster_layers.ImageOverlay(
        image=spring_frost_img, bounds=spring_frost_bounds, opacity=spring_frost_opacity,
        name="<b>Spring Frost (Mar–Apr)</b>", interactive=False, zindex=6
    ).add_to(m)
    legend_blocks.append(
        generate_discrete_legend("Spring Frost", COLOR_SCHEMES["spring_frost"], HAZARD_LABELS, spring_frost_opacity)
    )

if legend_blocks:
    combined_legend = f"""
    <div style="
        position: fixed; bottom: 26px; right: 26px; width: 200px; max-height: 70vh; overflow-y: auto;
        background: rgba(255,255,255,0.97); z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12px; border: 1px solid #cbd5e1; border-radius: 10px;
        padding: 14px 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    ">
        {"".join(legend_blocks)}
    </div>
    """
    m.get_root().html.add_child(Element(combined_legend))

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

folium.LayerControl(position="topright", collapsed=True).add_to(m)

map_col, info_col = st.columns([4.2, 1.0], gap="medium")
with map_col:
    map_data = st_folium(
        m, width="100%", height=640,
        returned_objects=["last_object_clicked_popup", "last_object_clicked_tooltip"],
        use_container_width=True
    )
with info_col:
    st.markdown("#### 📌 Selected Feature")
    clicked_name = None
    if map_data:
        popup_txt = map_data.get("last_object_clicked_popup")
        tooltip_txt = map_data.get("last_object_clicked_tooltip")
        if popup_txt:
            clicked_name = popup_txt
        elif tooltip_txt:
            clicked_name = tooltip_txt
    if clicked_name:
        st.markdown(
            f'<div class="info-card"><h4>Feature name</h4>'
            f'<p style="font-size:1.05rem;font-weight:600;color:#0f172a;">{clicked_name}</p></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="info-card"><p class="info-empty">'
            'Click any polygon or point on the map to display its name here.'
            '</p></div>',
            unsafe_allow_html=True
        )

st.markdown(
    '<p class="footer-note">'
    'Classified Hazards: Meteorological Drought, Flood, Sand & Dust Storms, Spring Heatwave, '
    'Summer Heatwave, and Spring Frost mapped across discrete risk categories.'
    '</p>',
    unsafe_allow_html=True
)