"""
tools.py – Wraps the existing, already-working `data_engine.py`,
`ml_models.py`, and `soil_classifier.py` functions as "Tools" the LLM
agent can choose to call.

IMPORTANT: this file does not reimplement any business logic. It is a
thin adapter layer only, on purpose — your CSV lookups, suitability
scoring, and trained models keep working exactly as before. The LLM's
job is purely to decide *which* of these to call and with *what
arguments*, based on the user's message.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any

import data_engine as de
import ml_models
import soil_classifier


@dataclass
class Tool:
    name: str
    description: str
    # JSON-schema-ish parameter spec shown to the LLM in the prompt.
    parameters: dict
    func: Callable[..., Any]

    def run(self, **kwargs) -> Any:
        try:
            return self.func(**kwargs)
        except TypeError as e:
            return {"error": f"Bad arguments for tool '{self.name}': {e}"}
        except Exception as e:  # noqa: BLE001 - surface any failure to the agent
            return {"error": f"Tool '{self.name}' failed: {e}"}


# ── data_engine-backed tools (CSV / historical lookups) ─────────────────

def _get_top_crops(district: str, soil_type: str = None, season: str = None):
    return de.get_top_crops(district, soil_type=soil_type, season=season)


def _get_best_districts_for_crop(crop_name: str, season: str = None):
    return de.get_best_districts_for_crop(crop_name, season=season)


def _get_district_overview(district: str):
    return de.get_district_overview(district)


def _get_rainfall_stats(district: str, year: int = None):
    return de.get_rainfall_stats(district, year=year)


def _get_wage_info(district: str):
    return de.get_wage_info(district)


def _get_irrigation_profile(district: str):
    return de.get_irrigation_profile(district)


def _get_yield_trend(district: str, crop: str):
    return de.get_yield_trend(district, crop)


def _get_pest_risk_historical(district: str):
    """Historical / rule-based pest risk from the dataset (not the ML model)."""
    return de.get_pest_risk(district)


def _get_fertilizer_recommendation(crop_name: str, soil_type: str = None,
                                    season: str = None, district: str = None):
    return de.get_fertilizer_recommendation(crop_name, soil_type=soil_type,
                                             season=season, district=district)


def _get_crop_planting_time(crop_name: str, district: str = None):
    return de.get_crop_planting_time(crop_name, district=district)


def _compute_suitability_score(district: str, crop_name: str, soil_type: str = None,
                                season: str = None):
    return de.compute_suitability_score(district, crop_name, soil_type=soil_type,
                                         season=season)


def _estimate_crop_cost(district: str, crop_name: str, area_acres: float = 1.0):
    return de.estimate_crop_cost(district, crop_name, area_acres=area_acres)


def _estimate_crop_profit(district: str, crop_name: str, area_acres: float = 1.0):
    return de.estimate_crop_profit(district, crop_name, area_acres=area_acres)


def _get_multi_criteria_crops(district: str, soil_type: str = None, season: str = None,
                               water_need: str = None, profit_tier: str = None):
    return de.get_multi_criteria_crops(district, soil_type=soil_type, season=season,
                                        water_need=water_need, profit_tier=profit_tier)


# ── ml_models-backed tools (trained model inference) ────────────────────
# We call the data_engine wrappers (predict_pest_risk_for_district /
# predict_crop_yield_for_district) rather than ml_models directly,
# because those wrappers already assemble the correct feature row from
# the historical CSVs before handing it to the .pkl models. That's the
# "glue" your project already has — the agent just triggers it.

def _predict_pest_risk_ml(district: str, crop_name: str, season: str = None,
                           soil_type: str = None):
    return de.predict_pest_risk_for_district(district, crop_name, season=season,
                                              soil_type=soil_type)


def _predict_crop_yield_ml(district: str, crop_name: str, season: str = None,
                            soil_type: str = None):
    return de.predict_crop_yield_for_district(district, crop_name, season=season,
                                               soil_type=soil_type)


def _classify_soil_image(image_path: str):
    label = soil_classifier.classify_soil(image_path)
    return {"soil_type": label}


def _get_market_price(crop_name: str = None, commodity: str = None, district: str = None):
    c = crop_name or commodity or ""
    if not c:
        return {"error": "Please specify a crop or commodity name."}
    import csv
    from pathlib import Path
    csv_path = Path(__file__).resolve().parent / "data" / "market_prices.csv"
    if not csv_path.exists():
        return {"error": "Market price dataset not found."}
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    c_lower = c.strip().lower()
    d_lower = (district or "").strip().lower()
    filtered = [
        r for r in rows
        if c_lower in r.get("commodity", "").lower()
        and (not d_lower or d_lower in r.get("district", "").lower())
    ]
    if not filtered:
        filtered = [r for r in rows if c_lower in r.get("commodity", "").lower()]
    if not filtered:
        return {"error": f"No market price records found for '{c}'"}
    try:
        def _pd(s):
            d, m, y = s.strip().split("/")
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        latest_date = max(_pd(r.get("arrival_date","")) for r in filtered)
        latest_rows = [r for r in filtered if _pd(r.get("arrival_date","")) == latest_date]
    except Exception:
        latest_rows = filtered[:6]
        latest_date = latest_rows[0].get("arrival_date", "")

    result = []
    for r in latest_rows[:6]:
        def _safe_int(v):
            try: return int(v)
            except: return v
        result.append({
            "state": r.get("state",""),
            "district": r.get("district",""),
            "market": r.get("market",""),
            "commodity": r.get("commodity",""),
            "variety": r.get("variety",""),
            "arrival_date": r.get("arrival_date",""),
            "min_price": _safe_int(r.get("min_price","")),
            "max_price": _safe_int(r.get("max_price","")),
            "modal_price": _safe_int(r.get("modal_price","")),
        })
    return {"commodity": c, "district": district, "arrival_date": latest_date, "records": result}


# ── list of tools ─────────────────────────────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="get_district_overview",
        description="General agricultural profile of a Tamil Nadu district: dominant soil, season, and top crops.",
        parameters={"district": "string, required — e.g. 'Madurai'"},
        func=_get_district_overview,
    ),
    Tool(
        name="get_top_crops",
        description="Best-performing crops for a district, optionally filtered by soil type and/or season.",
        parameters={"district": "string, required", "soil_type": "string, optional",
                     "season": "string, optional — Kharif/Rabi/Summer/Winter/Whole Year"},
        func=_get_top_crops,
    ),
    Tool(
        name="get_best_districts_for_crop",
        description="Which districts grow a given crop best, optionally filtered by season.",
        parameters={"crop_name": "string, required", "season": "string, optional"},
        func=_get_best_districts_for_crop,
    ),
    Tool(
        name="get_rainfall_stats",
        description="Rainfall statistics for a district, optionally for a specific year.",
        parameters={"district": "string, required", "year": "integer, optional"},
        func=_get_rainfall_stats,
    ),
    Tool(
        name="get_wage_info",
        description="Agricultural labour wage information for a district.",
        parameters={"district": "string, required"},
        func=_get_wage_info,
    ),
    Tool(
        name="get_irrigation_profile",
        description="Irrigation water sources and coverage for a district.",
        parameters={"district": "string, required"},
        func=_get_irrigation_profile,
    ),
    Tool(
        name="get_pest_risk_historical",
        description="Historical average pest risk (Low/Medium/High) and key pest list for a district.",
        parameters={"district": "string, required"},
        func=_get_pest_risk_historical,
    ),
    Tool(
        name="get_fertilizer_recommendation",
        description="Fertilizer/manure guidance for a crop, optionally scoped by soil/season/district.",
        parameters={"crop_name": "string, required", "soil_type": "string, optional",
                     "season": "string, optional", "district": "string, optional"},
        func=_get_fertilizer_recommendation,
    ),
    Tool(
        name="get_crop_planting_time",
        description="Best planting/sowing months for a crop, optionally scoped to a district.",
        parameters={"crop_name": "string, required", "district": "string, optional"},
        func=_get_crop_planting_time,
    ),
    Tool(
        name="compute_suitability_score",
        description="Numeric suitability score of growing a crop in a district given soil/season.",
        parameters={"district": "string, required", "crop_name": "string, required",
                     "soil_type": "string, optional", "season": "string, optional"},
        func=_compute_suitability_score,
    ),
    Tool(
        name="estimate_crop_cost",
        description="Estimated cultivation cost (seeds, fertilizer, labour, irrigation, pesticide) for a crop in a district.",
        parameters={"district": "string, required", "crop_name": "string, required",
                     "area_acres": "number, optional, default 1.0"},
        func=_estimate_crop_cost,
    ),
    Tool(
        name="estimate_crop_profit",
        description="Estimated profit (revenue minus cost) for growing a crop in a district.",
        parameters={"district": "string, required", "crop_name": "string, required",
                     "area_acres": "number, optional, default 1.0"},
        func=_estimate_crop_profit,
    ),
    Tool(
        name="get_multi_criteria_crops",
        description="Crop shortlist filtered by multiple criteria at once: soil, season, water need, profit tier.",
        parameters={"district": "string, required", "soil_type": "string, optional",
                     "season": "string, optional", "water_need": "string, optional — e.g. 'low'",
                     "profit_tier": "string, optional — e.g. 'high'"},
        func=_get_multi_criteria_crops,
    ),
    Tool(
        name="predict_pest_risk_ml",
        description=(
            "Run the TRAINED pest_risk_model.pkl to predict Low/Medium/High pest "
            "risk for a district+crop. Use this (not get_pest_risk_historical) "
            "whenever the user asks to 'predict' pest risk or asks a direct "
            "'what is the pest risk for X in Y' question."
        ),
        parameters={"district": "string, required", "crop_name": "string, required",
                     "season": "string, optional", "soil_type": "string, optional"},
        func=_predict_pest_risk_ml,
    ),
    Tool(
        name="predict_crop_yield_ml",
        description="Run the TRAINED yield_model.pkl to predict expected yield (t/ha) for a district+crop.",
        parameters={"district": "string, required", "crop_name": "string, required",
                     "season": "string, optional", "soil_type": "string, optional"},
        func=_predict_crop_yield_ml,
    ),
    Tool(
        name="classify_soil_image",
        description="Run the TRAINED soil_classification_model.h5 (CNN) on an uploaded image path to identify soil type.",
        parameters={"image_path": "string, required — server-side path to the uploaded image"},
        func=_classify_soil_image,
    ),
    Tool(
        name="get_market_price",
        description="Fetch today's live mandi market prices (min, modal, max price per quintal) for a crop/commodity in a district.",
        parameters={"crop_name": "string, required", "district": "string, optional"},
        func=_get_market_price,
    ),
]

TOOL_MAP: dict[str, Tool] = {t.name: t for t in TOOLS}


def tools_prompt_block() -> str:
    """Render the tool list as text for the ReAct system prompt."""
    lines = []
    for t in TOOLS:
        params = ", ".join(f"{k} ({v})" for k, v in t.parameters.items()) or "none"
        lines.append(f"- {t.name}({params}): {t.description}")
    return "\n".join(lines)
