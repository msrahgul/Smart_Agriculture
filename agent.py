
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

TAMIL_DISTRICT_ALIASES = {
    "அரியலூர்": "Ariyalur", "செங்கல்பட்டு": "Chengalpattu", "சென்னை": "Chennai",
    "கோயம்புத்தூர்": "Coimbatore", "கோயம்புத்தூரில்": "Coimbatore",
    "கோவை": "Coimbatore", "கோவையில்": "Coimbatore", "கடலூர்": "Cuddalore",
    "தர்மபுரி": "Dharmapuri", "திண்டுக்கல்": "Dindigul", "ஈரோடு": "Erode",
    "கள்ளக்குறிச்சி": "Kallakurichi", "காஞ்சிபுரம்": "Kancheepuram",
    "கன்னியாகுமரி": "Kanniyakumari", "கரூர்": "Karur", "கிருஷ்ணகிரி": "Krishnagiri",
    "மதுரை": "Madurai", "மதுரையில்": "Madurai", "நாகப்பட்டினம்": "Nagapattinam", "நாமக்கல்": "Namakkal",
    "நீலகிரி": "The Nilgiris", "பெரம்பலூர்": "Perambalur", "புதுக்கோட்டை": "Pudukkottai",
    "ராமநாதபுரம்": "Ramanathapuram", "ராணிப்பேட்டை": "Ranipet", "சேலம்": "Salem",
    "சேலத்தில்": "Salem", "சிவகங்கை": "Sivagangai", "தென்காசி": "Tenkasi", "தஞ்சாவூர்": "Thanjavur",
    "தஞ்சாவூரில்": "Thanjavur",
    "தேனி": "Theni", "தூத்துக்குடி": "Thoothukudi", "திருச்சி": "Tiruchirapalli",
    "திருச்சிராப்பள்ளி": "Tiruchirapalli", "திருநெல்வேலி": "Tirunelveli",
    "திருப்பத்தூர்": "Tirupathur", "திருப்பூர்": "Tiruppur", "திருவள்ளூர்": "Tiruvallur",
    "திருவண்ணாமலை": "Tiruvannamalai", "திருவாரூர்": "Tiruvarur", "வேலூர்": "Vellore",
    "விழுப்புரம்": "Villupuram", "விருதுநகர்": "Virudhunagar",
}

TAMIL_CROP_ALIASES = {
    "நெல்": "rice", "அரிசி": "rice", "தேங்காய்": "coconut", "தென்னை": "coconut",
    "நிலக்கடலை": "groundnut", "கரும்பு": "sugarcane", "பருத்தி": "cotton",
    "வாழை": "banana", "மக்காச்சோளம்": "maize", "சோளம்": "jowar", "கம்பு": "bajra",
    "ராகி": "ragi", "மஞ்சள்": "turmeric", "வெங்காயம்": "onion", "மரவள்ளி": "tapioca",
    "மிளகாய்": "chilli", "சூரியகாந்தி": "sunflower", "தக்காளி": "tomato",
    "இஞ்சி": "ginger", "பூண்டு": "garlic", "மாம்பழம்": "mango",
}

TAMIL_QUERY_REPLACEMENTS = {
    "வணக்கம்": "hello", "ஹலோ": "hello", "நன்றி": "thanks",
    "சிறந்த மாவட்டம்": "best district", "எந்த மாவட்டம்": "which district",
    "சிறந்த பயிர்": "best crop", "பயிர் பரிந்துரை": "recommend crop",
    "வளர்க்கலாமா": "can i grow", "பயிரிடலாமா": "can i grow", "சாகுபடி செய்யலாமா": "can i grow",
    "வளர்க்க": "grow", "பயிரிட": "grow", "சாகுபடி": "cultivation",
    "மொத்த செலவு": "total cost", "செலவு": "cost", "லாபம்": "profit", "வருமானம்": "income",
    "மழை அளவு": "rainfall", "மழை": "rainfall", "பாசனம்": "irrigation",
    "பாசன விவரம்": "irrigation profile", "மாவட்ட விவரம்": "district overview", "விவரம் சொல்லுங்கள்": "overview",
    "உரம்": "fertilizer", "பூச்சி": "pest", "நோய்": "disease", "மகசூல்": "yield",
    "சிறந்த மாதம்": "best month", "சிறந்த பருவம்": "best season",
    "மழைக்காலம்": "rainy season", "கோடை": "summer", "குளிர்காலம்": "winter",
    "காரிஃப்": "kharif", "ரபி": "rabi", "சிவப்பு மண்": "red soil",
    "கருப்பு மண்": "black soil", "களிமண்": "clay soil", "வண்டல் மண்": "alluvial soil",
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
        dynamic = [str(c).strip().lower() for c in de.get_supported_crop_names(include_aliases=True)]
    except Exception:
        try:
            if not de.hist_df.empty and "crop_name" in de.hist_df.columns:
                dynamic = sorted({str(c).strip().lower() for c in de.hist_df["crop_name"].dropna().unique().tolist()})
        except Exception:
            dynamic = []
    return sorted(set(dynamic + KNOWN_CROPS + list(CROP_ALIASES.keys())))


def _is_tamil_text(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))


def _normalize_tamil_query(message: str) -> str:
    normalized = message
    additions = []
    for tamil, english in TAMIL_QUERY_REPLACEMENTS.items():
        normalized = normalized.replace(tamil, english)
    for tamil, english in TAMIL_DISTRICT_ALIASES.items():
        variants = [tamil, f"{tamil}ில்", f"{tamil}ல்", f"{tamil}யில்"]
        if any(v in normalized for v in variants):
            for variant in sorted(variants, key=len, reverse=True):
                normalized = normalized.replace(variant, english)
            additions.append(english)
    for tamil, english in TAMIL_CROP_ALIASES.items():
        variants = [tamil, f"{tamil}ை", f"{tamil}ில்"]
        if any(v in normalized for v in variants):
            for variant in sorted(variants, key=len, reverse=True):
                normalized = normalized.replace(variant, english)
            additions.append(english)
    if additions:
        normalized = f"{normalized} {' '.join(additions)}"
    return normalized


def _ta(value: str | None) -> str:
    names = {
        "rice": "நெல்", "paddy": "நெல்", "coconut": "தென்னை", "groundnut": "நிலக்கடலை",
        "sugarcane": "கரும்பு", "cotton": "பருத்தி", "banana": "வாழை", "maize": "மக்காச்சோளம்",
        "cotton(lint)": "பருத்தி", "jowar": "சோளம்", "bajra": "கம்பு", "ragi": "ராகி",
        "mango": "மாம்பழம்", "onion": "வெங்காயம்", "turmeric": "மஞ்சள்", "chilli": "மிளகாய்",
        "tapioca": "மரவள்ளி", "ginger": "இஞ்சி", "sweet potato": "சர்க்கரைவள்ளிக் கிழங்கு", "guar seed": "கொத்தவரை விதை",
        "coimbatore": "கோயம்புத்தூர்", "madurai": "மதுரை", "thanjavur": "தஞ்சாவூர்", "cuddalore": "கடலூர்",
        "erode": "ஈரோடு", "salem": "சேலம்", "dharmapuri": "தர்மபுரி", "tiruchirapalli": "திருச்சிராப்பள்ளி",
        "red soil": "சிவப்பு மண்", "black soil": "கருப்பு மண்", "clay soil": "களிமண்",
        "alluvial soil": "வண்டல் மண்", "Kharif": "காரிஃப் / மழைக்காலம்", "Rabi": "ரபி",
        "Summer": "கோடை", "Winter": "குளிர்காலம்", "Autumn": "இலையுதிர் காலம்",
        "Whole Year": "முழு ஆண்டு",
    }
    if not value:
        return ""
    return names.get(str(value), names.get(str(value).lower(), str(value).title()))


def _extract_first(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text or "", re.I | re.S)
    return m.group(1).strip() if m else default


def _ta_yield_label(row: dict) -> str:
    return f"{row.get('avg_yield_t_ha', row.get('avg_yield', 0))} டன்/ஹெக்டேர்"


def _format_tamil_crop_recommend(result: dict) -> str | None:
    data = (result.get("data") or {}).get("crop_data") or {}
    if "error" in data:
        return "இந்த மாவட்டம் அல்லது தேர்ந்தெடுத்த மண்/பருவத்திற்கு பொருந்தும் பயிர் தரவு கிடைக்கவில்லை. மாவட்டப் பெயர், மண் வகை, பருவம் ஆகியவற்றை சரிபார்த்து மீண்டும் முயற்சி செய்யவும்."

    district = data.get("district") or (result.get("memory") or {}).get("district") or result.get("district") or ""
    district_ta = _ta(district)
    crops = data.get("crops") or []
    if not crops:
        return f"**{district_ta}** மாவட்டத்திற்கு பொருந்தும் பயிர் பதிவுகள் கிடைக்கவில்லை. மண் வகை அல்லது பருவ வடிகட்டலை நீக்கி மீண்டும் முயற்சி செய்யவும்."

    seen = {}
    for row in crops:
        name = row.get("crop_name")
        if name and (name not in seen or row.get("rank_score", 0) > seen[name].get("rank_score", 0)):
            seen[name] = row
    top = list(seen.values())[:5]
    if not top:
        return None

    soil_filter = data.get("soil_filter", "all")
    season_filter = data.get("season_filter", "all")
    filter_parts = []
    if soil_filter != "all":
        filter_parts.append(f"மண்: **{_ta(soil_filter)}**")
    if season_filter != "all":
        filter_parts.append(f"பருவம்: **{_ta(season_filter)}**")
    filter_text = " (" + ", ".join(filter_parts) + ")" if filter_parts else ""

    first = top[0]
    second_name = _ta(top[1].get("crop_name")) if len(top) > 1 else "மேலுள்ள பயிர்கள்"
    paras = [
        f"### {district_ta} மாவட்டத்திற்கு பயிர் பரிந்துரை{filter_text}",
        (
            f"வரலாற்று மகசூல், சாகுபடி பரப்பு, பதிவுகளின் நிலைத்தன்மை ஆகியவற்றை வைத்து பார்க்கும்போது "
            f"**{_ta(first.get('crop_name'))}** முதன்மையான தேர்வாக வருகிறது. "
            f"இதன் சராசரி மகசூல் **{_ta_yield_label(first)}**, சராசரி சாகுபடி பரப்பு **{first.get('area_ha', 0):,} ஹெக்டேர்**."
        ),
    ]

    if len(top) > 1:
        second = top[1]
        paras.append(
            f"அடுத்த வலுவான தேர்வாக **{_ta(second.get('crop_name'))}** உள்ளது. "
            f"இதன் சராசரி மகசூல் **{_ta_yield_label(second)}**, சராசரி பரப்பு **{second.get('area_ha', 0):,} ஹெக்டேர்**."
        )

    if len(top) > 2:
        others = ", ".join(f"**{_ta(row.get('crop_name'))}**" for row in top[2:6])
        paras.append(f"மேலும் தரவில் நல்ல வாய்ப்பு காணப்படும் பயிர்கள்: {others}.")

    rain = (result.get("data") or {}).get("rain_data") or {}
    if rain and "error" not in rain:
        annual = rain.get("avg_annual_mm")
        if annual:
            paras.append(f"மழை நிலவரப்படி, {district_ta} மாவட்டத்தின் சராசரி ஆண்டு மழை **{annual} மில்லிமீட்டர்**.")

    irrigation = (result.get("data") or {}).get("irrigation_data") or {}
    if irrigation and "error" not in irrigation:
        pct = irrigation.get("irrigation_coverage_pct")
        if pct is not None:
            paras.append(f"பாசன வசதி சுமார் **{pct}%** நிகர விதைப்பு பரப்பை உள்ளடக்குகிறது. எனவே நீர் கிடைப்பையும் சந்தை விலையையும் சேர்த்து இறுதி பயிரைத் தேர்வு செய்வது நல்லது.")

    if data.get("conversion_note"):
        paras.append("அட்டவணையில் உள்ள மகசூல் மதிப்புகள் அனைத்தும் ஒரே அளவான **டன்/ஹெக்டேர்** ஆக மாற்றப்பட்டுள்ளன. தென்னை காய்கள் 1 காய் = 1.2 கிலோ என்றும், பேல் பயிர்கள் 1 பேல் = 170 கிலோ என்றும் கணக்கிடப்பட்டுள்ளன.")

    paras.append(
        f"மொத்தத்தில், **{_ta(first.get('crop_name'))}** மற்றும் **{second_name}** ஆகியவை தரவின் அடிப்படையில் வலுவான தேர்வுகள். "
        "ஆனால் உங்கள் நிலத்தின் நீர் வசதி, மண் பரிசோதனை முடிவு, தற்போதைய சந்தை விலை ஆகியவற்றையும் சேர்த்து முடிவு செய்யவும்."
    )

    lines = [
        "",
        "| தரவரிசை | பயிர் | மண் | பருவம் | சராசரி மகசூல் (டன்/ஹெக்டேர்) | சராசரி பரப்பு |",
        "|---|---|---|---|---|---|",
    ]
    for idx, row in enumerate(top, 1):
        lines.append(
            f"| #{idx} | **{_ta(row.get('crop_name'))}** | {_ta(row.get('soil_type'))} | {_ta(row.get('season'))} | {_ta_yield_label(row)} | {row.get('area_ha', 0):,} ஹெக்டேர் |"
        )
    paras.append("\n".join(lines))
    return "\n\n".join(paras)


def _format_tamil_rainfall(result: dict) -> str | None:
    data = (result.get("data") or {}).get("rain_data") or {}
    if "error" in data:
        return "இந்த மாவட்டத்திற்கான மழைத் தரவு கிடைக்கவில்லை. மாவட்டப் பெயரை சரிபார்த்து மீண்டும் முயற்சி செய்யவும்."

    district = data.get("district") or (result.get("memory") or {}).get("district") or result.get("district") or ""
    district_ta = _ta(district)
    annual = data.get("avg_annual_mm", 0)
    sw = data.get("sw_monsoon_mm", 0)
    ne = data.get("ne_monsoon_mm", 0)
    hot = data.get("hot_weather_mm", 0)
    winter = data.get("winter_mm", 0)
    period = data.get("period", "வரலாற்று காலம்")
    trend = data.get("yearly_trend", [])

    if annual > 1500:
        rain_class = "மிக அதிக மழை"
        advice = "நீர் அதிகம் தேவைப்படும் நெல், கரும்பு போன்ற பயிர்களுக்கு இது சாதகமாக இருக்கும்."
    elif annual > 900:
        rain_class = "மிதமானது முதல் அதிக மழை"
        advice = "பல தமிழ்நாடு பயிர்களுக்கு இது ஏற்ற அளவாகும்; பாசனத்தை சேர்த்து திட்டமிடலாம்."
    elif annual > 500:
        rain_class = "மிதமான மழை"
        advice = "நெல், கரும்பு போன்ற பயிர்களுக்கு கூடுதல் பாசனம் தேவைப்படலாம்."
    else:
        rain_class = "குறைந்த மழை"
        advice = "கம்பு, சோளம், சிறுதானியங்கள் போன்ற வறட்சியைத் தாங்கும் பயிர்கள் பாதுகாப்பான தேர்வாக இருக்கும்."

    dominant = "தென்மேற்கு பருவமழை" if sw > ne else "வடகிழக்கு பருவமழை"
    secondary = "வடகிழக்கு பருவமழை" if sw > ne else "தென்மேற்கு பருவமழை"
    dominant_mm = max(sw, ne)
    secondary_mm = min(sw, ne)
    dominant_pct = round(dominant_mm / annual * 100) if annual else 0

    paras = [
        f"### {district_ta} மாவட்ட மழை விவரம்",
        f"{period} காலத்திற்கான வரலாற்று தரவின் அடிப்படையில், {district_ta} மாவட்டத்தின் சராசரி ஆண்டு மழை **{annual} மில்லிமீட்டர்**. இது **{rain_class}** வகையில் வருகிறது. {advice}",
        f"முக்கிய மழைக்காலம் **{dominant}**. இது சுமார் **{dominant_mm:.0f} மில்லிமீட்டர்** மழையை வழங்குகிறது; ஆண்டு மழையின் சுமார் **{dominant_pct}%** இதிலிருந்து வருகிறது. **{secondary}** மூலம் சுமார் **{secondary_mm:.0f} மில்லிமீட்டர்** மழை கிடைக்கிறது.",
    ]

    if hot:
        paras.append(f"மார்ச் முதல் மே வரை உள்ள வெப்பக்காலத்தில் சுமார் **{hot:.0f} மில்லிமீட்டர்** மழை கிடைக்கிறது. இது காரிஃப் நிலத் தயாரிப்புக்கு உதவலாம்.")
    if winter:
        paras.append(f"குளிர்கால மழை சுமார் **{winter:.0f} மில்லிமீட்டர்** ஆக உள்ளது.")

    if len(trend) >= 3:
        recent = [r["total_mm"] for r in trend[-3:]]
        avg_recent = sum(recent) / len(recent)
        direction = "அதிகரிக்கும்" if recent[-1] > recent[0] else "குறையும்"
        paras.append(f"சமீபத்திய பதிவுகளைப் பார்க்கும்போது மழைப் போக்கு **{direction}** நிலையில் உள்ளது. கடைசி மூன்று பதிவுகளின் சராசரி **{avg_recent:.0f} மில்லிமீட்டர்**.")
        lines = ["", "| ஆண்டு | ஆண்டு மழை |", "|---|---|"]
        for row in trend:
            lines.append(f"| {int(row['year'])} | {row['total_mm']} மில்லிமீட்டர் |")
        paras.append("\n".join(lines))

    paras.append("குறிப்பு: இது 2019 வரை உள்ள வரலாற்று தரவின் அடிப்படையில் உள்ள மதிப்பீடு. நடப்பு பருவ மழை நிலவரத்தையும் உள்ளூர் வேளாண்மை அலுவலர் ஆலோசனையையும் சேர்த்து முடிவு செய்யவும்.")
    return "\n\n".join(paras)


def _ta_list(values: list[str]) -> str:
    translated = []
    for value in values:
        name = _ta(value)
        if name not in translated:
            translated.append(name)
    return ", ".join(translated)


def _ta_severity(value: str) -> str:
    value = str(value or "").lower()
    if "high" in value and "moderate" in value:
        return "மிதமானது முதல் அதிகம்"
    if "high" in value:
        return "அதிகம்"
    if "moderate" in value:
        return "மிதமானது"
    if "low" in value:
        return "குறைவு"
    return str(value)


def _ta_pests(values: list[str]) -> str:
    names = {
        "Rice Blast (Magnaporthe oryzae)": "நெல் பிளாஸ்ட் நோய்",
        "Brown Plant Hopper": "பழுப்பு தத்துப்பூச்சி",
        "Stem Borer": "தண்டு துளைப்பான்",
        "Sheath Blight": "ஷீத் பிளைட் நோய்",
        "Leaf Folder": "இலை மடிப்பான்",
        "Fungal Leaf Spot": "பூஞ்சை இலைப் புள்ளி நோய்",
        "Aphids": "அஃபிட்ஸ்",
        "Whitefly": "வெள்ளை ஈ",
        "Red Spider Mite": "சிவப்பு சிலந்திப் பூச்சி",
        "Thrips": "திரிப்ஸ்",
        "Leaf Miners": "இலை சுரங்கப் பூச்சி",
        "Pod Borers": "காய் துளைப்பான்",
        "General garden pests (minor)": "பொதுவான சிறிய பூச்சிகள்",
    }
    return ", ".join(names.get(v, v) for v in values)


def _ta_prevention(text: str) -> str:
    normalized = str(text or "").replace("–", "-").replace("â€“", "-")
    options = {
        "Apply propiconazole fungicide; drain excess water; use resistant varieties.": "ப்ரோபிகோனசோல் பூஞ்சைக்கொல்லி பயன்படுத்தவும்; அதிக நீரை வடிகட்டவும்; நோய் எதிர்ப்பு வகைகளை பயன்படுத்தவும்.",
        "Ensure proper field drainage; apply mancozeb; monitor regularly in Oct-Dec.": "வயலில் நல்ல வடிகால் ஏற்பாடு செய்யவும்; மான்கோசெப் பயன்படுத்தவும்; அக்டோபர் முதல் டிசம்பர் வரை அடிக்கடி கண்காணிக்கவும்.",
        "Spray neem oil or imidacloprid; maintain adequate soil moisture.": "வேப்பெண்ணெய் அல்லது இமிடாக்ளோபிரிட் தெளிக்கவும்; மண்ணில் போதுமான ஈரப்பதத்தை பராமரிக்கவும்.",
        "Install yellow sticky traps; use spinosad insecticide; irrigate frequently.": "மஞ்சள் ஒட்டும் வலைகளை அமைக்கவும்; ஸ்பைனோசாட் பூச்சிக்கொல்லி பயன்படுத்தவும்; அடிக்கடி பாசனம் செய்யவும்.",
        "Routine monitoring and preventive neem sprays recommended.": "தொடர்ந்து கண்காணிக்கவும்; முன்னெச்சரிக்கையாக வேப்பெண்ணெய் தெளிக்கவும்.",
    }
    return options.get(normalized, text)


def _format_tamil_pest_risk(result: dict) -> str | None:
    data = (result.get("data") or {}).get("pest_data") or {}
    if "error" in data:
        return "இந்த மாவட்டத்திற்கான பூச்சி அபாயத் தரவு கிடைக்கவில்லை. மாவட்டப் பெயரை சரிபார்த்து மீண்டும் முயற்சி செய்யவும்."

    district = data.get("district") or (result.get("memory") or {}).get("district") or result.get("district") or ""
    district_ta = _ta(district)
    annual = data.get("avg_annual_rain_mm", 0)
    sw = data.get("sw_monsoon_mm", 0)
    ne = data.get("ne_monsoon_mm", 0)
    risks = data.get("risks", [])
    dev = data.get("deviation_pct")

    paras = [
        f"### {district_ta} மாவட்ட பூச்சி அபாய மதிப்பீடு",
        f"வரலாற்று மழை மற்றும் காலநிலை தரவின் அடிப்படையில் இந்த மதிப்பீடு செய்யப்பட்டுள்ளது. ஆண்டு சராசரி மழை **{annual} மில்லிமீட்டர்**; தென்மேற்கு பருவமழை **{sw:.0f} மில்லிமீட்டர்**, வடகிழக்கு பருவமழை **{ne:.0f} மில்லிமீட்டர்**.",
    ]

    if max(sw or 0, ne or 0) > 800:
        paras.append("அதிக பருவமழை ஈரப்பதத்தை உயர்த்தும். அதனால் பூஞ்சை நோய்கள் மற்றும் சில பூச்சி தாக்குதல்கள் அதிகரிக்கும் வாய்ப்பு உள்ளது.")
    else:
        paras.append("மழை மிதமாக இருப்பதால் ஈரப்பதம் சார்ந்த பூச்சிகள் குறையலாம்; ஆனால் வறட்சி காலங்களில் சாறு உறிஞ்சும் பூச்சிகளை கண்காணிக்க வேண்டும்.")

    for risk in risks:
        severity = _ta_severity(risk.get("severity"))
        pests = _ta_pests(risk.get("pests", []))
        crops = _ta_list(risk.get("crops_affected", []))
        prevention = _ta_prevention(risk.get("prevention", ""))
        paras.append(
            f"**அபாய நிலை: {severity}**\n\n"
            f"சாத்தியமான பூச்சி/நோய்கள்: **{pests}**.\n\n"
            f"அதிகம் பாதிக்கப்படக்கூடிய பயிர்கள்: **{crops}**.\n\n"
            f"பரிந்துரைக்கப்படும் நடவடிக்கை: {prevention}"
        )

    if isinstance(dev, (int, float)):
        dev_text = f"+{dev}%" if dev >= 0 else f"{dev}%"
        if dev > 5:
            msg = "அதிக மழை/நீர் தேக்கம் ஏற்பட்டால் பூஞ்சை நோய்களை கவனிக்க வேண்டும்."
        elif dev < -5:
            msg = "மழை குறைவு நீர் அழுத்தத்தை ஏற்படுத்தலாம்; இதனால் சாறு உறிஞ்சும் பூச்சிகள் அதிகரிக்கலாம்."
        else:
            msg = "மழை நிலை சாதாரணத்திற்கு அருகில் உள்ளது; வழக்கமான கண்காணிப்பு போதுமானது."
        paras.append(f"மாநில அளவிலான மழை விலகல் **{dev_text}**. {msg}")

    paras.append("பொது ஆலோசனை: ஒருங்கிணைந்த பூச்சி மேலாண்மை முறையைப் பயன்படுத்தவும். உயிரியல் கட்டுப்பாடு, எதிர்ப்பு வகைகள், வயல் கண்காணிப்பு ஆகியவற்றை முதலில் செய்யவும்; ரசாயன மருந்துகளை அவசியமானபோது மட்டும் பயன்படுத்தவும்.")
    return "\n\n".join(paras)


def _strict_tamil_summary(intent: str, memory: dict, text: str = "") -> str:
    district = _ta(memory.get("district") or "")
    crop = _ta(memory.get("crop") or "")
    season = _ta(memory.get("season") or "")
    month = memory.get("month") or ""
    place = f"**{district}** மாவட்டத்தில் " if district else ""
    crop_part = f"**{crop}** பயிருக்கு " if crop else ""

    if intent == "greeting":
        return "வணக்கம்! நான் தமிழ்நாடு வேளாண்மை உதவியாளர். பயிர் பரிந்துரை, மழை, பாசனம், உரம், பூச்சி அபாயம், செலவு, லாபம் போன்ற கேள்விகளை தமிழில் கேட்கலாம்."
    if "I need a district" in text:
        return "இந்த கேள்விக்கு மாவட்டப் பெயர் தேவை. உதாரணம்: **கோயம்புத்தூரில் நெல் பயிரிடலாமா?** அல்லது **மதுரையில் மழை அளவு என்ன?**"
    if "Which crop" in text or "Which crop would you like" in text:
        return f"இந்த கேள்விக்கு பயிர் பெயர் தேவை. உதாரணம்: **{district or 'கோயம்புத்தூர்'} மாவட்டத்தில் நெல் சாகுபடி செலவு என்ன?**"
    if "cannot find that particular crop" in text or "particular crop" in text:
        return "அந்த பயிருக்கு போதுமான பதிவுகள் கிடைக்கவில்லை. பயிர் பெயரை சரிபார்த்து மீண்டும் கேளுங்கள். ஏற்பட்ட சிரமத்திற்கு மன்னிக்கவும்."
    if "particular district" in text:
        return "அந்த மாவட்டத்திற்கான தரவு தற்போது கிடைக்கவில்லை. மாவட்டப் பெயரை சரிபார்த்து மீண்டும் கேளுங்கள்."
    if intent == "suitability":
        score = _extract_first(r"\*\*([0-9.]+/10)", text, "")
        score_text = f" மதிப்பெண்: **{score}**." if score else ""
        season_text = f" பருவம்: **{season}**." if season else ""
        month_text = f" மாதம்: **{month}**." if month else ""
        return f"{place}{crop_part}பொருத்த மதிப்பீடு கணக்கிடப்பட்டுள்ளது.{score_text}{season_text}{month_text} இந்த மதிப்பீடு மகசூல், மழை, மண், பாசனம் மற்றும் வரலாற்று பதிவுகளை அடிப்படையாகக் கொண்டது."
    if intent == "cost_estimate":
        return f"{place}{crop_part}சாகுபடி செலவு மதிப்பிடப்பட்டுள்ளது. விதை, உரம், கூலி, பாசனம், பூச்சிக்கொல்லி போன்ற செலவுகள் உள்ளூர் நிலைமைக்கு ஏற்ப மாறலாம்."
    if intent == "profit_estimate":
        return f"{place}{crop_part}லாப மதிப்பீடு கணக்கிடப்பட்டுள்ளது. இது வரலாற்று மகசூல், சாகுபடி செலவு மற்றும் திட்டமிடல் விலை அடிப்படையிலான வழிகாட்டும் மதிப்பீடு மட்டுமே."
    if intent == "multi_criteria":
        return f"{place}நீர் தேவை, மகசூல், சாகுபடி பரப்பு மற்றும் பதிவுகளின் நிலைத்தன்மை அடிப்படையில் பயிர் விருப்பங்கள் மதிப்பிடப்பட்டுள்ளன."
    if intent == "fertilizer_recommendation":
        return f"{place}{crop_part}உர பரிந்துரை தயாரிக்கப்பட்டுள்ளது. இறுதி அளவை மண் பரிசோதனை முடிவு மற்றும் உள்ளூர் வேளாண்மை அலுவலர் ஆலோசனைப்படி சரிசெய்யவும்."
    if intent == "planting_time":
        return f"{crop_part}ஏற்ற நடவு காலம் தரவின் அடிப்படையில் மதிப்பிடப்பட்டுள்ளது. உள்ளூர் மழை, பாசன வசதி, விதை வகை ஆகியவற்றை வைத்து இறுதி நேரத்தை தேர்வு செய்யவும்."
    if intent == "best_district_for_crop":
        return f"**{crop or 'இந்த பயிர்'}** பயிருக்கு ஏற்ற மாவட்டங்கள் வரலாற்று மகசூல், சாகுபடி பரப்பு மற்றும் பதிவுகளின் நிலைத்தன்மை அடிப்படையில் மதிப்பிடப்பட்டுள்ளன."
    if intent == "wage_info":
        return f"{place}வேளாண்மை கூலி விவரம் மாவட்டத் தரவின் அடிப்படையில் மதிப்பிடப்பட்டுள்ளது. வேலை வகை மற்றும் உள்ளூர் தேவைப் பொறுத்து கூலி மாறலாம்."
    if intent == "irrigation_info":
        return f"{place}பாசன விவரம் கணக்கிடப்பட்டுள்ளது. கால்வாய், குளம், கிணறு, போர்வெல் போன்ற நீர்மூலங்களை வைத்து பயிர் தேர்வை திட்டமிடலாம்."
    if intent == "yield_trend":
        return f"{place}{crop_part}மகசூல் போக்கு வரலாற்று பதிவுகளின் அடிப்படையில் மதிப்பிடப்பட்டுள்ளது. நடப்பு பருவ நிலைமையை சேர்த்து முடிவு செய்யவும்."
    if intent == "district_overview":
        return f"{place}வேளாண்மை சுருக்கம் தயாரிக்கப்பட்டுள்ளது. மழை, பாசனம், மண், முக்கிய பயிர்கள் ஆகியவற்றை வைத்து அடுத்த திட்டமிடலை செய்யலாம்."
    if intent == "whatif":
        return f"{place}{crop_part}மாற்றுச் சூழல் மதிப்பீடு கணக்கிடப்பட்டுள்ளது. பாசனம் அல்லது மழை மாறினால் பொருத்தம் எப்படி மாறும் என்பதை இது காட்டுகிறது."
    if intent == "yield_predict":
        return f"{place}{crop_part}மகசூல் கணிப்பு தயாரிக்கப்பட்டுள்ளது. இது வரலாற்று தரவு மற்றும் மாதிரி கணிப்பின் அடிப்படையிலான மதிப்பீடு."
    if intent == "pest_predict":
        return f"{place}{crop_part}பூச்சி அபாய கணிப்பு தயாரிக்கப்பட்டுள்ளது. வயல் கண்காணிப்பு மற்றும் ஒருங்கிணைந்த பூச்சி மேலாண்மை முறையைப் பயன்படுத்தவும்."
    if intent == "soil_info":
        return "மண் வகையை கண்டறிய பக்கப்பட்டியில் உள்ள மண் படம் பதிவேற்றும் வசதியை பயன்படுத்தவும்."
    return "உங்கள் கேள்விக்கான பதில் தமிழ்நாடு வேளாண்மை தரவின் அடிப்படையில் மதிப்பிடப்பட்டுள்ளது. கூடுதல் விவரத்திற்கு மாவட்டம், பயிர், மண் வகை அல்லது பருவத்தை குறிப்பிட்டு கேளுங்கள்."


def _tamil_response(result: dict) -> dict:
    intent = result.get("intent", "general")
    memory = result.get("memory") or {}
    text = result.get("text") or ""
    district = memory.get("district")
    crop = memory.get("crop")
    season = memory.get("season")
    month = memory.get("month")

    if intent == "crop_recommend":
        result = dict(result)
        result["text"] = _format_tamil_crop_recommend(result) or f"**{district}** மாவட்டத்திற்கு பயிர் பரிந்துரை கணக்கிடப்பட்டுள்ளது."
        result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
        return result
    if intent == "rainfall_info":
        result = dict(result)
        result["text"] = _format_tamil_rainfall(result) or "மழை விவரம் தமிழில் தயாரிக்க முடியவில்லை."
        result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
        return result
    if intent == "pest_risk":
        result = dict(result)
        result["text"] = _format_tamil_pest_risk(result) or "பூச்சி அபாய விவரம் தமிழில் தயாரிக்க முடியவில்லை."
        result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
        return result
    if intent == "context_update":
        parts = []
        if district:
            parts.append(f"மாவட்டம்: **{_ta(district)}**")
        if crop:
            parts.append(f"பயிர்: **{_ta(crop)}**")
        if season:
            parts.append(f"பருவம்: **{_ta(season)}**")
        if month:
            parts.append(f"மாதம்: **{month}**")
        result = dict(result)
        result["text"] = "சரி, செயலில் உள்ள சூழல் புதுப்பிக்கப்பட்டது: " + ", ".join(parts) + ". இதைப் பயன்படுத்தி அடுத்த கேள்வியை கேட்கலாம்."
        result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
        return result
    if intent == "general":
        result = dict(result)
        result["text"] = (
            "மன்னிக்கவும், உங்கள் கேள்வியை தெளிவாகப் புரிந்துகொள்ள முடியவில்லை. "
            "மாவட்டம், பயிர், மண் வகை அல்லது பருவத்தை குறிப்பிட்டு மீண்டும் கேளுங்கள். "
            "உதாரணம்: **கோயம்புத்தூரில் நெல் பயிரிடலாமா?** அல்லது **மதுரையில் மழை அளவு என்ன?**"
        )
        result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
        return result

    result = dict(result)
    result["text"] = _strict_tamil_summary(intent, memory, text)
    result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
    return result

    if intent == "greeting":
        ta_text = "வணக்கம்! நான் தமிழ்நாட்டிற்கான Smart Farming உதவியாளர். பயிர், மழை, செலவு, லாபம், பாசனம் போன்ற கேள்விகளை தமிழில் கேட்கலாம்."
    elif "I need a district" in text:
        ta_text = "இந்த கேள்விக்கு மாவட்டப் பெயர் தேவை. உதாரணம்: **கோயம்புத்தூரில் நெல் பயிரிடலாமா?** அல்லது **மதுரையில் நிலக்கடலை செலவு என்ன?**"
    elif "Which crop" in text or "Which crop would you like" in text:
        ta_text = f"இந்த கேள்விக்கு பயிர் பெயர் தேவை. உதாரணம்: **{district or 'Coimbatore'} மாவட்டத்தில் நெல் செலவு என்ன?**"
    elif "cannot find that particular crop" in text or "particular crop" in text:
        ta_text = "தமிழ்நாடு வேளாண்மை தரவுத்தொகுப்பில் அந்த குறிப்பிட்ட பயிர்க்கான போதுமான தகவலை கண்டுபிடிக்க முடியவில்லை. அந்த பயிர் பதிவுகள் குறைவாக இருக்கலாம் அல்லது சில பகுதிகளில் அதன் சாகுபடி வரம்பாக இருக்கலாம். ஏற்பட்ட சிரமத்திற்கு மன்னிக்கவும்; எதிர்காலத்தில் இந்த தகவலை மேம்படுத்த முயற்சிப்போம்."
    elif "particular district" in text:
        ta_text = "அந்த குறிப்பிட்ட மாவட்டத்திற்கான தரவு தற்போது கிடைக்கவில்லை. மாவட்டப் பெயரின் எழுத்துப்பிழையை ஒருமுறை சரிபார்க்கவும். ஏற்பட்ட சிரமத்திற்கு மன்னிக்கவும்."
    elif intent == "context_update":
        parts = []
        if district: parts.append(f"மாவட்டம்: **{district}**")
        if crop: parts.append(f"பயிர்: **{_ta(crop)}**")
        if season: parts.append(f"பருவம்: **{_ta(season)}**")
        if month: parts.append(f"மாதம்: **{month}**")
        ta_text = "சரி, செயலில் உள்ள சூழல் புதுப்பிக்கப்பட்டது: " + ", ".join(parts) + ". இதைப் பயன்படுத்தி அடுத்த கேள்வியை கேட்கலாம்."
    elif intent == "suitability":
        score = _extract_first(r"\*\*([0-9.]+/10[^*]*)\*\*", text, "")
        ta_text = f"**{district}** மாவட்டத்தில் **{_ta(crop)}** பயிரிடுவது பற்றிய பொருத்த மதிப்பீடு: **{score or 'கணக்கிடப்பட்டது'}**. பருவம்: **{_ta(season)}**, மாதம்: **{month or SEASON_DEFAULT_MONTH.get(season, '')}**. இந்த மதிப்பீடு மகசூல், மழை பொருத்தம், மண், பாசனம் மற்றும் வரலாற்று பதிவுகளை வைத்து கணக்கிடப்பட்டது."
    elif intent == "cost_estimate":
        total = _extract_first(r"TOTAL\*\* \| \*\*(₹[^|]+)\| \*\*(₹[^|]+)", text, "")
        ta_text = f"**{district}** மாவட்டத்தில் **{_ta(crop)}** சாகுபடிக்கான மதிப்பிடப்பட்ட செலவு கீழே உள்ளது. விதை, உரம், கூலி, பாசனம், பூச்சிக்கொல்லி போன்ற முக்கிய செலவுத்தலைகள் இதில் சேர்க்கப்பட்டுள்ளன.\n\n{text}"
    elif intent == "profit_estimate":
        ta_text = f"**{district}** மாவட்டத்தில் **{_ta(crop)}** பயிரின் லாப மதிப்பீடு கீழே உள்ளது. இது வரலாற்று மகசூல், சாகுபடி செலவு மற்றும் திட்டமிடல் விலை அடிப்படையில் கணக்கிடப்பட்ட ஒரு மதிப்பீடு மட்டுமே.\n\n{text}"
    elif intent == "crop_recommend":
        ta_text = f"**{district}** மாவட்டத்திற்கான பயிர் பரிந்துரை கீழே உள்ளது. இது வரலாற்று மகசூல், சாகுபடி பரப்பு மற்றும் பதிவுகளின் நிலைத்தன்மை அடிப்படையில் கணக்கிடப்பட்டது.\n\n{text}"
    elif intent == "multi_criteria":
        ta_text = f"**{district}** மாவட்டத்திற்கான லாப நோக்கிலான பயிர் விருப்பங்கள் கீழே உள்ளன. இது வரலாற்று மகசூல், சாகுபடி பரப்பு மற்றும் பதிவுகளின் நிலைத்தன்மையை லாபத்தின் மாற்று அளவுகோலாக வைத்து கணக்கிடப்பட்டது.\n\n{text}"
    elif intent == "rainfall_info":
        annual = _extract_first(r"averaging \*\*([0-9.]+ mm)", text, "")
        ta_text = f"**{district}** மாவட்டத்தின் மழை விவரம்: சராசரி ஆண்டு மழை **{annual or 'தரவின் அடிப்படையில் கணக்கிடப்பட்டது'}**. பருவ மழை மற்றும் சமீபத்திய மழைப் போக்கை வைத்து விவரம் கீழே உள்ளது.\n\n{text}"
    elif intent == "planting_time":
        ta_text = f"**{_ta(crop)}** பயிரிட ஏற்ற பருவம்/மாதம் பற்றிய தகவல் கீழே உள்ளது.\n\n{text}"
    elif intent == "best_district_for_crop":
        ta_text = f"**{_ta(crop)}** பயிருக்கு ஏற்ற மாவட்டங்களின் தரவரிசை கீழே உள்ளது. இது வரலாற்று மகசூல், சாகுபடி பரப்பு மற்றும் பதிவுகளின் நிலைத்தன்மை அடிப்படையில் கணக்கிடப்பட்டது.\n\n{text}"
    else:
        ta_text = "உங்கள் கேள்விக்கான பதில் கீழே உள்ளது. கணக்கீடு தமிழ்நாடு வேளாண்மை தரவுத்தொகுப்பின் அடிப்படையில் செய்யப்பட்டுள்ளது.\n\n" + text

    result = dict(result)
    result["text"] = ta_text
    result["text"] = _ensure_tamil_followup_chips(result["text"], intent, memory)
    return result


def _canonical_crop(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    if key in CROP_ALIASES:
        return CROP_ALIASES[key]
    supp = de.lookup_supplemental_crop(key)
    if supp:
        return supp.lower()
    crops = _all_known_crops()
    if key in crops:
        return key
    close = get_close_matches(key, crops, n=1, cutoff=0.75)
    if close:
        supp_close = de.lookup_supplemental_crop(close[0])
        return supp_close.lower() if supp_close else close[0]
    return None


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
            canonical = _canonical_crop(crop)
            return canonical.title() if canonical else None
    # fallback whole-query fuzzy against supplemental aliases
    supp = de.lookup_supplemental_crop(query)
    return supp.title() if supp else None


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


def _clear_memory_fields(memory: dict, fields: list[str]) -> dict:
    updated = dict(memory or {})
    for field in fields:
        if field in updated:
            updated[field] = None
    if "season" in fields and "month" not in fields:
        updated["month"] = None
    if "month" in fields and "season" not in fields:
        updated["season"] = None
    return updated


def _context_clear_fields(query: str) -> list[str]:
    ql = query.lower().strip()
    if not re.search(r"\b(?:remove|remve|clear|reset|forget|delete)\b", ql):
        return []
    fields = []
    field_words = {
        "crop": ["crop", "crops"],
        "district": ["district", "location", "place"],
        "soil": ["soil"],
        "season": ["season"],
        "month": ["month"],
    }
    for field, words in field_words.items():
        if any(re.search(rf"\b{re.escape(word)}\b", ql) for word in words):
            fields.append(field)
    if re.search(r"\b(?:context|memory|everything|all)\b", ql):
        fields = ["district", "soil", "season", "month", "crop"]
    return fields


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
            f"Rainfall in {district}",
            f"Overview of {district} district",
            f"What is the irrigation profile of {district}?",
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


def _suggest_followups_tamil(intent: str, context: dict | None = None) -> list[str]:
    ctx = context or {}
    district = _ta(ctx.get("district") or "Coimbatore")
    crop = _ta(ctx.get("crop") or "rice")
    crop_dative = "நெல்லுக்கு" if crop == "நெல்" else f"{crop}க்கு"
    options = {
        "crop_recommend": [
            f"{district} மாவட்டத்தில் {crop_dative} உரம் என்ன?",
            f"{district} மாவட்ட மழை அளவு என்ன?",
            f"{district} மாவட்டத்தில் {crop} பயிரிடலாமா?",
        ],
        "fertilizer_recommendation": [
            f"{district} மாவட்டத்தில் {crop} சாகுபடி செலவு என்ன?",
            f"{district} மாவட்டத்தில் {crop} மகசூல் கணிக்கவும்",
            f"{district} மாவட்டத்தில் {crop}க்கு பூச்சி அபாயம் என்ன?",
        ],
        "suitability": [
            f"{district} மாவட்டத்தில் {crop} மகசூல் கணிக்கவும்",
            f"{district} மாவட்டத்தில் {crop_dative} உரம் என்ன?",
            f"{district} மாவட்டத்தில் பாசனம் அதிகரித்தால் {crop}க்கு என்ன ஆகும்?",
        ],
        "rainfall_info": [
            f"{district} மாவட்டத்திற்கு சிறந்த பயிர்கள்?",
            f"{district} மாவட்ட பாசன விவரம் என்ன?",
            f"{district} மாவட்டத்தில் பூச்சி அபாயம் என்ன?",
        ],
        "pest_risk": [
            f"{district} மாவட்டத்திற்கு சிறந்த பயிர்கள்?",
            f"{district} மாவட்ட மழை அளவு என்ன?",
            f"{district} மாவட்டத்தில் {crop} பயிரிடலாமா?",
        ],
        "district_overview": [
            f"{district} மாவட்டத்திற்கு சிறந்த பயிர்கள்?",
            f"{district} மாவட்ட மழை அளவு என்ன?",
            f"{district} மாவட்ட பாசன விவரம் என்ன?",
        ],
        "whatif": [
            f"{district} மாவட்டத்தில் {crop} பயிரிடலாமா?",
            f"{district} மாவட்டத்தில் {crop} மகசூல் கணிக்கவும்",
            f"{district} மாவட்டத்தில் {crop} சாகுபடி செலவு என்ன?",
        ],
        "context_update": [
            f"{district} மாவட்டத்திற்கு சிறந்த பயிர்கள்?",
            f"{district} மாவட்ட மழை அளவு என்ன?",
            f"{district} மாவட்டத்தில் {crop} பயிரிடலாமா?",
        ],
    }
    return options.get(intent, [
        f"{district} மாவட்டத்திற்கு சிறந்த பயிர்கள்?",
        f"{district} மாவட்ட மழை அளவு என்ன?",
        f"{district} மாவட்ட விவரம் சொல்லுங்கள்",
    ])


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


def _ensure_tamil_followup_chips(text: str, intent: str, context: dict | None = None) -> str:
    if not text:
        return text
    text = re.sub(r"\n\n---\n\*\*FOLLOWUP_CHIPS:[\s\S]*?\*\*\s*$", "", text.rstrip())
    chips = _suggest_followups_tamil(intent, context)[:3]
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
    explicit_crop = _extract_crop(message)

    crop_independent_intents = {
        "crop_recommend",
        "rainfall_info",
        "wage_info",
        "irrigation_info",
        "pest_risk",
        "district_overview",
        "multi_criteria",
    }
    ignored_memory_crop = False
    if intent in crop_independent_intents and not explicit_crop:
        crop = None
        ignored_memory_crop = True

    if intent == "cost_estimate":
        district = district or "Coimbatore"
        crop = crop or "rice"
    elif intent == "profit_estimate":
        district = district or "Coimbatore"
        crop = crop or "rice"
    elif intent == "multi_criteria":
        district = district or "Coimbatore"

    new_memory = _merge_memory(memory, district=district, soil=soil, season=season, month=month, crop=crop)
    if ignored_memory_crop:
        new_memory["crop"] = None
    ctx = {"district": district, "soil": soil, "season": season, "month": month, "crop": crop}
    response_data = {}

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
        supp_crop = de.lookup_supplemental_crop(explicit_unknown_crop)
        if supp_crop:
            crop = supp_crop
            new_memory = _merge_memory(memory, district=district, soil=soil, season=season, month=month, crop=crop)
            ctx = {"district": district, "soil": soil, "season": season, "month": month, "crop": crop}
        else:
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

    is_fallback_crop = bool(crop and de.is_supplemental_crop(crop))
    fallback_supported_intents = {"suitability", "whatif", "planting_time", "fertilizer_recommendation"}
    if is_fallback_crop and intent not in fallback_supported_intents:
        text = de.get_fallback_only_message(crop)
        return {"text": _ensure_followup_chips(text, intent, ctx), "intent": intent, "district": district, "memory": new_memory}

    if intent == "crop_recommend":
        crop_data = de.get_top_crops(district, soil, season, top_n=40)
        response_data["crop_data"] = crop_data
        response_data["rain_data"] = de.get_rainfall_stats(district)
        response_data["irrigation_data"] = de.get_irrigation_profile(district)
        text = nlg.describe_crops(district, crop_data, response_data["rain_data"], response_data["irrigation_data"])
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
        response_data["rain_data"] = de.get_rainfall_stats(district)
        text = nlg.describe_rainfall(district, response_data["rain_data"])
    elif intent == "wage_info":
        text = nlg.describe_wages(district, de.get_wage_info(district))
    elif intent == "irrigation_info":
        text = nlg.describe_irrigation(district, de.get_irrigation_profile(district))
    elif intent == "yield_trend":
        text = nlg.describe_yield_trend(district, crop, de.get_yield_trend(district, crop))
    elif intent == "pest_risk":
        response_data["pest_data"] = de.get_pest_risk(district)
        text = nlg.describe_pest_risk(district, response_data["pest_data"])
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

    result = {"text": _ensure_followup_chips(text, intent, ctx), "intent": intent, "district": district, "memory": new_memory}
    if response_data:
        result["data"] = response_data
    return result


def process_query(message: str, history: list = None, language: str | None = None) -> dict:
    message = (message or "").strip()
    tamil_requested = (language or "").lower().startswith("ta")
    original_message = message
    if _is_tamil_text(message):
        message = _normalize_tamil_query(message)

    def finalize(result: dict) -> dict:
        if tamil_requested:
            return _tamil_response(result)
        return result

    blank_mem = {"district": None, "soil": None, "season": None, "month": None, "crop": None}
    if not message:
        return finalize({"text": WELCOME_TEXT, "intent": "greeting", "district": None, "memory": blank_mem})

    memory = _get_memory(history)
    clear_fields = _context_clear_fields(message)
    if clear_fields:
        new_memory = _clear_memory_fields(memory, clear_fields)
        fields_text = ", ".join(field.title() for field in clear_fields)
        text = f"Got it. I cleared **{fields_text}** from the active context."
        return finalize({
            "text": _ensure_followup_chips(text, "context_update", new_memory),
            "intent": "context_update",
            "district": new_memory.get("district"),
            "memory": new_memory,
        })

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
        return finalize({"text": WELCOME_TEXT, "intent": "greeting", "district": district, "memory": new_memory})

    if _detect_intent(message) == "general" and any([quick_district, quick_crop, quick_soil, quick_season, quick_month]):
        text = _describe_context_update(new_memory)
        return finalize({
            "text": _ensure_followup_chips(text, "context_update", new_memory),
            "intent": "context_update",
            "district": new_memory.get("district"),
            "memory": new_memory,
        })

    return finalize(_fallback_router(message, district, soil, season, crop, month, memory))
