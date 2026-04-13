"""
data_engine.py – Data Query & Analysis Layer
Loads all datasets once and exposes clean functions for the agent.
"""
import os
import pandas as pd
import numpy as np
from difflib import get_close_matches

# ── Dataset paths ──────────────────────────────────────────────────────────────
DATA_DIR = "data"
HIST_PATH = os.path.join(DATA_DIR, "TamilNadu_ML_Master_Historical.csv")
PROFILE_PATH = os.path.join(DATA_DIR, "TamilNadu_District_Profile_2024_25.csv")

# ── Loaded dataframes (populated on load_data()) ───────────────────────────────
hist_df: pd.DataFrame = pd.DataFrame()
profile_df: pd.DataFrame = pd.DataFrame()
ALL_DISTRICTS: list = []


def load_data():
    """Load all datasets into module-level globals. Call once at startup."""
    global hist_df, profile_df, ALL_DISTRICTS
    hist_df = pd.read_csv(HIST_PATH, low_memory=False)
    hist_df.columns = hist_df.columns.str.strip().str.lower()
    hist_df["district"] = hist_df["district"].str.strip().str.title()
    hist_df["crop_name"] = hist_df["crop_name"].str.strip().str.title()
    hist_df["soil_type"] = hist_df["soil_type"].str.strip().str.lower()
    hist_df["season"] = hist_df["season"].str.strip().str.title()

    profile_df = pd.read_csv(PROFILE_PATH)
    profile_df.columns = profile_df.columns.str.strip().str.lower()
    profile_df["district"] = profile_df["district"].str.strip().str.title()

    ALL_DISTRICTS = sorted(
        list(set(hist_df["district"].dropna().unique().tolist() +
                 profile_df["district"].dropna().unique().tolist()))
    )
    print(f"[data_engine] Loaded {len(hist_df):,} historical rows | {len(profile_df)} district profiles | {len(ALL_DISTRICTS)} districts")


# ── Utility ────────────────────────────────────────────────────────────────────
def fuzzy_district(name: str) -> str | None:
    """Return best-matching district name using fuzzy matching."""
    if not name:
        return None
    name_title = name.strip().title()
    if name_title in ALL_DISTRICTS:
        return name_title
    matches = get_close_matches(name_title, ALL_DISTRICTS, n=1, cutoff=0.6)
    return matches[0] if matches else None


def _hist_for(district: str) -> pd.DataFrame:
    return hist_df[hist_df["district"] == district]


def _profile_for(district: str) -> pd.Series | None:
    row = profile_df[profile_df["district"] == district]
    return row.iloc[0] if not row.empty else None


# ── 1. Crop Recommendations ────────────────────────────────────────────────────
def get_top_crops(district: str, soil_type: str = None, season: str = None, top_n: int = 7) -> dict:
    """Return top crops for a district, optionally filtered by soil and season."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found. Please check the spelling."}

    df = _hist_for(district)
    if df.empty:
        return {"error": f"No crop data available for {district}."}

    if soil_type:
        soil_type = soil_type.lower()
        df = df[df["soil_type"] == soil_type]
    if season:
        df = df[df["season"].str.lower() == season.lower()]

    if df.empty:
        return {"error": f"No data matching your filters for {district}."}

    # Average yield across all years for each crop + soil combo
    summary = (
        df.groupby(["crop_name", "soil_type", "season"])
        .agg(
            avg_yield=("yield", "mean"),
            max_yield=("yield", "max"),
            area_ha=("area", "mean"),
            records=("yield", "count"),
        )
        .reset_index()
        .sort_values("avg_yield", ascending=False)
        .head(top_n)
    )
    summary["avg_yield"] = summary["avg_yield"].round(2)
    summary["max_yield"] = summary["max_yield"].round(2)
    summary["area_ha"] = summary["area_ha"].round(0).astype(int)

    return {
        "district": district,
        "soil_filter": soil_type or "all",
        "season_filter": season or "all",
        "crops": summary.to_dict(orient="records"),
    }


# ── 2. Rainfall Statistics ─────────────────────────────────────────────────────
def get_rainfall_stats(district: str, year: int = None) -> dict:
    """Return rainfall breakdown (SW monsoon, NE monsoon, annual) for a district."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    df = _hist_for(district)
    if df.empty:
        return {"error": f"No rainfall data for {district}."}

    rain_cols = [
        "district_rain_total_mm",
        "district_sw_monsoon_rain_mm",
        "district_ne_monsoon_rain_mm",
        "district_hot_weather_rain_mm",
        "district_winter_rain_mm",
    ]

    if year:
        df = df[df["year_start"] == year]
        if df.empty:
            return {"error": f"No data for {district} in year {year}."}

    row_data = df[rain_cols + ["year_start"]].dropna(subset=["district_rain_total_mm"])
    if row_data.empty:
        return {"error": f"Rainfall data unavailable for {district}."}

    avg = row_data[rain_cols].mean().round(1)
    year_range = f"{int(row_data['year_start'].min())}–{int(row_data['year_start'].max())}"

    # Year-wise trend (last 10 distinct years)
    trend = (
        row_data.groupby("year_start")["district_rain_total_mm"]
        .mean()
        .round(1)
        .reset_index()
        .rename(columns={"year_start": "year", "district_rain_total_mm": "total_mm"})
        .sort_values("year")
        .tail(10)
        .to_dict(orient="records")
    )

    return {
        "district": district,
        "period": year_range,
        "avg_annual_mm": avg["district_rain_total_mm"],
        "sw_monsoon_mm": avg["district_sw_monsoon_rain_mm"],
        "ne_monsoon_mm": avg["district_ne_monsoon_rain_mm"],
        "hot_weather_mm": avg["district_hot_weather_rain_mm"],
        "winter_mm": avg["district_winter_rain_mm"],
        "yearly_trend": trend,
    }


# ── 3. Wage Information ────────────────────────────────────────────────────────
def get_wage_info(district: str) -> dict:
    """Return current 2024–25 agricultural wage data for a district."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    p = _profile_for(district)
    if p is None:
        return {"error": f"Wage data not available for {district}."}

    wage_keys = [
        "agri_wage_plough_men", "agri_wage_sowers_pluckers_men",
        "agri_wage_sowers_pluckers_women", "agri_wage_transplanters_weeders_men",
        "agri_wage_transplanters_weeders_women", "agri_wage_reapers_harvesters_men",
        "agri_wage_reapers_harvesters_women", "agri_wage_other_operations_men",
        "agri_wage_other_operations_women", "agri_wage_tractor_driver_men",
    ]
    wages = {}
    for k in wage_keys:
        val = p.get(k, None)
        if pd.notna(val):
            label = k.replace("agri_wage_", "").replace("_", " ").title()
            wages[label] = f"₹{int(val)}/day"

    return {
        "district": district,
        "year": "2024–25",
        "wages": wages,
    }


# ── 4. Irrigation Profile ──────────────────────────────────────────────────────
def get_irrigation_profile(district: str) -> dict:
    """Return irrigation sources and groundwater data for a district."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    p = _profile_for(district)
    if p is None:
        return {"error": f"Irrigation data not available for {district}."}

    total_irr = p.get("total_net_irrigated", 0) or 0
    net_sown = p.get("net_area_sown", 0) or 0
    irr_pct = round((total_irr / net_sown * 100), 1) if net_sown > 0 else 0

    sources = {}
    src_map = {
        "irrigation_canals": "Canals",
        "irrigation_tanks": "Tanks",
        "irrigation_tube_bore_wells": "Tube/Bore Wells",
        "irrigation_open_wells": "Open Wells",
        "irrigation_other_sources": "Other Sources",
    }
    for key, label in src_map.items():
        val = p.get(key, 0)
        if pd.notna(val) and val > 0:
            sources[label] = f"{int(val):,} ha"

    # Groundwater (pick a recent month)
    gw_months = [c for c in profile_df.columns if c.startswith("groundwater_") and not c.endswith("average")]
    gw_values = {}
    for col in sorted(gw_months):
        val = p.get(col, None)
        if pd.notna(val):
            month = col.replace("groundwater_", "").replace("_", " ").title()
            gw_values[month] = f"{val:.2f} m"

    gw_avg = p.get("groundwater_yearly_average", None)

    return {
        "district": district,
        "net_area_sown_ha": f"{int(net_sown):,}",
        "total_irrigated_ha": f"{int(total_irr):,}",
        "irrigation_coverage_pct": irr_pct,
        "irrigation_sources": sources,
        "groundwater_avg_m": round(gw_avg, 2) if pd.notna(gw_avg) else "N/A",
        "groundwater_monthly": gw_values,
    }


# ── 5. Yield Trend ────────────────────────────────────────────────────────────
def get_yield_trend(district: str, crop: str) -> dict:
    """Return year-wise average yield trend for a specific crop in a district."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    df = _hist_for(district)
    df = df[df["crop_name"].str.lower() == crop.lower()]
    if df.empty:
        # Try partial match
        all_crops = df["crop_name"].unique() if not df.empty else hist_df[hist_df["district"] == district]["crop_name"].unique()
        close = get_close_matches(crop.title(), list(all_crops), n=1, cutoff=0.5)
        if close:
            df = _hist_for(district)
            df = df[df["crop_name"] == close[0]]
            crop = close[0]
        if df.empty:
            return {"error": f"No data for crop '{crop}' in {district}."}

    trend = (
        df.groupby("year_start")["yield"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"year_start": "year", "yield": "avg_yield_t_ha"})
        .sort_values("year")
        .to_dict(orient="records")
    )

    avg_yield = round(df["yield"].mean(), 2)
    best_year = int(df.loc[df["yield"].idxmax(), "year_start"])
    best_yield = round(df["yield"].max(), 2)

    return {
        "district": district,
        "crop": crop,
        "avg_yield_t_ha": avg_yield,
        "best_year": best_year,
        "best_yield_t_ha": best_yield,
        "trend": trend,
    }


# ── 6. Pest Risk (Rule-Based) ─────────────────────────────────────────────────
PEST_RULES = [
    {
        "condition": lambda r, dev: r.get("sw_monsoon_mm", 0) > 1000,
        "pests": ["Rice Blast (Magnaporthe oryzae)", "Brown Plant Hopper", "Stem Borer"],
        "crops_affected": ["Rice", "Paddy"],
        "prevention": "Apply propiconazole fungicide; drain excess water; use resistant varieties.",
        "severity": "High",
    },
    {
        "condition": lambda r, dev: r.get("ne_monsoon_mm", 0) > 800,
        "pests": ["Sheath Blight", "Leaf Folder", "Fungal Leaf Spot"],
        "crops_affected": ["Rice", "Banana", "Groundnut"],
        "prevention": "Ensure proper field drainage; apply mancozeb; monitor regularly in Oct–Dec.",
        "severity": "Moderate–High",
    },
    {
        "condition": lambda r, dev: r.get("avg_annual_mm", 0) < 700,
        "pests": ["Aphids", "Whitefly", "Red Spider Mite"],
        "crops_affected": ["Pulses", "Groundnut", "Cotton", "Vegetables"],
        "prevention": "Spray neem oil or imidacloprid; maintain adequate soil moisture.",
        "severity": "Moderate",
    },
    {
        "condition": lambda r, dev: dev is not None and dev < -15,
        "pests": ["Thrips", "Leaf Miners", "Pod Borers"],
        "crops_affected": ["Chilli", "Onion", "Pulses"],
        "prevention": "Install yellow sticky traps; use spinosad insecticide; irrigate frequently.",
        "severity": "Moderate",
    },
]


def get_pest_risk(district: str) -> dict:
    """Analyze rainfall patterns to predict pest risks for a district."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    rain = get_rainfall_stats(district)
    if "error" in rain:
        return {"error": rain["error"]}

    df = _hist_for(district)
    dev = None
    if "tn_year_dev_pct" in df.columns:
        dev_vals = df["tn_year_dev_pct"].dropna()
        dev = float(dev_vals.mean()) if not dev_vals.empty else None

    risks = []
    for rule in PEST_RULES:
        try:
            if rule["condition"](rain, dev):
                risks.append({
                    "severity": rule["severity"],
                    "pests": rule["pests"],
                    "crops_affected": rule["crops_affected"],
                    "prevention": rule["prevention"],
                })
        except Exception:
            continue

    if not risks:
        risks = [{
            "severity": "Low",
            "pests": ["General garden pests (minor)"],
            "crops_affected": ["All crops"],
            "prevention": "Routine monitoring and preventive neem sprays recommended.",
        }]

    return {
        "district": district,
        "avg_annual_rain_mm": rain.get("avg_annual_mm"),
        "sw_monsoon_mm": rain.get("sw_monsoon_mm"),
        "ne_monsoon_mm": rain.get("ne_monsoon_mm"),
        "deviation_pct": round(dev, 1) if dev else "N/A",
        "risks": risks,
    }


# ── 7. District Overview ──────────────────────────────────────────────────────
def get_district_overview(district: str) -> dict:
    """Return a comprehensive agricultural profile of a district."""
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    p = _profile_for(district)
    df = _hist_for(district)

    result: dict = {"district": district}

    if p is not None:
        result["total_area_ha"] = f"{int(p.get('total_geographical_area', 0)):,}"
        result["net_area_sown_ha"] = f"{int(p.get('net_area_sown', 0)):,}"
        result["forest_area_ha"] = f"{int(p.get('forest_area', 0)):,}"
        result["total_irrigated_ha"] = f"{int(p.get('total_net_irrigated', 0)):,}"

    if not df.empty:
        top_crops = (
            df.groupby("crop_name")["yield"]
            .mean()
            .round(2)
            .sort_values(ascending=False)
            .head(5)
        )
        result["top_5_crops"] = top_crops.reset_index().rename(
            columns={"crop_name": "crop", "yield": "avg_yield_t_ha"}
        ).to_dict(orient="records")

        result["soil_types"] = df["soil_type"].value_counts().to_dict()
        result["seasons"] = df["season"].value_counts().to_dict()
        result["data_years"] = f"{int(df['year_start'].min())}–{int(df['year_start'].max())}"

    return result


# ── 8. Search crops by query ───────────────────────────────────────────────────
def get_all_crops_for_district(district: str) -> list:
    """Return list of all unique crops grown in a district."""
    district = fuzzy_district(district)
    if not district:
        return []
    df = _hist_for(district)
    return sorted(df["crop_name"].dropna().unique().tolist())


def get_all_districts() -> list:
    return ALL_DISTRICTS
