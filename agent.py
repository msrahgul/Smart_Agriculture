"""
agent.py – Smart Farming AI Agent v3
Gemini-first intelligent advisor: AI understands every query, selects tools,
and reasons like an expert agricultural consultant.
"""
import re
from difflib import get_close_matches
import data_engine as de
import nlg

# ── Entity keywords (used only for memory extraction, not query routing) ─────
SOIL_KEYWORDS = {
    "alluvial soil": ["alluvial", "alluvium", "river soil"],
    "black soil":    ["black", "regur", "black cotton"],
    "clay soil":     ["clay", "clayey"],
    "red soil":      ["red", "laterite", "red loam"],
}

SEASON_KEYWORDS = {
    "Kharif":     ["kharif", "june", "july", "august", "southwest monsoon", "sw monsoon", "summer crop"],
    "Rabi":       ["rabi", "october", "november", "december", "northeast monsoon", "ne monsoon", "winter crop"],
    "Whole Year": ["whole year", "annual", "year round", "perennial"],
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
    r"what can you (do|help)",
    r"how are you", r"what are you",
    r"^start$", r"^help$",
]

WELCOME_TEXT = """👋 **Vanakkam! I'm your Smart Farming AI Expert for Tamil Nadu.**

I'm powered by 20 years of district-level agricultural data and Gemini AI intelligence. I understand your questions in plain language — no rigid templates.

**What I can do:**

🌾 **Crop Recommendations** — *"Best crops for Coimbatore with red soil?"*
📊 **Suitability Scoring** — *"How suitable is rice in Thanjavur? Give me a score."*
🌧️ **Rainfall Analysis** — *"How much rainfall does Salem get?"*
💰 **Cost Estimation** — *"What's the cost to grow groundnut in Madurai?"*
💧 **Irrigation & Water** — *"Water availability in Thanjavur"*
📈 **Yield Trends** — *"How has rice yield changed in Cuddalore?"*
🐛 **Pest Risk** — *"What pests affect cotton in Coimbatore?"*
🔬 **What-If Simulation** — *"If irrigation improved in Erode, how does it help rice?"*
🧠 **Multi-Criteria Search** — *"Best crop with low water and high profit in Salem red soil"*
🤖 **ML Predictions** — *"Predict yield of rice in Thanjavur"*
🏔️ **Soil Classification** — Upload a soil photo using the 📎 button

Just ask naturally — I'll figure it out! 🇮🇳
"""


# ════════════════════════════════════════════════════════════
# ENTITY EXTRACTION (for session memory only)
# ════════════════════════════════════════════════════════════
def _extract_district(query: str) -> str | None:
    if not de.ALL_DISTRICTS:
        return None
    ql = query.lower()
    matches = [(d, len(d)) for d in de.ALL_DISTRICTS if d.lower() in ql]
    if matches:
        return max(matches, key=lambda x: x[1])[0]
    words = re.findall(r"[a-zA-Z]+", query)
    for word in words:
        if len(word) < 4:
            continue
        r = de.fuzzy_district(word)
        if r:
            return r
    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i+1]}"
        r = de.fuzzy_district(phrase)
        if r:
            return r
    return None


def _extract_soil(query: str) -> str | None:
    ql = query.lower()
    for soil, keywords in SOIL_KEYWORDS.items():
        if any(kw in ql for kw in keywords):
            return soil
    return None


def _extract_season(query: str) -> str | None:
    ql = query.lower()
    for season, keywords in SEASON_KEYWORDS.items():
        if any(kw in ql for kw in keywords):
            return season
    return None


def _extract_crop(query: str) -> str | None:
    ql = query.lower()
    for alias, canonical in CROP_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", ql):
            return canonical
    for crop in KNOWN_CROPS:
        if re.search(rf"\b{re.escape(crop)}\b", ql):
            return crop
    return None


def _extract_year(query: str) -> int | None:
    m = re.search(r"\b(19|20)\d{2}\b", query)
    return int(m.group()) if m else None


def _get_memory(history: list | None) -> dict:
    memory = {"district": None, "soil": None, "season": None, "crop": None}
    if not history:
        return memory
    for item in history:
        if item.get("role") == "system_memory" and isinstance(item.get("memory"), dict):
            saved = item["memory"]
            memory["district"] = saved.get("district") or memory["district"]
            memory["soil"]     = saved.get("soil")     or memory["soil"]
            memory["season"]   = saved.get("season")   or memory["season"]
            memory["crop"]     = saved.get("crop")     or memory["crop"]
    return memory


def _merge_memory(memory: dict, district=None, soil=None, season=None, crop=None) -> dict:
    updated = dict(memory or {})
    if district: updated["district"] = district
    if soil:     updated["soil"]     = soil
    if season:   updated["season"]   = season
    if crop:     updated["crop"]     = crop
    return updated


# ════════════════════════════════════════════════════════════
# GEMINI AGENTIC LOOP — PRIMARY INTELLIGENCE LAYER
# ════════════════════════════════════════════════════════════
def _run_agentic_loop(user_query: str, history: list, context: dict) -> str | None:
    """
    Gemini-first AI loop. ALL queries go here first.
    Gemini reads the query in natural language, selects the right tools (possibly multiple),
    executes them, then synthesizes an expert response with reasoning.
    """
    import os, json
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
        from google.generativeai import protos

        genai.configure(api_key=api_key)

        # ── Tool definitions ─────────────────────────────────────────────────
        tools = [{"function_declarations": [
            {
                "name": "get_top_crops",
                "description": (
                    "Get the top recommended crops for a district in Tamil Nadu. "
                    "Use for: 'best crop', 'what to grow', 'suitable crop', 'crop recommendation', 'profitable crop'. "
                    "Supports optional soil_type and season filters."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":  {"type": "string", "description": "Tamil Nadu district name"},
                        "soil_type": {"type": "string", "description": "Filter: red soil, black soil, alluvial soil, clay soil"},
                        "season":    {"type": "string", "description": "Filter: Kharif, Rabi, Whole Year"},
                    },
                    "required": ["district"]
                }
            },
            {
                "name": "get_rainfall_stats",
                "description": (
                    "Get rainfall statistics for a district: annual total, SW monsoon, NE monsoon, yearly trend. "
                    "Use for: 'rainfall', 'rain', 'precipitation', 'monsoon', 'how much rain', 'wet/dry season', 'drought'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district": {"type": "string"},
                        "year":     {"type": "integer", "description": "Specific year (optional)"},
                    },
                    "required": ["district"]
                }
            },
            {
                "name": "get_wage_info",
                "description": (
                    "Get agricultural labour wage rates for a district. "
                    "Use for: 'wage', 'salary', 'labour cost', 'worker pay', 'how much do workers earn'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"district": {"type": "string"}},
                    "required": ["district"]
                }
            },
            {
                "name": "get_irrigation_profile",
                "description": (
                    "Get irrigation sources, coverage, and groundwater data for a district. "
                    "Use for: 'irrigation', 'water source', 'groundwater', 'canal', 'tank', 'borewell', 'water availability'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"district": {"type": "string"}},
                    "required": ["district"]
                }
            },
            {
                "name": "get_yield_trend",
                "description": (
                    "Get year-by-year historical yield trend for a specific crop in a district. "
                    "Use for: 'yield trend', 'how has yield changed', 'productivity over years', 'historic yield of [crop]'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":  {"type": "string"},
                        "crop_name": {"type": "string", "description": "Crop name e.g. Rice, Groundnut"},
                    },
                    "required": ["district", "crop_name"]
                }
            },
            {
                "name": "get_pest_risk",
                "description": (
                    "Get pest and disease risk assessment for a district based on climate profile. "
                    "Use for: 'pest risk', 'disease risk', 'what pests', 'crop protection', 'fungal', 'borer', 'aphid'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"district": {"type": "string"}},
                    "required": ["district"]
                }
            },
            {
                "name": "get_district_overview",
                "description": (
                    "Get a comprehensive agricultural overview of a district: top crops, soil, seasons, area, irrigation. "
                    "Use for: 'tell me about [district]', 'overview', 'profile', 'summary of', 'agriculture in [district]', 'everything about'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"district": {"type": "string"}},
                    "required": ["district"]
                }
            },
            {
                "name": "compute_suitability_score",
                "description": (
                    "Compute a 0–10 suitability score for growing a specific crop in a district. "
                    "Use for: 'how suitable is [crop] in [district]', 'can I grow [crop] in [district]', 'is [district] good for [crop]', "
                    "'suitability score', 'rate the suitability', 'analyze growing conditions'. "
                    "Returns subscores for yield, rainfall, soil, irrigation, and historical presence."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":         {"type": "string"},
                        "crop_name":        {"type": "string"},
                        "soil_type":        {"type": "string", "description": "Optional soil type filter"},
                        "season":           {"type": "string", "description": "Optional season"},
                        "irrigation_boost": {"type": "boolean", "description": "Set true if user asks 'what if irrigation improved'"},
                    },
                    "required": ["district", "crop_name"]
                }
            },
            {
                "name": "compute_whatif_simulation",
                "description": (
                    "Simulate how suitability changes if irrigation or rainfall improved. "
                    "Use for: 'what if irrigation improved', 'if we had more rain', 'what if water availability increased', "
                    "'simulate irrigation boost', 'how would score change if...'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":           {"type": "string"},
                        "crop_name":          {"type": "string"},
                        "irrigation_boost":   {"type": "boolean", "description": "Whether to simulate irrigation improvement"},
                        "extra_rainfall_mm":  {"type": "number", "description": "Additional rainfall in mm to simulate (e.g. 200)"},
                        "soil_type":          {"type": "string"},
                        "season":             {"type": "string"},
                    },
                    "required": ["district", "crop_name"]
                }
            },
            {
                "name": "estimate_crop_cost",
                "description": (
                    "Estimate the full-season cultivation cost for a crop in a district (seeds, fertilizer, labour, irrigation, pesticide). "
                    "Use for: 'cost to grow', 'how much does it cost', 'budget for [crop]', 'investment for [crop]', "
                    "'fertilizer cost', 'labour cost', 'total cost of cultivation', 'expenditure for farming'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":    {"type": "string"},
                        "crop_name":   {"type": "string"},
                        "area_acres":  {"type": "number", "description": "Farm area in acres (default 1 acre)"},
                    },
                    "required": ["district", "crop_name"]
                }
            },
            {
                "name": "get_multi_criteria_crops",
                "description": (
                    "Find crops matching multiple criteria simultaneously: water need level AND profit potential AND soil AND season. "
                    "Use for: 'low water high profit', 'drought tolerant crops', 'best crop with minimum water', "
                    "'profitable crop for dry region', 'water-efficient crop', complex multi-condition crop queries."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":      {"type": "string"},
                        "soil_type":     {"type": "string"},
                        "season":        {"type": "string"},
                        "water_need":    {"type": "string", "description": "low / medium / high"},
                        "profit_target": {"type": "string", "description": "low / medium / high"},
                    },
                    "required": ["district"]
                }
            },
            {
                "name": "predict_crop_yield",
                "description": (
                    "Use the ML model to predict expected yield (tonnes/hectare). "
                    "Use for: 'predict yield', 'expected yield', 'how much will I get', 'yield forecast', 'ML yield prediction'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":  {"type": "string"},
                        "crop_name": {"type": "string"},
                        "season":    {"type": "string"},
                        "soil_type": {"type": "string"},
                    },
                    "required": ["district", "crop_name"]
                }
            },
            {
                "name": "predict_pest_risk",
                "description": (
                    "Use the ML model to predict pest risk level (High/Medium/Low). "
                    "Use for: 'predict pest risk', 'ML pest forecast', 'disease prediction', 'classify pest risk'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "district":  {"type": "string"},
                        "crop_name": {"type": "string"},
                        "season":    {"type": "string"},
                        "soil_type": {"type": "string"},
                    },
                    "required": ["district", "crop_name"]
                }
            },
        ]}]

        # ── Tool dispatcher ────────────────────────────────────────────────
        def _dispatch(name: str, args: dict) -> dict:
            d = de.fuzzy_district(args.get("district", "")) or args.get("district", "")
            if name == "get_top_crops":
                return de.get_top_crops(d, args.get("soil_type"), args.get("season"), top_n=7)
            if name == "get_rainfall_stats":
                return de.get_rainfall_stats(d, args.get("year"))
            if name == "get_wage_info":
                return de.get_wage_info(d)
            if name == "get_irrigation_profile":
                return de.get_irrigation_profile(d)
            if name == "get_yield_trend":
                return de.get_yield_trend(d, args.get("crop_name", ""))
            if name == "get_pest_risk":
                return de.get_pest_risk(d)
            if name == "get_district_overview":
                return de.get_district_overview(d)
            if name == "compute_suitability_score":
                return de.compute_suitability_score(
                    d, args.get("crop_name",""), args.get("soil_type"),
                    args.get("season"), bool(args.get("irrigation_boost", False))
                )
            if name == "compute_whatif_simulation":
                return de.compute_whatif_simulation(
                    d, args.get("crop_name",""), args.get("soil_type"),
                    args.get("season"), bool(args.get("irrigation_boost", False)),
                    float(args.get("extra_rainfall_mm", 0))
                )
            if name == "estimate_crop_cost":
                return de.estimate_crop_cost(d, args.get("crop_name",""), float(args.get("area_acres", 1.0)))
            if name == "get_multi_criteria_crops":
                return de.get_multi_criteria_crops(
                    d, args.get("soil_type"), args.get("season"),
                    args.get("water_need"), args.get("profit_target")
                )
            if name == "predict_crop_yield":
                return de.predict_crop_yield_for_district(d, args.get("crop_name",""), args.get("season"), args.get("soil_type"))
            if name == "predict_pest_risk":
                return de.predict_pest_risk_for_district(d, args.get("crop_name",""), args.get("season"), args.get("soil_type"))
            return {"error": f"Unknown function: {name}"}

        # ── Build conversation context ─────────────────────────────────────
        ctx_parts = [f"{k}: {v}" for k, v in context.items() if v]
        ctx_str = ", ".join(ctx_parts) if ctx_parts else "none yet"

        history_text = ""
        if history:
            recent = [h for h in history if h.get("role") in ("user", "bot")][-8:]
            for h in recent:
                role = "User" if h["role"] == "user" else "Assistant"
                history_text += f"{role}: {h.get('text','')[:400]}\n"

        # ── Master system prompt ───────────────────────────────────────────
        system_instruction = f"""You are an expert AI agricultural advisor for Tamil Nadu, India, with access to 20+ years of real district-level agricultural data through the tools provided.

## YOUR CORE IDENTITY
You think like a seasoned agricultural scientist and field consultant combined. You understand questions posed naturally, informally, or incompletely — and you still give precise, data-backed answers.

## CRITICAL RULES FOR QUERY UNDERSTANDING
1. UNDERSTAND INTENT, not keywords. A user asking "is Thanjavur good for paddy?" is asking for suitability analysis — call `compute_suitability_score`.
2. A user asking "what happens if I improve irrigation in Erode for cotton?" wants `compute_whatif_simulation`.
3. A user asking "how much does it cost to farm rice in Madurai" wants `estimate_crop_cost`.
4. A user asking "best crop with low water in Salem red soil" wants `get_multi_criteria_crops` with water_need=low.
5. For ANY district overview / "tell me about X" — call `get_district_overview`, THEN also `get_rainfall_stats` and `get_top_crops` to make the answer complete.
6. NEVER say "I don't understand" or reject a query. Extract whatever information you can and answer as well as possible.
7. If the user doesn't mention a district but says something like "for my area" or leaves it vague, ask naturally for the district.

## MULTI-TOOL BEHAVIOR
- For broad or complex questions, call MULTIPLE tools simultaneously in your first response.
- For "compare [district A] vs [district B]" — call all relevant tools for BOTH districts.
- For "complete analysis / full report" — call overview + crops + rainfall + irrigation + pest risk.
- For suitability questions, ALWAYS also call get_rainfall_stats to enrich the explanation.

## HOW TO PRESENT SUITABILITY SCORES
When you have a suitability score result, ALWAYS include this special marker in your response:
**SCORE:{score}/10:{label}**
(Example: **SCORE:7.5/10:Very Good**)
This marker allows the UI to render a visual score badge.

## RESPONSE FORMAT
- Use Markdown with headers, tables, and bullet points.
- Always explain WHY — not just what. Include reasoning behind recommendations.
- For suitability: explain each subscore (yield, rainfall, soil, irrigation).
- For costs: explain what drives the costs and where to save money.
- For what-if: show the before → after comparison clearly.
- Include practical farmer-friendly tips at the end.
- Speak confidently in first person, like an expert who knows this data.

## FOLLOW-UP SUGGESTIONS
At the END of every response, include this section:
---
**FOLLOWUP_CHIPS:[chip1]|[chip2]|[chip3]**
(3 contextual follow-up questions the user might ask next, relevant to what was just answered)

## CURRENT SESSION CONTEXT
Remembered from this conversation: {ctx_str}

## RECENT CONVERSATION
{history_text or "(start of conversation)"}"""

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system_instruction,
            tools=tools
        )

        # ── Agentic loop ──────────────────────────────────────────────────
        chat = model.start_chat()
        response = chat.send_message(user_query)

        for _ in range(6):  # max 6 rounds of tool calls
            parts = response.candidates[0].content.parts
            tool_calls = [p for p in parts if hasattr(p, "function_call") and p.function_call.name]

            if not tool_calls:
                text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
                return "\n\n".join(text_parts).strip() if text_parts else None

            function_responses = []
            for part in tool_calls:
                fc = part.function_call
                tool_name = fc.name
                tool_args = dict(fc.args)
                print(f"[Agent] Calling tool: {tool_name}({tool_args})")
                result = _dispatch(tool_name, tool_args)
                function_responses.append(
                    protos.Part(
                        function_response=protos.FunctionResponse(
                            name=tool_name,
                            response={"result": json.dumps(result, default=str)[:5000]}
                        )
                    )
                )

            response = chat.send_message(protos.Content(parts=function_responses, role="user"))

        parts = response.candidates[0].content.parts
        text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
        return "\n\n".join(text_parts).strip() if text_parts else None

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Agent] Agentic loop failed: {e}. Falling back to rule-based routing.")
        return None


# ════════════════════════════════════════════════════════════
# NLG FORMATTERS FOR NON-GEMINI FALLBACK
# ════════════════════════════════════════════════════════════
def _fmt_yield_prediction(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    pred   = data["predicted_yield"]
    crop   = data["crop_name"]
    dist   = data["district"]
    season = data.get("season", "Unknown")
    soil   = data.get("soil_type", "Unknown")
    if pred > 20:
        assessment = "an exceptionally high yield."
    elif pred > 8:
        assessment = "a strong commercial yield, well above Tamil Nadu's average."
    elif pred > 3:
        assessment = "a moderate yield, typical for this crop and district."
    else:
        assessment = "a modest yield — consider soil improvement and optimised irrigation."
    return (
        f"### 🌾 ML Yield Prediction — {crop} in {dist}\n\n"
        f"Based on the trained **Random Forest regression model**, the expected yield for **{crop}** in **{dist}** is:\n\n"
        f"## **{pred} tonnes per hectare**\n\n"
        f"That's {assessment}\n\n"
        f"| Detail | Value |\n|--------|-------|\n"
        f"| 🌍 District | {dist} |\n| 🌾 Crop | {crop} |\n"
        f"| 📅 Season | {season} |\n| 🏔️ Soil Type | {soil} |\n"
        f"| 📊 Predicted Yield | **{pred} t/ha** |\n\n"
        f"*This is a data-driven ML estimate. Actual yields vary with field conditions.*"
    )


def _fmt_pest_prediction(data: dict) -> str:
    if "error" in data:
        return f"❌ {data['error']}"
    risk   = data["pest_risk"]
    crop   = data["crop_name"]
    dist   = data["district"]
    season = data.get("season", "Unknown")
    soil   = data.get("soil_type", "Unknown")
    emoji  = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "🟡")
    advice = {
        "High":   "Immediate preventive action recommended. Apply targeted crop protection before symptoms appear.",
        "Medium": "Moderate pest pressure likely. Apply IPM practices proactively and scout twice weekly.",
        "Low":    "Low risk currently. Continue routine monitoring and preventive neem sprays.",
    }.get(risk, "Regular monitoring recommended.")
    return (
        f"### 🐛 ML Pest Risk — {crop} in {dist}\n\n"
        f"## {emoji} **{risk} Pest Risk**\n\n"
        f"{advice}\n\n"
        f"| Detail | Value |\n|--------|-------|\n"
        f"| 🌍 District | {dist} |\n| 🌾 Crop | {crop} |\n"
        f"| 📅 Season | {season} |\n| 🏔️ Soil | {soil} |\n"
        f"| 🐛 Risk Level | **{risk}** |"
    )


# ════════════════════════════════════════════════════════════
# FALLBACK RULE-BASED ROUTER (used only when Gemini is unavailable)
# ════════════════════════════════════════════════════════════
INTENT_PATTERNS = {
    "crop_recommend": [
        r"best crop", r"which crop", r"what crop", r"recommend crop",
        r"suggest crop", r"crop for", r"grow in", r"suitable crop",
        r"what should i (grow|plant|cultivate)", r"what to (grow|plant)",
        r"top crop", r"good crop", r"crops? to grow", r"what can i grow",
        r"ideal crop", r"profitable crop",
    ],
    "suitability": [
        r"suitab", r"can i grow", r"is .+ good for", r"how good", r"rate",
        r"score", r"how suitable", r"is .+ suitable", r"assess", r"evaluate",
        r"right condition", r"grow .+ in", r"plant .+ in",
    ],
    "rainfall_info": [
        r"rain(fall)?", r"precipitation", r"monsoon", r"how much rain",
        r"wet season", r"dry season", r"annual rain", r"mm of rain", r"rainy", r"drought",
    ],
    "wage_info": [
        r"wage", r"salary", r"pay", r"labour cost", r"labor",
        r"worker pay", r"daily wage", r"field labour", r"farm worker",
        r"how much.*earn", r"cost of labour",
    ],
    "irrigation_info": [
        r"irrigation", r"water source", r"canal", r"tank", r"bore.?well",
        r"tube.?well", r"open well", r"groundwater", r"water level",
        r"how is water", r"water supply", r"water availability",
    ],
    "yield_trend": [
        r"yield trend", r"production trend", r"crop yield", r"how much.*produce",
        r"yield.*(year|history|over)", r"productivity", r"output of",
        r"tonnes per", r"t/ha", r"harvest trend", r"yield history",
    ],
    "pest_risk": [
        r"pest", r"disease", r"insect", r"fungal", r"blight", r"borer",
        r"aphid", r"risk", r"crop disease", r"plant disease", r"infestation",
        r"spray", r"fungicide", r"pesticide", r"whitefly", r"thrip",
    ],
    "district_overview": [
        r"overview", r"profile", r"tell me about", r"about.*district",
        r"summary of", r"general info", r"information about",
        r"details of", r"describe", r"agriculture in", r"everything about",
        r"full report", r"give me info",
    ],
    "cost_estimate": [
        r"cost", r"expense", r"budget", r"investment", r"how much.*spend",
        r"fertilizer.*cost", r"labour.*cost", r"cultivation cost",
        r"how much.*farm", r"price.*grow", r"cost.*per acre",
    ],
    "whatif": [
        r"what if", r"if irrigation", r"if.*rain", r"if.*water",
        r"simulate", r"what would happen", r"suppose", r"assuming",
        r"hypothetically", r"if.*improve",
    ],
    "multi_criteria": [
        r"low water.*profit", r"water.*efficient.*profit", r"drought.*profit",
        r"(minimum|low) water.*(high|maximum) profit",
        r"best crop.*low water", r"best crop.*drought",
        r"water efficient crop", r"multiple criteria",
    ],
    "yield_predict": [
        r"predict yield", r"expected yield", r"forecast yield", r"estimate yield",
        r"yield prediction", r"yield estimate", r"predict.*yield",
    ],
    "pest_predict": [
        r"predict pest", r"pest.*predict", r"ml pest", r"classify pest",
        r"predict.*disease", r"predict.*risk",
    ],
    "soil_info": [
        r"soil type", r"what soil", r"identify soil", r"black soil",
        r"red soil", r"alluvial", r"clay soil", r"upload.*soil",
    ],
    "compare": [
        r"compare", r"vs\.?", r"versus", r"difference between",
        r"which district.*better", r"between .+ and .+",
    ],
    "greeting": [
        r"^(hi|hello|hey|howdy)[\s!.]*$",
        r"good (morning|afternoon|evening)",
        r"what can you (do|help)", r"how are you", r"what are you",
        r"^start$", r"^help$",
    ],
}


def _detect_intent(query: str) -> str:
    ql = query.lower().strip()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, ql))
        if score > 0:
            scores[intent] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def _missing_district_reply(intent: str) -> str:
    examples = {
        "crop_recommend": "Best crops for Coimbatore?",
        "rainfall_info":  "Rainfall in Salem?",
        "wage_info":      "Wages in Thanjavur?",
        "irrigation_info":"Irrigation sources in Madurai?",
        "yield_trend":    "Rice yield trend in Cuddalore?",
        "pest_risk":      "Pest risks in Dharmapuri?",
        "district_overview": "Overview of Erode district?",
        "suitability":    "How suitable is rice in Thanjavur?",
        "cost_estimate":  "Cost to grow groundnut in Madurai?",
        "whatif":         "What if irrigation improved in Erode for rice?",
    }
    example = examples.get(intent, "Tell me about Coimbatore?")
    sample_districts = ", ".join(de.ALL_DISTRICTS[:8]) + "..."
    return (
        f"I'd love to help with that! I just need a **district name** to pull the right data.\n\n"
        f"For example: *\"{example}\"*\n\n"
        f"I cover all **{len(de.ALL_DISTRICTS)} districts** of Tamil Nadu: {sample_districts}"
    )


def _fallback_router(message: str, district: str, soil: str, season: str, crop: str, memory: dict) -> dict:
    """Rule-based fallback when Gemini is unavailable."""
    intent = _detect_intent(message)
    new_memory = _merge_memory(
        memory,
        district=_extract_district(message),
        soil=_extract_soil(message),
        season=_extract_season(message),
        crop=_extract_crop(message),
    )

    district_required = {
        "crop_recommend", "rainfall_info", "wage_info", "irrigation_info",
        "yield_trend", "pest_risk", "district_overview", "suitability",
        "cost_estimate", "whatif", "multi_criteria", "yield_predict", "pest_predict",
    }
    if intent in district_required and not district:
        return {"text": _missing_district_reply(intent), "intent": intent, "district": None, "memory": new_memory}

    if intent == "crop_recommend":
        crop_data = de.get_top_crops(district, soil, season, top_n=7)
        rain_data = de.get_rainfall_stats(district)
        irr_data  = de.get_irrigation_profile(district)
        return {"text": nlg.describe_crops(district, crop_data, rain_data, irr_data), "intent": intent, "district": district, "memory": new_memory}

    if intent == "suitability":
        if not crop:
            return {"text": f"Which crop would you like me to score for **{district}**? For example: *\"Suitability of rice in {district}\"*", "intent": intent, "district": district, "memory": new_memory}
        score_data = de.compute_suitability_score(district, crop, soil, season)
        return {"text": nlg.describe_suitability_score(district, crop, score_data), "intent": intent, "district": district, "memory": new_memory}

    if intent == "whatif":
        if not crop:
            return {"text": f"Which crop should I simulate for **{district}**? Try: *\"What if irrigation improved in {district} for rice?\"*", "intent": intent, "district": district, "memory": new_memory}
        irr_boost = bool(re.search(r"irrigat", message, re.I))
        rain_extra = 0.0
        m = re.search(r"(\d+)\s*mm", message)
        if m:
            rain_extra = float(m.group(1))
        whatif_data = de.compute_whatif_simulation(district, crop, soil, season, irr_boost, rain_extra)
        return {"text": nlg.describe_whatif(district, crop, whatif_data), "intent": intent, "district": district, "memory": new_memory}

    if intent == "cost_estimate":
        if not crop:
            return {"text": f"Which crop do you want cost estimates for in **{district}**? Try: *\"Cost to grow rice in {district}\"*", "intent": intent, "district": district, "memory": new_memory}
        cost_data = de.estimate_crop_cost(district, crop)
        return {"text": nlg.describe_cost_estimate(district, crop, cost_data), "intent": intent, "district": district, "memory": new_memory}

    if intent == "multi_criteria":
        water_need = "low" if re.search(r"low water|drought|dry|water.efficien", message, re.I) else None
        profit_t   = "high" if re.search(r"high profit|maximum profit|profitable", message, re.I) else None
        mc_data = de.get_multi_criteria_crops(district, soil, season, water_need, profit_t)
        return {"text": nlg.describe_crops(district, mc_data), "intent": intent, "district": district, "memory": new_memory}

    if intent == "rainfall_info":
        return {"text": nlg.describe_rainfall(district, de.get_rainfall_stats(district)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "wage_info":
        return {"text": nlg.describe_wages(district, de.get_wage_info(district)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "irrigation_info":
        return {"text": nlg.describe_irrigation(district, de.get_irrigation_profile(district)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "yield_trend":
        if not crop:
            crops_available = de.get_all_crops_for_district(district)
            sample = ", ".join(f"**{c}**" for c in crops_available[:6]) if crops_available else "various crops"
            return {"text": f"Which crop in **{district}**? Crops grown there include: {sample}...\n\nTry: *\"Rice yield trend in {district}\"*", "intent": intent, "district": district, "memory": new_memory}
        return {"text": nlg.describe_yield_trend(district, crop, de.get_yield_trend(district, crop)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "pest_risk":
        return {"text": nlg.describe_pest_risk(district, de.get_pest_risk(district)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "district_overview":
        return {"text": nlg.describe_overview(district, de.get_district_overview(district), de.get_rainfall_stats(district)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "yield_predict":
        if not district or not crop:
            return {"text": "To predict yield, I need both a **district** and a **crop**. Try: *\"Predict yield of rice in Thanjavur\"*", "intent": intent, "district": district, "memory": new_memory}
        return {"text": _fmt_yield_prediction(de.predict_crop_yield_for_district(district, crop, season, soil)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "pest_predict":
        if not district or not crop:
            return {"text": "I need a **district** and **crop** to predict pest risk. Try: *\"Predict pest risk for cotton in Coimbatore\"*", "intent": intent, "district": district, "memory": new_memory}
        return {"text": _fmt_pest_prediction(de.predict_pest_risk_for_district(district, crop, season, soil)), "intent": intent, "district": district, "memory": new_memory}

    if intent == "soil_info":
        district_hint = f" for **{district}**" if district else ""
        return {"text": f"📸 Use the image button below to upload a soil photo. I'll identify the soil type{district_hint} and recommend crops!", "intent": intent, "district": district, "memory": new_memory}

    hints = [
        '- *"Best crops for Madurai with red soil?"*',
        '- *"Suitability of rice in Thanjavur?"*',
        '- *"Cost to grow groundnut in Coimbatore?"*',
        '- *"What if irrigation improved in Erode for cotton?"*',
    ]
    if district:
        hints.insert(0, f'- *"Best crops for {district}?"*')
    return {
        "text": "🤖 I'm best at answering agricultural questions about Tamil Nadu.\n\nTry:\n\n" + "\n".join(hints) + "\n\nOr type **help** to see all capabilities.",
        "intent": "general", "district": district, "memory": new_memory,
    }


# ════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════
def process_query(message: str, history: list = None) -> dict:
    message = message.strip()
    blank_mem = {"district": None, "soil": None, "season": None, "crop": None}
    if not message:
        return {"text": WELCOME_TEXT, "intent": "greeting", "district": None, "memory": blank_mem}

    memory = _get_memory(history)

    # Extract entities for session memory enrichment
    quick_district = _extract_district(message)
    quick_soil     = _extract_soil(message)
    quick_season   = _extract_season(message)
    quick_crop     = _extract_crop(message)

    district = quick_district or memory.get("district")
    soil     = quick_soil     or memory.get("soil")
    season   = quick_season   or memory.get("season")
    crop     = quick_crop     or memory.get("crop")

    new_memory = _merge_memory(memory, district=quick_district, soil=quick_soil,
                               season=quick_season, crop=quick_crop)

    ctx = {"district": district, "soil": soil, "season": season, "crop": crop}

    # Greeting shortcut (no Gemini call needed)
    ql = message.lower().strip()
    if any(re.search(p, ql) for p in GREETING_PATTERNS):
        return {"text": WELCOME_TEXT, "intent": "greeting", "district": district, "memory": new_memory}

    # ── PRIMARY: Gemini AI understands and routes everything ─────────────
    agentic_text = _run_agentic_loop(message, history or [], ctx)
    if agentic_text:
        return {"text": agentic_text, "intent": "agentic", "district": district, "memory": new_memory}

    # ── FALLBACK: Rule-based routing (only if Gemini is unavailable) ──────
    print("[Agent] Running rule-based fallback (Gemini unavailable).")
    return _fallback_router(message, district, soil, season, crop, memory)
