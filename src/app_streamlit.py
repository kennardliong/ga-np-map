# src/app_streamlit.py
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
import numpy as np
from streamlit_folium import st_folium
from branca.colormap import linear
from branca.utilities import color_brewer

# ---------- App setup ----------
st.set_page_config(page_title="Georgia NP Map", layout="wide")
st.title("Georgia Nurse Practitioners — Interactive Map")

DATA_CSV = Path("data/npmaster.csv")
GA_GEOJSON = Path("data/ga_counties.geojson")  # optional; app works without it
POP_CSV = Path("data/georgia-counties-by-population-(2025).csv")  # optional; enables per-capita metric

# ---------- Load data ----------
def read_csv_robust(p: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "ISO-8859-1"):
        try:
            return pd.read_csv(p, dtype=str, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(p, dtype=str)

# ---------- helpers ----------
def county_core(x: str) -> str:
    if not isinstance(x, str):
        return ""
    x = x.strip()
    return x[:-7].strip() if x.lower().endswith(" county") else x

if not DATA_CSV.exists():
    st.error(f"Missing CSV at {DATA_CSV}. Put your cleaned file there.")
    st.stop()

df = read_csv_robust(DATA_CSV)
df.columns = [c.strip() for c in df.columns]  # trim header whitespace

# Optional population data (2025)
pop_map = {}
if POP_CSV.exists():
    pop_df = read_csv_robust(POP_CSV)
    pop_df.columns = [c.strip() for c in pop_df.columns]
    pop_col = None
    for c in ("pop2025", "population", "population_2025"):
        if c in pop_df.columns:
            pop_col = c
            break
    county_col_pop = None
    for c in ("CountyName", "County", "county", "name"):
        if c in pop_df.columns:
            county_col_pop = c
            break
    if pop_col and county_col_pop:
        pop_df["CountyName"] = pop_df[county_col_pop].apply(lambda x: county_core(str(x)))
        try:
            pop_df[pop_col] = pd.to_numeric(pop_df[pop_col], errors="coerce")
        except Exception:
            pass
        pop_map = dict(zip(pop_df["CountyName"], pop_df[pop_col]))
    else:
        st.warning("Population file found but missing expected columns (needs county + pop2025). Using raw counts.")

# ---------- pick columns (handles alternatives) ----------
def pick_col(cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

COL_NPI    = pick_col(["NPI"])
COL_FIRST  = pick_col(["Provider_First_Name"])
COL_LAST   = pick_col(["Provider_Last_Name"])
COL_CRED   = pick_col(["Provider_Credentials"])
COL_STREET = pick_col(["Street1"])
COL_CITY   = pick_col(["City"])
COL_COUNTY = pick_col(["County", "CountyName"])  # accept either
COL_STATE  = pick_col(["State"])
COL_ZIP    = pick_col(["ZIP"])
COL_PHONE  = pick_col(["Phone"])
COL_LAT    = pick_col(["Latitude", "lat_clean"])
COL_LON    = pick_col(["Longitude", "lon_clean"])
COL_SPEC   = pick_col(["NP_Type", "NP_Type_filled"])  # prefer NP_Type but fall back

# If we only have NP_Type_filled, alias it to NP_Type to avoid downstream warnings
if "NP_Type" not in df.columns and "NP_Type_filled" in df.columns:
    df["NP_Type"] = df["NP_Type_filled"]
    COL_SPEC = "NP_Type"

# ---------- ensure CountyName exists ----------
if "CountyName" in df.columns:
    df["CountyName"] = df["CountyName"].astype(str).str.strip()
elif COL_COUNTY:
    df["CountyName"] = df[COL_COUNTY].apply(county_core)
else:
    df["CountyName"] = ""  # empty placeholder

# ---------- coerce lat/lon robustly ----------
def to_num_series(colname):
    if not colname or colname not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[colname].astype(str).str.replace(",", "").str.strip(), errors="coerce")

df["lat"] = to_num_series(COL_LAT)
df["lon"] = to_num_series(COL_LON)

# GA bounds sanity
valid_geo = df["lat"].between(30, 35) & df["lon"].between(-86, -81)
n_valid = int(valid_geo.sum())

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")

spec_series = df[COL_SPEC].fillna("").astype(str).str.strip() if COL_SPEC else pd.Series([], dtype=str)
all_specs = sorted([s for s in spec_series.unique() if s != ""])
spec_choice = st.sidebar.selectbox("Specialty", ["All specialties"] + all_specs, index=0)

county_series = df["CountyName"].fillna("").astype(str).str.strip()
all_counties = sorted([c for c in county_series.unique() if c != ""])
county_choice = st.sidebar.selectbox("County", ["All counties"] + all_counties, index=0)

metric_choice = st.sidebar.radio(
    "Metric",
    ["NP count", "NPs per 1k population"],
    index=0,
    help="Use population-based rate when population file is available; otherwise raw counts."
)


# --- Update control (prevents constant reruns) ---
# Auto-update always on; no manual toggle
update_now = True


# masks (always Series to avoid KeyError: True)
def series_mask(m):
    if isinstance(m, pd.Series): return m
    return pd.Series([bool(m)] * len(df), index=df.index)

mask_spec = (df[COL_SPEC] == spec_choice) if (COL_SPEC and spec_choice != "All specialties") else True
mask_cty  = (df["CountyName"] == county_choice) if (county_choice != "All counties") else True
mask = series_mask(mask_spec) & series_mask(mask_cty)

df_view = df[mask].copy()
valid_view = df_view["lat"].between(30, 35) & df_view["lon"].between(-86, -81)

# ---------- KPIs ----------
c1, c2, c3 = st.columns(3)
with c1: st.metric("Providers (selection)", f"{len(df_view):,}")
with c2: st.metric("Specialties", df_view["NP_Type"].nunique() if "NP_Type" in df_view.columns else 0)
with c3: st.metric("Counties", df_view["CountyName"].nunique())

st.caption(f"Rows in file: {len(df):,} • Valid lat/lon: {n_valid:,} • In selection: {int(valid_view.sum()):,}")
if n_valid == 0:
    st.warning("No valid points to plot. Check that 'Latitude'/'Longitude' are numeric (no commas) and within GA bounds (lat 30–35, lon -86 to -81).")

# ---------- County counts (for choropleth) ----------
use_geojson = GA_GEOJSON.exists()
ga_gj = None
if use_geojson:
    with open(GA_GEOJSON, "r") as f:
        ga_gj = json.load(f)

# Use filtered view (spec + county) for counts/density
counts = (
    df_view.groupby("CountyName", dropna=False)
    .size()
    .reset_index(name="np_count")
)
counts["np_count"] = counts["np_count"].fillna(0).astype(float)

# Add population if available, then compute per-capita rate
if pop_map:
    counts["population_2025"] = counts["CountyName"].map(pop_map)
    counts["np_per_1k_pop"] = counts.apply(
        lambda r: (r["np_count"] / r["population_2025"] * 1000.0) if pd.notna(r.get("population_2025")) and r.get("population_2025") not in (0, "0") else np.nan,
        axis=1
    )

# Pick metric: per-capita if requested and available; otherwise counts
metric_col = "np_count"
metric_label = "NP count"
if metric_choice == "NPs per 1k population":
    if "np_per_1k_pop" in counts.columns and counts["np_per_1k_pop"].notna().any():
        metric_col = "np_per_1k_pop"
        metric_label = "NPs per 1,000 population"
    else:
        st.warning("Population data not available for rate calculation; showing raw NP counts.")

vals = counts[metric_col].fillna(0).astype(float)

# ---------- Geometry helpers for zoom-to-county ----------
def feature_bounds(feat):
    coords = []
    def collect(obj):
        if isinstance(obj, (list, tuple)):
            if len(obj) == 2 and all(isinstance(x, (int, float)) for x in obj):
                lon, lat = obj
                coords.append((lat, lon))
            else:
                for v in obj:
                    collect(v)
    collect(feat.get("geometry", {}).get("coordinates", []))
    if not coords:
        return None
    lats, lons = zip(*coords)
    return [(min(lats), min(lons)), (max(lats), max(lons))]

# Try to get bounds for the selected county (from GeoJSON or data points)
selected_bounds = None
if county_choice != "All counties":
    if ga_gj:
        feat = next((f for f in ga_gj.get("features", []) if str(f.get("properties", {}).get("NAME", "")).strip() == county_choice), None)
        if feat:
            selected_bounds = feature_bounds(feat)
    if selected_bounds is None and valid_view.any():
        sub = df_view[valid_view]
        lat_min, lat_max = sub["lat"].min(), sub["lat"].max()
        lon_min, lon_max = sub["lon"].min(), sub["lon"].max()
        pad = 0.15
        selected_bounds = [(lat_min - pad, lon_min - pad), (lat_max + pad, lon_max + pad)]

# ---------- Map ----------
m = folium.Map(location=[32.9, -83.3], zoom_start=6, tiles="cartodbpositron")

if use_geojson and ga_gj:
    count_map = dict(zip(counts["CountyName"].fillna(""), counts["np_count"]))
    metric_map = dict(zip(counts["CountyName"].fillna(""), vals))
    for feat in ga_gj["features"]:
        nm = str(feat["properties"].get("NAME", "")).strip()
        feat["properties"]["np_count"] = int(count_map.get(nm, 0))
        feat["properties"][metric_col] = float(metric_map.get(nm, 0))

    if vals.empty:
        st.warning("No data for the current filter.")
        st.stop()

    vmin, vmax = vals.min(), vals.max()
    if vmin == vmax:
        v = vmin
        bins = [v - 0.5, v + 0.5, v + 1.5, v + 2.5]  # need at least 4 edges => 3 colors
    else:
        # Log-spaced bins (5 classes) for better spread on skewed data
        adj_min = vmin if vmin > 0 else max(vmax * 0.001, 0.001)
        adj_max = vmax if vmax > 0 else adj_min + 1
        raw_bins = np.geomspace(adj_min, adj_max, 6)
        bins = []
        for b in raw_bins:
            if not bins or b > bins[-1] * (1 + 1e-6):
                bins.append(float(b))
        if len(bins) < 4:  # ensure Folium has enough breaks
            bins = np.linspace(vmin, vmax, 4).tolist()

    # Ensure bins cover data range (folium requires all values to fall inside)
    if bins:
        bins[0] = min(bins[0], vmin) - 1e-9
        bins[-1] = max(bins[-1], vmax) + 1e-9
    if len(bins) < 4:  # absolute fallback
        bins = [vmin - 1, (vmin + vmax) / 2, vmax, vmax + 1]
    bin_labels = [f"{bins[i]:g} – {bins[i+1]:g}" for i in range(len(bins)-1)]
    # Build a discrete palette aligned to folium's ColorBrewer use
    color_bins = []
    if len(bin_labels) > 0:
        palette = color_brewer("Greens", n=max(len(bin_labels), 3))
        color_bins = palette[:len(bin_labels)]

    legend = f"{metric_label} — {'All specialties' if spec_choice=='All specialties' else spec_choice}"
    folium.Choropleth(
        geo_data=ga_gj,
        data=counts,
        columns=["CountyName", metric_col],
        key_on="feature.properties.NAME",
        fill_color="Greens",
        bins=bins,
        fill_opacity=0.9,
        line_opacity=0.6,
        line_color="#555",
        legend_name=legend,
        nan_fill_color="#f0f0f0",
    ).add_to(m)

    folium.GeoJson(
        ga_gj,
        name="County tooltips",
        tooltip=folium.features.GeoJsonTooltip(
            fields=["NAME", "np_count", metric_col],
            aliases=["County", "NPs", metric_label],
            localize=True,
            sticky=False,
            labels=True
        ),
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent"}
    ).add_to(m)

if selected_bounds:
    m.fit_bounds(selected_bounds, padding=(20, 20))

st_folium(m, width=1100, height=700)

# Manual legend/key with color swatches (add explicit zero entry without overlap)
if color_bins and len(color_bins) == len(bin_labels):
    legend_lines = []
    if (vals == 0).any():
        zero_block = "<span style='display:inline-block;width:14px;height:14px;background:#f0f0f0;border:1px solid #ccc;margin-right:6px;'></span>"
        legend_lines.append(f"{zero_block}0")
    for col, label in zip(color_bins, bin_labels):
        block = f"<span style='display:inline-block;width:14px;height:14px;background:{col};border:1px solid #ccc;margin-right:6px;'></span>"
        legend_lines.append(f"{block}{label}")
    st.markdown("**Legend:**<br/>" + "<br/>".join(legend_lines), unsafe_allow_html=True)
else:
    st.markdown("**Legend (bin edges):** " + "; ".join(bin_labels))

with st.expander("Show table of current selection"):
    county_counts = counts.rename(columns={"CountyName": "County"}).copy()
    if metric_col in county_counts.columns and metric_col != "np_count":
        county_counts[metric_label] = county_counts[metric_col]
        cols = ["County", "np_count", metric_label]
    else:
        cols = ["County", "np_count"]
    st.dataframe(
        county_counts[cols]
        .sort_values("np_count", ascending=False)
        .reset_index(drop=True)
    )
