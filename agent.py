
"""
agent.py – Smart Farming AI Agent
Pure local routing and response orchestration.
"""
import re
from difflib import get_close_matches
import data_engine as de
import nlg

MONTH_TO_SEASON = {
    "january": "Winter", "february": "Winter",
    "march": "Summer", "april": "Summer", "may": "Summer",
    "june": "Kharif", "july": "Kharif", "august": "Kharif", "september": "Kharif",
    "october": "Rabi", "november": "Rabi",
    "december": "Winter",
}
MONTH_ALIASES = {m[:3]: m for m in MONTH_TO_SEASON}

SEASON_DEFAULT_MONTH = {
    "Kharif": "July",
    "Rabi": "November",
    "Summer": "April",
    "Winter": "January",
    "Autumn": "October",
    "Whole Year": "April",
}

SOIL_KEYWORDS = {
    "alluvial soil": ["alluvial", "alluvium", "river soil"],
    "black soil": ["black", "regur", "black cotton"],
    "clay soil": ["clay", "clayey"],
    "red soil": ["red soil", "red", "laterite", "red loam"],
}

SEASON_KEYWORDS = {
    "Kharif": ["kharif", "rainy", "rainy season", "monsoon season", "southwest monsoon", "sw monsoon"],
    "Rabi": ["rabi", "northeast monsoon", "ne monsoon"],
    "Summer": ["summer", "summer season", "hot season", "dry season"],
    "Winter": ["winter", "winter season", "cold season"],
    "Autumn": ["autumn", "autumn season"],
    "Whole Year": ["whole year", "year round", "year-round", "annual", "perennial"],
}

KNOWN_CROPS = [
    "rice", "paddy", "groundnut", "sugarcane", "cotton", "banana", "maize",
    "jowar", "bajra", "ragi", "urad", "moong", "horsegram", "arhar", "tur",
    "turmeric", "onion", "tapioca", "coconut", "mango", "cashew", "chilli",
    "sesamum", "sunflower", "sorghum", "wheat", "tomato", "ginger", "garlic",
    "cardamom", "pepper", "coriander", "tobacco", "potato", "coffee", "tea",
    "rubber", "jute", "hemp", "linseed", "mustard", "safflower",
]

CROP_ALIASES = {
    "paddy": "rice", "tur": "arhar", "red gram": "arhar",
    "green gram": "moong", "black gram": "urad",
    "cholam": "sorghum", "cumbu": "bajra",
}

GREETING_PATTERNS = [
    r"^(hi|hello|hey|howdy)[\s!.]*$",
    r"good (morning|afternoon|evening)",
    r"what can you (do|help)", r"how are you", r"what are you",
    r"^start$", r"^help$",
]

WELCOME_TEXT = """👋 **Vanakkam! I'm your Smart Farming AI for Tamil Nadu.**"""

UNKNOWN_QUERY_TEXT = (
    "Sorry, I couldn't understand what you are saying. "
    "I may not have sufficient data to answer your query right now. "
    "Sorry for the inconvenience, but you can still try rephrasing your own query "
    "or use one of the suggested queries below."
)

INTENT_PATTERNS = {
    "best_district_for_crop": [r"which district.*(?:best|grow|grows|suitable)", r"where.*(?:best|grow|grows).*(?:crop|rice|coconut|groundnut|sugarcane|cotton|maize|banana)", r"best district.*(?:for|to grow)", r"district.*(?:grows|grow).*best"],
    "crop_recommend": [r"best crop", r"best crops", r"which crop", r"what crop", r"recommend crop", r"top crop", r"good crop", r"what can i grow"],
    "suitability": [r"suitab", r"can\s*i grow", r"cani grow", r"can .* grow", r"is .+ good for", r"how suitable", r"score", r"rate", r"evaluate"],
    "rainfall_info": [r"\brain(?:fall)?\b", r"precipitation", r"\bmonsoon rainfall\b", r"how much rain", r"annual rain"],
    "wage_info": [r"wage", r"salary", r"labour cost", r"worker pay", r"daily wage"],
    "irrigation_info": [r"irrigation", r"water source", r"canal", r"tank", r"groundwater", r"water availability"],
    "yield_trend": [r"yield trend", r"yield history", r"how has .+ yield changed", r"productivity over"],
    "pest_risk": [r"pest", r"disease", r"insect", r"fungal", r"blight", r"borer", r"aphid", r"whitefly"],
    "district_overview": [r"overview", r"profile", r"tell me about", r"summary of", r"agriculture in", r"everything about"],
    "cost_estimate": [r"cost", r"total cost", r"totoal cost", r"tot[a-z]* cost", r"expense", r"budget", r"investment", r"how much.*spend", r"cultivation cost"],
    "profit_estimate": [r"total profit", r"profit.*(?:growing|grow|planting|plant)", r"net profit", r"income.*(?:growing|grow)", r"revenue.*(?:growing|grow)"],
    "fertilizer_recommendation": [r"fertilizer", r"fertiliser", r"manure", r"npk", r"urea", r"dap", r"potash"],
    "planting_time": [r"best season", r"best month", r"which season", r"which month", r"when (?:to|should i) grow", r"when (?:to|should i) plant", r"season to grow", r"month to grow", r"planting time", r"sowing time"],
    "whatif": [r"what if", r"if irrigation", r"if.*rain", r"simulate", r"suppose", r"assuming"],
    "multi_criteria": [r"\bprofit\b", r"profitable", r"high profit", r"maximum profit", r"low water.*profit", r"minimum water.*profit", r"water efficient crop", r"drought.*profit"],
    "yield_predict": [r"predict yield", r"expected yield", r"forecast yield", r"yield prediction"],
    "pest_predict": [r"predict pest", r"predict.*risk", r"pest.*predict", r"ml pest"],
    "soil_info": [r"soil type", r"what soil", r"identify soil", r"upload.*soil"],
    "greeting": GREETING_PATTERNS,
}


def _all_known_crops() -> list[str]:
    dynamic = []
    try:
        if not de.hist_df.empty and "crop_name" in de.hist_df.columns:
            dynamic = sorted({str(c).strip().lower() for c in de.hist_df["crop_name"].dropna().unique().tolist()})
    except Exception:
        dynamic = []
    return sorted(set(dynamic + KNOWN_CROPS + list(CROP_ALIASES.keys())))


def _canonical_crop(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    if key in CROP_ALIASES:
        return CROP_ALIASES[key]
    crops = _all_known_crops()
    if key in crops:
        return key
    close = get_close_matches(key, crops, n=1, cutoff=0.75)
    return close[0] if close else None


def _clean_entity_phrase(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = re.split(r"\b(?:with|during|when|season|for crop|about)\b", raw, maxsplit=1, flags=re.I)[0]
    phrase = re.sub(
        r"\b(best|top|good|crop|crops|district|soil|rainfall|rain|pest|risks|risk|overview|profile|location|place|month|summer|winter|rainy|monsoon|autumn|kharif|rabi|hot|cold|dry|grow|growing|cultivate|cultivating|cultivation|plant|planting|with|during|season|for|in|of|the|a|an|certain|particular)\b",
        " ",
        raw,
        flags=re.I,
    )
    phrase = re.sub(r"\s+", " ", phrase).strip(" ?.!,")
    if phrase.lower() in {"my", "your", "our", "current", "this", "that", "it", "here"}:
        return None
    return phrase or None


def _exact_district(name: str | None) -> str | None:
    if not name:
        return None
    target = name.strip().lower()
    for district in de.ALL_DISTRICTS:
        if district.lower() == target:
            return district
    return None


def _extract_district(query: str) -> str | None:
    if not de.ALL_DISTRICTS:
        return None
    ql = query.lower()
    matches = [(d, len(d)) for d in de.ALL_DISTRICTS if d.lower() in ql]
    if matches:
        return max(matches, key=lambda x: x[1])[0]
    prep = re.search(r"\b(?:in|for|of)\s+([A-Za-z][A-Za-z ]{2,30})", query, re.I)
    if prep:
        cleaned = _clean_entity_phrase(prep.group(1))
        exact = _exact_district(cleaned)
        if exact:
            return exact
        if cleaned:
            close = get_close_matches(cleaned.title(), de.ALL_DISTRICTS, n=1, cutoff=0.82)
            if close:
                return close[0]
    words = re.findall(r"[a-zA-Z]+", query)
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i+n])
            exact = _exact_district(phrase)
            if exact:
                return exact
    return None


def _extract_soil(query: str) -> str | None:
    ql = query.lower()
    for soil, keywords in SOIL_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(kw)}\b", ql) for kw in keywords):
            return soil
    return None


def _extract_month(query: str) -> str | None:
    ql = query.lower()
    for month in MONTH_TO_SEASON:
        if re.search(rf"\b{month}\b", ql):
            return month.title()
    for short, full in MONTH_ALIASES.items():
        if re.search(rf"\b{short}\b", ql):
            return full.title()
    return None


def _extract_season(query: str) -> str | None:
    ql = query.lower()
    for season, keywords in SEASON_KEYWORDS.items():
        if any(kw in ql for kw in keywords):
            return season
    month = _extract_month(query)
    if month:
        return MONTH_TO_SEASON.get(month.lower())
    return None


def _extract_crop(query: str) -> str | None:
    ql = query.lower()
    crops = _all_known_crops()
    for alias, canonical in CROP_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", ql):
            return canonical
    for crop in sorted(crops, key=len, reverse=True):
        if re.search(rf"\b{re.escape(crop)}\b", ql):
            return _canonical_crop(crop)
    return None


def _get_memory(history: list | None) -> dict:
    memory = {"district": None, "soil": None, "season": None, "month": None, "crop": None}
    if not history:
        return memory
    for item in history:
        if item.get("role") == "system_memory" and isinstance(item.get("memory"), dict):
            for key in memory:
                memory[key] = item["memory"].get(key) or memory[key]
    return memory


def _merge_memory(memory: dict, district=None, soil=None, season=None, month=None, crop=None) -> dict:
    updated = dict(memory or {})
    for key, value in {"district": district, "soil": soil, "season": season, "month": month, "crop": crop}.items():
        if value:
            updated[key] = value
    if updated.get("month") and not updated.get("season"):
        updated["season"] = MONTH_TO_SEASON.get(updated["month"].lower())
    if updated.get("season") and not updated.get("month"):
        updated["month"] = SEASON_DEFAULT_MONTH.get(updated["season"])
    return updated


def _detect_intent(query: str) -> str:
    ql = query.lower().strip()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, ql))
        if score > 0:
            scores[intent] = score
    return max(scores, key=scores.get) if scores else "general"


def _entity_not_found_message(kind: str, raw: str | None) -> str:
    if kind == "district":
        suggestion = de.fuzzy_district(raw or "")
        msg = "Sorry for the inconvenience, I don't have data for that particular district right now. We are still in development, and it may be available in the future."
        if suggestion:
            msg += f" Please check the spelling once or twice. Did you mean **{suggestion}**?"
        else:
            msg += " Please check the spelling once or twice and try again."
        return msg
    crops = _all_known_crops()
    suggestion = None
    if raw:
        close = get_close_matches(raw.lower(), crops, n=1, cutoff=0.6)
        suggestion = close[0].title() if close else None
    msg = (
        "Based on the Tamil Nadu agriculture dataset, I cannot find that particular crop. "
        "The crop records may be sparse, or the crop may have limited growth around the available districts, "
        "so I don't have enough details regarding it. I sincerely apologize for the inconvenience, "
        "and I will surely improve this coverage in the future."
    )
    if suggestion:
        msg += f" Please check the spelling once or twice. Did you mean **{suggestion}**?"
    else:
        msg += " Please check the spelling once or twice and try again."
    return msg


def _missing_district_reply(intent: str) -> str:
    examples = {
        "crop_recommend": "Best crops for Coimbatore?",
        "best_district_for_crop": "Which district is best for rice?",
        "rainfall_info": "Rainfall in Salem?",
        "irrigation_info": "Irrigation sources in Madurai?",
        "yield_trend": "Rice yield trend in Cuddalore?",
        "pest_risk": "Pest risks in Dharmapuri?",
        "district_overview": "Overview of Erode district?",
        "suitability": "How suitable is rice in Thanjavur?",
        "cost_estimate": "Cost to grow groundnut in Madurai?",
        "planting_time": "Best season to grow coconut in Coimbatore?",
        "whatif": "What if irrigation improved in Erode for rice?",
    }
    return f"I need a district name for that. For example: *\"{examples.get(intent, 'Tell me about Coimbatore?')}\"*"


def _candidate_unknown_district(query: str) -> str | None:
    if re.search(r"\b(?:my|your|our|current|this)\s+district\b", query, re.I):
        return None
    if re.search(r"\b(?:cost|expense|budget|investment|profit|profitable|income|revenue)\b", query, re.I) and re.search(r"\b(?:for|of|to|in)\s+(?:growing|grow|cultivating|cultivate|cultivation|planting|plant)\b", query, re.I):
        return None
    patterns = [
        r"\b(?:in|for|of)\s+([A-Za-z][A-Za-z ]{2,30})",
        r"\brainfall\s+(?:does\s+)?([A-Za-z][A-Za-z ]{2,30})\s+(?:receive|get|have)",
        r"\b(?:does|do)\s+([A-Za-z][A-Za-z ]{2,30})\s+(?:receive|get|have)",
    ]
    for pat in patterns:
        m = re.search(pat, query, re.I)
        if not m:
            continue
        phrase = _clean_entity_phrase(m.group(1))
        if not phrase:
            continue
        if _exact_district(phrase):
            return None
        return phrase
    return None


def _candidate_unknown_crop(query: str) -> str | None:
    if re.search(r"\b(?:my|your|our|current|this)\s+crop\b", query, re.I):
        return None
    patterns = [
        r"(?:how suitable is|how suitable would|is)\s+([A-Za-z ]+?)\s+(?:in|for)\b",
        r"(?:best month|best season|which month|which season|season|month).*?\b(?:grow|plant)\s+([A-Za-z ]+?)(?:\s+(?:in|for)\b|$)",
        r"(?:suitability of|predict yield of|predict pest risk for|fertilizer for|cost to grow|cost of cultivating|grow|cultivate|cultivating)\s+([A-Za-z ]+?)\s+(?:in|for)\b",
        r"is\s+([A-Za-z ]+?)\s+good\s+for",
    ]
    for pat in patterns:
        m = re.search(pat, query, re.I)
        if m:
            phrase = _clean_entity_phrase(m.group(1))
            if not phrase:
                return None
            if _canonical_crop(phrase):
                return None
            return phrase
    return None


def _suggest_followups(intent: str, context: dict | None = None) -> list[str]:
    ctx = context or {}
    district = ctx.get("district") or "Coimbatore"
    crop = ctx.get("crop") or "rice"
    options = {
        "crop_recommend": [
            f"Fertilizer for {crop} in {district}",
            f"Rainfall in {district}",
            f"How suitable is {crop} in {district}?",
        ],
        "fertilizer_recommendation": [
            f"Cost to grow {crop} in {district}",
            f"Predict yield of {crop} in {district}",
            f"What pests affect {crop} in {district}?",
        ],
        "suitability": [
            f"Predict yield of {crop} in {district}",
            f"Fertilizer for {crop} in {district}",
            f"What if irrigation improved in {district} for {crop}?",
        ],
        "rainfall_info": [
            f"Best crops for {district}",
            f"What is the irrigation profile of {district}?",
            f"What if rainfall reduced in {district} for {crop}?",
        ],
        "district_overview": [
            f"Best crops for {district}",
            f"Rainfall in {district}",
            f"Irrigation profile of {district}",
        ],
        "whatif": [
            f"How suitable is {crop} in {district}?",
            f"Predict yield of {crop} in {district}",
            f"Cost to grow {crop} in {district}",
        ],
    }
    return options.get(intent, [f"Best crops for {district}", f"Rainfall in {district}", f"Overview of {district} district"])


def _describe_context_update(context: dict) -> str:
    parts = []
    labels = {
        "district": "district",
        "crop": "crop",
        "soil": "soil",
        "season": "season",
        "month": "month",
    }
    for key in ("district", "crop", "soil", "season", "month"):
        value = context.get(key)
        if value:
            parts.append(f"**{labels[key]}:** {str(value).title()}")
    if not parts:
        return UNKNOWN_QUERY_TEXT
    return "Got it. I have updated the active context: " + ", ".join(parts) + ". You can now ask a follow-up question using this context."


def _ensure_followup_chips(text: str, intent: str, context: dict | None = None) -> str:
    if not text:
        return text
    if "FOLLOWUP_CHIPS:" in text:
        return text
    chips = _suggest_followups(intent, context)[:3]
    return text.rstrip() + "\n\n---\n**FOLLOWUP_CHIPS:" + "|".join(chips) + "**"


def _fmt_yield_prediction(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    return (
        f"### 🌾 ML Yield Prediction — {data['crop_name']} in {data['district']}\n\n"
        f"Expected yield: **{data['predicted_yield']} tonnes per hectare**\n\n"
        f"| Detail | Value |\n|--------|-------|\n"
        f"| District | {data['district']} |\n| Crop | {data['crop_name']} |\n"
        f"| Season | {data.get('season', 'Unknown')} |\n| Soil Type | {data.get('soil_type', 'Unknown')} |\n"
        f"| Predicted Yield | **{data['predicted_yield']} t/ha** |"
    )


def _fmt_pest_prediction(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    return (
        f"### 🐛 ML Pest Risk — {data['crop_name']} in {data['district']}\n\n"
        f"Predicted pest risk: **{data['pest_risk']}**\n\n"
        f"| Detail | Value |\n|--------|-------|\n"
        f"| District | {data['district']} |\n| Crop | {data['crop_name']} |\n"
        f"| Season | {data.get('season', 'Unknown')} |\n| Soil | {data.get('soil_type', 'Unknown')} |\n"
        f"| Risk Level | **{data['pest_risk']}** |"
    )


def _fallback_router(message: str, district: str, soil: str, season: str, crop: str, month: str, memory: dict) -> dict:
    intent = _detect_intent(message)

    if intent == "cost_estimate":
        district = district or "Coimbatore"
        crop = crop or "rice"
    elif intent == "profit_estimate":
        district = district or "Coimbatore"
        crop = crop or "rice"
    elif intent == "multi_criteria":
        district = district or "Coimbatore"

    new_memory = _merge_memory(memory, district=district, soil=soil, season=season, month=month, crop=crop)
    ctx = {"district": district, "soil": soil, "season": season, "month": month, "crop": crop}

    district_required = {"crop_recommend", "rainfall_info", "wage_info", "irrigation_info", "yield_trend", "pest_risk", "district_overview", "suitability", "cost_estimate", "whatif", "multi_criteria", "yield_predict", "pest_predict"}
    crop_required = {"suitability", "cost_estimate", "whatif", "fertilizer_recommendation", "yield_predict", "pest_predict", "yield_trend"}
    crop_required.add("planting_time")
    crop_required.add("best_district_for_crop")
    district_required.add("profit_estimate")
    crop_required.add("profit_estimate")

    explicit_unknown_district = _candidate_unknown_district(message)
    if intent != "best_district_for_crop" and intent in district_required and explicit_unknown_district and not _extract_district(message):
        text = _entity_not_found_message("district", explicit_unknown_district)
        return {"text": _ensure_followup_chips(text, intent, ctx), "intent": intent, "district": None, "memory": memory}

    explicit_unknown_crop = _candidate_unknown_crop(message)
    if intent in crop_required and explicit_unknown_crop and not _extract_crop(message):
        text = _entity_not_found_message("crop", explicit_unknown_crop)
        unknown_crop_memory = _merge_memory(memory, district=district, soil=soil, season=season, month=month)
        unknown_crop_memory["crop"] = None
        return {"text": _ensure_followup_chips(text, intent, {**ctx, "crop": None}), "intent": intent, "district": district, "memory": unknown_crop_memory}

    if intent == "best_district_for_crop":
        requested_season = _extract_season(message)
        text = nlg.describe_best_districts_for_crop(de.get_best_districts_for_crop(crop, requested_season, top_n=7))
        return {"text": _ensure_followup_chips(text, intent, {**ctx, "district": None}), "intent": intent, "district": None, "memory": new_memory}

    if intent in district_required and not district:
        unknown = _candidate_unknown_district(message)
        text = _entity_not_found_message("district", unknown) if unknown else _missing_district_reply(intent)
        return {"text": _ensure_followup_chips(text, intent, ctx), "intent": intent, "district": None, "memory": new_memory}

    if intent in crop_required and not crop:
        unknown = _candidate_unknown_crop(message)
        if unknown:
            text = _entity_not_found_message("crop", unknown)
        else:
            text = f"Which crop would you like me to use for **{district or 'this district'}**?"
        return {"text": _ensure_followup_chips(text, intent, ctx), "intent": intent, "district": district, "memory": new_memory}

    if intent == "crop_recommend":
        crop_data = de.get_top_crops(district, soil, season, top_n=7)
        text = nlg.describe_crops(district, crop_data, de.get_rainfall_stats(district), de.get_irrigation_profile(district))
    elif intent == "suitability":
        text = nlg.describe_suitability_score(district, crop, de.compute_suitability_score(district, crop, soil, season))
    elif intent == "whatif":
        irr_delta = 0.0
        rain_delta = 0.0
        m = re.search(r"([+-]?\d+)\s*%", message)
        if m:
            irr_delta = float(m.group(1))
        elif re.search(r"(less|decrease|reduced|drop)", message, re.I):
            irr_delta = -20.0
        elif re.search(r"(improve|increase|boost|more)", message, re.I):
            irr_delta = 20.0
        m2 = re.search(r"([+-]?\d+)\s*mm", message, re.I)
        if m2:
            rain_delta = float(m2.group(1))
        elif re.search(r"rain(?:fall)?\s+(?:is\s+|gets\s+|becomes\s+)?(less|low|lower|decrease|decreased|reduced|drop)", message, re.I):
            rain_delta = -200.0
        elif re.search(r"rain(?:fall)?\s+(?:is\s+|gets\s+|becomes\s+)?(more|increase|increased|improve|higher)", message, re.I):
            rain_delta = 200.0
        text = nlg.describe_whatif(district, crop, de.compute_whatif_simulation(district, crop, soil, season, irr_delta, rain_delta))
    elif intent == "cost_estimate":
        text = nlg.describe_cost_estimate(district, crop, de.estimate_crop_cost(district, crop))
    elif intent == "profit_estimate":
        text = nlg.describe_profit_estimate(de.estimate_crop_profit(district, crop))
    elif intent == "multi_criteria":
        water_need = "low" if re.search(r"low water|drought|dry|water.efficien", message, re.I) else None
        profit_t = "high" if re.search(r"\bprofit\b|high profit|maximum profit|profitable", message, re.I) else None
        text = nlg.describe_crops(district, de.get_multi_criteria_crops(district, soil, season, water_need, profit_t))
        if profit_t == "high":
            text = (
                f"Here are the strongest profit-oriented crop options for **{district}**. "
                "I am using historical yield, cultivated area, and consistency as the available profitability proxy.\n\n"
                + text
            )
    elif intent == "fertilizer_recommendation":
        text = nlg.describe_fertilizer(de.get_fertilizer_recommendation(crop, soil, season, district))
    elif intent == "planting_time":
        text = nlg.describe_planting_time(de.get_crop_planting_time(crop, district))
    elif intent == "rainfall_info":
        text = nlg.describe_rainfall(district, de.get_rainfall_stats(district))
    elif intent == "wage_info":
        text = nlg.describe_wages(district, de.get_wage_info(district))
    elif intent == "irrigation_info":
        text = nlg.describe_irrigation(district, de.get_irrigation_profile(district))
    elif intent == "yield_trend":
        text = nlg.describe_yield_trend(district, crop, de.get_yield_trend(district, crop))
    elif intent == "pest_risk":
        text = nlg.describe_pest_risk(district, de.get_pest_risk(district))
    elif intent == "district_overview":
        text = nlg.describe_overview(district, de.get_district_overview(district), de.get_rainfall_stats(district))
    elif intent == "yield_predict":
        text = _fmt_yield_prediction(de.predict_crop_yield_for_district(district, crop, season, soil))
    elif intent == "pest_predict":
        text = _fmt_pest_prediction(de.predict_pest_risk_for_district(district, crop, season, soil))
    elif intent == "soil_info":
        text = "📎 Use the soil upload option in the sidebar to identify soil type."
    else:
        text = UNKNOWN_QUERY_TEXT
        intent = "general"

    return {"text": _ensure_followup_chips(text, intent, ctx), "intent": intent, "district": district, "memory": new_memory}


def process_query(message: str, history: list = None) -> dict:
    message = (message or "").strip()
    blank_mem = {"district": None, "soil": None, "season": None, "month": None, "crop": None}
    if not message:
        return {"text": WELCOME_TEXT, "intent": "greeting", "district": None, "memory": blank_mem}

    memory = _get_memory(history)
    quick_district = _extract_district(message)
    quick_soil = _extract_soil(message)
    quick_month = _extract_month(message)
    quick_season = _extract_season(message)
    quick_crop = _extract_crop(message)

    district = quick_district or memory.get("district")
    soil = quick_soil or memory.get("soil")
    month = quick_month or memory.get("month")
    season = quick_season or memory.get("season")
    crop = quick_crop or memory.get("crop")

    if month and not season:
        season = MONTH_TO_SEASON.get(month.lower())
    if quick_season and not quick_month:
        month = SEASON_DEFAULT_MONTH.get(quick_season) or month

    new_memory = _merge_memory(memory, district=quick_district, soil=quick_soil, season=quick_season or season, month=quick_month or month, crop=quick_crop)

    ql = message.lower().strip()
    if any(re.search(p, ql) for p in GREETING_PATTERNS):
        return {"text": WELCOME_TEXT, "intent": "greeting", "district": district, "memory": new_memory}

    if _detect_intent(message) == "general" and any([quick_district, quick_crop, quick_soil, quick_season, quick_month]):
        text = _describe_context_update(new_memory)
        return {
            "text": _ensure_followup_chips(text, "context_update", new_memory),
            "intent": "context_update",
            "district": new_memory.get("district"),
            "memory": new_memory,
        }

    return _fallback_router(message, district, soil, season, crop, month, memory)
