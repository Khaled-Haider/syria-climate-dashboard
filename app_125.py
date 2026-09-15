# Save this file to replace app_110.py or update the relevant sections in your script.

import io
import base64
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
import geopandas as gpd
import folium
from folium.plugins import MousePosition, MeasureControl
from folium import MacroElement
from jinja2 import Template
from streamlit_folium import st_folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds, from_bounds
from rasterio.crs import CRS
from rasterio.features import rasterize
import numpy as np
import matplotlib.colors as mcolors
from branca.element import Element
from shapely.geometry import box

# --- Climate Hazard Explorer Icon Definition ---
HAZARD_SVG_BADGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 48" width="56" height="20">
  <rect width="140" height="48" rx="8" fill="#1f78b4"/>
  <text x="70" y="34" font-family="'Arial Black', 'Impact', sans-serif" font-weight="900" font-size="24" fill="#FFFFFF" text-anchor="middle" letter-spacing="1">HAZARD</text>
</svg>"""
hazard_b64 = base64.b64encode(HAZARD_SVG_BADGE.encode("utf-8")).decode("utf-8")
hazard_icon_uri = f"data:image/svg+xml;base64,{hazard_b64}"
hazard_page_label = f"![HAZARD]({hazard_icon_uri}) Climate Hazard Explorer"

# --- RICCAR Icon Definition ---
RICCAR_SVG_BADGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 48" width="56" height="20">
  <rect width="140" height="48" rx="8" fill="#000000"/>
  <text x="70" y="34" font-family="'Arial Black', 'Impact', sans-serif" font-weight="900" font-size="30" fill="#FFFFFF" text-anchor="middle" letter-spacing="1">RICCAR</text>
</svg>"""
riccar_b64 = base64.b64encode(RICCAR_SVG_BADGE.encode("utf-8")).decode("utf-8")
riccar_icon_uri = f"data:image/svg+xml;base64,{riccar_b64}"
riccar_page_label = f"![RICCAR]({riccar_icon_uri}) Historical & Projected Climate (RICCAR)"

st.set_page_config(
    layout="wide",
    page_title="Syria Climate & Hazard Explorer",
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
    div[data-testid="stRadio"] label p {
        font-size: 18px !important;
        font-weight: 700 !important;
        line-height: 1.3 !important;
        white-space: nowrap !important;
    }
    div[data-testid="stRadio"] label p img {
        vertical-align: middle !important;
        margin-right: 6px !important;
        height: 28px !important;
        width: auto !important;
    }
    /* Hide native scrollbars (main + sidebar) – custom blue bars replace them */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > div,
    section.main, .main,
    [data-testid="stMain"],
    [data-testid="stVerticalBlock"],
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }
    html::-webkit-scrollbar,
    body::-webkit-scrollbar,
    [data-testid="stAppViewContainer"]::-webkit-scrollbar,
    [data-testid="stAppViewContainer"] > div::-webkit-scrollbar,
    section.main::-webkit-scrollbar,
    .main::-webkit-scrollbar,
    [data-testid="stMain"]::-webkit-scrollbar,
    [data-testid="stVerticalBlock"]::-webkit-scrollbar,
    section[data-testid="stSidebar"]::-webkit-scrollbar,
    section[data-testid="stSidebar"] > div::-webkit-scrollbar,
    [data-testid="stSidebarContent"]::-webkit-scrollbar,
    [data-testid="stSidebarUserContent"]::-webkit-scrollbar {
        width: 0 !important;
        height: 0 !important;
        display: none !important;
    }
    .block-container { padding-top: 1.2rem !important; padding-bottom: 1rem !important; max-width: 100% !important; padding-right: 28px !important; }
    h1 { color: #0f172a !important; font-weight: 700 !important; letter-spacing: -0.4px; margin-bottom: 0.2rem !important; }
    .developer-tag { font-size: 0.95rem; font-weight: 600; color: #1f78b4; margin-bottom: 0.4rem; }
    .subtitle { color: #64748b; font-size: 0.95rem; margin-bottom: 1.2rem; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border-right: 1px solid #e2e8f0;
        width: 450px !important;
        min-width: 450px !important;
        max-width: 450px !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 450px !important;
        min-width: 450px !important;
    }
    section[data-testid="stSidebar"] .stExpander {
        background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px;
    }
    /* Larger font for key expander titles (Climate Hazard Layers, Precipitation/Temperature/Water Balance Indicators, etc.) */
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
    section[data-testid="stSidebar"] .streamlit-expanderHeader,
    section[data-testid="stSidebar"] .streamlit-expanderHeader p {
        font-size: 18px !important;
        font-weight: 700 !important;
        line-height: 1.35 !important;
    }
    /* Keep radio / checkbox labels on a single line + larger checkbox labels */
    div[data-testid="stRadio"] label p,
    div[data-testid="stCheckbox"] label p,
    section[data-testid="stSidebar"] label p {
        white-space: nowrap !important;
        overflow: visible !important;
    }
    /* Increase font size of hazard & RICCAR layer checkbox labels (~+3 px) */
    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] label p,
    section[data-testid="stSidebar"] div[data-testid="stCheckbox"] label span,
    section[data-testid="stSidebar"] [data-testid="stCheckbox"] p {
        font-size: 17px !important;
        font-weight: 600 !important;
        line-height: 1.35 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        white-space: nowrap !important;
    }
    iframe { border-radius: 12px !important; box-shadow: 0 4px 24px rgba(0,0,0,0.07) !important; }
    .footer-note { color: #94a3b8; font-size: 0.8rem; margin-top: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# Custom blue scrollbars (main page + sidebar Navigation) injected into parent page
components.html("""
<script>
(function() {
  var doc = window.parent.document;
  var win = window.parent;

  // Remove previous instances
  ['csb-track', 'csb-side-track'].forEach(function(id) {
    var el = doc.getElementById(id);
    if (el) el.remove();
  });

  // Shared styles (always refresh so width/color updates apply)
  var oldStyle = doc.getElementById('csb-styles');
  if (oldStyle) oldStyle.remove();
  {
    var style = doc.createElement('style');
    style.id = 'csb-styles';
    style.textContent = `
      #csb-track, #csb-side-track {
        position: fixed !important;
        top: 0 !important;
        width: 20px !important;
        height: 100vh !important;
        background: #e2e8f0 !important;
        z-index: 999999 !important;
        margin: 0 !important;
        padding: 0 !important;
      }
      #csb-track {
        right: 0 !important;
        border-left: 1px solid #94a3b8 !important;
      }
      #csb-side-track {
        /* placed on the right edge of the sidebar */
        border-right: 1px solid #94a3b8 !important;
      }
      #csb-thumb, #csb-side-thumb {
        position: absolute !important;
        left: 2px !important;
        width: 16px !important;
        height: 80px !important;
        background: linear-gradient(180deg, #94a3b8 0%, #64748b 45%, #475569 100%) !important;
        border-radius: 8px !important;
        border: 1px solid #64748b !important;
        box-shadow: 0 1px 6px rgba(71,85,105,0.35), inset 0 1px 0 rgba(255,255,255,0.25) !important;
        cursor: grab !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        user-select: none !important;
        touch-action: none !important;
      }
      #csb-thumb:hover, #csb-side-thumb:hover {
        background: linear-gradient(180deg, #a8b4c4 0%, #7b8a9c 45%, #64748b 100%) !important;
      }
      #csb-thumb:active, #csb-side-thumb:active { cursor: grabbing !important; }
      .csb-grip {
        width: 8px; height: 22px;
        display: flex; flex-direction: column; justify-content: space-between;
        pointer-events: none;
      }
      .csb-grip i {
        display: block; height: 2px;
        background: rgba(255,255,255,0.85); border-radius: 1px;
      }
    `;
    doc.head.appendChild(style);
  }

  var THUMB_H = 80;

  function isWin(el) {
    return el === doc.documentElement || el === doc.body || el === doc.scrollingElement;
  }
  function getTop(el) {
    return isWin(el) ? (win.pageYOffset || doc.documentElement.scrollTop || 0) : el.scrollTop;
  }
  function setTop(el, y) {
    if (isWin(el)) win.scrollTo(0, y);
    else el.scrollTop = y;
  }
  function getMax(el) {
    return Math.max(1, (el.scrollHeight || 0) - (el.clientHeight || win.innerHeight));
  }

  function makeScrollbar(trackId, thumbId, getScrollEl, positionTrack) {
    var track = doc.createElement('div');
    track.id = trackId;
    var thumb = doc.createElement('div');
    thumb.id = thumbId;
    thumb.title = 'Drag to scroll';
    thumb.innerHTML = '<div class="csb-grip"><i></i><i></i><i></i></div>';
    track.appendChild(thumb);
    doc.body.appendChild(track);

    if (positionTrack) positionTrack(track);

    var dragging = false;
    var startY = 0;
    var startRatio = 0;

    function syncThumb() {
      try {
        var el = getScrollEl();
        if (!el) return;
        var max = getMax(el);
        var ratio = getTop(el) / max;
        var trackH = track.clientHeight || win.innerHeight;
        var maxTop = Math.max(0, trackH - THUMB_H);
        thumb.style.top = (ratio * maxTop) + 'px';
      } catch (err) {}
    }

    thumb.addEventListener('mousedown', function(e) {
      e.preventDefault();
      e.stopPropagation();
      dragging = true;
      startY = e.clientY;
      var el = getScrollEl();
      startRatio = el ? getTop(el) / getMax(el) : 0;
      doc.body.style.userSelect = 'none';
    });

    win.addEventListener('mousemove', function(e) {
      if (!dragging) return;
      e.preventDefault();
      var trackH = track.clientHeight || win.innerHeight;
      var maxTop = Math.max(1, trackH - THUMB_H);
      var delta = e.clientY - startY;
      var ratio = Math.max(0, Math.min(1, startRatio + delta / maxTop));
      var el = getScrollEl();
      if (el) setTop(el, ratio * getMax(el));
      thumb.style.top = (ratio * maxTop) + 'px';
    });

    win.addEventListener('mouseup', function() {
      dragging = false;
      doc.body.style.userSelect = '';
    });

    track.addEventListener('mousedown', function(e) {
      if (e.target === thumb || thumb.contains(e.target)) return;
      e.preventDefault();
      var trackH = track.clientHeight || win.innerHeight;
      var maxTop = Math.max(1, trackH - THUMB_H);
      var y = e.clientY - track.getBoundingClientRect().top - THUMB_H / 2;
      y = Math.max(0, Math.min(maxTop, y));
      var ratio = y / maxTop;
      var el = getScrollEl();
      if (el) setTop(el, ratio * getMax(el));
      thumb.style.top = y + 'px';
    });

    win.addEventListener('scroll', syncThumb, true);
    doc.addEventListener('scroll', syncThumb, true);
    setInterval(function() {
      if (positionTrack) positionTrack(track);
      syncThumb();
    }, 250);
    setTimeout(syncThumb, 100);
    setTimeout(syncThumb, 500);
    setTimeout(syncThumb, 1500);

    return { track: track, thumb: thumb, sync: syncThumb };
  }

  // ---- MAIN PAGE scrollbar (far right) ----
  function getMainScrollEl() {
    var candidates = [
      doc.querySelector('[data-testid="stAppViewContainer"]'),
      doc.querySelector('section.main'),
      doc.querySelector('.main'),
      doc.querySelector('[data-testid="stMain"]'),
      doc.scrollingElement,
      doc.documentElement,
      doc.body
    ];
    var best = null, bestDelta = 0;
    for (var i = 0; i < candidates.length; i++) {
      var el = candidates[i];
      if (!el) continue;
      var delta = (el.scrollHeight || 0) - (el.clientHeight || 0);
      if (delta > bestDelta) { bestDelta = delta; best = el; }
    }
    if (bestDelta < 50) {
      var all = doc.querySelectorAll('div, section, main');
      for (var j = 0; j < all.length; j++) {
        var e = all[j];
        // skip sidebar
        if (e.closest && e.closest('[data-testid="stSidebar"]')) continue;
        var st = win.getComputedStyle(e);
        if ((st.overflowY === 'auto' || st.overflowY === 'scroll') && e.scrollHeight > e.clientHeight + 50) {
          var d = e.scrollHeight - e.clientHeight;
          if (d > bestDelta) { bestDelta = d; best = e; }
        }
      }
    }
    return best || doc.documentElement;
  }

  makeScrollbar('csb-track', 'csb-thumb', getMainScrollEl, null);

  // ---- SIDEBAR (Navigation) scrollbar ----
  function getSidebarScrollEl() {
    var sidebar = doc.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) return null;
    var candidates = [
      sidebar.querySelector('[data-testid="stSidebarContent"]'),
      sidebar.querySelector('[data-testid="stSidebarUserContent"]'),
      sidebar.querySelector('[data-testid="stVerticalBlock"]'),
      sidebar
    ];
    var best = null, bestDelta = 0;
    for (var i = 0; i < candidates.length; i++) {
      var el = candidates[i];
      if (!el) continue;
      var delta = (el.scrollHeight || 0) - (el.clientHeight || 0);
      if (delta > bestDelta) { bestDelta = delta; best = el; }
    }
    // scan inside sidebar
    var all = sidebar.querySelectorAll('div, section');
    for (var j = 0; j < all.length; j++) {
      var e = all[j];
      var st = win.getComputedStyle(e);
      if ((st.overflowY === 'auto' || st.overflowY === 'scroll' || st.overflowY === 'overlay') &&
          e.scrollHeight > e.clientHeight + 20) {
        var d = e.scrollHeight - e.clientHeight;
        if (d > bestDelta) { bestDelta = d; best = e; }
      }
    }
    return best || sidebar;
  }

  function positionSideTrack(track) {
    var sidebar = doc.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) {
      track.style.display = 'none';
      return;
    }
    var rect = sidebar.getBoundingClientRect();
    if (rect.width < 10) {
      track.style.display = 'none';
      return;
    }
    track.style.display = 'block';
    track.style.left = (rect.right - 20) + 'px';
    track.style.right = 'auto';
    track.style.top = rect.top + 'px';
    track.style.height = rect.height + 'px';
  }

  makeScrollbar('csb-side-track', 'csb-side-thumb', getSidebarScrollEl, positionSideTrack);
})();
</script>
""", height=0)

# --- Standardized Color Palettes and Specialized Layer Configurations ---
COLOR_SCHEMES = {
    "drought": [
        "#ffffcc", "#fffae6", "#ffe680", "#ffd94d", 
        "#ffcc33", "#ffb81a", "#ffa300", "#ff8c00", 
        "#e66000", "#cc4400"
    ],
    "flood": ["#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#a50f15", "#67000d", "#400008"],
    "dust": [
        "#2b7bba", "#52a2c5", "#7cb8bd", "#a1cca4", "#c9e29a", 
        "#eef48b", "#fdd867", "#fca245", "#f0562b", "#d7191c"
    ],
    "windstorm": [
        "#3b71ab", "#5987be", "#84a6cc", "#adc0d9", "#d6dee6",
        "#eef2d8", "#faeeaf", "#fde092", "#f9c179", "#f49d5c",
        "#eb7546", "#de4a33", "#ce2529", "#b01222", "#8c0919"
    ],
    "cropland_fire": [
        "#52b1b3", "#7fa2b6", "#abdda4", "#cbe6a3", 
        "#ffffbf", "#fdae61", "#f46d43", "#d7191c", "#a50026"
    ],
    "forest_fire": [
        "#38bdf8",  # 0.25 - 0.33 (Relatively Low)
        "#6ee7b7",  # 0.34 - 0.41
        "#fef08a",  # 0.42 - 0.49
        "#f97316",  # 0.50 - 0.59
        "#dc2626"   # 0.60 - 1.00 (High Hazard)
    ],
    "waterspout": ["#e5e7eb", "#2563eb", "#38bdf8", "#4ade80", "#a3e635", "#facc15", "#f97316", "#ef4444", "#dc2626", "#991b1b"],
    "spring_heat": ["#ffffe5", "#fff7bc", "#fee391", "#fec44f", "#fe9929", "#fd8d3c", "#f16913", "#d94801", "#a63603", "#7f2704"],
    "summer_heat": ["#ffffcc", "#ffeb99", "#ffcc66", "#ffaa33", "#ff8800", "#e65500", "#cc2200", "#990000", "#660000", "#400000"],
    "spring_frost": ["#ffffcc", "#ffebaa", "#ffaa88", "#ff66aa", "#e633cc", "#b300ff", "#8800cc", "#550099", "#330066", "#1a0033"],
    # --- RICCAR color ramps matched exactly to Chapter 4 map legends ---
    # Precipitation absolute (Fig 1): dry (red/pink) → wet (blue/purple)
    "precip_abs_15": [
        "#f89898", "#f8a898", "#f8b898", "#f8c898", "#f8d898",
        "#f8e098", "#f8f098", "#e8f8b0", "#d8f8c0", "#b0f0d8",
        "#90e0e8", "#70c8f0", "#50a8f0", "#3888e8", "#2060d0"
    ],
    # Precipitation change (Fig 2): strong decrease (red) → increase (blue)
    "precip_change_15": [
        "#f80a06", "#f94106", "#f96806", "#f98c06", "#f9a606",
        "#f9c606", "#f9e506", "#f8f923", "#e2f947", "#cbf96a",
        "#b4f989", "#95f9b0", "#6cf9cf", "#35f9f1", "#20e1f9",
        "#32baf9", "#3d9bf9", "#3979f7", "#2f58f8", "#2733f9", "#0606d1"
    ],
    # Heavy precip days R10 hist – exact colors from provided legend (9 classes)
    "r10_hist": [
        "#0505f5", "#326bf9", "#2fc0fa", "#55fadc", "#b6fa8f",
        "#e8fa42", "#f9c70e", "#f97a06", "#f20808"
    ],
    # Projected Change in Heavy Precipitation R10 – exact colors from provided legend (16 classes)
    "r10_change": [
        "#c1503a", "#ce602d", "#db7d1f", "#e79e0d", "#f2ba0b",
        "#f9d704", "#fdfe00", "#a8f301", "#53e501", "#00dd02",
        "#09c33f", "#11a96c", "#1d9a8c", "#1a7a8d", "#145185", "#0d3a6b"
    ],
    # Mean annual temp hist (Fig 5): cool (blue) → hot (red)
    "temp_abs": [
        "#3c3fa0", "#0402e8", "#233bf9", "#335efe", "#3582f9",
        "#33a7ff", "#28d5ff", "#00fdfa", "#63ffdb", "#8fffb7",
        "#b1fe89", "#cefc65", "#e7fe3a", "#fefd02", "#f9d700",
        "#f6b40b", "#ef9123", "#e8721d", "#f54605"
    ],
    # Projected Change in Mean Annual Temperature (tas) – Matched directly to attachment (8 classes)
    "temp_change": [
        "#0f2b70",  # 1.83 - 1.85 (Dark Blue)
        "#277382",  # 1.86 - 1.9  (Teal)
        "#3ca658",  # 1.91 - 1.95 (Medium Green)
        "#33e312",  # 1.96 - 2    (Bright Green)
        "#e2f716",  # 2.01 - 2.05 (Yellow)
        "#f4be1b",  # 2.06 - 2.1  (Gold / Light Orange)
        "#e8822e",  # 2.11 - 2.15 (Orange)
        "#c74d3c"   # 2.16 - 2.2  (Red-Brown)
    ],
    # Very hot days hist (Fig 7): 0 (pale) → high (purple)
    "su40_hist": [
        "#ececb3",
        "#f2ee8a",
        "#f8f145",
        "#f6f000",
        "#ffd200",
        "#ffcc00",
        "#ff9c00",
        "#ff6a00",
        "#ff0000",
        "#e91e8f",
        "#e11ac8",
        "#d31cff",
        "#ab1ce6",
        "#8a2be2",
        "#6f2bd9",
        "#4d33cc",
        "#1034bf"
    ],
    # Very hot days change (Fig 8): 0 (blue) → large increase (red)
    "su40_change": [
        "#2f5cc0",  # 0
        "#7086d6",  # 1-5
        "#b2badf",  # 6-10
        "#e6e6e1",  # 11-15
        "#f4f4bf",  # 16-20
        "#f2d2a2",  # 21-25
        "#e9a276",  # 26-30
        "#df7855",  # 31-35
        "#d84f3f"   # 36-40
    ],
    # Frost days hist (Fig 9): low (red) → high (blue)
    "frost_hist": [
        "#c95a45",
        "#df7d3b",
        "#ef9a21",
        "#e9bb22",
        "#f4dd18",
        "#dff51a",
        "#8cf01c",
        "#2fdc28",
        "#2bc94a",
        "#31af86",
        "#2f95a0",
        "#246fa3",
        "#163f98"
    ],
    # Frost days change (Fig 10): large decrease (blue/purple) → small decrease (orange)
    "frost_change": [
        "#2f2c96",
        "#3837a3",
        "#4546b0",
        "#5959bb",
        "#7871c7",
        "#a39bcf",
        "#d8d4d1",
        "#f1efb4",
        "#f2da87",
        "#f5c360",
        "#eea53d",
        "#d1722c",
        "#bc512f"
    ],
    # Evaporation hist (Fig 11): low (blue) → high (red)
    "evap_hist": [
        "#3b96c8", "#5ba9cf", "#7bb9d0", "#99c8c7", "#afd3be",
        "#bddcb0", "#c9e2a0", "#d8e57f", "#e4e36a", "#efe764",
        "#f1de63", "#f4ce59", "#f6bd50", "#f7ac45", "#f9913d",
        "#fa7833", "#f95f2d", "#f24425", "#e31a1c"
    ],
    # Evaporation change (Fig 12): decrease (red) → increase (blue)
    "evap_change": [
        "#f6a2a6",  # -25 to -20
        "#f4b7a3",  # -19 to -15
        "#f2cf9a",  # -14 to -10
        "#efe39a",  # -9 to -8
        "#e4ef9a",  # -7 to -6
        "#cfeeb0",  # -5 to -4
        "#b7eac9",  # -3 to -2
        "#9fe6df",  # -1 to 0
        "#9ad9ea",  # 1 to 2
        "#9fc5ed",  # 3 to 4
        "#9eaff1",  # 5 to 10
        "#9793ee"   # 11 to 19
    ],
    # Runoff hist (Fig 13): low (red) → high (blue)
    "ro_hist": [
        "#cf563f",
        "#de7a34",
        "#ef9925",
        "#f4bb1c",
        "#f1da1c",
        "#f6f211",
        "#a8ef1a",
        "#57e91f",
        "#22db25",
        "#2cc65d",
        "#2da48b",
        "#258ca3",
        "#1e5f97",
        "#163b96"
    ],
    # Runoff change (Fig 14): large decrease (blue/purple) → near-zero (yellow)
    "ro_change": [
        "#1f32c6",
        "#5b2ccf",
        "#8e29d9",
        "#b61ee4",
        "#dd1fc1",
        "#f01484",
        "#ff5a0a",
        "#f8ab1c",
        "#f4ea17",
        "#e7ec58",
        "#eceb7a",
        "#e8e7a9"
    ],
    # Retained generic schemes
    "blue_seq": ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"],
    "heat_seq": ["#ffffcc", "#ffeb99", "#ffcc66", "#ffaa33", "#ff8800", "#e65500", "#cc2200", "#800000"],
    "frost_seq": ["#fff7fb", "#ece7f2", "#d0d1e6", "#a6bddb", "#74a9cf", "#3690c0", "#0570b0", "#034e7b"],
    "purple_seq": ["#49006a", "#7a0177", "#ae017e", "#dd3497", "#f768a1", "#fa9fb5", "#fde0dd"],
    "green_seq": ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45"]
}

DEFAULT_HAZARD_BINS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
CROPLAND_FIRE_BINS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
FOREST_FIRE_BINS = [5.0, 25.0, 42.0, 50.0, 60.0, 100.0]
DUST_HAZARD_BINS = [0.0, 13.0, 21.0, 30.0, 39.0, 47.0, 57.0, 67.0, 77.0, 87.0, 100.0]
WINDSTORM_HAZARD_BINS = [0.0, 7.0, 14.0, 21.0, 27.0, 34.0, 40.0, 45.0, 51.0, 56.0, 63.0, 69.0, 76.0, 84.0, 91.0, 100.0]

HAZARD_METADATA = {
    "drought": {
        "title": "Meteorological Drought Hazard",
        "description": "Reflects climate-driven conditions of long-term precipitation deficit and high atmospheric evaporative demand.",
        "indicators": "Normalized SPI, LST-Derived TCI, PET Anomalies, precipitation decrease, temperature increase, and actual evaporation decrease.",
        "spatial": "Concentrated primarily in northeastern Syria (Al-Hasakeh) and northern zones (Aleppo), with moderate-to-high hazard pockets in central, western, and southern regions."
    },
    "flood": {
        "title": "Flood Hazard",
        "description": "Measures physical susceptibility to riverine and flash flooding from short-duration, high-intensity rainfall.",
        "indicators": "JRC 100-year flood depth, river influence, TWI, land cover flood susceptibility, flow accumulation, inverted slope, extreme daily rainfall (Rx1day), and runoff projections.",
        "spatial": "High hazard areas are located along major river systems, low-lying lands, and flash-flood-prone semi-arid regions."
    },
    "spring_heat": {
        "title": "Spring Heatwave Hazard (March–April)",
        "description": "Evaluates early-season extreme heat during key phenological crop stages such as flowering and early grain filling.",
        "indicators": "Derived from ERA5-Land (2015–2025) and CMIP6 NEX-GDDP ACCESS-CM2 projections (SSP5-8.5, 2040–2060) relative to the 1981–2010 baseline.",
        "spatial": "Highest hazards occur in inland, northeastern regions, and northwestern Aleppo."
    },
    "summer_heat": {
        "title": "Summer Heatwave Hazard (July–August)",
        "description": "Evaluates peak seasonal cumulative heat stress coinciding with the critical growth stages of summer irrigated crops.",
        "indicators": "Derived from ERA5-Land (2015–2025) and CMIP6 NEX-GDDP ACCESS-CM2 projections (SSP5-8.5, 2040–2060) relative to the 1981–2010 baseline.",
        "spatial": "Widespread high to very high hazard levels across northeastern and southern Syria."
    },
    "spring_frost": {
        "title": "Spring Frost Hazard (March–April)",
        "description": "Measures freezing temperature risk (minimum temperature <= 0°C) during sensitive crop emergence and flowering periods.",
        "indicators": "Derived from ERA5-Land (2015–2025) and CMIP6 NEX-GDDP ACCESS-CM2 projections (SSP5-8.5, 2040–2060) relative to the 1981–2010 baseline.",
        "spatial": "High hazard levels concentrate in elevated mountain terrains and inland valleys."
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
        "spatial": "Peak hazard centers around Al-Bishri Mountain and parts of southern Syria."
    },
    "waterspout": {
        "title": "Waterspout Hazard (Coastal Zone)",
        "description": "Evaluates localized marine wind-vortex hazards occurring along the Mediterranean shoreline.",
        "indicators": "GIS-based Euclidean distance analysis and terrain elevation derived from SRTM DEM (30 m) combined with recorded waterspout events.",
        "spatial": "Strictly confined to the immediate coastal strip of Latakia and Tartous Governorates."
    },
    "cropland_fire": {
        "title": "Cropland Fire Hazard",
        "description": "Evaluates seasonal fire risk in agricultural fields (wheat and barley focus) during the summer harvest period (May–July).",
        "indicators": "Multi-factor analysis integrating LST, NDVI, Fire Weather Index (FWI), wind speed, proximity to roads and settlements, and cropland extent mask.",
        "spatial": "High susceptibility across major irrigation schemes in Aleppo, Ar-Raqqa, and Deir Ezzor."
    },
    "forest_fire": {
        "title": "Forest Fire Hazard",
        "description": "Assesses wildfire susceptibility within dense forested areas based on terrain, fuel load, and climate indicators.",
        "indicators": "Multi-criteria composite methodology integrating NDVI, LST, FWI, slope, canopy height, forest extent mask, and proximity to urban areas.",
        "spatial": "Concentrated in interior mountainous zones of western Homs, western Hama, eastern Tartous, and northern Latakia."
    }
}

RICCAR_METADATA = {
    "pr_hist": {
        "title": "Long-Term Mean Annual Precipitation (1995–2014)",
        "description": "Historical baseline map illustrating a strong spatial gradient across Syria, critical for understanding water security and rain-fed agriculture.",
        "indicators": "Mean Annual Precipitation (mm/year) based on RICCAR Mashreq dataset, smoothed via Kriging geostatistical interpolation with contour overlays.",
        "spatial": "Concentrated high values in coastal and western mountains (951–1,000 mm/year), dropping sharply inland to 108–150 mm/year in the interior Badia, with a secondary increase in the northern Fertile Crescent arc (500–600 mm/year)."
    },
    "pr_proj": {
        "title": "Projected Change in Annual Precipitation (2041–2060, SSP5-8.5)",
        "description": "Mid-century projection showing general rainfall decline across primary water-catchment areas.",
        "indicators": "Change in Mean Annual Precipitation (mm/year) under SSP5-8.5 relative to 1995–2014 baseline.",
        "spatial": "Severe drying in the western coastal and mountain zones (-45 to -81 mm/year); moderate declines in transition agricultural areas (-10 to -40 mm/year); slight, high-intensity marginal gains in the eastern Badia (+5 to +15 mm/year)."
    },
    "r10_hist": {
        "title": "Long-Term Mean Annual Heavy Precipitation Days - R10 (1995–2014)",
        "description": "Frequency of days with precipitation >= 10 mm, serving as a primary driver for groundwater recharge and aquifer replenishment.",
        "indicators": "Annual count of days with precipitation >= 10 mm.",
        "spatial": "High frequency in coastal/mountain west (31–35 days/year), moderate in northern agricultural arc (11–20 days/year), and rare in the arid interior (2–5 days/year)."
    },
    "r10_proj": {
        "title": "Projected Change in Heavy Precipitation Days - R10 (2041–2060, SSP5-8.5)",
        "description": "Future shifts in climate intensity and heavy rainfall event frequency.",
        "indicators": "Change in annual R10 days under SSP5-8.5 relative to 1995–2014 baseline.",
        "spatial": "Significant reduction in key western water-generating highlands (-3.9 to -2.1 days/year); moderate reduction in northern grain belts (-2.0 to -0.6 days/year); minor increases in eastern arid zones (-0.2 to +0.9 days/year) linked to flash flooding risks."
    },
    "tas_hist": {
        "title": "Long-Term Mean Annual Temperature (1995–2014)",
        "description": "Baseline distribution of mean surface air temperature shaped by topography and maritime proximity.",
        "indicators": "Mean Annual Air Temperature (°C).",
        "spatial": "Cool highlands in southwest (12–14°C) and temperate coast (16.5–18.5°C), moderate central plains (18–19°C), and high eastern continental interior (21–22°C)."
    },
    "tas_proj": {
        "title": "Projected Change in Mean Annual Temperature (2041–2060, SSP5-8.5)",
        "description": "Widespread warming trend increasing atmospheric evaporative demand and land degradation.",
        "indicators": "Change in Mean Annual Air Temperature (°C) under SSP5-8.5 relative to 1995–2014 baseline.",
        "spatial": "Pronounced warming across eastern interior (+2.0 to +2.5°C), western and northern regions warming by +1.6 to +2.0°C, and southern plains by +1.8 to +2.2°C."
    },
    "su40_hist": {
        "title": "Long-Term Mean Annual Very Hot Days - Tmax > 40°C (1995–2014)",
        "description": "Historical threshold for extreme heat stress affecting agricultural cycles and water availability.",
        "indicators": "Annual count of days with Tmax > 40°C.",
        "spatial": "Highest in eastern governorates (40–50 days/year), moderate in central steppe (10–30 days/year), and minimal in western/coastal zones (<3 days/year)."
    },
    "su40_proj": {
        "title": "Projected Change in Very Hot Days - Tmax > 40°C (2041–2060, SSP5-8.5)",
        "description": "Expansion of extreme heat stress days across the Syrian landmass.",
        "indicators": "Change in annual count of days with Tmax > 40°C under SSP5-8.5.",
        "spatial": "Massive increase in eastern regions (+30 to +35 days/year), significant expansion in central/northern areas (+20 to +30 days/year), and modest increase in western mountains (+1 to +10 days/year)."
    },
    "fd_hist": {
        "title": "Long-Term Mean Annual Frost Days - Tmin < 0°C (1995–2014)",
        "description": "Historical baseline for freezing temperature occurrences affecting winter crops and snow storage.",
        "indicators": "Annual count of days with Tmin < 0°C.",
        "spatial": "High in Anti-Lebanon and southwestern highlands (40–60 days/year), moderate in central/northern plains (10–25 days/year), and rare along the coast (0–5 days/year)."
    },
    "fd_proj": {
        "title": "Projected Change in Annual Frost Days - Tmin < 0°C (2041–2060, SSP5-8.5)",
        "description": "Substantial decrease in frost frequency across traditional freezing zones.",
        "indicators": "Change in annual frost days under SSP5-8.5 relative to 1995–2014 baseline.",
        "spatial": "Sharpest loss in high elevation southwestern highlands (-15 to -25 days/year), moderate reduction in inland/northern plains (-5 to -15 days/year), and minimal shift in coastal regions (-0 to -2 days/year)."
    },
    "evap_hist": {
        "title": "Long-Term Mean Annual Actual Evaporation (1995–2014)",
        "description": "Historical actual surface evaporation constrained by moisture availability and thermal load.",
        "indicators": "Mean Annual Actual Evaporation (mm/year) derived from raw RCM ensemble outputs.",
        "spatial": "Highest along coastal/western mountains and water bodies (up to 750+ mm/year), moderate in northern plains, and lowest in the hyper-arid eastern Badia due to lack of soil moisture."
    },
    "evap_proj": {
        "title": "Projected Change in Annual Actual Evaporation (2041–2060, SSP5-8.5)",
        "description": "Spatially divergent actual evaporation response driven by severe soil moisture depletion in the west.",
        "indicators": "Change in Annual Actual Evaporation (mm/year) under SSP5-8.5.",
        "spatial": "Notable decrease in western agricultural zones (-15 to -25 mm/year) reflecting extreme soil drying; slight increase in eastern areas (+2 to +15 mm/year) due to high heat and localized rainfall bursts."
    },
    "ro_hist": {
        "title": "Long-Term Mean Annual Runoff (1995–2014)",
        "description": "Historical surface water generation essential for river discharge and reservoir replenishment.",
        "indicators": "Mean Annual Total Runoff (mm/year).",
        "spatial": "Concentrated overwhelmingly in western coastal/mountain zones (300 to >750 mm/year), moderate in northern Euphrates tributaries (50–200 mm/year), and minimal across central/eastern plains (5–20 mm/year)."
    },
    "ro_proj": {
        "title": "Projected Change in Annual Runoff (2041–2060, SSP5-8.5)",
        "description": "Widespread reduction in surface runoff generation across primary hydrological catchments.",
        "indicators": "Change in Annual Total Runoff (mm/year) under SSP5-8.5.",
        "spatial": "Critical losses in high-rainfall western highlands (-60 to -180 mm/year); moderate declines in northern and southwestern catchments (-10 to -30 mm/year); minor absolute change in already hyper-arid eastern Badia (-1 to -5 mm/year)."
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
def load_raster_overlay(filepath, cmap_colors=None, bins=None, min_threshold=None):
    if cmap_colors is None:
        cmap_colors = COLOR_SCHEMES["temp_abs"]

    try:
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

        if min_threshold is not None:
            data[data < min_threshold] = np.nan

        nan_mask = np.isnan(data)
        valid_data = data[~nan_mask]

        if len(valid_data) == 0:
            return None, None, None, None

        if bins is None:
            vmin, vmax = np.percentile(valid_data, 1), np.percentile(valid_data, 99)
            if vmin == vmax:
                vmin, vmax = np.nanmin(valid_data), np.nanmax(valid_data)
            if vmin == vmax:
                vmax = vmin + 1.0
            bins = np.linspace(vmin, vmax, len(cmap_colors) + 1).tolist()

        palette_rgb = [mcolors.to_rgba(c) for c in cmap_colors]
        palette_uint8 = (np.array(palette_rgb) * 255).astype(np.uint8)

        binned = np.digitize(data, bins) - 1

        # Values falling below the minimum specified bin are treated as transparent NoData
        out_of_bounds = (binned < 0) | (binned >= len(cmap_colors))
        binned = np.clip(binned, 0, len(cmap_colors) - 1)

        colored_uint8 = palette_uint8[binned]
        colored_uint8[nan_mask | out_of_bounds] = [0, 0, 0, 0]

        img = Image.fromarray(colored_uint8, mode='RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG', compress_level=6)
        png_data = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
        return png_data, bounds, bins, data.shape
    except Exception:
        try:
            gdf = gpd.read_file(filepath)
            if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)
            
            num_cols = [c for c in gdf.columns if c.lower() != "geometry" and np.issubdtype(gdf[c].dtype, np.number)]
            if not num_cols:
                return None, None, None, None
            val_col = num_cols[0]

            west, south, east, north = gdf.total_bounds
            height, width = 600, 600
            transform = from_bounds(west, south, east, north, width, height)
            
            shapes = ((geom, val) for geom, val in zip(gdf.geometry, gdf[val_col]))
            data = rasterize(shapes=shapes, out_shape=(height, width), transform=transform, fill=np.nan, dtype=np.float32)

            bounds = [[south, west], [north, east]]
            if min_threshold is not None:
                data[data < min_threshold] = np.nan

            nan_mask = np.isnan(data)
            valid_data = data[~nan_mask]

            if len(valid_data) == 0:
                return None, None, None, None

            if bins is None:
                vmin, vmax = np.percentile(valid_data, 1), np.percentile(valid_data, 99)
                if vmin == vmax:
                    vmin, vmax = np.nanmin(valid_data), np.nanmax(valid_data)
                if vmin == vmax:
                    vmax = vmin + 1.0
                bins = np.linspace(vmin, vmax, len(cmap_colors) + 1).tolist()

            palette_rgb = [mcolors.to_rgba(c) for c in cmap_colors]
            palette_uint8 = (np.array(palette_rgb) * 255).astype(np.uint8)

            binned = np.digitize(data, bins) - 1

            out_of_bounds = (binned < 0) | (binned >= len(cmap_colors))
            binned = np.clip(binned, 0, len(cmap_colors) - 1)

            colored_uint8 = palette_uint8[binned]
            colored_uint8[nan_mask | out_of_bounds] = [0, 0, 0, 0]

            img = Image.fromarray(colored_uint8, mode='RGBA')
            buf = io.BytesIO()
            img.save(buf, format='PNG', compress_level=6)
            png_data = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
            return png_data, bounds, bins, (width, height)
        except Exception:
            return None, None, None, None


def add_named_geojson(m, gdf, layer_name, style_fn, marker=None):
    kwargs = dict(name=layer_name, style_function=style_fn)
    if marker is not None:
        kwargs["marker"] = marker
    folium.GeoJson(gdf, **kwargs).add_to(m)


def get_admin_center_name_column(gdf, level):
    """Find the most likely English administrative-centre name field."""
    candidates = {
        "L1": [
            "name", "NAME", "NAME_1", "admin1Name", "Governorate",
            "ADM1_EN", "ADM1_NAME", "AR_NAME"
        ],
        "L2": [
            "name", "NAME", "NAME_2", "admin2Name", "District",
            "ADM2_EN", "ADM2_NAME", "AR_NAME"
        ],
        "L3": [
            "name", "NAME", "NAME_3", "admin3Name", "Subdistrict",
            "Sub_District", "ADM3_EN", "ADM3_NAME", "AR_NAME"
        ],
    }

    for col in candidates.get(level, []):
        if col in gdf.columns:
            return col

    str_cols = [
        c for c in gdf.columns
        if c.lower() != "geometry"
        and (gdf[c].dtype == object or gdf[c].dtype.name == "string")
    ]
    return str_cols[0] if str_cols else None


def add_admin_center_click_popup(m, gdf, layer_name, level, marker):
    """
    Add administrative centre points with a popup that opens ONLY when
    the point is clicked. No hover tooltip is used.
    """
    name_col = get_admin_center_name_column(gdf, level)

    popup = None
    if name_col:
        popup = folium.GeoJsonPopup(
            fields=[name_col],
            aliases=["Administrative Centre:"],
            labels=True,
            localize=True,
            sticky=False,
            style=(
                "background-color: white; color: #0f172a; "
                "font-family: Arial, sans-serif; font-size: 13px; "
                "padding: 8px;"
            ),
            max_width=300,
        )

    kwargs = dict(
        name=layer_name,
        style_function=lambda x: {},
        marker=marker,
    )
    if popup is not None:
        kwargs["popup"] = popup

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


def generate_discrete_legend(title, colors, opacity, bins=None, unit="", custom_labels=None):
    """Compact legend used by Hazard layers (min / mid / max only). Reduced ~0.85x to limit map coverage."""
    num_classes = len(colors)
    block_height = 9 if num_classes > 10 else 11
    
    color_blocks = "".join([
        f'<div style="background:{c}; height:{block_height}px; width:15px;"></div>'
        for c in reversed(colors)
    ])
    total_height = len(colors) * block_height

    if custom_labels is not None:
        top_label, mid_label, bot_label = custom_labels
        range_html = f"""
            <div style="display: flex; flex-direction: column; justify-content: space-between; height: {total_height}px; font-size: 9px; font-weight: 600; color: #334155;">
                <div>{top_label}</div>
                <div style="font-size: 8px; color: #64748b;">{mid_label}</div>
                <div>{bot_label}</div>
            </div>
        """
    elif bins is not None and len(bins) > 1:
        top_val = f"{bins[-1]:g}"
        mid_val = f"{bins[len(bins)//2]:g}"
        bot_val = f"{bins[0]:g}"
        range_html = f"""
            <div style="display: flex; flex-direction: column; justify-content: space-between; height: {total_height}px; font-size: 9px; font-weight: 600; color: #334155;">
                <div>{top_val} {unit}</div>
                <div style="font-size: 8px; color: #64748b;">{mid_val}</div>
                <div>{bot_val} {unit}</div>
            </div>
        """
    else:
        range_html = f"""
            <div style="display: flex; flex-direction: column; justify-content: space-between; height: {total_height}px; font-size: 9px; font-weight: 600; color: #334155;">
                <div>↑ High</div>
                <div style="font-size: 8px; color: #64748b; font-weight: normal;">▲ Increase</div>
                <div>↓ Low</div>
            </div>
        """

    return f"""
        <div style="margin-bottom: 12px;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 5px; font-size: 11px;">{title} ({num_classes} Classes)</div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="display: flex; flex-direction: column; border: 1px solid #94a3b8; border-radius: 3px; overflow: hidden;">
                    {color_blocks}
                </div>
                {range_html}
            </div>
            <div style="margin-top: 3px; font-size: 9px; color: #94a3b8;">Opacity: {int(opacity * 100)}%</div>
        </div>
    """


def generate_riccar_full_legend(title, colors, opacity, bins=None, unit=""):
    """Full class-by-class legend for RICCAR layers. Reduced ~0.85x to limit map coverage."""
    num_classes = len(colors)
    row_h = 12 if num_classes <= 12 else 10

    # Build one row per class: colour swatch + interval label
    # colours are ordered low→high; bins has len = num_classes+1
    rows = []
    for i, c in enumerate(colors):
        if bins is not None and len(bins) == num_classes + 1:
            lo, hi = bins[i], bins[i + 1]
            # Format nicely (drop trailing .0 for integers)
            def _fmt(v):
                return f"{v:g}"
            label = f"{_fmt(lo)} – {_fmt(hi)}"
        else:
            label = f"Class {i + 1}"
        rows.append(
            f'<div style="display:flex;align-items:center;gap:5px;height:{row_h}px;">'
            f'<div style="background:{c};width:14px;height:{row_h - 2}px;'
            f'border:1px solid #94a3b8;border-radius:2px;flex-shrink:0;"></div>'
            f'<span style="font-size:9px;font-weight:600;color:#334155;'
            f'white-space:nowrap;">{label} {unit}</span>'
            f'</div>'
        )

    # Reverse so high values appear at the top (standard cartographic convention)
    rows_html = "".join(reversed(rows))

    return f"""
        <div style="margin-bottom: 12px;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 5px; font-size: 11px;">
                {title}
            </div>
            <div style="display: flex; flex-direction: column; gap: 1px;">
                {rows_html}
            </div>
            <div style="margin-top: 3px; font-size: 9px; color: #94a3b8;">
                Opacity: {int(opacity * 100)}%
            </div>
        </div>
    """


def generate_custom_su40_legend(title, colors, labels, opacity):
    """Custom SU40 legend. Reduced ~0.85x to limit map coverage."""
    rows = []
    for color, label in zip(colors, labels):
        rows.append(f"""
        <div style="display:flex;align-items:center;margin-bottom:2px;">
            <div style="width:15px;height:10px;background:{color};border:1px solid #999;margin-right:7px;"></div>
            <span style="font-size:9px;">{label}</span>
        </div>
        """)

    rows_html = ''.join(reversed(rows))

    return f"""
    <div style='margin-bottom:12px;'>
      <div style='font-weight:700;font-size:12px;color:#000;margin-bottom:6px;'>
      Very Hot Days,<br>Tmax > 40°C<br>( Days )
      </div>
      {rows_html}
      <div style='margin-top:5px;font-size:9px;color:#777;'>Opacity: {int(opacity*100)}%</div>
    </div>
    """

def add_advanced_measure_tools(m):
    """
    Measurement tool (works with streamlit-folium):
    - Distance (line) and Area (polygon)
    - Units: distance km / m ; area km² / ha
    Click the ruler icon (top-left), then measure on the map.
    In the measure panel you can switch units and choose line vs area.
    """
    MeasureControl(
        position="topleft",
        primary_length_unit="kilometers",
        secondary_length_unit="meters",
        primary_area_unit="sqkilometers",
        secondary_area_unit="hectares",
        active_color="#2563eb",
        completed_color="#1d4ed8",
    ).add_to(m)


def add_zoom_to_extent_control(m, bounds_list):
    """
    Toolbar button (top-left) that zooms to the combined bounds of active layers.
    Must be added with m.add_child so the map is the parent of the MacroElement.
    """
    if bounds_list:
        souths = [b[0][0] for b in bounds_list]
        wests = [b[0][1] for b in bounds_list]
        norths = [b[1][0] for b in bounds_list]
        easts = [b[1][1] for b in bounds_list]
        combined = [[min(souths), min(wests)], [max(norths), max(easts)]]
    else:
        combined = [[32.3, 35.6], [37.3, 42.4]]

    # Also fit on load so the layer frame is visible immediately
    try:
        m.fit_bounds(combined, padding=(30, 30))
    except Exception:
        pass

    zoom_js = """
    {% macro script(this, kwargs) %}
    (function() {
      var map = {{ this._parent.get_name() }};
      var targetBounds = [[{{ this.south }}, {{ this.west }}], [{{ this.north }}, {{ this.east }}]];

      var ZoomExtentControl = L.Control.extend({
        options: { position: 'topleft' },
        onAdd: function(map) {
          var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
          container.style.background = '#fff';
          container.style.borderRadius = '4px';
          var link = L.DomUtil.create('a', '', container);
          link.href = '#';
          link.title = 'Zoom to active layer extent';
          link.setAttribute('role', 'button');
          link.innerHTML = '&#9635;';
          link.style.cssText = 'width:34px;height:34px;line-height:34px;display:block;text-align:center;font-size:18px;color:#1e293b;text-decoration:none;';
          L.DomEvent.disableClickPropagation(container);
          L.DomEvent.on(link, 'click', function(e) {
            L.DomEvent.preventDefault(e);
            try { map.fitBounds(targetBounds, { padding: [40, 40], maxZoom: 12 }); }
            catch (err) { console.warn(err); }
          });
          return container;
        }
      });
      map.addControl(new ZoomExtentControl());
    })();
    {% endmacro %}
    """
    el = MacroElement()
    el.south = combined[0][0]
    el.west = combined[0][1]
    el.north = combined[1][0]
    el.east = combined[1][1]
    el._template = Template(zoom_js)
    # Critical: parent must be the map (not figure root) for this._parent.get_name()
    m.add_child(el)


# --- Sidebar Navigation ---
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio(
    "Select Explorer Page:",
    [hazard_page_label, riccar_page_label],
    index=0
)

syria_boundary = load_data("data/Vector_Parquet/Syria_Admin0_National-Level.parquet")

# --- Consolidated Sidebar Controls ---
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🎛️ Map Controls")

    if page == hazard_page_label:
        with st.expander("🏜️ Climate Hazard Layers", expanded=True):
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

    elif page == riccar_page_label:
        with st.expander("🌧️ Precipitation Indicators", expanded=True):
            show_pr_hist = st.checkbox("Mean Annual Precipitation (1995–2014)", value=True)
            show_pr_proj = st.checkbox("Change in Annual Precipitation (2041–2060)", value=False)
            show_r10_hist = st.checkbox("Heavy Precipitation Days - R10 (1995–2014)", value=False)
            show_r10_proj = st.checkbox("Change in Heavy Precipitation Days (2041–2060)", value=False)

        with st.expander("🌡️ Temperature Indicators", expanded=False):
            show_tas_hist = st.checkbox("Mean Annual Temperature (1995–2014)", value=False)
            show_tas_proj = st.checkbox("Change in Mean Temperature (2041–2060)", value=False)
            show_su40_hist = st.checkbox("Very Hot Days Tmax>40°C (1995–2014)", value=False)
            show_su40_proj = st.checkbox("Change in Very Hot Days (2041–2060)", value=False)
            show_fd_hist = st.checkbox("Frost Days Tmin<0°C (1995–2014)", value=False)
            show_fd_proj = st.checkbox("Change in Frost Days (2041–2060)", value=False)

        with st.expander("💧 Water Balance Indicators", expanded=False):
            show_evap_hist = st.checkbox("Mean Annual Evaporation (1995–2014)", value=False)
            show_evap_proj = st.checkbox("Change in Annual Evaporation (2041–2060)", value=False)
            show_ro_hist = st.checkbox("Mean Annual Runoff (1995–2014)", value=False)
            show_ro_proj = st.checkbox("Change in Annual Runoff (2041–2060)", value=False)

        riccar_opacity = st.slider("RICCAR Layer Opacity", 0.1, 1.0, 0.90, 0.05, key="riccar_opacity")

    with st.expander("MAP Administrative Boundaries", expanded=True):
        show_poly_l0 = st.checkbox("National Boundary (L0)", value=True)
        show_poly_l1 = st.checkbox("Governorates (L1)", value=True)
        show_poly_l2 = st.checkbox("Districts (L2)", value=False)
        show_poly_l3 = st.checkbox("Subdistricts (L3)", value=False)

    with st.expander("📍 Administrative Centers", expanded=True):
        show_center_l1 = st.checkbox("Governorate Centers (L1)", value=True)
        show_l1_names = st.checkbox("Display Governorate Names (L1)", value=True)
        show_center_l2 = st.checkbox("District Centers (L2)", value=False)
        show_center_l3 = st.checkbox("Subdistrict Centers (L3)", value=False)

    with st.expander("💧 Hydrology", expanded=True):
        show_rivers = st.checkbox("Main Rivers", value=True)
        show_water_bodies = st.checkbox("Water Bodies (Reservoirs + Sabkha)", value=True)

    with st.expander("🖼️ Base Map", expanded=False):
        basemap_option = st.radio(
            "Select base layer",
            ["None", "OpenStreetMap", "Google Maps", "Google Satellite"],
            index=0
        )


# ==============================================================================
# PAGE 1: CLIMATE HAZARD EXPLORER
# ==============================================================================
if page == hazard_page_label:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
            <img src="{hazard_icon_uri}" alt="Hazard Emblem" style="height: 40px; width: auto;"/>
            <h1 style="margin: 0; font-size: 2rem; font-weight: 700; color: #0f172a;">
                Syria Climate Hazard Explorer
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="developer-tag">Developed by FAO Office in Syria, Damascus</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Classified climate-hazard maps for Syria: <b>meteorological drought</b>, <b>flood</b>, '
        '<b>sand and dust storms</b>, <b>windstorm</b>, <b>cropland fire</b>, <b>forest fire</b>, <b>waterspout</b>, and <b>temperature extremes</b>. '
        'Track coordinates using the mouse position tool. Use the <b>ruler icon</b> (top-left) to measure <b>distance</b> (km/m) or <b>area</b> (km²/ha). '
        'Click the <b>□ frame icon</b> (top-left) to zoom to the active layer extent.</p>',
        unsafe_allow_html=True
    )

    m = folium.Map(
        location=[34.8021, 38.9968], zoom_start=7, tiles=None,
        control_scale=True, prefer_canvas=True, zoom_control=True
    )
    add_advanced_measure_tools(m)
    MousePosition(position="bottomleft", separator=" | ", prefix="Cursor: ").add_to(m)

    if basemap_option == "OpenStreetMap":
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap", control=True).add_to(m)
    elif basemap_option == "Google Maps":
        folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps", name="Google Maps", control=True).add_to(m)
    elif basemap_option == "Google Satellite":
        folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", attr="Google Satellite", name="Google Satellite", control=True).add_to(m)

    legend_blocks = []
    active_hazards = []
    active_layer_bounds = []

    hazard_layers_config = [
        ("drought", show_drought, "data/Raster/Drought_Hazard.tif", "Meteorological Drought", COLOR_SCHEMES["drought"], DEFAULT_HAZARD_BINS, drought_opacity, 1, None),
        ("flood", show_flood, "data/Raster/Flood_Hazard.tif", "Flood Hazard", COLOR_SCHEMES["flood"], DEFAULT_HAZARD_BINS, flood_opacity, 2, None),
        ("dust", show_dust, "data/Raster/Dust_Hazard.tif", "Sand & Dust Storms", COLOR_SCHEMES["dust"], DUST_HAZARD_BINS, dust_opacity, 3, None),
        ("windstorm", show_windstorm, "data/Raster/Ensemble_Wind_Index.tif", "Windstorm Hazard", COLOR_SCHEMES["windstorm"], WINDSTORM_HAZARD_BINS, windstorm_opacity, 4, None),
        ("cropland_fire", show_cropland_fire, "data/Raster/Fire_Hazard_for_Cropland.tif", "Cropland Fire Hazard", COLOR_SCHEMES["cropland_fire"], CROPLAND_FIRE_BINS, cropland_fire_opacity, 5, None),
        ("forest_fire", show_forest_fire, "data/Raster/Fire_Hazard_for_Forest_land.tif", "Forest Fire Hazard", COLOR_SCHEMES["forest_fire"], FOREST_FIRE_BINS, forest_fire_opacity, 5, None),
        ("waterspout", show_waterspout, "data/Raster/Waterspout_Hazard.tif", "Waterspout Hazard", COLOR_SCHEMES["waterspout"], DEFAULT_HAZARD_BINS, waterspout_opacity, 7, None),
        ("spring_heat", show_spring_heat, "data/Raster/Spring_Hot_Day_Hazard.tif", "Spring Heatwave", COLOR_SCHEMES["spring_heat"], DEFAULT_HAZARD_BINS, spring_heat_opacity, 8, None),
        ("summer_heat", show_summer_heat, "data/Raster/Summer_Hot_Day_Hazard.tif", "Summer Heatwave", COLOR_SCHEMES["summer_heat"], DEFAULT_HAZARD_BINS, summer_heat_opacity, 9, None),
        ("spring_frost", show_spring_frost, "data/Raster/Spring_Frost_Day_Hazard.tif", "Spring Frost", COLOR_SCHEMES["spring_frost"], [0, 0.1, 1, 5, 10, 20, 30, 50, 70, 100], spring_frost_opacity, 10, None),
    ]

    for key, is_active, rpath, label, colors, hbins, opac, z_idx, min_thresh in hazard_layers_config:
        if is_active:
            active_hazards.append((key, label, rpath))
            img, bounds, used_bins, _ = load_raster_overlay(rpath, cmap_colors=colors, bins=hbins, min_threshold=min_thresh)
            if img:
                if key == "flood":
                    bounds = [
                        [bounds[0][0] - 0.0340, bounds[0][1]],
                        [bounds[1][0] - 0.0340, bounds[1][1]]
                    ]
                active_layer_bounds.append(bounds)
                folium.raster_layers.ImageOverlay(
                    image=img, bounds=bounds, opacity=opac, name=f"<b>{label}</b>", interactive=False, zindex=z_idx
                ).add_to(m)
                if key == "drought":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High Hazard", "▲", "Relatively Moderate Hazard")
                    ))
                elif key == "flood":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High Hazard", "▲", "Low Hazard")
                    ))
                elif key == "dust":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("Very High Hazard", "▲", "Relatively Low Hazard")
                    ))
                elif key == "windstorm":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High hazard", "▲", "Relatively low hazard")
                    ))
                elif key == "cropland_fire":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High hazard", "▲", "Relatively low hazard")
                    ))
                elif key == "forest_fire":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High Hazard", "▲", "Relatively Low Hazard")
                    ))
                elif key == "waterspout":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High Hazard", "▲", "Low Hazard")
                    ))
                elif key == "spring_heat":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High Hazard", "▲", "Moderate Hazard")
                    ))
                elif key == "summer_heat":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("High Hazard", "▲", "Moderate Hazard")
                    ))
                elif key == "spring_frost":
                    legend_blocks.append(generate_discrete_legend(
                        label, colors, opac,
                        custom_labels=("Moderate Hazard", "▲", "Low Hazard")
                    ))
                else:
                    legend_blocks.append(generate_discrete_legend(label, colors, opac, used_bins, unit="%"))

    # Zoom-to-extent control for active hazard layers
    add_zoom_to_extent_control(m, active_layer_bounds)

    outside_mask_gdf = get_outside_mask(syria_boundary)
    folium.GeoJson(outside_mask_gdf, name="Outside Mask", style_function=lambda x: {"fillColor": "#ffffff", "color": "none", "fillOpacity": 1.0, "weight": 0}).add_to(m)

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

    if show_poly_l0:
        add_named_geojson(m, syria_boundary, "National Boundary (L0)", lambda x: {"fillColor": "transparent", "color": "#0f172a", "weight": 2.6, "fillOpacity": 0, "opacity": 1.0})
    if show_poly_l3:
        add_named_geojson(m, load_data(poly_paths["L3"]), "Subdistricts (L3)", lambda x: {"fillColor": "transparent", "color": "#94a3b8", "weight": 0.55, "fillOpacity": 0, "opacity": 0.85})
    if show_poly_l2:
        add_named_geojson(m, load_data(poly_paths["L2"]), "Districts (L2)", lambda x: {"fillColor": "transparent", "color": "#64748b", "weight": 1.0, "fillOpacity": 0, "opacity": 0.9})
    if show_poly_l1:
        add_named_geojson(m, load_data(poly_paths["L1"]), "Governorates (L1)", lambda x: {"fillColor": "transparent", "color": "#334155", "weight": 1.6, "fillOpacity": 0, "opacity": 0.95})

    if show_rivers:
        add_named_geojson(m, load_data("data/Vector_Parquet/Main_Rivers.parquet"), "Main Rivers", lambda x: {"color": "#2563eb", "weight": 1.2, "opacity": 0.95})

    if show_water_bodies:
        gdf_wb = load_data("data/Vector_Parquet/Water_Bodies.parquet")
        gdf_res, gdf_sab = classify_water_bodies(gdf_wb)
        if len(gdf_res) > 0:
            add_named_geojson(m, gdf_res, "Reservoirs / Lakes", lambda x: {"fillColor": "#3b82f6", "color": "#1d4ed8", "weight": 1.3, "fillOpacity": 0.60, "opacity": 0.95})
        if len(gdf_sab) > 0:
            add_named_geojson(m, gdf_sab, "Sabkha / Salt Lakes", lambda x: {"fillColor": "#d1d5db", "color": "#6b7280", "weight": 1.0, "fillOpacity": 0.70, "opacity": 0.9})

    if show_center_l3:
        gdf_l3_c = load_data(center_paths["L3"])
        add_admin_center_click_popup(
            m,
            gdf_l3_c,
            "Subdistrict Centers (L3)",
            "L3",
            folium.CircleMarker(
                radius=3, color="#be185d", fill=True,
                fill_color="#ec4899", fill_opacity=0.9, weight=1
            )
        )

    if show_center_l2:
        gdf_l2_c = load_data(center_paths["L2"])
        add_admin_center_click_popup(
            m,
            gdf_l2_c,
            "District Centers (L2)",
            "L2",
            folium.CircleMarker(
                radius=4, color="#5b21b6", fill=True,
                fill_color="#8b5cf6", fill_opacity=0.9, weight=1
            )
        )
    if show_center_l1:
        gdf_l1_c = load_data(center_paths["L1"])
        add_named_geojson(m, gdf_l1_c, "Governorate Centers (L1)", lambda x: {}, marker=folium.CircleMarker(radius=4, color="black", fill=True, fill_color="#ffffff", fill_opacity=1.0, weight=1.2))
        if show_l1_names:
            name_col = None
            for col in ['name', 'NAME', 'NAME_1', 'admin1Name', 'Governorate', 'ADM1_EN', 'AR_NAME']:
                if col in gdf_l1_c.columns:
                    name_col = col
                    break
            if not name_col:
                str_cols = [c for c in gdf_l1_c.columns if gdf_l1_c[c].dtype == object or gdf_l1_c[c].dtype.name == 'string']
                if str_cols:
                    name_col = str_cols[0]
            if name_col:
                for _, row in gdf_l1_c.iterrows():
                    geom = row.geometry
                    if geom and geom.geom_type == 'Point':
                        folium.Marker(
                            location=[geom.y, geom.x],
                            icon=folium.DivIcon(
                                icon_size=(150, 36),
                                icon_anchor=(-8, 12),
                                html=f'<div style="font-size: 11px; font-weight: bold; color: #1e293b; white-space: nowrap; text-shadow: 1px 1px 0px #ffffff, -1px -1px 0px #ffffff, 1px -1px 0px #ffffff, -1px 1px 0px #ffffff;">{row[name_col]}</div>'
                            )
                        ).add_to(m)

    if legend_blocks:
        combined_legend = f"""
        <div style="
            position: fixed; bottom: 26px; right: 26px; width: 170px; max-height: 65vh; overflow-y: auto;
            background: rgba(255,255,255,0.97); z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 11px; border: 1px solid #cbd5e1; border-radius: 8px;
            padding: 10px 12px; box-shadow: 0 3px 12px rgba(0,0,0,0.12);
        ">
            {"".join(legend_blocks)}
        </div>
        """
        m_root = m.get_root()
        if m_root:
            m_root.html.add_child(Element(combined_legend))

    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    col_map, col_meta = st.columns([2.4, 1], gap="medium")

    with col_map:
        st_folium(m, width="100%", height=700, use_container_width=True, key="map_hazard")

    with col_meta:
        st.markdown("### ℹ️ Hazard Layer Metadata")
        if not active_hazards:
            st.caption("No climate hazard layer currently selected.")
        else:
            for key, label, rpath in active_hazards:
                meta = HAZARD_METADATA[key]
                with st.expander(f"**{meta['title']}**", expanded=True):
                    st.markdown(f"**Description:** {meta['description']}")
                    st.markdown(f"**Indicators / Methodology:** {meta['indicators']}")
                    st.markdown(f"**Spatial Highlights:** {meta['spatial']}")

    st.markdown(
        '<p class="footer-note">'
        '<b>Syria Climate Hazard Explorer</b> | Developed by the <b>Technical Team of the FAO Office in Syria, Damascus</b>'
        '</p>',
        unsafe_allow_html=True
    )


# ==============================================================================
# PAGE 2: HISTORICAL & PROJECTED CLIMATE PARAMETERS (RICCAR-BASED)
# ==============================================================================
elif page == riccar_page_label:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
            <img src="{riccar_icon_uri}" alt="RICCAR Emblem" style="height: 40px; width: auto;"/>
            <h1 style="margin: 0; font-size: 2rem; font-weight: 700; color: #0f172a;">
                Historical & Projected Climate Parameters in Syria
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="developer-tag">RICCAR-Based Assessment | Mid-Century Outlook (2041–2060, SSP5-8.5)</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Spatially explicit evidence base documenting long-term historical climate conditions (1995–2014) '
        'and projected mid-century changes (2041–2060) under high emissions scenario SSP5-8.5 from the <b>RICCAR Mashreq Dataset</b>. '
        'Use the <b>ruler icon</b> (top-left) to measure <b>distance</b> (km/m) or <b>area</b> (km²/ha). Click the <b>□ frame icon</b> (top-left) to zoom to the active layer extent.</p>',
        unsafe_allow_html=True
    )

    m_riccar = folium.Map(
        location=[34.8021, 38.9968], zoom_start=7, tiles=None,
        control_scale=True, prefer_canvas=True, zoom_control=True
    )
    add_advanced_measure_tools(m_riccar)
    MousePosition(position="bottomleft", separator=" | ", prefix="Cursor: ").add_to(m_riccar)

    if basemap_option == "OpenStreetMap":
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap", control=True).add_to(m_riccar)
    elif basemap_option == "Google Maps":
        folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps", name="Google Maps", control=True).add_to(m_riccar)
    elif basemap_option == "Google Satellite":
        folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", attr="Google Satellite", name="Google Satellite", control=True).add_to(m_riccar)

    legend_blocks_r = []
    active_riccar = []
    active_riccar_details = []
    active_riccar_bounds = []

    # Bins and color ramps matched to Chapter 4 figure legends
    precip_15_bins = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 700, 800, 900, 1000, 1100]
    precip_change_15_bins = [
        -81, -79, -74, -69, -64, -59, -54, -49, -44, -39,
        -34, -29, -24, -19, -14, -9, -4, 1, 6, 11, 16, 21
    ]
    
    # Exact classification bins for Change in Temperature matching the attached legend
    temp_change_bins = [1.83, 1.86, 1.91, 1.96, 2.01, 2.06, 2.11, 2.16, 2.20]

    SU40_HIST_LABELS = [
        "0 - 0","1","2","3","4 - 4","5 - 5","6 - 7","8 - 10",
        "11 - 15","16 - 20","21 - 25","26 - 30","31 - 35",
        "36 - 40","41 - 45","46 - 50","51 - 55"
    ]

    riccar_layers_config = [
        # Fig 1 – Mean Annual Precipitation
        ("pr_hist", show_pr_hist, "data/RICCAR/Historical_Precipitation.gpkg", "Mean Annual Precipitation (1995-2014)",
         COLOR_SCHEMES["precip_abs_15"], precip_15_bins, "mm/yr"),
        # Fig 2 – Change in Precipitation
        ("pr_proj", show_pr_proj, "data/RICCAR/Change_in_Precipitation.gpkg", "Change in Precipitation (SSP5-8.5)",
         COLOR_SCHEMES["precip_change_15"], precip_change_15_bins, "mm/yr"),
        # Fig 3 – Heavy Precipitation Days R10 hist
        ("r10_hist", show_r10_hist, "data/RICCAR/Heavy_Precipitation_days_R10.gpkg", "Heavy Precip Days R10 (1995-2014)",
         COLOR_SCHEMES["r10_hist"], [2, 4, 6, 8, 11, 16, 21, 26, 31, 36], "days"),
        # Fig 4 – Change in Heavy Precip Days
        ("r10_proj", show_r10_proj, "data/RICCAR/Change_in_Heavy_Precipitation_R10.gpkg", "Change in Heavy Precip Days (SSP5-8.5)",
         COLOR_SCHEMES["r10_change"],
         [-3.9, -3.5, -3.2, -2.9, -2.6, -2.3, -2.0, -1.7, -1.4, -1.1, -0.8, -0.5, -0.2, 0.1, 0.4, 0.7, 1.0], "days"),
        # Fig 5 – Mean Annual Temperature
        ("tas_hist", show_tas_hist, "data/RICCAR/Mean_Annual_Temp.gpkg", "Mean Annual Temp (1995-2014)",
         COLOR_SCHEMES["temp_abs"],
         [12.8, 13.1, 13.6, 14.1, 14.6, 15.1, 15.6, 16.1, 16.6, 17.1, 17.6, 18.1, 18.6, 19.1, 19.6, 20.1, 20.6, 21.1, 21.6, 22.1], "°C"),
        # Fig 6 – Change in Mean Temperature
        ("tas_proj", show_tas_proj, "data/RICCAR/Change_in_Temp.gpkg", "Change in Mean Temp (SSP5-8.5)",
         COLOR_SCHEMES["temp_change"], temp_change_bins, "°C"),
        # Fig 7 – Very Hot Days hist
        ("su40_hist", show_su40_hist, "data/RICCAR/Very_hot_days.gpkg", "Very Hot Days Tmax>40°C (1995-2014)",
         COLOR_SCHEMES["su40_hist"], [0, 1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30, 40, 50], "days"),
        # Fig 8 – Change in Very Hot Days
        ("su40_proj", show_su40_proj, "data/RICCAR/Change_in_very_hot_days.gpkg", "Change in Very Hot Days (SSP5-8.5)",
         COLOR_SCHEMES["su40_change"], [0, 1, 6, 11, 16, 21, 26, 31, 36, 41], "days"),
        # Fig 9 – Frost Days hist
        ("fd_hist", show_fd_hist, "data/RICCAR/Frost_Days.gpkg", "Frost Days Tmin<0°C (1995-2014)",
         COLOR_SCHEMES["frost_hist"], [0, 3, 6, 8, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56], "days"),
        # Fig 10 – Change in Frost Days
        ("fd_proj", show_fd_proj, "data/RICCAR/Change_in_Frost_Days.gpkg", "Change in Frost Days (SSP5-8.5)",
         COLOR_SCHEMES["frost_change"], [-27, -25, -23, -21, -19, -17, -15, -13, -11, -9, -7, -5, -3, 1], "days"),
        # Fig 11 – Evaporation hist
        ("evap_hist", show_evap_hist, "data/RICCAR/Actual_Evaporation.gpkg", "Mean Annual Evaporation (1995-2014)",
         COLOR_SCHEMES["evap_hist"], [151, 201, 251, 301, 351, 401, 451, 501, 551, 601, 651, 701, 751, 801, 851, 901, 951, 1001, 1051, 1101], "mm/yr"),
        # Fig 12 – Change in Evaporation
        ("evap_proj", show_evap_proj, "data/RICCAR/Change_in_Evaporation.gpkg", "Change in Evaporation (SSP5-8.5)",
         COLOR_SCHEMES["evap_change"], [-25, -19, -14, -9, -7, -5, -3, -1, 1, 3, 5, 11, 20], "mm/yr"),
        # Fig 13 – Runoff hist
        ("ro_hist", show_ro_hist, "data/RICCAR/Mean_Annual_Runoff.gpkg", "Mean Annual Runoff (1995-2014)",
         COLOR_SCHEMES["ro_hist"], [5, 11, 16, 21, 31, 41, 51, 76, 101, 151, 201, 301, 501, 751, 1001], "mm/yr"),
        # Fig 14 – Change in Runoff
        ("ro_proj", show_ro_proj, "data/RICCAR/Change_in_Annual_Runoff.gpkg", "Change in Runoff (SSP5-8.5)",
         COLOR_SCHEMES["ro_change"], [-180, -99, -59, -39, -29, -19, -14, -9, -4, -1, 1, 3, 6], "mm/yr")
    ]

    z_idx = 1
    for key, is_active, rpath, label, colors, rbins, unit in riccar_layers_config:
        if is_active:
            active_riccar.append(key)
            active_riccar_details.append((key, label, rpath, unit))
            img, bounds, used_bins, _ = load_raster_overlay(rpath, cmap_colors=colors, bins=rbins)
            if img:
                active_riccar_bounds.append(bounds)
                folium.raster_layers.ImageOverlay(
                    image=img, bounds=bounds, opacity=riccar_opacity,
                    name=f"<b>{label}</b>", interactive=False, zindex=z_idx
                ).add_to(m_riccar)
                if key == "su40_hist":
                    legend_blocks_r.append(generate_custom_su40_legend(label, colors, SU40_HIST_LABELS, riccar_opacity))
                else:
                    legend_blocks_r.append(generate_riccar_full_legend(label, colors, riccar_opacity, bins=rbins, unit=unit))
            z_idx += 1

    add_zoom_to_extent_control(m_riccar, active_riccar_bounds)

    outside_mask_gdf = get_outside_mask(syria_boundary)
    folium.GeoJson(outside_mask_gdf, name="Outside Mask", style_function=lambda x: {"fillColor": "#ffffff", "color": "none", "fillOpacity": 1.0, "weight": 0}).add_to(m_riccar)

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

    if show_poly_l0:
        add_named_geojson(m_riccar, syria_boundary, "National Boundary (L0)", lambda x: {"fillColor": "transparent", "color": "#0f172a", "weight": 2.6, "fillOpacity": 0, "opacity": 1.0})
    if show_poly_l3:
        add_named_geojson(m_riccar, load_data(poly_paths["L3"]), "Subdistricts (L3)", lambda x: {"fillColor": "transparent", "color": "#94a3b8", "weight": 0.55, "fillOpacity": 0, "opacity": 0.85})
    if show_poly_l2:
        add_named_geojson(m_riccar, load_data(poly_paths["L2"]), "Districts (L2)", lambda x: {"fillColor": "transparent", "color": "#64748b", "weight": 1.0, "fillOpacity": 0, "opacity": 0.9})
    if show_poly_l1:
        add_named_geojson(m_riccar, load_data(poly_paths["L1"]), "Governorates (L1)", lambda x: {"fillColor": "transparent", "color": "#334155", "weight": 1.6, "fillOpacity": 0, "opacity": 0.95})

    if show_rivers:
        add_named_geojson(m_riccar, load_data("data/Vector_Parquet/Main_Rivers.parquet"), "Main Rivers", lambda x: {"color": "#2563eb", "weight": 1.2, "opacity": 0.95})

    if show_water_bodies:
        gdf_wb = load_data("data/Vector_Parquet/Water_Bodies.parquet")
        gdf_res, gdf_sab = classify_water_bodies(gdf_wb)
        if len(gdf_res) > 0:
            add_named_geojson(m_riccar, gdf_res, "Reservoirs / Lakes", lambda x: {"fillColor": "#3b82f6", "color": "#1d4ed8", "weight": 1.3, "fillOpacity": 0.60, "opacity": 0.95})
        if len(gdf_sab) > 0:
            add_named_geojson(m_riccar, gdf_sab, "Sabkha / Salt Lakes", lambda x: {"fillColor": "#d1d5db", "color": "#6b7280", "weight": 1.0, "fillOpacity": 0.70, "opacity": 0.9})

    if show_center_l3:
        gdf_l3_c = load_data(center_paths["L3"])
        add_admin_center_click_popup(
            m_riccar,
            gdf_l3_c,
            "Subdistrict Centers (L3)",
            "L3",
            folium.CircleMarker(
                radius=3, color="#be185d", fill=True,
                fill_color="#ec4899", fill_opacity=0.9, weight=1
            )
        )

    if show_center_l2:
        gdf_l2_c = load_data(center_paths["L2"])
        add_admin_center_click_popup(
            m_riccar,
            gdf_l2_c,
            "District Centers (L2)",
            "L2",
            folium.CircleMarker(
                radius=4, color="#5b21b6", fill=True,
                fill_color="#8b5cf6", fill_opacity=0.9, weight=1
            )
        )
    if show_center_l1:
        gdf_l1_c = load_data(center_paths["L1"])
        add_named_geojson(m_riccar, gdf_l1_c, "Governorate Centers (L1)", lambda x: {}, marker=folium.CircleMarker(radius=4, color="black", fill=True, fill_color="#ffffff", fill_opacity=1.0, weight=1.2))
        if show_l1_names:
            name_col = None
            for col in ['name', 'NAME', 'NAME_1', 'admin1Name', 'Governorate', 'ADM1_EN', 'AR_NAME']:
                if col in gdf_l1_c.columns:
                    name_col = col
                    break
            if not name_col:
                str_cols = [c for c in gdf_l1_c.columns if gdf_l1_c[c].dtype == object or gdf_l1_c[c].dtype.name == 'string']
                if str_cols:
                    name_col = str_cols[0]
            if name_col:
                for _, row in gdf_l1_c.iterrows():
                    geom = row.geometry
                    if geom and geom.geom_type == 'Point':
                        folium.Marker(
                            location=[geom.y, geom.x],
                            icon=folium.DivIcon(
                                icon_size=(150, 36),
                                icon_anchor=(-8, 12),
                                html=f'<div style="font-size: 11px; font-weight: bold; color: #1e293b; white-space: nowrap; text-shadow: 1px 1px 0px #ffffff, -1px -1px 0px #ffffff, 1px -1px 0px #ffffff, -1px 1px 0px #ffffff;">{row[name_col]}</div>'
                            )
                        ).add_to(m_riccar)

    if legend_blocks_r:
        combined_legend_r = f"""
        <div style="
            position: fixed; bottom: 26px; right: 26px; width: 185px; max-height: 65vh; overflow-y: auto;
            background: rgba(255,255,255,0.97); z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 11px; border: 1px solid #cbd5e1; border-radius: 8px;
            padding: 10px 12px; box-shadow: 0 3px 12px rgba(0,0,0,0.12);
        ">
            {"".join(legend_blocks_r)}
        </div>
        """
        m_riccar_root = m_riccar.get_root()
        if m_riccar_root:
            m_riccar_root.html.add_child(Element(combined_legend_r))

    folium.LayerControl(position="topright", collapsed=True).add_to(m_riccar)

    col_map_r, col_meta_r = st.columns([2.4, 1], gap="medium")

    with col_map_r:
        st_folium(m_riccar, width="100%", height=700, use_container_width=True, key="map_riccar")

    with col_meta_r:
        st.markdown("### ℹ️ RICCAR Layer Metadata")
        if not active_riccar:
            st.caption("No RICCAR climate layer currently selected.")
        else:
            for key, label, rpath, unit in active_riccar_details:
                meta = RICCAR_METADATA.get(key)
                if meta:
                    with st.expander(f"**{meta['title']}**", expanded=True):
                        st.markdown(f"**Description:** {meta['description']}")
                        st.markdown(f"**Indicators / Methodology:** {meta['indicators']}")
                        st.markdown(f"**Spatial Highlights:** {meta['spatial']}")
                else:
                    with st.expander(f"**{label}**", expanded=True):
                        st.caption(f"Layer path: `{rpath}` · Unit: {unit}")

    st.markdown(
        '<p class="footer-note">'
        '<b>Historical & Projected Climate (RICCAR)</b> | Developed by the <b>Technical Team of the FAO Office in Syria, Damascus</b>'
        '</p>',
        unsafe_allow_html=True
    )