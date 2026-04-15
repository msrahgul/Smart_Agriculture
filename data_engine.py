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
    """
    Return top crops for a district, optionally filtered by soil and season.

    Ranking is balanced using:
    - average yield
    - cultivated area
    - number of records
    This avoids recommending crops only because of one extreme metric.
    """
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found. Please check the spelling."}

    df = _hist_for(district)
    if df.empty:
        return {"error": f"No crop data available for {district}."}

    if soil_type:
        soil_type = soil_type.lower().strip()
        df = df[df["soil_type"] == soil_type]

    if season:
        df = df[df["season"].str.lower() == season.lower().strip()]

    if df.empty:
        return {"error": f"No data matching your filters for {district}."}

    summary = (
        df.groupby(["crop_name", "soil_type", "season"])
        .agg(
            avg_yield=("yield", "mean"),
            max_yield=("yield", "max"),
            area_ha=("area", "mean"),
            records=("yield", "count"),
        )
        .reset_index()
    )

    # Log-transform to reduce domination by very large values
    summary["yield_score"] = np.log1p(summary["avg_yield"].clip(lower=0))
    summary["area_score"] = np.log1p(summary["area_ha"].clip(lower=0))
    summary["record_score"] = np.log1p(summary["records"].clip(lower=1))

    # Balanced score
    summary["rank_score"] = (
        summary["yield_score"] * 0.50 +
        summary["area_score"] * 0.35 +
        summary["record_score"] * 0.15
    )

    summary = summary.sort_values(
        ["rank_score", "avg_yield", "area_ha"],
        ascending=[False, False, False]
    ).head(top_n)

    summary["avg_yield"] = summary["avg_yield"].round(2)
    summary["max_yield"] = summary["max_yield"].round(2)
    summary["area_ha"] = summary["area_ha"].round(0).astype(int)
    summary["rank_score"] = summary["rank_score"].round(3)

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


# ══════════════════════════════════════════════════════════════
# 9. ML MODEL PREDICTION BRIDGE
# ══════════════════════════════════════════════════════════════
def get_latest_district_crop_context(district: str, crop_name: str = None) -> dict:
    """
    Pull the most recent historical row for a district+crop as a feature dict.
    This is used as the input row to the ML models.
    """
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    df = _hist_for(district).copy()
    if df.empty:
        return {"error": f"No historical data for {district}."}

    if crop_name:
        crop_name_lower = crop_name.strip().lower()
        filtered = df[df["crop_name"].str.lower() == crop_name_lower]
        if filtered.empty:
            # Fuzzy crop match
            all_crops = df["crop_name"].unique().tolist()
            close = get_close_matches(crop_name.title(), all_crops, n=1, cutoff=0.5)
            if close:
                filtered = df[df["crop_name"] == close[0]]
                crop_name = close[0]
        if not filtered.empty:
            df = filtered

    if "year_start" in df.columns:
        df = df.sort_values("year_start", ascending=False)

    row = df.iloc[0].to_dict()
    return row


def predict_crop_yield_for_district(
    district: str,
    crop_name: str,
    season: str = None,
    soil_type: str = None,
) -> dict:
    """Use the trained RF yield model to predict yield for a district+crop."""
    import ml_models
    row = get_latest_district_crop_context(district, crop_name)
    if "error" in row:
        return row

    # Override with user-supplied context if provided
    if season:
        row["season"] = season
    if soil_type:
        row["soil_type"] = soil_type.lower()

    try:
        if not ml_models.models_available()["yield_model"]:
            return {"error": "Yield model not trained yet. Run: python train_yield_model.py"}
        pred = ml_models.predict_yield(row)
        return {
            "district": row.get("district", district),
            "crop_name":  str(row.get("crop_name", crop_name)).title(),
            "season":     str(row.get("season", "Unknown")),
            "soil_type":  str(row.get("soil_type", "Unknown")).title(),
            "predicted_yield": round(pred, 2),
            "unit": "tonnes/hectare",
        }
    except Exception as e:
        return {"error": f"Yield prediction failed: {e}"}


def predict_pest_risk_for_district(
    district: str,
    crop_name: str,
    season: str = None,
    soil_type: str = None,
) -> dict:
    """Use the trained RF classifier to predict pest risk level."""
    import ml_models
    row = get_latest_district_crop_context(district, crop_name)
    if "error" in row:
        return row

    if season:
        row["season"] = season
    if soil_type:
        row["soil_type"] = soil_type.lower()

    try:
        if not ml_models.models_available()["pest_risk_model"]:
            return {"error": "Pest model not trained yet. Run: python train_pest_risk_model.py"}
        risk = ml_models.predict_pest_risk(row)
        return {
            "district":  row.get("district", district),
            "crop_name": str(row.get("crop_name", crop_name)).title(),
            "season":    str(row.get("season", "Unknown")),
            "soil_type": str(row.get("soil_type", "Unknown")).title(),
            "pest_risk": risk,
        }
    except Exception as e:
        return {"error": f"Pest risk prediction failed: {e}"}


# ══════════════════════════════════════════════════════════════
# 10. SUITABILITY SCORING ENGINE
# ══════════════════════════════════════════════════════════════

# Crop water requirement profile (mm/season) — general agronomic knowledge
CROP_WATER_REQ_MM = {
    "Rice": 1200, "Paddy": 1200, "Sugarcane": 1500, "Banana": 1100,
    "Cotton": 700, "Groundnut": 500, "Maize": 600, "Jowar": 400,
    "Bajra": 350, "Ragi": 450, "Sorghum": 400, "Wheat": 450,
    "Urad": 400, "Moong": 350, "Arhar": 500, "Horsegram": 350,
    "Turmeric": 800, "Onion": 450, "Tapioca": 1000, "Coconut": 1300,
    "Mango": 900, "Cashew": 800, "Chilli": 600, "Sesamum": 350,
    "Sunflower": 500, "Tobacco": 600, "Tomato": 550, "Ginger": 800,
    "Cardamom": 1800, "Coffee": 1200, "Tea": 1500, "Rubber": 2000,
    "Potato": 550, "Garlic": 400, "Coriander": 350, "Mustard": 350,
}

# Soil compatibility scores per crop (1.0 = ideal, 0.5 = marginal, 0.0 = poor)
CROP_SOIL_COMPATIBILITY = {
    "Rice":      {"alluvial soil": 1.0, "clay soil": 0.9, "red soil": 0.4, "black soil": 0.5},
    "Paddy":     {"alluvial soil": 1.0, "clay soil": 0.9, "red soil": 0.4, "black soil": 0.5},
    "Groundnut": {"red soil": 1.0, "black soil": 0.7, "alluvial soil": 0.6, "clay soil": 0.3},
    "Cotton":    {"black soil": 1.0, "red soil": 0.6, "alluvial soil": 0.7, "clay soil": 0.5},
    "Sugarcane": {"alluvial soil": 1.0, "black soil": 0.8, "red soil": 0.6, "clay soil": 0.7},
    "Banana":    {"alluvial soil": 1.0, "clay soil": 0.6, "red soil": 0.5, "black soil": 0.7},
    "Maize":     {"alluvial soil": 0.9, "red soil": 0.8, "black soil": 0.7, "clay soil": 0.6},
    "Jowar":     {"black soil": 1.0, "red soil": 0.8, "alluvial soil": 0.6, "clay soil": 0.5},
    "Bajra":     {"red soil": 0.9, "black soil": 0.8, "alluvial soil": 0.7, "clay soil": 0.4},
    "Ragi":      {"red soil": 1.0, "black soil": 0.7, "alluvial soil": 0.6, "clay soil": 0.5},
    "Turmeric":  {"alluvial soil": 1.0, "clay soil": 0.8, "red soil": 0.6, "black soil": 0.7},
    "Coconut":   {"alluvial soil": 0.9, "red soil": 0.8, "clay soil": 0.7, "black soil": 0.6},
}

# Estimated full-season cost ranges ₹/acre: (min, max) per crop
CROP_COST_PROFILES = {
    "Rice":      {"seeds": (1200, 2000), "fertilizer": (3500, 6000), "labour": (8000, 14000), "irrigation": (2000, 4000), "pesticide": (1000, 2500)},
    "Paddy":     {"seeds": (1200, 2000), "fertilizer": (3500, 6000), "labour": (8000, 14000), "irrigation": (2000, 4000), "pesticide": (1000, 2500)},
    "Groundnut": {"seeds": (3000, 5000), "fertilizer": (2500, 4500), "labour": (5000, 9000), "irrigation": (1500, 3000), "pesticide": (800, 1800)},
    "Sugarcane": {"seeds": (4000, 7000), "fertilizer": (5000, 9000), "labour": (10000, 18000), "irrigation": (3000, 6000), "pesticide": (1200, 2500)},
    "Cotton":    {"seeds": (1500, 3000), "fertilizer": (4000, 7000), "labour": (7000, 12000), "irrigation": (2500, 5000), "pesticide": (2000, 4500)},
    "Banana":    {"seeds": (5000, 9000), "fertilizer": (4500, 8000), "labour": (6000, 11000), "irrigation": (3000, 5500), "pesticide": (1500, 3000)},
    "Maize":     {"seeds": (1000, 2500), "fertilizer": (3000, 5500), "labour": (4000, 8000), "irrigation": (1500, 3000), "pesticide": (600, 1500)},
    "Jowar":     {"seeds": (500,  1200), "fertilizer": (1500, 3000), "labour": (3000, 6000), "irrigation": (500,  1500), "pesticide": (400, 1000)},
    "Bajra":     {"seeds": (400,  1000), "fertilizer": (1200, 2500), "labour": (2500, 5000), "irrigation": (400,  1200), "pesticide": (300,  800)},
    "Ragi":      {"seeds": (400,  900),  "fertilizer": (1500, 3000), "labour": (3000, 6000), "irrigation": (600,  1500), "pesticide": (300,  800)},
    "Turmeric":  {"seeds": (8000, 14000),"fertilizer": (4000, 7000), "labour": (7000, 12000),"irrigation": (2500, 5000), "pesticide": (1000, 2500)},
    "Onion":     {"seeds": (2000, 4000), "fertilizer": (3500, 6000), "labour": (6000, 10000), "irrigation": (2000, 4000), "pesticide": (1500, 3500)},
    "Chilli":    {"seeds": (1500, 3000), "fertilizer": (4000, 7000), "labour": (8000, 14000), "irrigation": (2000, 4000), "pesticide": (2000, 4000)},
    "Coconut":   {"seeds": (2000, 5000), "fertilizer": (3000, 6000), "labour": (3000, 6000),  "irrigation": (2000, 4000), "pesticide": (500, 1500)},
    "Urad":      {"seeds": (1000, 2000), "fertilizer": (1500, 3000), "labour": (3000, 6000),  "irrigation": (800,  2000), "pesticide": (500, 1200)},
    "Moong":     {"seeds": (1000, 2000), "fertilizer": (1500, 3000), "labour": (3000, 6000),  "irrigation": (800,  2000), "pesticide": (500, 1200)},
    "Arhar":     {"seeds": (800,  1800), "fertilizer": (2000, 4000), "labour": (3500, 7000),  "irrigation": (1000, 2500), "pesticide": (600, 1500)},
    "Sunflower": {"seeds": (800,  1500), "fertilizer": (2500, 4500), "labour": (3500, 7000),  "irrigation": (1500, 3000), "pesticide": (600, 1500)},
    "Tomato":    {"seeds": (1500, 3000), "fertilizer": (5000, 9000), "labour": (10000, 18000),"irrigation": (3000, 6000), "pesticide": (2500, 5000)},
}

DEFAULT_COST = {"seeds": (1000, 2500), "fertilizer": (2000, 4500), "labour": (4000, 8000), "irrigation": (1500, 3000), "pesticide": (800, 2000)}


def compute_suitability_score(
    district: str,
    crop_name: str,
    soil_type: str = None,
    season: str = None,
    irrigation_boost: bool = False,
    extra_rainfall_mm: float = 0.0,
) -> dict:
    """
    Compute a 0–10 suitability score for growing crop_name in district.

    Sub-scores:
      1. Yield Performance Score  (0–3): based on historical avg yield rank in district
      2. Rainfall Alignment Score (0–2.5): crop water needs vs district rainfall
      3. Soil Compatibility Score (0–2): based on CROP_SOIL_COMPATIBILITY table
      4. Irrigation Coverage Score(0–1.5): irrigation % supports this crop's water needs
      5. Historical Presence Score(0–1): whether this crop has been grown here historically

    Returns a dict with total_score, subscores, label, and reasoning.
    """
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    crop_title = crop_name.strip().title()

    # ── 1. Historical yield rank ──────────────────────────────────────────────
    df = _hist_for(district)
    crop_df = df[df["crop_name"].str.lower() == crop_title.lower()]
    all_crops_avg = (
        df.groupby("crop_name")["yield"].mean().sort_values(ascending=False).reset_index()
    )
    historical_presence = not crop_df.empty

    if historical_presence:
        crop_avg_yield = crop_df["yield"].mean()
        max_yield_in_district = all_crops_avg["yield"].max() if not all_crops_avg.empty else crop_avg_yield
        yield_score = min(3.0, round((crop_avg_yield / max(max_yield_in_district, 0.01)) * 3.0, 2))
    else:
        yield_score = 0.5  # some base credit — crop not local but may still grow

    # ── 2. Rainfall alignment ─────────────────────────────────────────────────
    rain_data = get_rainfall_stats(district)
    annual_mm = rain_data.get("avg_annual_mm", 0) + extra_rainfall_mm
    sw_mm = rain_data.get("sw_monsoon_mm", 0)
    ne_mm = rain_data.get("ne_monsoon_mm", 0)

    crop_key = crop_title if crop_title in CROP_WATER_REQ_MM else None
    needed_mm = CROP_WATER_REQ_MM.get(crop_key, 600) if crop_key else 600

    # Effective water = annual rain + 30% boost if irrigation_boost
    effective_water = annual_mm * (1.30 if irrigation_boost else 1.0)

    ratio = effective_water / max(needed_mm, 1)
    if ratio >= 1.2:
        rain_score = 2.5
    elif ratio >= 1.0:
        rain_score = 2.0
    elif ratio >= 0.8:
        rain_score = 1.5
    elif ratio >= 0.6:
        rain_score = 1.0
    else:
        rain_score = 0.5

    # ── 3. Soil compatibility ─────────────────────────────────────────────────
    if not soil_type:
        df_soil = df.groupby("soil_type").size()
        soil_type = df_soil.idxmax() if not df_soil.empty else "red soil"

    soil_compat = CROP_SOIL_COMPATIBILITY.get(crop_title, {})
    compat_val = soil_compat.get(soil_type.lower(), 0.65)  # default moderate
    soil_score = round(compat_val * 2.0, 2)

    # ── 4. Irrigation coverage ────────────────────────────────────────────────
    irr_data = get_irrigation_profile(district)
    irr_pct = irr_data.get("irrigation_coverage_pct", 0)
    effective_irr = min(100, irr_pct + (20 if irrigation_boost else 0))

    if needed_mm > 900:  # water-intensive — needs high irrigation
        irr_score = round(min(1.5, (effective_irr / 70) * 1.5), 2)
    else:  # drought-tolerant — irrigation is a bonus
        irr_score = round(min(1.5, 0.8 + (effective_irr / 100) * 0.7), 2)

    # ── 5. Historical presence ────────────────────────────────────────────────
    presence_score = 1.0 if historical_presence else 0.3

    # ── Total ─────────────────────────────────────────────────────────────────
    total = round(yield_score + rain_score + soil_score + irr_score + presence_score, 1)
    total = min(10.0, total)

    # Label
    if total >= 8.5:
        label = "Excellent"
    elif total >= 7.0:
        label = "Very Good"
    elif total >= 5.5:
        label = "Moderate"
    elif total >= 4.0:
        label = "Below Average"
    else:
        label = "Poor"

    return {
        "district": district,
        "crop": crop_title,
        "soil_type": soil_type,
        "season": season or "All seasons",
        "irrigation_boost_applied": irrigation_boost,
        "total_score": total,
        "label": label,
        "subscores": {
            "yield_performance": yield_score,
            "rainfall_alignment": rain_score,
            "soil_compatibility": soil_score,
            "irrigation_coverage": irr_score,
            "historical_presence": presence_score,
        },
        "effective_water_mm": round(effective_water, 0),
        "crop_water_need_mm": needed_mm,
        "annual_rainfall_mm": round(annual_mm, 0),
        "irrigation_pct": effective_irr,
        "historical_presence": historical_presence,
    }


def compute_whatif_simulation(
    district: str,
    crop_name: str,
    soil_type: str = None,
    season: str = None,
    irrigation_boost: bool = False,
    extra_rainfall_mm: float = 0.0,
) -> dict:
    """
    Run two suitability scores (baseline + modified) and return the delta.
    """
    baseline = compute_suitability_score(district, crop_name, soil_type, season, False, 0.0)
    if "error" in baseline:
        return baseline
    modified = compute_suitability_score(district, crop_name, soil_type, season, irrigation_boost, extra_rainfall_mm)
    if "error" in modified:
        return modified

    changes = []
    if irrigation_boost:
        changes.append("irrigation infrastructure improved")
    if extra_rainfall_mm > 0:
        changes.append(f"rainfall increased by {extra_rainfall_mm:.0f} mm")

    delta = round(modified["total_score"] - baseline["total_score"], 1)

    return {
        "district": district,
        "crop": crop_name.title(),
        "baseline": baseline,
        "modified": modified,
        "delta": delta,
        "changes_applied": changes,
        "verdict": (
            f"Suitability improves from {baseline['total_score']}/10 ({baseline['label']}) "
            f"to {modified['total_score']}/10 ({modified['label']}) "
            f"with {' and '.join(changes)}."
            if delta > 0
            else f"No significant improvement from these changes. Score stays at {baseline['total_score']}/10."
        ),
    }


def estimate_crop_cost(district: str, crop_name: str, area_acres: float = 1.0) -> dict:
    """
    Estimate the full-season cost of growing crop_name in district across area_acres.
    Adjusts labour costs using actual wage data from district profile.
    """
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    crop_title = crop_name.strip().title()
    profile = CROP_COST_PROFILES.get(crop_title, DEFAULT_COST)

    # Labour adjustment using real district wage data
    wage_data = get_wage_info(district)
    wage_adjustment = 1.0
    if "wages" not in wage_data or not wage_data["wages"]:
        wage_adjustment = 1.0
    else:
        wages = wage_data["wages"]
        male_wages = [
            int(v.replace("₹","").replace("/day","").strip())
            for k, v in wages.items()
            if "men" in k.lower() or "Men" in k
        ]
        if male_wages:
            avg_male = sum(male_wages) / len(male_wages)
            # Baseline TN avg ~₹350/day — adjust relative to that
            wage_adjustment = round(avg_male / 350, 2)

    components = {}
    total_min, total_max = 0, 0
    for component, (lo, hi) in profile.items():
        adj_lo = lo * area_acres
        adj_hi = hi * area_acres
        if component == "labour":
            adj_lo = round(adj_lo * wage_adjustment)
            adj_hi = round(adj_hi * wage_adjustment)
        else:
            adj_lo = round(adj_lo)
            adj_hi = round(adj_hi)
        components[component] = {"min": adj_lo, "max": adj_hi}
        total_min += adj_lo
        total_max += adj_hi

    return {
        "district": district,
        "crop": crop_title,
        "area_acres": area_acres,
        "wage_adjustment_factor": wage_adjustment,
        "components": components,
        "total_cost_min": total_min,
        "total_cost_max": total_max,
        "cost_per_acre_min": round(total_min / area_acres),
        "cost_per_acre_max": round(total_max / area_acres),
        "note": "Costs in Indian Rupees (₹). Labour adjusted for district wage rates.",
    }


def get_multi_criteria_crops(
    district: str,
    soil_type: str = None,
    season: str = None,
    water_need: str = None,      # "low" | "medium" | "high"
    profit_target: str = None,   # "low" | "medium" | "high"
    top_n: int = 5,
) -> dict:
    """
    Smart multi-criteria crop recommendation that filters by water need and profit.
    water_need: 'low' (<500mm), 'medium' (500–900mm), 'high' (>900mm)
    profit_target: derived from yield rank in district (~proxy for profitability)
    """
    district = fuzzy_district(district)
    if not district:
        return {"error": "District not found."}

    # Water need filter
    if water_need == "low":
        eligible_crops = [c for c, mm in CROP_WATER_REQ_MM.items() if mm < 500]
    elif water_need == "high":
        eligible_crops = [c for c, mm in CROP_WATER_REQ_MM.items() if mm >= 900]
    elif water_need == "medium":
        eligible_crops = [c for c, mm in CROP_WATER_REQ_MM.items() if 500 <= mm < 900]
    else:
        eligible_crops = list(CROP_WATER_REQ_MM.keys())

    crops = get_top_crops(district, soil_type, season, top_n=20)
    if "error" in crops:
        return crops

    filtered = [
        c for c in crops["crops"]
        if c["crop_name"] in [e.title() for e in eligible_crops]
           or c["crop_name"].lower() in [e.lower() for e in eligible_crops]
    ]

    if profit_target == "high":
        filtered = sorted(filtered, key=lambda x: x.get("avg_yield", 0), reverse=True)
    elif profit_target == "low":
        filtered = sorted(filtered, key=lambda x: x.get("avg_yield", 0))

    return {
        "district": district,
        "soil_filter": soil_type or "all",
        "season_filter": season or "all",
        "water_need_filter": water_need or "any",
        "profit_target": profit_target or "any",
        "crops": filtered[:top_n],
    }
