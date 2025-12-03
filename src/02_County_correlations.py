"""Streamlit page: explore county-level relationships between NP supply and public health metrics."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path("data")
NP_FILE = DATA_DIR / "npmaster.csv"
PH_FILE = DATA_DIR / "public_health_metrics_by_county.csv"
POP_FILE = DATA_DIR / "georgia-counties-by-population-(2025).csv"


def county_core(x: str) -> str:
    if not isinstance(x, str):
        return ""
    x = x.strip()
    return x[:-7].strip() if x.lower().endswith(" county") else x


@st.cache_data
def load_np() -> pd.DataFrame:
    if not NP_FILE.exists():
        st.error(f"Missing NP master file at {NP_FILE}")
        st.stop()
    df = pd.read_csv(NP_FILE, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    return df


@st.cache_data
def load_ph() -> pd.DataFrame:
    if not PH_FILE.exists():
        st.error(f"Missing public health metrics at {PH_FILE}")
        st.stop()
    df = pd.read_csv(PH_FILE, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    # Normalize FIPS to 5-digit string
    fips_col = "FIPS" if "FIPS" in df.columns else "county_fips" if "county_fips" in df.columns else None
    if fips_col:
        df["county_fips"] = df[fips_col].astype(str).str.zfill(5)
    else:
        st.error("Public health metrics file must include a FIPS column.")
        st.stop()
    # Coerce numeric metrics (except identifiers)
    for c in df.columns:
        if c not in {"County", "county_fips", fips_col}:
            df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")
    return df


@st.cache_data
def load_pop() -> pd.DataFrame:
    if not POP_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(POP_FILE, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    if "fips" in df.columns:
        df["county_fips"] = df["fips"].astype(str).str.zfill(5)
    else:
        return pd.DataFrame()
    # Normalize county name and population
    df["CountyName"] = df["name"].apply(county_core) if "name" in df.columns else ""
    for pop_col in ("pop2025", "population", "population_2025"):
        if pop_col in df.columns:
            df["population"] = pd.to_numeric(df[pop_col].str.replace(",", ""), errors="coerce")
            break
    return df[["county_fips", "CountyName", "population"]] if "population" in df.columns else pd.DataFrame()


def nice_label(col: str) -> str:
    return col.replace("_", " ").replace("%", " %").strip().title()


def main():
    st.title("County-level relationships between NP supply and public health metrics")

    np_df_raw = load_np()
    ph_df = load_ph()
    pop_df = load_pop()

    # Column selection for NP data
    def pick_col(cands):
        for c in cands:
            if c in np_df_raw.columns:
                return c
        return None

    col_county = pick_col(["CountyName", "County"])
    col_spec = pick_col(["NP_Type", "NP_Type_filled", "specialty"])
    if not col_county:
        st.error("Could not find a county column in npmaster (expected County or CountyName).")
        st.stop()
    if not col_spec:
        st.error("Could not find a specialty column in npmaster (expected NP_Type or NP_Type_filled).")
        st.stop()

    np_df = np_df_raw.copy()
    np_df["county_name"] = np_df[col_county].apply(county_core)
    np_df["specialty"] = np_df[col_spec].fillna("").astype(str).str.strip()

    # Map county -> fips and population (from pop file or PH file)
    fips_map = {}
    pop_map = {}
    if not pop_df.empty:
        for _, r in pop_df.iterrows():
            if pd.notna(r.get("CountyName")):
                fips_map[county_core(str(r["CountyName"]))] = str(r["county_fips"]).zfill(5)
            if pd.notna(r.get("population")):
                pop_map[county_core(str(r["CountyName"]))] = r["population"]
    # Fallback: use PH county names/fips if available
    if "County" in ph_df.columns:
        for _, r in ph_df[["County", "county_fips"]].dropna().iterrows():
            cname = county_core(str(r["County"]))
            if cname and cname not in fips_map:
                fips_map[cname] = str(r["county_fips"]).zfill(5)

    # Sidebar controls
    st.sidebar.header("Filters")
    specialties = sorted([s for s in np_df["specialty"].dropna().unique().tolist() if s])
    spec_choice = st.sidebar.selectbox("Specialty", ["All NPs"] + specialties, index=0)

    np_metric_choice = st.sidebar.radio("NP metric", ["NP count", "NPs per 1k population"], index=0)
    np_metric_col = "np_count" if np_metric_choice == "NP count" else "np_per_1k"

    ph_numeric_cols = [
        c for c in ph_df.columns
        if c not in {"County", "county_fips", "FIPS"} and pd.api.types.is_numeric_dtype(ph_df[c])
    ]
    if not ph_numeric_cols:
        st.error("No numeric public health metrics found.")
        st.stop()
    ph_options = {nice_label(c): c for c in ph_numeric_cols}
    ph_label_choice = st.sidebar.selectbox("Public health metric", list(ph_options.keys()))
    ph_metric_col = ph_options[ph_label_choice]

    # Filter/aggregate NP data
    if spec_choice != "All NPs":
        np_df = np_df[np_df["specialty"] == spec_choice]

    np_grouped = (
        np_df.groupby("county_name", dropna=False)
        .size()
        .reset_index(name="np_count")
    )
    np_grouped["county_fips"] = np_grouped["county_name"].map(fips_map)
    np_grouped["population"] = np_grouped["county_name"].map(pop_map)
    np_grouped["np_per_1k"] = np_grouped.apply(
        lambda r: (r["np_count"] / r["population"] * 1000.0) if pd.notna(r["population"]) and r["population"] not in (0, "0") else pd.NA,
        axis=1
    )

    merged = np_grouped.merge(ph_df, on="county_fips", how="inner")
    merged_clean = merged.dropna(subset=[np_metric_col, ph_metric_col])

    st.caption(
        f"Specialty: {spec_choice} • NP metric: {np_metric_choice} • "
        f"Public metric: {ph_label_choice} • Counties: {len(merged_clean)}"
    )

    if merged_clean.empty:
        st.warning("No data available after filtering. Adjust selections.")
        st.stop()

    fig = px.scatter(
        merged_clean,
        x=np_metric_col,
        y=ph_metric_col,
        hover_name="county_name",
        trendline="ols",
        labels={
            np_metric_col: np_metric_choice,
            ph_metric_col: ph_label_choice,
        },
        title=None,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Extract R² from trendline; fall back to correlation^2 if needed
    r2_val = None
    try:
        trend = px.get_trendline_results(fig)
        if not trend.empty and "px_fit" in trend.columns:
            model = trend.iloc[0]["px_fit"]
            if hasattr(model, "rsquared"):
                r2_val = float(model.rsquared)
    except Exception:
        r2_val = None

    if r2_val is None:
        try:
            x = pd.to_numeric(merged_clean[np_metric_col], errors="coerce")
            y = pd.to_numeric(merged_clean[ph_metric_col], errors="coerce")
            valid = x.notna() & y.notna()
            if valid.sum() >= 2 and x[valid].nunique() > 1:
                corr = x[valid].corr(y[valid])
                if pd.notna(corr):
                    r2_val = float(corr ** 2)
        except Exception:
            r2_val = None

    st.metric("R² (linear fit)", f"{r2_val:.3f}" if r2_val is not None else "N/A")


if __name__ == "__main__":
    main()
