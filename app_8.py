import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
import numpy as np
import matplotlib.colors as mcolors
from branca.element import Element

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Syria Climate Hazard Explorer",
    page_icon="🌍",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# Theme & CSS – blue accent
# ─────────────────────────────────────────────────────────────
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
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        margin-bottom: 8px;
    }

    iframe { border-radius: 12px !important; box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important; }

    .info-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        min-height: 120px;
    }
    .info-card h4 { margin: 0 0 8px 0; color: #0f172a; font-size: 0.95rem; }
    .info-card p { margin: 0; color: #475569; font-size: 0.9rem; line-height: 1.45; }
    .info-empty { color: #94a3b8; font-style: italic; }

    .footer-note { color: #94a3b8; font-size: 0.8rem; margin-top: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data(filepath):
    return gpd.read_parquet(filepath)

@st.cache_data
def load_raster_overlay(filepath):
    with rasterio.open(filepath) as src:
        dst_crs = CRS.from_epsg(4326)
        if src.crs != dst_crs:
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            data = np.empty((height, width), dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest
            )
            west, bottom = transform * (0, height)
            east, top = transform * (width, 0)
            bounds = [[bottom, west], [top, east]]
            nodata = src.nodata
        else:
            data = src.read(1).astype(float)
            nodata = src.nodata
            bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
        if nodata is not None:
            data[data == nodata] = np.nan

    cmap = mcolors.LinearSegmentedColormap.from_list("drought", ["#ffffcc", "#ff9900", "#cc0000"])
    valid = data[~np.isnan(data)]
    if len(valid) > 0:
        norm = mcolors.Normalize(vmin=np.nanmin(valid), vmax=np.nanmax(valid))
        colored = cmap(norm(data))
    else:
        colored = cmap(data)
    colored[np.isnan(data), 3] = 0.0
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
            fields=[name_field],
            aliases=[""],
            sticky=True,
            style=("background:white;color:#1e293b;font-family:sans-serif;"
                   "font-size:13px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;")
        )
        popup = folium.GeoJsonPopup(
            fields=[name_field],
            aliases=["Name"],
            labels=True,
            style="font-family:sans-serif;font-size:13px;"
        )
    kwargs = dict(name=layer_name, style_function=style_fn, tooltip=tooltip, popup=popup)
    if marker is not None:
        kwargs["marker"] = marker
    folium.GeoJson(gdf, **kwargs).add_to(m)


def classify_water_bodies(gdf):
    """
    Split water bodies into:
      - Reservoirs / lakes / dams  → blue
      - Sabkha / salt lakes        → grey
    """
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

    mask = gdf.apply(is_sabkha_row, axis=1)
    return gdf[~mask].copy(), gdf[mask].copy()


STYLE_RESERVOIR = lambda x: {
    "fillColor": "#3b82f6",
    "color": "#1d4ed8",
    "weight": 1.3,
    "fillOpacity": 0.60,
    "opacity": 0.95
}
STYLE_SABKHA = lambda x: {
    "fillColor": "#d1d5db",
    "color": "#6b7280",
    "weight": 1.0,
    "fillOpacity": 0.70,
    "opacity": 0.9
}


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
st.title("Syria Climate Hazard Explorer")
st.markdown(
    '<p class="subtitle">Explore administrative units, hydrology and drought hazard across Syria. '
    'Click any feature to inspect its name. Use the sidebar to control layers and opacity.</p>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Controls")

    with st.expander("🌡️ Climate Hazard", expanded=True):
        show_drought = st.checkbox("Drought Hazard", value=True)
        drought_opacity = st.slider(
            "Drought opacity", 0.1, 1.0, 0.80, 0.05,
            help="Adjust transparency of the drought raster"
        )

    with st.expander("🗺️ Administrative Boundaries", expanded=True):
        show_poly_l0 = st.checkbox("National Boundary (L0)", value=True)
        show_poly_l1 = st.checkbox("Governorates (L1)", value=True)
        show_poly_l2 = st.checkbox("Districts (L2)", value=False)
        show_poly_l3 = st.checkbox("Subdistricts (L3)", value=False)

    with st.expander("📍 Administrative Centers", expanded=False):
        show_center_l1 = st.checkbox("Governorate Centers (L1)", value=True)
        show_center_l2 = st.checkbox("District Centers (L2)", value=False)
        show_center_l3 = st.checkbox("Subdistrict Centers (L3)", value=False)

    with st.expander("💧 Hydrology", expanded=False):
        show_rivers = st.checkbox("Main Rivers", value=False)
        show_water_bodies = st.checkbox("Water Bodies (Reservoirs + Sabkha)", value=False)

    with st.expander("🖼️ Base Map", expanded=False):
        basemap_option = st.radio(
            "Select base layer",
            ["None", "OpenStreetMap", "Google Maps", "Google Satellite"],
            index=0
        )

    st.markdown("---")
    st.caption(
        "Water bodies are classified into **Reservoirs (blue)** and "
        "**Sabkha / Salt lakes (grey)**. National boundary has no name label."
    )

# ─────────────────────────────────────────────────────────────
# Build map
# ─────────────────────────────────────────────────────────────
m = folium.Map(
    location=[34.8021, 38.9968],
    zoom_start=7,
    tiles=None,
    control_scale=True,
    prefer_canvas=True,
    zoom_control=True
)

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

# Drought raster
if show_drought:
    drought_img, bounds = load_raster_overlay("data/Raster/Drought_Hazard.tif")
    folium.raster_layers.ImageOverlay(
        image=drought_img,
        bounds=bounds,
        opacity=drought_opacity,
        name="Drought Hazard",
        interactive=False,
        zindex=1
    ).add_to(m)

    # Drought legend – lower right
    legend_html = f"""
    <div style="
        position: fixed; bottom: 26px; right: 26px; width: 160px;
        background: rgba(255,255,255,0.96); z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12px; border: 1px solid #cbd5e1; border-radius: 8px;
        padding: 11px 13px; box-shadow: 0 4px 14px rgba(0,0,0,0.11);
    ">
        <div style="font-weight: 600; color: #0f172a; margin-bottom: 8px; font-size: 12.5px;">
            Drought Hazard
        </div>
        <div style="display: flex; align-items: stretch; height: 100px;">
            <div style="
                background: linear-gradient(to top, #ffffcc, #ff9900, #cc0000);
                width: 16px; border-radius: 3px; border: 1px solid #94a3b8;
                margin-right: 10px; flex-shrink: 0;
            "></div>
            <div style="
                display: flex; flex-direction: column; justify-content: space-between;
                color: #334155; font-size: 11px; line-height: 1.25;
            ">
                <span>Very high</span>
                <span style="color: #64748b;">Moderate</span>
                <span>Relatively low</span>
            </div>
        </div>
        <div style="margin-top: 6px; font-size: 10.5px; color: #94a3b8;">
            Opacity: {int(drought_opacity * 100)}%
        </div>
    </div>
    """
    m.get_root().html.add_child(Element(legend_html))

# Administrative polygons
if show_poly_l0:
    add_named_geojson(
        m, load_data(poly_paths["L0"]), "National Boundary (L0)",
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

# Rivers
if show_rivers:
    add_named_geojson(
        m, load_data("data/Vector_Parquet/Main_Rivers.parquet"), "Main Rivers",
        lambda x: {"color": "#2563eb", "weight": 1.2, "opacity": 0.95}
    )

# Water bodies – split into Reservoirs (blue) + Sabkha (grey)
if show_water_bodies:
    gdf_wb = load_data("data/Vector_Parquet/Water_Bodies.parquet")
    gdf_res, gdf_sab = classify_water_bodies(gdf_wb)

    if len(gdf_res) > 0:
        add_named_geojson(m, gdf_res, "Reservoirs / Lakes", STYLE_RESERVOIR)
    if len(gdf_sab) > 0:
        add_named_geojson(m, gdf_sab, "Sabkha / Salt Lakes", STYLE_SABKHA)

    # Water-bodies legend – MIDDLE LOWER (bottom center of the map)
    wb_legend = """
    <div style="
        position: fixed;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        width: 200px;
        background: rgba(255,255,255,0.96);
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 11px 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.11);
        text-align: left;
    ">
        <div style="font-weight: 600; color: #0f172a; margin-bottom: 8px; font-size: 12.5px; text-align: center;">
            Water Bodies
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 6px;">
            <div style="width: 18px; height: 14px; background: #3b82f6; border: 1px solid #1d4ed8;
                        border-radius: 3px; margin-right: 8px; flex-shrink: 0;"></div>
            <span style="color: #334155;">Reservoirs / Lakes</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 18px; height: 14px; background: #d1d5db; border: 1px solid #6b7280;
                        border-radius: 3px; margin-right: 8px; flex-shrink: 0;"></div>
            <span style="color: #334155;">Sabkha / Salt Lakes</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(Element(wb_legend))

# Centers
if show_center_l3:
    add_named_geojson(
        m, load_data(center_paths["L3"]), "Subdistrict Centers (L3)",
        lambda x: {},
        marker=folium.CircleMarker(radius=3, color="#be185d", fill=True,
                                   fill_color="#ec4899", fill_opacity=0.9, weight=1)
    )
if show_center_l2:
    add_named_geojson(
        m, load_data(center_paths["L2"]), "District Centers (L2)",
        lambda x: {},
        marker=folium.CircleMarker(radius=4, color="#5b21b6", fill=True,
                                   fill_color="#8b5cf6", fill_opacity=0.9, weight=1)
    )
if show_center_l1:
    add_named_geojson(
        m, load_data(center_paths["L1"]), "Governorate Centers (L1)",
        lambda x: {},
        marker=folium.CircleMarker(radius=5.5, color="#c2410c", fill=True,
                                   fill_color="#f59e0b", fill_opacity=0.95, weight=1.5)
    )

folium.LayerControl(position="topright", collapsed=True).add_to(m)

# ─────────────────────────────────────────────────────────────
# Main layout
# ─────────────────────────────────────────────────────────────
map_col, info_col = st.columns([4.2, 1.0], gap="medium")

with map_col:
    map_data = st_folium(
        m,
        width="100%",
        height=640,
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

    st.markdown("")
    st.markdown("#### 🧭 Quick tips")
    st.markdown(
        """
        - **Hover** → name tooltip  
        - **Click** → name popup + panel  
        - **L0** has no name label  
        - **Water bodies**:  
          - Reservoirs / Lakes → **blue**  
          - Sabkha / Salt lakes → **grey**  
        - Water-bodies legend is at the **bottom center** of the map  
        """
    )

st.markdown(
    '<p class="footer-note">'
    'Drought hazard: pale yellow = relatively low → deep red = very high. '
    'Water bodies classified into Reservoirs/Lakes (blue) and Sabkha/Salt lakes (grey). '
    'National boundary name is omitted from tooltips/popups.'
    '</p>',
    unsafe_allow_html=True
)
