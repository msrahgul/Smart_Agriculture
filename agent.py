"""
agent.py – Smart Farming AI Agent (optimised ReAct loop)

Key features
────────────────────────────────────────────
1. DUAL-MODEL split
   • Router (0.5b-instruct)  – picks tool + args in one shot, JSON-forced output.
     Typical latency: 1–4 s on CPU.
   • Formatter (1.5b-instruct) – renders a structured Markdown answer from the
     raw tool observation.  Supports *streaming* so the user sees tokens immediately.

2. RULE-BASED FAST-PATHS (English queries only)
   • Greetings return immediately.
   • Keyword patterns map directly to tool names + argument extraction.
   • Tamil queries bypass fast-path entirely → go straight to the LLM router.

3. MULTILINGUAL LLM ROUTING
   • qwen2.5 understands Tamil natively.
   • The router system prompt includes a Tamil→English reference table so the
     model maps Tamil district/soil/season/crop terms to correct English arg values.
   • The router always outputs English values in the JSON args regardless of
     query language — tools expect English.

4. LANGUAGE-AWARE FORMATTER
   • When language='ta', the formatter is instructed to reply directly in Tamil.
   • Follow-up chips (FOLLOWUP_CHIPS) are also generated in Tamil.
   • No post-hoc translation step needed for streaming responses.

5. CONTEXT-ENRICHED FALLBACK
   • When no tool matches, inject today's date + known memory (district, crop,
     soil, season) so general questions ("what to plant this month?") are answered
     intelligently.

Public interface (shape unchanged — app.py works without modification):
    agent.process_query(message, history, language="en") -> dict
    agent.process_query_stream(message, history, language="en") -> (generator, memory, meta)
    agent._translate_same_template_to_tamil(text) -> str
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Generator

from llm_client import router_llm, prose_llm, extract_json_block
from tools import TOOL_MAP, tools_prompt_block
import data_engine as de

# ── constants ─────────────────────────────────────────────────────────────
MAX_STEPS = 2   # rarely need more than 1 tool; hard cap prevents runaway loops

# ── greeting fast-path ────────────────────────────────────────────────────
WELCOME_TEXT = (
    "👋 **Vanakkam! I'm your Smart Farming AI for Tamil Nadu.**\n\n"
    "Ask me about **crops**, **soil**, **pest risks**, **rainfall**, **cost/profit**, "
    "or **yield** for any district.\n\n"
    "**Example questions:**\n"
    "- Best crops for Madurai with red soil during Kharif?\n"
    "- What is the pest risk for rice in Thanjavur?\n"
    "- Estimate profit for sugarcane in Erode (2 acres).\n"
    "- How much rainfall does Coimbatore get?"
)

GREETING_RE = re.compile(
    r"^(hi|hello|hey|howdy|vanakkam|வணக்கம்|வணக்கம்|நமஸ்தே)[\\s!.]*$", re.I | re.UNICODE
)
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")   # Unicode block for Tamil script


def _is_tamil_text(text: str) -> bool:
    """Return True if the message contains Tamil script characters."""
    return bool(TAMIL_RE.search(text))


# ── known-district fast lookup ────────────────────────────────────────────
_DISTRICT_LOWER: dict[str, str] = {}
_district_map_ready = False


def _ensure_district_map() -> None:
    global _district_map_ready
    if _district_map_ready and _DISTRICT_LOWER:
        return
    if not de.ALL_DISTRICTS:
        try:
            de.load_data()
        except Exception:
            pass
    for d in (de.ALL_DISTRICTS or []):
        _DISTRICT_LOWER[d.lower()] = d
    _district_map_ready = bool(_DISTRICT_LOWER)


def _extract_district(text: str, fallback: str | None = None) -> str | None:
    """Scan text for any known Tamil Nadu district name (case-insensitive, English only)."""
    _ensure_district_map()
    lower = text.lower()
    for key, canonical in _DISTRICT_LOWER.items():
        if key in lower:
            return canonical
    return fallback


def _extract_crop(text: str, fallback: str | None = None) -> str | None:
    """Return the first English crop keyword found in text, or fallback."""
    crops = [
        "rice", "wheat", "maize", "cotton", "sugarcane", "turmeric", "groundnut",
        "banana", "millet", "jowar", "bajra", "sorghum", "tomato", "onion",
        "potato", "ragi", "sunflower", "coconut", "arecanut", "cashew",
        "ginger", "pepper", "cardamom", "coffee", "tea", "rubber",
    ]
    lower = text.lower()
    for crop in crops:
        if crop in lower:
            return crop
    return fallback


# ── intent classifiers (English keyword fast-path) ────────────────────────
_RAINFALL_KW = re.compile(r"\b(rainfall|rain(?:fall)?|precipitation|rain\s+data)\b", re.I)
_OVERVIEW_KW = re.compile(r"\b(overview|profile|agriculture(?:al)?\s+info|tell\s+me\s+about)\b", re.I)
_CROPS_KW    = re.compile(r"\b(crops?|cultivat|grow|farming|suitable\s+crop|what\s+to\s+grow)\b", re.I)
_FERT_KW     = re.compile(r"\b(fertilizer|fertiliser|manure|npk|nutrient|urea)\b", re.I)
_WAGE_KW     = re.compile(r"\b(wage|wages|labour|labor|worker|farm(?:\s+worker)?)\b", re.I)
_PEST_KW     = re.compile(r"\b(pest|disease|risk|blight|infestation)\b", re.I)
_YIELD_KW    = re.compile(r"\b(yield|production|output|harvest(?:ed)?\s+amount)\b", re.I)
_PROFIT_KW   = re.compile(r"\b(profit|cost|revenue|income|earning)\b", re.I)
_PLANTING_KW = re.compile(r"\b(plant(?:ing)?|sow(?:ing)?|season|when\s+to\s+(?:plant|grow|sow))\b", re.I)
_IRRIGATE_KW = re.compile(r"\b(irrigation|water\s+source|canal|borewell|well)\b", re.I)
_PRICE_KW    = re.compile(r"\b(price|rate|mandi|market\s+price|today'?s?\s+rate)\b", re.I)


# ── memory helpers ────────────────────────────────────────────────────────

def _get_memory(history: list | None) -> dict:
    memory = {"district": None, "soil": None, "season": None, "month": None, "crop": None}
    if not history:
        return memory
    for item in history:
        if item.get("role") == "system_memory" and isinstance(item.get("memory"), dict):
            for key in memory:
                memory[key] = item["memory"].get(key) or memory[key]
    return memory


def _merge_memory(memory: dict, **updates) -> dict:
    merged = dict(memory or {})
    for key, value in updates.items():
        if value:
            merged[key] = value
    return merged


def _format_memory(memory: dict) -> str:
    known = {k: v for k, v in memory.items() if v}
    return json.dumps(known) if known else "(none yet)"


# ── router system prompt ──────────────────────────────────────────────────
# The LLM router (qwen2.5) handles both English and Tamil natively.
# We provide a compact Tamil→English reference table inside the prompt
# so the model maps Tamil terms to the correct English arg values — no
# hardcoded Python translation logic needed.

_ROUTER_SYSTEM = """\
You are a tool-routing agent for a Tamil Nadu Smart Farming assistant.
The user may ask in English OR Tamil. You MUST understand both languages.
Output ONE JSON object on a single line: {{"tool": "<name>", "args": {{"<key>": "<value>", ...}}}}

IMPORTANT: Always output English values in args, even if the user asked in Tamil.
- District names must be in English (e.g. "Madurai", "Coimbatore", "Erode")
- Soil types must be in English: "red soil", "black soil", "alluvial soil", or "clay soil"
- Season must be one of: Kharif, Rabi, Summer, Winter, Whole Year
- Crop names must be in English (e.g. "rice", "sugarcane", "cotton", "groundnut")

Tamil reference (common terms → English arg values):
  Districts: மதுரை→Madurai, கோயம்புத்தூர்→Coimbatore, ஈரோடு→Erode,
             திருச்சி→Tiruchirapalli, சேலம்→Salem, தஞ்சாவூர்→Thanjavur,
             வேலூர்→Vellore, திருநெல்வேலி→Tirunelveli, தர்மபுரி→Dharmapuri,
             கரூர்→Karur, நாமக்கல்→Namakkal, விருதுநகர்→Virudhunagar,
             நாகப்பட்டினம்→Nagapattinam, கடலூர்→Cuddalore, புதுக்கோட்டை→Pudukkottai,
             திண்டுக்கல்→Dindigul, திருவண்ணாமலை→Tiruvannamalai,
             கன்னியாகுமரி→Kanniyakumari, ராணிப்பேட்டை→Ranipet, அரியலூர்→Ariyalur,
             பெரம்பலூர்→Perambalur, குடலூர்→Cuddalore
  Soil: சிவப்பு மண்→red soil, கரிசல் மண்→black soil, வண்டல் மண்→alluvial soil, களிமண்→clay soil
  Season: காரிஃப்→Kharif, ரபி→Rabi, கோடை→Summer, குளிர்காலம்→Winter,
          முழு ஆண்டு→Whole Year, மழைக்காலம்→Kharif
  Crops: நெல்→rice, கரும்பு→sugarcane, பருத்தி→cotton, கடலை→groundnut,
         வாழை→banana, மக்காச்சோளம்→maize, தக்காளி→tomato, வெங்காயம்→onion,
         மஞ்சள்→turmeric, ராகி→ragi, நிலக்கடலை→groundnut, சோளம்→sorghum

English examples:
  "best crops for Madurai with red soil during Kharif" → {{"tool": "get_top_crops", "args": {{"district": "Madurai", "soil_type": "red soil", "season": "Kharif"}}}}
  "rainfall in Coimbatore" → {{"tool": "get_rainfall_stats", "args": {{"district": "Coimbatore"}}}}
  "pest risk for rice in Thanjavur" → {{"tool": "predict_pest_risk_ml", "args": {{"district": "Thanjavur", "crop_name": "rice"}}}}
  "yield of sugarcane in Erode" → {{"tool": "predict_crop_yield_ml", "args": {{"district": "Erode", "crop_name": "sugarcane"}}}}
  "overview of Salem" → {{"tool": "get_district_overview", "args": {{"district": "Salem"}}}}
  "fertilizer for rice" → {{"tool": "get_fertilizer_recommendation", "args": {{"crop_name": "rice"}}}}
  "wage info for Madurai" → {{"tool": "get_wage_info", "args": {{"district": "Madurai"}}}}
  "irrigation profile of Erode" → {{"tool": "get_irrigation_profile", "args": {{"district": "Erode"}}}}
  "planting time for cotton" → {{"tool": "get_crop_planting_time", "args": {{"crop_name": "cotton"}}}}
  "profit for sugarcane in Coimbatore" → {{"tool": "estimate_crop_profit", "args": {{"district": "Coimbatore", "crop_name": "sugarcane"}}}}

Tamil examples:
  "மதுரையில் சிவப்பு மண்ணில் காரிஃப் பருவத்திற்கு சிறந்த பயிர்கள்?" → {{"tool": "get_top_crops", "args": {{"district": "Madurai", "soil_type": "red soil", "season": "Kharif"}}}}
  "கோயம்புத்தூரில் மழை அளவு என்ன?" → {{"tool": "get_rainfall_stats", "args": {{"district": "Coimbatore"}}}}
  "தஞ்சாவூரில் நெல்லுக்கு பூச்சி அபாயம் என்ன?" → {{"tool": "predict_pest_risk_ml", "args": {{"district": "Thanjavur", "crop_name": "rice"}}}}
  "ஈரோடு மாவட்ட விவரம் சொல்லுங்கள்" → {{"tool": "get_district_overview", "args": {{"district": "Erode"}}}}
  "நெல்லுக்கு உரம் என்ன?" → {{"tool": "get_fertilizer_recommendation", "args": {{"crop_name": "rice"}}}}
  "தர்மபுரியில் பூச்சி அபாயம் என்ன?" → {{"tool": "get_pest_risk_historical", "args": {{"district": "Dharmapuri"}}}}
  "சேலத்தில் கரும்பு விளைச்சல் எவ்வளவு?" → {{"tool": "predict_crop_yield_ml", "args": {{"district": "Salem", "crop_name": "sugarcane"}}}}
  "மதுரையில் தொழிலாளர் கூலி என்ன?" → {{"tool": "get_wage_info", "args": {{"district": "Madurai"}}}}
  "கோயம்புத்தூரில் நெல் பயிரிட சரியான நேரம்?" → {{"tool": "get_crop_planting_time", "args": {{"crop_name": "rice", "district": "Coimbatore"}}}}

Known context (USE THESE if the user message omits them — do NOT override explicit values):
{memory_block}

Available tools:
{tools_block}

Rules:
- Output ONLY the JSON object. No explanation, no markdown, no triple backticks.
- Extract district, crop, soil type, season from the message in ANY language.
- ALWAYS output English values in the args JSON.
- If known context has district/crop/soil/season not mentioned in the message, include it.
- If no tool fits, output: {{"tool": "none", "args": {{}}}}
"""


# ── formatter system prompt (language-aware) ──────────────────────────────

def _get_formatter_system(language: str = "en") -> str:
    """
    Return a language-specific formatter system prompt.
    When language is Tamil, the model replies directly in Tamil — no
    post-hoc translation needed, which also avoids the translation delay.
    """
    is_tamil = language.startswith("ta")

    if is_tamil:
        lang_instruction = (
            "Reply ENTIRELY in Tamil (தமிழ்). Use natural, conversational Tamil.\n"
            "Preserve Markdown formatting (bold **text**, bullet points •, headings ##).\n"
            "Keep numbers, units (₹, mm, t/ha, %), and proper nouns (district names, "
            "crop names in English) as-is.\n"
            "End with exactly this line (2-3 short follow-up questions in Tamil, max 6 words each):\n"
            "FOLLOWUP_CHIPS: <தமிழில் கேள்வி 1>|<தமிழில் கேள்வி 2>|<தமிழில் கேள்வி 3>"
        )
    else:
        lang_instruction = (
            "Reply in clear, helpful English.\n"
            "End with exactly this line (2-3 short suggested question chips, max 6 words each, e.g. 'Coimbatore rainfall?|Pest risk for rice?'):\n"
            "FOLLOWUP_CHIPS: <short suggestion 1>|<short suggestion 2>|<short suggestion 3>"
        )

    return f"""\
You are an expert agronomy assistant for Tamil Nadu farmers.
You will receive a user question and the EXACT JSON output of a data lookup tool.
Your job: turn the raw JSON data into a clear, helpful, well-formatted response.

{lang_instruction}

CRITICAL RULES:
- Use ONLY information from the tool result. Do NOT say "not found" or "unavailable" \
if the JSON contains data — present what is there.
- If the JSON has an "error" key, apologise briefly and suggest the user rephrase.
- Format numbers clearly. Use ₹ for rupees, t/ha for tonnes per hectare, mm for millimetres.
- Use bullet points or a short table when listing multiple items.
- Keep the response concise: 3-8 sentences or bullet points.
"""


# ── fallback prompt builder ───────────────────────────────────────────────

def _build_fallback_prompt(
    user_message: str,
    memory: dict,
    language: str = "en",
) -> list[dict]:
    """
    Build a context-enriched fallback prompt for general questions that
    don't match any data tool. Injects today's date + known session memory
    so the LLM can answer "what to plant this month?" sensibly.
    """
    today = date.today()
    month_name = today.strftime("%B")   # e.g. "July"

    context_parts = [f"Today: {today.isoformat()} — Month: {month_name}"]
    if memory.get("district"):
        context_parts.append(f"User district: {memory['district']}")
    if memory.get("crop"):
        context_parts.append(f"Current crop: {memory['crop']}")
    if memory.get("soil"):
        context_parts.append(f"Soil type: {memory['soil']}")
    if memory.get("season"):
        context_parts.append(f"Season: {memory['season']}")

    context_block = "\n".join(context_parts)
    if is_tamil:
        lang_note = (
            "Reply in natural, conversational Tamil (தமிழ்). "
            "Keep numbers and proper nouns (district, crop names) as-is.\n"
            "End with exactly this line (2-3 short follow-up questions in Tamil, max 6 words each):\n"
            "FOLLOWUP_CHIPS: <தமிழில் கேள்வி 1>|<தமிழில் கேள்வி 2>|<தமிழில் கேள்வி 3>"
        )
    else:
        lang_note = (
            "Reply in clear English.\n"
            "End with exactly this line (2-3 short suggested question chips, max 6 words each, e.g. 'Coimbatore rainfall?|Pest risk for rice?'):\n"
            "FOLLOWUP_CHIPS: <short suggestion 1>|<short suggestion 2>|<short suggestion 3>"
        )

    return [
        {"role": "system", "content": (
            f"You are a Tamil Nadu Smart Farming assistant. {lang_note}\n"
            "Answer helpfully using general agricultural knowledge combined with "
            "the current context below. If unsure, say so clearly. "
            "Keep the answer to 3-5 sentences.\n\n"
            f"Current context:\n{context_block}"
        )},
        {"role": "user", "content": user_message},
    ]


# ── router call ───────────────────────────────────────────────────────────

def _router_call(user_message: str, memory: dict) -> dict | None:
    """
    Single LLM call to the tiny router model.
    Returns parsed tool-call dict or None if routing failed.
    """
    system = _ROUTER_SYSTEM.format(
        memory_block=_format_memory(memory),
        tools_block=tools_prompt_block(),
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_message},
    ]
    try:
        raw = router_llm.chat(
            messages,
            temperature=0.0,
            num_predict=128,    # routing output is tiny — just a JSON blob
            format_json=True,   # Ollama enforces valid JSON
        )
        parsed = extract_json_block(raw)
        if not parsed or parsed.get("tool") == "none":
            return None
        return parsed
    except Exception:
        return None


def _generate_context_chips(memory: dict, language: str = "en") -> list[str]:
    district = memory.get("district")
    crop = memory.get("crop")
    is_tamil = language.startswith("ta")

    if is_tamil:
        if district and crop:
            return [
                f"{district}-இல் {crop}-க்கு உரம் என்ன?",
                f"{district}-இல் {crop}-க்கு பூச்சி அபாயம் என்ன?",
                f"{district}-இல் {crop} லாப மதிப்பீடு?",
            ]
        elif district:
            return [
                f"{district}-இல் சிறந்த பயிர்கள்?",
                f"{district} மழை அளவு என்ன?",
                f"{district} மாவட்ட விவரம்?",
            ]
        elif crop:
            return [
                f"{crop}-க்கு உரம் என்ன?",
                f"{crop}-க்கு பூச்சி அபாயம் என்ன?",
                f"{crop} பயிரிட சரியான நேரம்?",
            ]
        else:
            return [
                "மதுரையில் காரிஃப் சிறந்த பயிர்கள்?",
                "கோயம்புத்தூர் மழை அளவு என்ன?",
                "தஞ்சாவூரில் நெல்லுக்கு பூச்சி அபாயம்?",
            ]
    else:
        if district and crop:
            return [
                f"Fertilizer recommendation for {crop} in {district}?",
                f"Pest risk for {crop} in {district}?",
                f"Estimate profit for {crop} in {district}?",
            ]
        elif district:
            return [
                f"Best crops for {district}?",
                f"{district} rainfall stats?",
                f"{district} district overview?",
            ]
        elif crop:
            return [
                f"Fertilizer recommendation for {crop}?",
                f"Pest risk for {crop}?",
                f"Planting time for {crop}?",
            ]
        else:
            return [
                "Best crops for Madurai during Kharif?",
                "Coimbatore rainfall stats?",
                "Pest risk for rice in Thanjavur?",
            ]


# ── formatter ─────────────────────────────────────────────────────────────

def _format_answer_no_llm(user_message: str, observation: dict, memory: dict, language: str = "en") -> str:
    """
    Rule-based formatter used when Ollama is unavailable.
    Produces a clean Markdown answer directly from the tool's JSON output.
    """
    if not observation or "error" in observation:
        err = (observation or {}).get("error", "No data available.")
        return f"⚠️ {err}"

    lines: list[str] = []
    district = observation.get("district") or memory.get("district") or ""

    # --- Top-crops ---
    if "crops" in observation:
        crops = observation["crops"]
        h = f"### 🌾 Best Crops — {district}" if district else "### 🌾 Recommended Crops"
        lines.append(h)
        for c in (crops or [])[:8]:
            name  = c.get("crop_name", "").title()
            score = c.get("score")
            extra = f" (score: {score:.1f})" if score is not None else ""
            lines.append(f"- **{name}**{extra}")

    # --- Rainfall ---
    elif "avg_annual_mm" in observation:
        mm   = observation.get("avg_annual_mm", "—")
        dist = observation.get("district", district)
        lines.append(f"### 🌧 Rainfall — {dist}")
        lines.append(f"- **Average annual rainfall:** {mm} mm")
        if observation.get("rainy_months"):
            lines.append(f"- **Rainy months:** {', '.join(observation['rainy_months'])}")
        if observation.get("drought_prone"):
            lines.append(f"- **Drought prone:** {'Yes' if observation['drought_prone'] else 'No'}")

    # --- Pest risk ---
    elif "pest_risk" in observation:
        level = observation.get("pest_risk", "—")
        crop  = observation.get("crop", "").title()
        emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(level, "⚪")
        lines.append(f"### 🐛 Pest Risk — {crop} in {district}")
        lines.append(f"- **Risk level:** {emoji} {level}")
        if observation.get("recommendation"):
            lines.append(f"- **Recommendation:** {observation['recommendation']}")

    # --- Yield prediction ---
    elif "predicted_yield_t_ha" in observation:
        y    = observation.get("predicted_yield_t_ha", "—")
        crop = observation.get("crop", "").title()
        lines.append(f"### 📊 Yield Estimate — {crop} in {district}")
        lines.append(f"- **Predicted yield:** {y} t/ha")

    # --- Fertilizer ---
    elif "npk" in observation or "fertilizer" in observation or "recommended_fertilizer" in observation:
        crop = observation.get("crop", "").title()
        lines.append(f"### 🧪 Fertilizer Recommendation — {crop}")
        for key in ("npk", "recommended_fertilizer", "urea", "dap", "mop", "organic"):
            if observation.get(key):
                lines.append(f"- **{key.upper().replace('_',' ')}:** {observation[key]}")

    # --- District overview ---
    elif "area_ha" in observation or "agro_zone" in observation:
        lines.append(f"### 🗺 District Overview — {district}")
        for key, label in [("agro_zone", "Agro-climatic zone"), ("area_ha", "Agricultural area (ha)"),
                           ("main_crops", "Main crops"), ("avg_annual_rainfall_mm", "Average rainfall (mm)")]:
            if observation.get(key):
                lines.append(f"- **{label}:** {observation[key]}")

    # --- Wage info ---
    elif "daily_wage_inr" in observation or "wage" in observation.get("district", ""):
        lines.append(f"### 💵 Labour Wages — {district}")
        for key, label in [("daily_wage_inr", "Daily wage (₹)"), ("skilled_wage_inr", "Skilled wage (₹)"),
                           ("unskilled_wage_inr", "Unskilled wage (₹)")]:
            if observation.get(key):
                lines.append(f"- **{label}:** {observation[key]}")

    # --- Profit estimate ---
    elif "profit_per_acre" in observation or "cost_per_acre" in observation:
        crop = observation.get("crop", "").title()
        lines.append(f"### 💰 Profit Estimate — {crop} in {district}")
        for key, label in [("revenue_per_acre", "Revenue/acre (₹)"), ("cost_per_acre", "Cost/acre (₹)"),
                           ("profit_per_acre", "Profit/acre (₹)"), ("roi_pct", "ROI (%)")]:
            if observation.get(key) is not None:
                lines.append(f"- **{label}:** {observation[key]}")

    # --- Irrigation ---
    elif "irrigation_sources" in observation or "canal" in str(observation):
        lines.append(f"### 💧 Irrigation — {district}")
        for k, v in observation.items():
            if k != "district" and v:
                lines.append(f"- **{k.replace('_',' ').title()}:** {v}")

    # --- Market Prices ---
    elif "records" in observation or ("commodity" in observation and "arrival_date" in observation):
        comm = (observation.get("commodity") or "Commodity").title()
        arr_date = observation.get("arrival_date") or "today"
        dist_str = f" in {district}" if district else ""
        lines.append(f"### 📊 Market Prices — **{comm}** ({arr_date}){dist_str}")
        recs = observation.get("records") or [observation]
        for r in recs[:6]:
            mkt = r.get("market") or r.get("district") or "Mandi"
            min_p = r.get("min_price", "—")
            mod_p = r.get("modal_price", "—")
            max_p = r.get("max_price", "—")
            var = r.get("variety", "")
            var_str = f" ({var})" if var and var != "Local" else ""
            min_str = f"{min_p:,}" if isinstance(min_p, (int, float)) else str(min_p)
            mod_str = f"{mod_p:,}" if isinstance(mod_p, (int, float)) else str(mod_p)
            max_str = f"{max_p:,}" if isinstance(max_p, (int, float)) else str(max_p)
            lines.append(f"- **{mkt}**{var_str}: Min: ₹{min_str} | Modal: **₹{mod_str}** | Max: ₹{max_str} /quintal")

    # --- Generic fallback: print all top-level keys ---
    else:
        title = district or "Result"
        lines.append(f"### ℹ️ {title}")
        for k, v in observation.items():
            if k != "district" and v not in (None, "", [], {}):
                lines.append(f"- **{k.replace('_',' ').title()}:** {v}")

    if not lines:
        return "I found some data but could not format it right now. Please try again."

    chips = _generate_context_chips(memory, language)
    lines.append(f"\n\nFOLLOWUP_CHIPS: {'|'.join(chips)}")
    return "\n".join(lines)


def _format_answer_stream(
    user_message: str,
    observation: dict,
    memory: dict,
    language: str = "en",
) -> Generator[str, None, None]:
    """Generator: streams the formatted Markdown answer from the prose model.
    Falls back to rule-based formatting when Ollama is unavailable."""
    obs_text = json.dumps(observation, default=str, ensure_ascii=False)
    messages = [
        {"role": "system", "content": _get_formatter_system(language)},
        {"role": "user",   "content": (
            f"User question: {user_message}\n\n"
            f"Tool result (JSON):\n{obs_text}"
        )},
    ]
    seen_chips = False
    full_text_acc = []
    try:
        for token in prose_llm.chat_stream(messages, temperature=0.3, num_predict=512):
            full_text_acc.append(token)
            if "FOLLOWUP_CHIPS:" in "".join(full_text_acc):
                seen_chips = True
            yield token
    except RuntimeError:
        # Ollama offline — yield rule-based answer instead
        yield _format_answer_no_llm(user_message, observation, memory, language)
        return

    if not seen_chips:
        chips = _generate_context_chips(memory, language)
        yield f"\n\nFOLLOWUP_CHIPS: {'|'.join(chips)}"


def _format_answer_blocking(
    user_message: str,
    observation: dict,
    memory: dict,
    language: str = "en",
) -> str:
    """Blocking version — collects the streamed answer into one string."""
    return "".join(_format_answer_stream(user_message, observation, memory, language))


# ── fast-path dispatcher (English-only keyword matching) ─────────────────

def _try_fast_path(message: str, memory: dict) -> tuple[str, dict] | None:
    """
    Classify intent using English keyword matching.
    Returns (tool_name, args) or None.
    NOTE: Only called for English messages — Tamil bypasses this entirely.
    """
    mem_district = memory.get("district")
    mem_crop     = memory.get("crop")
    district     = _extract_district(message, mem_district)
    crop         = _extract_crop(message, mem_crop)

    if _RAINFALL_KW.search(message):
        if district:
            return "get_rainfall_stats", {"district": district}

    if _OVERVIEW_KW.search(message):
        if district:
            return "get_district_overview", {"district": district}

    if _WAGE_KW.search(message):
        if district:
            return "get_wage_info", {"district": district}

    if _IRRIGATE_KW.search(message):
        if district:
            return "get_irrigation_profile", {"district": district}

    if _FERT_KW.search(message) and crop:
        return "get_fertilizer_recommendation", {
            "crop_name": crop,
            "district":  district,
        }

    if _PLANTING_KW.search(message) and crop:
        return "get_crop_planting_time", {
            "crop_name": crop,
            "district":  district,
        }

    if _PEST_KW.search(message):
        if district and crop:
            return "predict_pest_risk_ml", {"district": district, "crop_name": crop}
        if district:
            return "get_pest_risk_historical", {"district": district}

    if _YIELD_KW.search(message):
        if district and crop:
            return "predict_crop_yield_ml", {"district": district, "crop_name": crop}
        if district:
            return "get_district_overview", {"district": district}

    if _PROFIT_KW.search(message) and district and crop:
        return "estimate_crop_profit", {"district": district, "crop_name": crop}

    if _CROPS_KW.search(message) and district:
        return "get_top_crops", {"district": district}

    if _PRICE_KW.search(message):
        # Extract commodity or fallback to first word that looks like a commodity
        target_crop = crop
        if not target_crop:
            # find candidate crop in text
            words = [w.strip(",.?!") for w in message.split()]
            for w in words:
                if w.lower() not in ("price", "of", "in", "today", "todays", "rate", "the", "for", "mandi", "what", "is"):
                    target_crop = w
                    break
        return "get_market_price", {
            "crop_name": target_crop or "onion",
            "district":  district,
        }

    return None


# ── core react loop ───────────────────────────────────────────────────────

KEY_MAP = {
    "crop_name": "crop",
    "crop": "crop",
    "soil_type": "soil",
    "soil": "soil",
    "district": "district",
    "season": "season",
    "month": "month",
}

def _run_agent(
    user_message: str,
    memory: dict,
    stream: bool = False,
    language: str = "en",
) -> tuple[str | Generator, dict]:
    """
    Returns (answer, entities_seen).
    If stream=True, answer is a generator of text tokens.
    """
    entities_seen: dict = {}

    def _record_args(args_dict: dict):
        if not args_dict or not isinstance(args_dict, dict):
            return
        for k, v in args_dict.items():
            if not v or not isinstance(v, str):
                continue
            mapped = KEY_MAP.get(k, k)
            if mapped in ("district", "crop", "soil", "season", "month"):
                entities_seen[mapped] = v

    # Initial text extraction from message
    d_direct = _extract_district(user_message)
    if d_direct:
        entities_seen["district"] = d_direct
    c_direct = _extract_crop(user_message)
    if c_direct:
        entities_seen["crop"] = c_direct

    # ── Step 1: Fast-path — English-only keyword routing ─────────────────
    if not _is_tamil_text(user_message):
        fast = _try_fast_path(user_message, memory)
        if fast:
            tool_name, args = fast
            if tool_name in TOOL_MAP:
                _record_args(args)
                observation = TOOL_MAP[tool_name].run(**args)
                if stream:
                    return _format_answer_stream(user_message, observation, memory, language), entities_seen
                else:
                    return _format_answer_blocking(user_message, observation, memory, language), entities_seen

    # ── Step 2: LLM router — handles English fallthrough + all Tamil ─────
    observation = None
    for _step in range(MAX_STEPS):
        tool_call = _router_call(user_message, memory)
        if not tool_call:
            break

        args = tool_call.get("args", {}) or {}
        _record_args(args)

        tool_name = tool_call.get("tool", "")
        if tool_name not in TOOL_MAP:
            break

        observation = TOOL_MAP[tool_name].run(**args)
        break   # single tool call is almost always enough

    # ── Step 3: Format the tool observation ──────────────────────────────
    if observation is not None:
        if stream:
            return _format_answer_stream(user_message, observation, memory, language), entities_seen
        else:
            return _format_answer_blocking(user_message, observation, memory, language), entities_seen

    # ── Step 4: Fallback — no tool matched; answer from general knowledge ─
    fallback_prompt = _build_fallback_prompt(user_message, memory, language)

    def _fallback_stream_with_chips():
        seen_chips = False
        full_text_acc = []
        for token in prose_llm.chat_stream(fallback_prompt, temperature=0.4, num_predict=350):
            full_text_acc.append(token)
            if "FOLLOWUP_CHIPS:" in "".join(full_text_acc):
                seen_chips = True
            yield token
        if not seen_chips:
            merged = _merge_memory(memory, **entities_seen)
            chips = _generate_context_chips(merged, language)
            yield f"\n\nFOLLOWUP_CHIPS: {'|'.join(chips)}"

    if stream:
        def _fallback_stream_with_chips():
            seen_chips = False
            full_text_acc = []
            try:
                for token in prose_llm.chat_stream(fallback_prompt, temperature=0.4, num_predict=350):
                    full_text_acc.append(token)
                    if "FOLLOWUP_CHIPS:" in "".join(full_text_acc):
                        seen_chips = True
                    yield token
            except RuntimeError:
                # Ollama offline — yield a helpful rule-based fallback
                chips = _generate_context_chips(_merge_memory(memory, **entities_seen), language)
                yield (
                    "I couldn't reach the language model right now, but I'm still here to help!\n\n"
                    "Try asking something specific like:\n"
                    "- *Best crops for Madurai?*\n"
                    "- *Rainfall stats for Coimbatore?*\n"
                    "- *Pest risk for rice in Thanjavur?*\n\n"
                    f"FOLLOWUP_CHIPS: {'|'.join(chips)}"
                )
                return
            if not seen_chips:
                merged = _merge_memory(memory, **entities_seen)
                chips = _generate_context_chips(merged, language)
                yield f"\n\nFOLLOWUP_CHIPS: {'|'.join(chips)}"
        return _fallback_stream_with_chips(), entities_seen
    else:
        try:
            return prose_llm.chat(fallback_prompt, temperature=0.4, num_predict=350), entities_seen
        except RuntimeError:
            chips = _generate_context_chips(_merge_memory(memory, **entities_seen), language)
            return (
                "The language model is offline, but you can still ask me about specific data: "
                "crop recommendations, rainfall, pest risk, yield, fertilizer, or wages for any Tamil Nadu district."
                f"\n\nFOLLOWUP_CHIPS: {'|'.join(chips)}"
            ), entities_seen


# ── public interface ──────────────────────────────────────────────────────

def process_query(
    message: str,
    history: list | None = None,
    language: str | None = None,
) -> dict:
    """Blocking interface (kept for /chat backward compatibility)."""
    message  = (message or "").strip()
    memory   = _get_memory(history)
    language = (language or "en").strip().lower()

    if not message or GREETING_RE.match(message):
        return {
            "text":     WELCOME_TEXT,
            "intent":   "greeting",
            "district": memory.get("district"),
            "memory":   memory,
        }

    try:
        answer, entities = _run_agent(message, memory, stream=False, language=language)
    except RuntimeError as e:
        return {
            "text":     f"⚠️ I couldn't reach the local model. {e}",
            "intent":   "error",
            "district": memory.get("district"),
            "memory":   memory,
        }

    new_memory = _merge_memory(memory, **entities)
    fallback_msg = (
        "பதில் கிடைக்கவில்லை. கேள்வியை திரும்பவும் கேட்கவும்."
        if language.startswith("ta") else
        "I wasn't able to find specific information. Please try rephrasing."
    )
    return {
        "text":     answer or fallback_msg,
        "intent":   "agent",
        "district": new_memory.get("district"),
        "memory":   new_memory,
    }


def process_query_stream(
    message: str,
    history: list | None = None,
    language: str | None = None,
) -> tuple[Generator, dict, dict]:
    """
    Streaming interface for the /chat_stream SSE endpoint.
    Returns (token_generator, new_memory, meta).
    The formatter generates directly in the target language — no post-translation needed.
    """
    message  = (message or "").strip()
    memory   = _get_memory(history)
    language = (language or "en").strip().lower()

    if not message or GREETING_RE.match(message):
        def _static():
            yield WELCOME_TEXT
        return _static(), memory, {"intent": "greeting", "district": memory.get("district")}

    try:
        gen, entities = _run_agent(message, memory, stream=True, language=language)
    except RuntimeError as e:
        def _err():
            yield f"⚠️ Could not reach the local model. {e}"
        return _err(), memory, {"intent": "error", "district": memory.get("district")}

    new_memory = _merge_memory(memory, **entities)
    return gen, new_memory, {"intent": "agent", "district": new_memory.get("district")}


def _translate_same_template_to_tamil(text: str) -> str:
    """
    Translate an already-composed English answer to Tamil using the prose model.
    Kept as a standalone helper — app.py calls this for simulation / soil result
    templates which are pre-built in English.
    Note: In streaming chat mode, the formatter now generates Tamil directly,
    so this function is only needed for the blocking template endpoints.
    """
    messages = [
        {"role": "system", "content": (
            "Translate the following farming-assistant message into natural, "
            "conversational Tamil. Preserve any Markdown formatting (bold, "
            "headings, bullet points) and preserve numbers/units exactly. "
            "Output only the translated text, nothing else."
        )},
        {"role": "user", "content": text},
    ]
    try:
        return prose_llm.chat(messages, temperature=0.0, num_predict=600).strip()
    except RuntimeError:
        return text   # fall back to English if Ollama is unreachable
