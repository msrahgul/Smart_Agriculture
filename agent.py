"""
agent.py – NLP Intent Engine
Parses natural language agricultural queries and dispatches to data_engine functions.
No external API needed — pure keyword + regex + fuzzy matching.
"""
import re
from difflib import get_close_matches
import data_engine as de

# ── Intent keywords ────────────────────────────────────────────────────────────
INTENT_PATTERNS = {
    "crop_recommend": [
        r"best crop", r"which crop", r"what crop", r"recommend crop",
        r"suggest crop", r"crop for", r"grow in", r"suitable crop",
        r"what should i grow", r"what to grow", r"what to plant",
        r"which crops", r"top crops",
    ],
    "rainfall_info": [
        r"rain", r"rainfall", r"precipitation", r"monsoon",
        r"how much rain", r"wet season", r"dry season",
    ],
    "wage_info": [
        r"wage", r"salary", r"pay", r"labour cost", r"labor cost",
        r"how much does labour", r"worker pay", r"daily wage",
        r"field labour", r"farm worker",
    ],
    "irrigation_info": [
        r"irrigation", r"water source", r"canal", r"tank", r"bore well",
        r"tube well", r"open well", r"groundwater", r"water level",
        r"how is water", r"water availability",
    ],
    "yield_trend": [
        r"yield", r"production trend", r"crop yield", r"how much.*produce",
        r"yield trend", r"yield over years", r"yield history",
        r"productivity", r"output of", r"produce trend",
    ],
    "pest_risk": [
        r"pest", r"disease", r"insect", r"fungal", r"blight", r"borer",
        r"aphid", r"risk", r"crop disease", r"pest risk", r"plant disease",
        r"crop protection", r"which pest",
    ],
    "district_overview": [
        r"overview", r"profile", r"tell me about", r"about.*district",
        r"summary of", r"general info", r"information about",
        r"details of", r"describe", r"what is.*like", r"agriculture in",
    ],
    "soil_info": [
        r"soil", r"soil type", r"what soil", r"identify soil",
        r"black soil", r"red soil", r"alluvial", r"clay soil",
    ],
    "greeting": [
        r"^hi$", r"^hello$", r"^hey$", r"good morning", r"good afternoon",
        r"good evening", r"what can you do", r"help me", r"what are you",
        r"how are you", r"^start$",
    ],
}

# ── Soil type keywords ────────────────────────────────────────────────────────
SOIL_KEYWORDS = {
    "alluvial soil": ["alluvial", "alluvium"],
    "black soil": ["black", "regur", "black cotton"],
    "clay soil": ["clay", "clayey"],
    "red soil": ["red", "laterite"],
}

# ── Season keywords ───────────────────────────────────────────────────────────
SEASON_KEYWORDS = {
    "Kharif": ["kharif", "summer", "june", "july", "august", "southwest monsoon"],
    "Rabi": ["rabi", "winter", "october", "november", "december", "northeast monsoon"],
    "Whole Year": ["whole year", "annual", "year round", "perennial"],
}

# ── Crop name hints ───────────────────────────────────────────────────────────
KNOWN_CROPS = [
    "rice", "paddy", "groundnut", "sugarcane", "cotton", "banana", "maize",
    "jowar", "bajra", "ragi", "urad", "moong", "horsegram", "arhar", "tur",
    "turmeric", "onion", "tapioca", "coconut", "mango", "cashew", "chilli",
    "sesamum", "sunflower", "sorghum", "wheat", "tomato", "ginger", "garlic",
    "cardamom", "pepper", "coriander", "tobacco", "potato",
]

GREETING_RESPONSE = """👋 **Welcome to the Smart Farming AI Assistant!**

I'm your intelligent agricultural expert for **Tamil Nadu**. Here's what I can help you with:

🌾 **Crop Recommendations** — *"Best crops for Madurai with red soil?"*
🌧️ **Rainfall Data** — *"How much rain does Salem get?"*
💰 **Wage Information** — *"What are daily wages in Coimbatore?"*
💧 **Irrigation & Groundwater** — *"Water availability in Thanjavur?"*
📈 **Yield Trends** — *"Rice yield trend in Cuddalore?"*
🐛 **Pest Risk Analysis** — *"Pest risks in Dharmapuri?"*
📋 **District Overview** — *"Give me an overview of Erode"*
🖼️ **Soil Detection** — Upload a soil image to identify soil type

Just type your question naturally — I understand plain English! 🇮🇳
"""

HELP_RESPONSE = GREETING_RESPONSE


def _detect_intent(query: str) -> str:
    ql = query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, ql):
                return intent
    return "general"


def _extract_district(query: str) -> str | None:
    """Fuzzy-match a district name from the query."""
    if not de.ALL_DISTRICTS:
        return None
    ql = query.lower()
    # Try direct match first
    for d in de.ALL_DISTRICTS:
        if d.lower() in ql:
            return d
    # Try word-by-word fuzzy
    words = re.findall(r"[a-zA-Z]+", query)
    for word in words:
        if len(word) < 4:
            continue
        result = de.fuzzy_district(word)
        if result:
            return result
    # Try bigrams
    tokens = re.findall(r"[a-zA-Z]+", query)
    for i in range(len(tokens) - 1):
        phrase = f"{tokens[i]} {tokens[i+1]}"
        result = de.fuzzy_district(phrase)
        if result:
            return result
    return None


def _extract_soil(query: str) -> str | None:
    ql = query.lower()
    for soil, keywords in SOIL_KEYWORDS.items():
        for kw in keywords:
            if kw in ql:
                return soil
    return None


def _extract_season(query: str) -> str | None:
    ql = query.lower()
    for season, keywords in SEASON_KEYWORDS.items():
        for kw in keywords:
            if kw in ql:
                return season
    return None


def _extract_crop(query: str) -> str | None:
    ql = query.lower()
    for crop in KNOWN_CROPS:
        if crop in ql:
            return crop
    return None


def _extract_year(query: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", query)
    return int(match.group()) if match else None


# ── Response Formatters ────────────────────────────────────────────────────────
def _fmt_crop_recommend(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    district = data["district"]
    soil = data["soil_filter"]
    season = data["season_filter"]
    crops = data["crops"]
    out = [f"### 🌾 Top Crops for **{district}**"]
    if soil != "all":
        out[0] += f" · {soil.title()}"
    if season != "all":
        out[0] += f" · {season} Season"
    out.append("")
    out.append("| Rank | Crop | Soil Type | Season | Avg Yield (t/ha) | Max Yield (t/ha) |")
    out.append("|------|------|-----------|--------|-----------------|-----------------|")
    for i, c in enumerate(crops, 1):
        out.append(f"| #{i} | **{c['crop_name']}** | {c['soil_type'].title()} | {c['season']} | {c['avg_yield']} | {c['max_yield']} |")
    out.append("")
    out.append(f"*Data covers historical records up to 2019. Yield in tonnes per hectare.*")
    return "\n".join(out)


def _fmt_rainfall(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    d = data["district"]
    out = [f"### 🌧️ Rainfall Statistics — **{d}** ({data['period']})"]
    out.append("")
    out.append(f"| Metric | Average (mm) |")
    out.append(f"|--------|-------------|")
    out.append(f"| 🌍 Annual Rainfall | **{data['avg_annual_mm']}** |")
    out.append(f"| 🌀 SW Monsoon (Jun–Sep) | {data['sw_monsoon_mm']} |")
    out.append(f"| 🌊 NE Monsoon (Oct–Dec) | {data['ne_monsoon_mm']} |")
    out.append(f"| ☀️ Hot Weather (Mar–May) | {data['hot_weather_mm']} |")
    out.append(f"| ❄️ Winter (Jan–Feb) | {data['winter_mm']} |")
    out.append("")
    if data.get("yearly_trend"):
        out.append("**Recent Annual Rainfall Trend:**")
        out.append("| Year | Total (mm) |")
        out.append("|------|-----------|")
        for row in data["yearly_trend"]:
            out.append(f"| {int(row['year'])} | {row['total_mm']} |")
    return "\n".join(out)


def _fmt_wage(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    d = data["district"]
    out = [f"### 💰 Agricultural Wages — **{d}** ({data['year']})"]
    out.append("")
    out.append("| Operation | Daily Wage |")
    out.append("|-----------|-----------|")
    for op, wage in data["wages"].items():
        out.append(f"| {op} | **{wage}** |")
    if not data["wages"]:
        out.append("*Wage data not available for this district.*")
    return "\n".join(out)


def _fmt_irrigation(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    d = data["district"]
    out = [f"### 💧 Irrigation Profile — **{d}** (2024–25)"]
    out.append("")
    out.append(f"- 🌱 **Net Area Sown:** {data['net_area_sown_ha']} ha")
    out.append(f"- 💦 **Total Irrigated:** {data['total_irrigated_ha']} ha ({data['irrigation_coverage_pct']}%)")
    out.append(f"- 🔋 **Avg Groundwater Depth:** {data['groundwater_avg_m']} m")
    out.append("")
    out.append("**Irrigation Sources:**")
    out.append("| Source | Area |")
    out.append("|--------|------|")
    for src, area in data["irrigation_sources"].items():
        out.append(f"| {src} | {area} |")
    return "\n".join(out)


def _fmt_yield_trend(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    d, crop = data["district"], data["crop"]
    out = [f"### 📈 Yield Trend — **{crop}** in {d}"]
    out.append("")
    out.append(f"- 📊 **Average Yield:** {data['avg_yield_t_ha']} t/ha")
    out.append(f"- 🏆 **Best Year:** {data['best_year']} ({data['best_yield_t_ha']} t/ha)")
    out.append("")
    out.append("**Year-wise Average Yield:**")
    out.append("| Year | Yield (t/ha) |")
    out.append("|------|-------------|")
    for row in data["trend"]:
        out.append(f"| {int(row['year'])} | {row['avg_yield_t_ha']} |")
    return "\n".join(out)


def _fmt_pest_risk(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    d = data["district"]
    out = [f"### 🐛 Pest Risk Analysis — **{d}**"]
    out.append("")
    out.append(f"- 🌧️ Avg Annual Rain: **{data['avg_annual_rain_mm']} mm**")
    out.append(f"- 🌀 SW Monsoon: **{data['sw_monsoon_mm']} mm** | 🌊 NE Monsoon: **{data['ne_monsoon_mm']} mm**")
    out.append(f"- 📉 Deviation from Normal: **{data['deviation_pct']}%**")
    out.append("")
    for r in data["risks"]:
        sev_emoji = "🔴" if r["severity"] == "High" else "🟡" if "Moderate" in r["severity"] else "🟢"
        out.append(f"**{sev_emoji} Severity: {r['severity']}**")
        out.append(f"- 🦟 **Likely Pests:** {', '.join(r['pests'])}")
        out.append(f"- 🌿 **Crops at Risk:** {', '.join(r['crops_affected'])}")
        out.append(f"- 🛡️ **Prevention:** {r['prevention']}")
        out.append("")
    return "\n".join(out)


def _fmt_overview(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    d = data["district"]
    out = [f"### 📋 Agricultural Overview — **{d}**"]
    out.append("")
    if "total_area_ha" in data:
        out.append(f"| Metric | Value |")
        out.append(f"|--------|-------|")
        out.append(f"| 🗺️ Total Geographical Area | {data['total_area_ha']} ha |")
        out.append(f"| 🌱 Net Area Sown | {data['net_area_sown_ha']} ha |")
        out.append(f"| 🌳 Forest Area | {data['forest_area_ha']} ha |")
        out.append(f"| 💦 Total Irrigated | {data['total_irrigated_ha']} ha |")
        out.append("")
    if "data_years" in data:
        out.append(f"*Historical crop data: {data['data_years']}*")
        out.append("")
    if "top_5_crops" in data:
        out.append("**Top 5 Crops by Average Yield:**")
        out.append("| Crop | Avg Yield (t/ha) |")
        out.append("|------|-----------------|")
        for c in data["top_5_crops"]:
            out.append(f"| {c['crop']} | {c['avg_yield_t_ha']} |")
        out.append("")
    if "soil_types" in data:
        soils = ", ".join([f"{k.title()} ({v} records)" for k, v in list(data["soil_types"].items())[:4]])
        out.append(f"🏔️ **Soil Types:** {soils}")
        out.append("")
    if "seasons" in data:
        seasons = ", ".join([f"{k} ({v} records)" for k, v in data["seasons"].items()])
        out.append(f"📅 **Seasons:** {seasons}")
    return "\n".join(out)


# ── Main Entry Point ──────────────────────────────────────────────────────────
def process_query(message: str, history: list = None) -> dict:
    """
    Main agent entry. Parse the message, call data functions, return response.
    Returns: {"text": str, "intent": str, "district": str|None, "data": dict}
    """
    message = message.strip()
    if not message:
        return {"text": GREETING_RESPONSE, "intent": "greeting", "district": None}

    intent = _detect_intent(message)
    district = _extract_district(message)
    soil = _extract_soil(message)
    season = _extract_season(message)
    crop = _extract_crop(message)
    year = _extract_year(message)

    # ── Greeting ────────────────────────────────────────────────────────────────
    if intent == "greeting":
        return {"text": GREETING_RESPONSE, "intent": "greeting", "district": None}

    # ── Generic without district ────────────────────────────────────────────────
    if intent in ("crop_recommend", "rainfall_info", "wage_info", "irrigation_info",
                  "yield_trend", "pest_risk", "district_overview") and not district:
        return {
            "text": f"🤔 I need a **district name** to answer that.\n\nFor example:\n- *\"Best crops for Coimbatore?\"*\n- *\"Rainfall in Salem?\"*\n\nAvailable districts: {', '.join(de.ALL_DISTRICTS[:10])}... and {len(de.ALL_DISTRICTS)-10} more.",
            "intent": intent,
            "district": None,
        }

    # ── Route to data functions ─────────────────────────────────────────────────
    if intent == "crop_recommend":
        raw = de.get_top_crops(district, soil, season)
        return {"text": _fmt_crop_recommend(raw), "intent": intent, "district": district, "data": raw}

    if intent == "rainfall_info":
        raw = de.get_rainfall_stats(district, year)
        return {"text": _fmt_rainfall(raw), "intent": intent, "district": district, "data": raw}

    if intent == "wage_info":
        raw = de.get_wage_info(district)
        return {"text": _fmt_wage(raw), "intent": intent, "district": district, "data": raw}

    if intent == "irrigation_info":
        raw = de.get_irrigation_profile(district)
        return {"text": _fmt_irrigation(raw), "intent": intent, "district": district, "data": raw}

    if intent == "yield_trend":
        if not crop:
            # Ask what crop
            crops_available = de.get_all_crops_for_district(district)
            sample = ", ".join(crops_available[:8]) if crops_available else "various crops"
            return {
                "text": f"📊 Sure! Which **crop** yield trend do you want in **{district}**?\n\nAvailable crops include: *{sample}*...",
                "intent": intent,
                "district": district,
            }
        raw = de.get_yield_trend(district, crop)
        return {"text": _fmt_yield_trend(raw), "intent": intent, "district": district, "data": raw}

    if intent == "pest_risk":
        raw = de.get_pest_risk(district)
        return {"text": _fmt_pest_risk(raw), "intent": intent, "district": district, "data": raw}

    if intent == "district_overview":
        raw = de.get_district_overview(district)
        return {"text": _fmt_overview(raw), "intent": intent, "district": district, "data": raw}

    if intent == "soil_info":
        return {
            "text": "🖼️ **Soil Classification** — Please use the 📎 image button below to upload a soil photo. I'll analyze and identify the soil type, then give crop recommendations based on it!",
            "intent": "soil_info",
            "district": district,
        }

    # ── General fallback ────────────────────────────────────────────────────────
    fallback_hints = []
    if district:
        fallback_hints.append(f"- *\"Best crops for {district}?\"*")
        fallback_hints.append(f"- *\"Rainfall in {district}?\"*")
        fallback_hints.append(f"- *\"Overview of {district}\"*")
    else:
        fallback_hints = [
            "- *\"Best crops for Madurai with red soil?\"*",
            "- *\"Rainfall in Salem?\"*",
            "- *\"Pest risk in Coimbatore?\"*",
            "- *\"Wages in Thanjavur?\"*",
        ]
    hints = "\n".join(fallback_hints)
    return {
        "text": f"🤖 I'm a Smart Farming assistant focused on **Tamil Nadu agriculture**. Try asking:\n{hints}\n\nOr type **'help'** for the full capability list.",
        "intent": "general",
        "district": district,
    }
