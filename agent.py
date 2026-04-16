
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
    "best_district_for_crop": [r"which district.*(?:best|grow|grows|suitable)", r"where.*(?:best|grow|grows).*(?:crop|rice|coconut|groundnut|sugarcane|cotton|maize|banana)", r"best district", r"district.*(?:grows|grow).*best"],
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
    direct_replacements = {
        "கூலி": "wage",
        "சம்பளம்": "wage",
        "வேளாண்மை கூலி": "wage",
        "மகசூல் போக்கு": "yield trend",
        "மகசூல் நிலை": "yield trend",
        "சிறந்த மாவட்டம்": "best district",
        "எந்த மாவட்டம்": "which district",
        "என்ன ஆகும்": "what if",
        "குறைந்தால்": "reduced",
        "அதிகரித்தால்": "increased",
        "குறைத்தால்": "reduced",
        "மாறினால்": "changed",
    }
    for tamil, english in direct_replacements.items():
        normalized = normalized.replace(tamil, english)
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
        "villupuram": "விழுப்புரம்", "tiruvarur": "திருவாரூர்", "kancheepuram": "காஞ்சிபுரம்", "nagapattinam": "நாகப்பட்டினம்",
        "tiruvannamalai": "திருவண்ணாமலை", "ariyalur": "அரியலூர்", "chennai": "சென்னை", "dindigul": "திண்டுக்கல்",
        "kallakurichi": "கள்ளக்குறிச்சி", "karur": "கரூர்", "krishnagiri": "கிருஷ்ணகிரி", "namakkal": "நாமக்கல்",
        "perambalur": "பெரம்பலூர்", "pudukkottai": "புதுக்கோட்டை", "ramanathapuram": "ராமநாதபுரம்", "ranipet": "ராணிப்பேட்டை",
        "sivagangai": "சிவகங்கை", "tenkasi": "தென்காசி", "theni": "தேனி", "thoothukudi": "தூத்துக்குடி",
        "tirunelveli": "திருநெல்வேலி", "tirupathur": "திருப்பத்தூர்", "tiruppur": "திருப்பூர்", "tiruvallur": "திருவள்ளூர்",
        "vellore": "வேலூர்", "virudhunagar": "விருதுநகர்",
        "red soil": "சிவப்பு மண்", "black soil": "கருப்பு மண்", "clay soil": "களிமண்",
        "alluvial soil": "வண்டல் மண்", "Kharif": "காரிஃப் / மழைக்காலம்", "Rabi": "ரபி",
        "Summer": "கோடை", "Winter": "குளிர்காலம்", "Autumn": "இலையுதிர் காலம்",
        "Whole Year": "முழு ஆண்டு",
        "Moderate": "மிதமானது", "Below Average": "சராசரிக்கு கீழ்", "Very Good": "மிக நல்லது", "Excellent": "மிகச் சிறந்தது", "Poor": "பலவீனமானது",
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


def _format_tamil_cost_estimate(result: dict) -> str | None:
    data = (result.get("data") or {}).get("cost_data") or {}
    if not data or "error" in data:
        return None

    district = _ta(data.get("district") or (result.get("memory") or {}).get("district") or "")
    crop = _ta(data.get("crop") or (result.get("memory") or {}).get("crop") or "")
    area = data.get("area_acres", 1.0)
    total_lo = data.get("total_cost_min", 0)
    total_hi = data.get("total_cost_max", 0)
    cpa_lo = data.get("cost_per_acre_min", 0)
    cpa_hi = data.get("cost_per_acre_max", 0)
    wage_adj = data.get("wage_adjustment_factor", 1.0)
    comps = data.get("components") or {}
    labels = {
        "seeds": "விதை",
        "fertilizer": "உரம்",
        "labour": "கூலி",
        "irrigation": "பாசனம்",
        "pesticide": "பூச்சிக்கொல்லி",
    }

    wage_note = ""
    if isinstance(wage_adj, (int, float)) and wage_adj > 1.1:
        wage_note = f" இந்த மாவட்டத்தில் கூலி சராசரியை விட அதிகமாக இருப்பதால் கூலி செலவு சுமார் **{round((wage_adj - 1) * 100)}%** உயர்த்திக் கணக்கிடப்பட்டுள்ளது."
    elif isinstance(wage_adj, (int, float)) and wage_adj < 0.9:
        wage_note = f" இந்த மாவட்டத்தில் கூலி சராசரியை விட குறைவாக இருப்பதால் கூலி செலவு சுமார் **{round((1 - wage_adj) * 100)}%** குறைத்து கணக்கிடப்பட்டுள்ளது."

    lines = [
        "| செலவு பகுதி | குறைந்தபட்சம் (ரூ.) | அதிகபட்சம் (ரூ.) |",
        "|------------|-------------------|------------------|",
    ]
    for key in ["seeds", "fertilizer", "labour", "irrigation", "pesticide"]:
        vals = comps.get(key)
        if vals:
            lines.append(f"| {labels.get(key, key)} | ரூ.{vals.get('min', 0):,} | ரூ.{vals.get('max', 0):,} |")
    lines.append(f"| **மொத்தம்** | **ரூ.{total_lo:,}** | **ரூ.{total_hi:,}** |")

    biggest = ""
    if comps:
        max_comp = max(comps, key=lambda key: comps[key].get("max", 0))
        max_val = comps[max_comp].get("max", 0)
        pct = round(max_val / total_hi * 100) if total_hi else 0
        advice = {
            "labour": "கூலி செலவை குறைக்க இயந்திர நடவு அல்லது அறுவடை இயந்திரங்களைப் பயன்படுத்தலாம்.",
            "seeds": "அரசு அங்கீகரித்த தரமான விதைகளைப் பயன்படுத்துவது நல்லது.",
            "fertilizer": "மண் பரிசோதனை செய்து உர அளவை திட்டமிட்டால் செலவை குறைக்கலாம்.",
            "irrigation": "சொட்டு அல்லது தெளிப்பு பாசனம் நீர் மற்றும் பாசன செலவை குறைக்க உதவும்.",
            "pesticide": "ஒருங்கிணைந்த பூச்சி மேலாண்மை பூச்சிக்கொல்லி செலவை குறைத்து மண் ஆரோக்கியத்தையும் பாதுகாக்கும்.",
        }.get(max_comp, "இந்த செலவு பகுதியை திட்டமிட்டு கட்டுப்படுத்தலாம்.")
        biggest = f"\n\n**அதிக செலவு பகுதி:** {labels.get(max_comp, max_comp)} அதிகபட்சம் **ரூ.{max_val:,}** வரை ஆகலாம். இது மொத்த செலவில் சுமார் **{pct}%**. {advice}"

    return (
        f"### சாகுபடி செலவு மதிப்பீடு - {district} மாவட்டத்தில் {crop}\n\n"
        f"**{area:g} ஏக்கர்** பரப்பளவில் **{crop}** பயிரிட மதிப்பிடப்பட்ட முழு பருவ செலவு கீழே உள்ளது.{wage_note}\n\n"
        + "\n".join(lines)
        + f"\n\n**மொத்த முதலீடு:** ரூ.{total_lo:,} முதல் ரூ.{total_hi:,} வரை.\n\n"
        f"**ஏக்கருக்கு செலவு:** ரூ.{cpa_lo:,} முதல் ரூ.{cpa_hi:,} வரை."
        + biggest
        + "\n\n*இவை திட்டமிட உதவும் மதிப்பீடுகள். உண்மையான செலவு உள்ளீட்டு விலை, நில அளவு, கூலி நிலை மற்றும் உள்ளூர் சந்தை நிலைமையைப் பொறுத்து மாறலாம்.*"
    )


def _format_tamil_wage_info(result: dict) -> str | None:
    data = (result.get("data") or {}).get("wage_data") or {}
    wages = data.get("wages") or {}
    if not wages:
        return None
    district = _ta(data.get("district") or (result.get("memory") or {}).get("district") or "")
    year = data.get("year", "")
    label_map = {
        "Sowers Pluckers Men": "விதைப்பு/பறிப்பு - ஆண்",
        "Sowers Pluckers Women": "விதைப்பு/பறிப்பு - பெண்",
        "Transplanters Weeders Men": "நடவு/களை எடுப்பு - ஆண்",
        "Transplanters Weeders Women": "நடவு/களை எடுப்பு - பெண்",
        "Reapers Harvesters Men": "அறுவடை - ஆண்",
        "Reapers Harvesters Women": "அறுவடை - பெண்",
        "Other Operations Men": "மற்ற பணிகள் - ஆண்",
        "Other Operations Women": "மற்ற பணிகள் - பெண்",
        "Tractor Driver Men": "டிராக்டர் ஓட்டுநர்",
    }
    lines = ["| வேலை வகை | தின கூலி |", "|----------|----------|"]
    for key, value in wages.items():
        wage_value = str(value).replace("₹", "ரூ.").replace("/day", "/நாள்")
        lines.append(f"| {label_map.get(key, key)} | {wage_value} |")
    return (
        f"### வேளாண்மை கூலி விவரம் - {district}\n\n"
        f"**ஆண்டு:** {year}\n\n"
        + "\n".join(lines)
        + "\n\n*கூலி விவரம் மாவட்டத் தரவை அடிப்படையாகக் கொண்டது. வேலை வகை, பருவம் மற்றும் உள்ளூர் தேவைப் பொறுத்து மாறலாம்.*"
    )


def _format_tamil_yield_trend(result: dict) -> str | None:
    data = (result.get("data") or {}).get("yield_trend_data") or {}
    trend = data.get("trend") or []
    if not trend:
        return None
    district = _ta(data.get("district") or (result.get("memory") or {}).get("district") or "")
    crop = _ta(data.get("crop") or (result.get("memory") or {}).get("crop") or "")
    lines = ["| ஆண்டு | சராசரி மகசூல் (டன்/ஹெக்டேர்) |", "|------|------------------------------|"]
    for row in trend[-10:]:
        lines.append(f"| {int(row.get('year'))} | {row.get('avg_yield_t_ha')} |")
    return (
        f"### மகசூல் போக்கு - {district} மாவட்டத்தில் {crop}\n\n"
        f"**சராசரி மகசூல்:** {data.get('avg_yield_t_ha')} டன்/ஹெக்டேர்.\n\n"
        f"**சிறந்த பதிவு:** {data.get('best_year')} ஆம் ஆண்டில் {data.get('best_yield_t_ha')} டன்/ஹெக்டேர்.\n\n"
        + "\n".join(lines)
        + "\n\n*இது வரலாற்று பதிவுகளின் அடிப்படையில் உள்ளது. நடப்பு பருவ மழை, பாசனம் மற்றும் வயல் நிலையை சேர்த்து முடிவு செய்யவும்.*"
    )


def _format_tamil_best_districts(result: dict) -> str | None:
    data = (result.get("data") or {}).get("best_district_data") or {}
    rows = data.get("districts") or []
    if not rows:
        return None
    crop = _ta(data.get("crop") or (result.get("memory") or {}).get("crop") or "")
    lines = ["| வரிசை | மாவட்டம் | சராசரி மகசூல் | சராசரி பரப்பளவு | பருவம் | மண் |", "|------|----------|---------------|----------------|--------|-----|"]
    for idx, row in enumerate(rows, 1):
        lines.append(
            f"| #{idx} | {_ta(row.get('district'))} | {row.get('avg_yield')} டன்/ஹெக்டேர் | {row.get('avg_area_ha', 0):,} ஹெக்டேர் | {_ta(row.get('common_season'))} | {_ta(row.get('common_soil'))} |"
        )
    top = rows[0]
    return (
        f"### {crop} பயிருக்கு சிறந்த மாவட்டங்கள்\n\n"
        f"வரலாற்று மகசூல், சாகுபடி பரப்பளவு மற்றும் பதிவுகளின் நிலைத்தன்மை அடிப்படையில் **{_ta(top.get('district'))}** முதல் இடத்தில் உள்ளது.\n\n"
        + "\n".join(lines)
        + "\n\n*இறுதி தேர்வில் தற்போதைய நீர் கிடைப்பாடு, சந்தை விலை மற்றும் உள்ளூர் வயல் நிலைமைகளையும் பார்க்கவும்.*"
    )


def _format_tamil_whatif(result: dict) -> str | None:
    data = (result.get("data") or {}).get("whatif_data") or {}
    baseline = data.get("baseline") or {}
    modified = data.get("modified") or {}
    if not baseline or not modified:
        return None
    district = _ta(data.get("district") or (result.get("memory") or {}).get("district") or "")
    crop = _ta(data.get("crop") or (result.get("memory") or {}).get("crop") or "")
    changes = data.get("changes_applied") or []
    changes_ta = _translate_same_template_to_tamil(", ".join(changes)) if changes else "மாற்றம் இல்லை"
    changes_ta = changes_ta.replace("reduced by", "குறைக்கப்பட்டது").replace("increased by", "அதிகரிக்கப்பட்டது")
    delta = data.get("delta", 0)
    irrigation_before = round(float(baseline.get("irrigation_pct", 0)), 1)
    irrigation_after = round(float(modified.get("irrigation_pct", 0)), 1)
    return (
        f"### என்ன ஆகும்? சோதனை - {district} மாவட்டத்தில் {crop}\n\n"
        f"**சூழ்நிலை:** {changes_ta}\n\n"
        "| நிலை | மதிப்பெண் | நிலை விளக்கம் |\n"
        "|------|-----------|---------------|\n"
        f"| தற்போதைய நிலை | {baseline.get('total_score')}/10 | {_ta(baseline.get('label'))} |\n"
        f"| மாற்றத்திற்குப் பிறகு | {modified.get('total_score')}/10 | {_ta(modified.get('label'))} |\n"
        f"| மாற்றம் | {delta} | - |\n\n"
        f"**நீர் கிடைப்பாடு:** {baseline.get('effective_water_mm')} மில்லிமீட்டர் → {modified.get('effective_water_mm')} மில்லிமீட்டர்.\n\n"
        f"**பாசன அளவு:** {irrigation_before}% → {irrigation_after}%.\n\n"
        f"**பரிந்துரை:** மதிப்பெண் குறைந்தால் பாசனம், மண் ஈரப்பதம் மற்றும் பூச்சி கண்காணிப்பை கவனமாக திட்டமிடவும்."
    )


def _translate_same_template_to_tamil(text: str) -> str:
    """Translate the generated English answer while preserving its Markdown layout."""
    if not text:
        return ""

    out = text

    def _ta_named(value: str) -> str:
        clean = re.sub(r"[*_`]", "", value or "").strip()
        return _ta(clean) or clean

    regex_map = [
        (r"What-If Simulation:\s*([A-Za-z ()/-]+) in ([A-Za-z ]+)", lambda m: f"என்ன ஆகும்? சோதனை: {_ta_named(m.group(2))} மாவட்டத்தில் {_ta_named(m.group(1))}"),
        (r"Suitability Analysis\s*.?\s*([A-Za-z ()/-]+) in ([A-Za-z ]+)", lambda m: f"பொருத்த மதிப்பீடு - {_ta_named(m.group(2))} மாவட்டத்தில் {_ta_named(m.group(1))}"),
        (r"Best Districts For\s+([A-Za-z ()/-]+)", lambda m: f"{_ta_named(m.group(1))} பயிருக்கு சிறந்த மாவட்டங்கள்"),
        (r"Vanakkam! I'm your Smart Farming AI for Tamil Nadu\.", "வணக்கம்! நான் தமிழ்நாட்டுக்கான உங்கள் ஸ்மார்ட் வேளாண்மை AI உதவியாளர்."),
        (r"Based on the agricultural data I have for ([^,]+),", lambda m: f"{_ta_named(m.group(1))} பற்றிய வேளாண்மை தரவைப் பார்க்கும்போது,"),
        (r"Looking at the historical records for ([^,]+),", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தின் வரலாற்று பதிவுகளைப் பார்க்கும்போது,"),
        (r"From what our datasets tell us about ([^,]+),", lambda m: f"{_ta_named(m.group(1))} பற்றிய தரவுகளின் அடிப்படையில்,"),
        (r"After analysing ([^']+)'s agricultural profile,", lambda m: f"{_ta_named(m.group(1))} வேளாண்மை சுயவிவரத்தை ஆய்வு செய்தபோது,"),
        (r"The data for ([^ ]+) paints an interesting picture .", lambda m: f"{_ta_named(m.group(1))} பற்றிய தரவு ஒரு முக்கியமான நிலையை காட்டுகிறது."),
        (r"the rainfall pattern falls in the \*\*([^*]+)\*\* category,\s+averaging \*\*([^*]+)\*\* over the ([^.]+) period\.", lambda m: f"மழை முறை **{m.group(1)}** வகையில் உள்ளது; {m.group(3)} காலத்தில் சராசரியாக **{m.group(2)}** பதிவாகியுள்ளது."),
        (r"This puts it among the wetter districts of Tamil Nadu, making it well-suited for water-intensive crops like rice and sugarcane\.", "இதனால் இது தமிழ்நாட்டின் அதிக மழை பெறும் மாவட்டங்களில் ஒன்றாகும்; நெல் மற்றும் கரும்பு போன்ற நீர் அதிகம் தேவைப்படும் பயிர்களுக்கு இது பொருத்தமானது."),
        (r"This is a comfortable range for most Tamil Nadu crops .+?minimal irrigation dependency\.", "இது தமிழ்நாட்டின் பெரும்பாலான பயிர்களுக்கு ஏற்ற மழை அளவு; குறைந்த கூடுதல் பாசனத்துடன் சாகுபடி செய்ய உதவும்."),
        (r"Farmers here typically rely on irrigation to supplement rain, especially for water-intensive crops like paddy and sugarcane\.", "இங்கு விவசாயிகள் மழைக்கு கூடுதலாக பாசனத்தை நம்புகிறார்கள், குறிப்பாக நெல் மற்றும் கரும்பு போன்ற நீர் அதிகம் தேவைப்படும் பயிர்களுக்கு."),
        (r"Water management is critical in this district\. Drought-tolerant crops like jowar, bajra, and millets are recommended for rain-fed farming\.", "இந்த மாவட்டத்தில் நீர் மேலாண்மை மிகவும் முக்கியம். மழை சார்ந்த சாகுபடிக்கு சோளம், கம்பு மற்றும் சிறுதானியங்கள் போன்ற வறட்சியை தாங்கும் பயிர்கள் பரிந்துரைக்கப்படுகின்றன."),
        (r"The \*\*([^*]+)\*\* is the dominant rainy season, contributing \*\*([^*]+)\*\* .+?roughly ([0-9]+)% of the annual total\.", lambda m: f"**{_ta_named(m.group(1))}** முக்கிய மழைக்காலமாக உள்ளது; இது **{m.group(2)}** அளவு மழை தருகிறது, ஆண்டு மொத்தத்தின் சுமார் {m.group(3)}%."),
        (r"The ([A-Za-z ]+) brings in \*\*([^*]+)\*\*, which is still significant for the post-kharif season crops\.", lambda m: f"{_ta_named(m.group(1))} **{m.group(2)}** அளவு மழை தருகிறது; இது காரிஃப் பிந்தைய பருவப் பயிர்களுக்கு இன்னும் முக்கியமானது."),
        (r"The ([A-Za-z ]+) brings in \*\*([^*]+)\*\*, which is relatively modest, so post-monsoon crops need supplemental irrigation\.", lambda m: f"{_ta_named(m.group(1))} **{m.group(2)}** அளவு மழை தருகிறது; இது குறைவானது என்பதால் மழைக்காலத்திற்குப் பிறகான பயிர்களுக்கு கூடுதல் பாசனம் தேவை."),
        (r"The hot weather season \(March.?May\) contributes about \*\*([^*]+)\*\* of pre-monsoon showers, which helps in early Kharif land preparation\.", lambda m: f"வெப்பமான காலமான மார்ச்-மே மாதங்களில் மழைக்காலத்திற்கு முன் சுமார் **{m.group(1)}** மழை கிடைக்கிறது; இது ஆரம்ப காரிஃப் நிலத் தயாரிப்புக்கு உதவும்."),
        (r"The hot weather season \(March.?May\) contributes about \*\*([^*]+)\*\* of pre-monsoon showers, though this is minimal and farmers should plan for dry spells in spring\.", lambda m: f"வெப்பமான காலமான மார்ச்-மே மாதங்களில் மழைக்காலத்திற்கு முன் சுமார் **{m.group(1)}** மழை கிடைக்கிறது; இது குறைவானதால் விவசாயிகள் வறண்ட இடைவெளிகளுக்குத் திட்டமிட வேண்டும்."),
        (r"(What's particularly noteworthy is that|Interestingly,|It's also worth mentioning that|On top of that,|Another key insight is that|Digging deeper into the data,) looking at recent years, the rainfall trend appears to be \*\*([^*]+)\*\*\.", lambda m: f"சமீபத்திய ஆண்டுகளைப் பார்க்கும்போது, மழை போக்கு **{m.group(2)}** நிலையில் உள்ளது."),
        (r"The last three recorded years averaged \*\*([^*]+)\*\*, suggesting improving water availability\.", lambda m: f"கடைசி மூன்று பதிவு செய்யப்பட்ட ஆண்டுகளில் சராசரி **{m.group(1)}**; இது நீர் கிடைப்பில் முன்னேற்றம் இருப்பதை காட்டுகிறது."),
        (r"The last three recorded years averaged \*\*([^*]+)\*\*, which calls for more careful water conservation planning\.", lambda m: f"கடைசி மூன்று பதிவு செய்யப்பட்ட ஆண்டுகளில் சராசரி **{m.group(1)}**; எனவே நீர் சேமிப்பு திட்டமிடல் மேலும் கவனமாக இருக்க வேண்டும்."),
        (r"Keep in mind this is based on historical trends up to 2019\.", "இது 2019 வரை உள்ள வரலாற்று போக்குகளின் அடிப்படையில் அமைந்தது என்பதை நினைவில் கொள்ளவும்."),
        (r"As always, local conditions on the ground can vary\.", "எப்போதும் போல, உள்ளூர் வயல் நிலைமைகள் மாறுபடலாம்."),
        (r"Note that on-farm conditions, pest pressure, and market prices should also factor into your final decision\.", "வயல் நிலை, பூச்சி அழுத்தம் மற்றும் சந்தை விலையும் இறுதி முடிவில் சேர்த்து பார்க்கப்பட வேண்டும்."),
        (r"This analysis draws from 20 years of district-level records .+?validate with local agricultural officers\.", "இந்த பகுப்பாய்வு 20 ஆண்டுகளுக்கான மாவட்ட அளவிலான பதிவுகளை அடிப்படையாகக் கொண்டது; உள்ளூர் வேளாண்மை அலுவலர்களுடன் சரிபார்க்கவும்."),
        (r"when looking at overall crop performance,", "மொத்த பயிர் செயல்திறனைப் பார்க்கும்போது,"),
        (r"specifically for \*\*([^*]+)\*\* during the \*\*([^*]+)\*\* season,", lambda m: f"குறிப்பாக **{_ta_named(m.group(1))}** மண்ணில் **{_ta_named(m.group(2))}** பருவத்தில்,"),
        (r"when it comes to \*\*([^*]+)\*\*,", lambda m: f"**{_ta_named(m.group(1))}** மண்ணைப் பார்க்கும்போது,"),
        (r"focusing on the \*\*([^*]+)\*\* season,", lambda m: f"**{_ta_named(m.group(1))}** பருவத்தைப் பார்க்கும்போது,"),
        (r"\*\*([^*]+)\*\* stands out as the strongest overall option, combining good historical yield, meaningful cultivation area, and consistent presence in the records\.", lambda m: f"**{_ta_named(m.group(1))}** நல்ல வரலாற்று மகசூல், குறிப்பிடத்தக்க சாகுபடி பரப்பளவு மற்றும் பதிவுகளில் தொடர்ந்து காணப்படுவதால் சிறந்த தேர்வாக உள்ளது."),
        (r"In ([^,]+), it averages \*\*([^*]+)\*\* on \*\*([^*]+)\*\* during the \*\*([^*]+)\*\* season, with about \*\*([^*]+)\*\* cultivated on average\.", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தில் இது **{m.group(2)}** சராசரி மகசூல் தருகிறது; **{_ta_named(m.group(3))}** மண்ணில் **{_ta_named(m.group(4))}** பருவத்தில் சராசரியாக **{m.group(5)}** சாகுபடி செய்யப்படுகிறது."),
        (r"(What's particularly noteworthy is that|Interestingly,|It's also worth mentioning that|On top of that,|Another key insight is that|Digging deeper into the data,) \*\*([^*]+)\*\* is another strong choice, with an average yield of \*\*([^*]+)\*\* and around \*\*([^*]+)\*\* cultivated\.", lambda m: f"**{_ta_named(m.group(2))}** மற்றொரு வலுவான தேர்வு; சராசரி மகசூல் **{m.group(3)}**, சாகுபடி பரப்பளவு சுமார் **{m.group(4)}**."),
        (r"That makes it a practical alternative for both commercial farming and crop rotation\.", "இதனால் இது வணிக சாகுபடிக்கும் பயிர் சுழற்சிக்கும் பயனுள்ள மாற்று தேர்வாக இருக்கும்."),
        (r"Other promising crops in this environment include (.+?)\.", lambda m: f"இந்த சூழலில் மற்ற நம்பகமான பயிர்கள்: {m.group(1)}."),
        (r"From a rainfall standpoint, ([^ ]+) receives an average of \*\*([^*]+)\*\*, with the ([A-Za-z ()/-]+) being the dominant rain source at \*\*([^*]+)\*\*\.", lambda m: f"மழை அடிப்படையில், {_ta_named(m.group(1))} மாவட்டம் சராசரியாக **{m.group(2)}** பெறுகிறது; முக்கிய மழை ஆதாரம் {_ta_named(m.group(3))}, அதன் அளவு **{m.group(4)}**."),
        (r"Irrigation coverage in ([^ ]+) is \*\*([^*]+)\*\* of net sown area, with \*\*([^*]+)\*\* as the primary water source\.", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தில் நிகர விதைப்பு பரப்பளவில் **{m.group(2)}** பாசன வசதி உள்ளது; முக்கிய நீர் ஆதாரம் **{_ta_named(m.group(3))}**."),
        (r"This supports more flexible crop choices\.", "இது பல வகை பயிர் தேர்வுகளுக்கு உதவுகிறது."),
        (r"So drought-tolerant or rainfall-aligned crops are safer choices\.", "எனவே வறட்சியைத் தாங்கும் அல்லது மழைக்கு ஏற்ற பயிர்கள் பாதுகாப்பான தேர்வுகள்."),
        (r"Taking everything into account,|Putting it all together,|In summary,|My recommendation, based on all this data, is that|All things considered,", "மொத்தத்தில்,"),
        (r"if you're farming in ([^,]+), starting with \*\*([^*]+)\*\* and \*\*([^*]+)\*\* would be a sensible data-backed choice\.", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தில் விவசாயம் செய்தால் **{_ta_named(m.group(2))}** மற்றும் **{_ta_named(m.group(3))}** ஆகியவற்றில் தொடங்குவது தரவு அடிப்படையில் நல்ல தேர்வாகும்."),
        (r"Final selection should still consider current market price, water availability, and local field conditions\.", "இறுதி தேர்வில் தற்போதைய சந்தை விலை, நீர் கிடைப்பாடு மற்றும் உள்ளூர் வயல் நிலைமைகளையும் கருத்தில் கொள்ள வேண்டும்."),
        (r"Yield values in the table are normalized to \*\*([^*]+)\*\*\. Coconut nuts are converted at 1\.2 kg/nut; bale crops are converted at 170 kg/bale\.", lambda m: f"அட்டவணையில் உள்ள மகசூல் மதிப்புகள் **{m.group(1)}** ஆக ஒரே அளவுக்கு மாற்றப்பட்டுள்ளன. தென்னை எண்ணிக்கை 1.2 கிலோ/காய் அடிப்படையிலும், பேல் பயிர்கள் 170 கிலோ/பேல் அடிப்படையிலும் மாற்றப்பட்டுள்ளன."),
        (r"This score combines yield performance, rainfall alignment, soil compatibility, irrigation coverage, and historical presence\.", "இந்த மதிப்பெண் மகசூல் செயல்திறன், மழை பொருத்தம், மண் பொருத்தம், பாசன வசதி மற்றும் வரலாற்று பதிவுகளை இணைத்து கணக்கிடப்படுகிறது."),
        (r"\*\*Water Analysis:\*\* District receives \*\*([^*]+)\*\* per year versus crop need of \*\*([^*]+)\*\* . well-covered by rainfall\.", lambda m: f"**நீர் பகுப்பாய்வு:** மாவட்டம் ஆண்டுக்கு **{m.group(1)}** பெறுகிறது; பயிரின் தேவை **{m.group(2)}**. மழை மூலம் நன்றாகப் பூர்த்தியாகிறது."),
        (r"\*\*Water Analysis:\*\* District receives \*\*([^*]+)\*\* per year versus crop need of \*\*([^*]+)\*\* . a deficit of \*\*([^*]+)\*\* means irrigation support is important\.", lambda m: f"**நீர் பகுப்பாய்வு:** மாவட்டம் ஆண்டுக்கு **{m.group(1)}** பெறுகிறது; பயிரின் தேவை **{m.group(2)}**. **{m.group(3)}** பற்றாக்குறை இருப்பதால் பாசன உதவி முக்கியம்."),
        (r"\*\*Season considered:\*\* All seasons\.", "**கருதப்பட்ட பருவம்:** அனைத்து பருவங்களும்."),
        (r"\*\*Irrigation coverage used in scoring:\*\* ([^.]+)\.", lambda m: f"**மதிப்பீட்டில் பயன்படுத்திய பாசன வசதி:** {m.group(1)}."),
        (r"Try a scenario test next: \*\"What if irrigation improved in ([^ ]+) for ([^\"]+)\"\*", lambda m: f"அடுத்ததாக ஒரு சூழ்நிலை சோதனை முயற்சிக்கவும்: *\"{_ta_named(m.group(1))} மாவட்டத்தில் {_ta_named(m.group(2))} பயிருக்கு பாசனம் மேம்பட்டால் என்ன ஆகும்?\"*"),
        (r"\*\*Water Analysis:\*\* District receives \*\*([^*]+)\*\* annually versus crop need of \*\*([^*]+)\*\* .+? well-covered by rainfall\.", lambda m: f"**நீர் பகுப்பாய்வு:** மாவட்டம் ஆண்டுக்கு **{m.group(1)}** பெறுகிறது; பயிரின் தேவை **{m.group(2)}**. மழை மூலம் நன்றாக பூர்த்தியாகிறது."),
        (r"\*\*Water Analysis:\*\* District receives \*\*([^*]+)\*\* annually versus crop need of \*\*([^*]+)\*\* .+? a deficit of \*\*([^*]+)\*\* means irrigation support is important\.", lambda m: f"**நீர் பகுப்பாய்வு:** மாவட்டம் ஆண்டுக்கு **{m.group(1)}** பெறுகிறது; பயிரின் தேவை **{m.group(2)}**. **{m.group(3)}** பற்றாக்குறை இருப்பதால் பாசன உதவி முக்கியம்."),
        (r"Use nitrogen in split doses, with phosphorus and potash applied near planting based on soil test results\.", "நைட்ரஜனைப் பிரிக்கப்பட்ட அளவுகளில் இடவும்; மண் பரிசோதனை முடிவின் அடிப்படையில் நடவு நேரத்தில் பாஸ்பரஸ் மற்றும் பொட்டாஷ் இடவும்."),
        (r"Farmyard manure, green manure, or compost before transplanting improves soil structure and nutrient holding\.", "நடவு முன் தொழு உரம், பச்சை உரம் அல்லது கம்போஸ்ட் இடுவது மண் அமைப்பையும் சத்துத் தாங்கும் திறனையும் மேம்படுத்தும்."),
        (r"Avoid heavy nitrogen application when rainfall is intense or drainage is poor\.", "மழை அதிகமாக இருக்கும்போது அல்லது வடிகால் பலவீனமாக இருக்கும்போது அதிக நைட்ரஜன் இடுவதைத் தவிர்க்கவும்."),
        (r"Estimated fertilizer input cost is roughly \*\*([^*]+)\*\*, depending on current input prices and soil condition\.", lambda m: f"தற்போதைய உள்ளீட்டு விலை மற்றும் மண் நிலைக்கு ஏற்ப உர செலவு சுமார் **{m.group(1)}** ஆகும்."),
        (r"Use this as planning guidance only\. A local soil test is still the best way to decide exact fertilizer quantity\.", "இதை திட்டமிடும் வழிகாட்டுதலாக மட்டும் பயன்படுத்தவும். சரியான உர அளவைத் தீர்மானிக்க உள்ளூர் மண் பரிசோதனையே சிறந்த வழி."),
        (r"Let me give you a pest risk assessment for \*\*([^*]+)\*\* based on its historical rainfall and climate profile\.", lambda m: f"**{_ta_named(m.group(1))}** மாவட்டத்தின் வரலாற்று மழை மற்றும் காலநிலை அடிப்படையில் பூச்சி அபாய மதிப்பீடு இதோ."),
        (r"The district receives about \*\*([^*]+)\*\*, with the Southwest Monsoon contributing \*\*([^*]+)\*\* and the Northeast Monsoon \*\*([^*]+)\*\*\.", lambda m: f"மாவட்டம் சுமார் **{m.group(1)}** மழை பெறுகிறது; தென்மேற்கு பருவமழை **{m.group(2)}**, வடகிழக்கு பருவமழை **{m.group(3)}** அளவு பங்களிக்கின்றன."),
        (r"High monsoon intensity creates humid conditions that are particularly favourable for fungal diseases and certain insect pests\.", "அதிக பருவமழை ஈரமான சூழலை உருவாக்குகிறது; இது பூஞ்சை நோய்கள் மற்றும் சில பூச்சிகளுக்கு சாதகமாக இருக்கும்."),
        (r"The moderate rainfall pattern limits some moisture-dependent pests, though dry spells can trigger a different set of risks\.", "மிதமான மழை சில ஈரப்பதம் சார்ந்த பூச்சிகளை கட்டுப்படுத்தினாலும், வறண்ட இடைவெளிகள் வேறு அபாயங்களை உருவாக்கலாம்."),
        (r"(What's particularly noteworthy is that|Interestingly,|It's also worth mentioning that|On top of that,|Another key insight is that|Digging deeper into the data,) Tamil Nadu's statewide rainfall deviation for this district's period is \*\*([^*]+)\*\* from normal\.", lambda m: f"இந்த மாவட்டத்தின் காலப்பகுதியில் தமிழ்நாடு மாநில மழை இயல்பை விட **{m.group(2)}** மாறுபட்டுள்ளது."),
        (r"A positive deviation means surplus water .+? watch for waterlogging and fungal outbreaks\.", "நேர்மறை மாறுபாடு கூடுதல் நீரை குறிக்கிறது; நீர் தேக்கம் மற்றும் பூஞ்சை நோய் பரவலை கவனிக்கவும்."),
        (r"A negative deviation indicates drier than normal conditions .+? water stress in crops can make them more vulnerable to sucking pests\.", "எதிர்மறை மாறுபாடு இயல்பை விட வறண்ட நிலையை குறிக்கிறது; நீர் அழுத்தம் பயிர்களை சாறு உறிஞ்சும் பூச்சிகளுக்கு எளிதாக பாதிக்கக்கூடும்."),
        (r"Rainfall is near normal levels, so standard seasonal pest management should suffice\.", "மழை இயல்பான அளவுக்கு அருகில் உள்ளது; வழக்கமான பருவகால பூச்சி மேலாண்மை போதுமானதாக இருக்கும்."),
        (r"\*\*General advisory for Tamil Nadu:\*\* Integrate pest management \(IPM\) is always recommended .+? extremely useful\.", "**தமிழ்நாட்டுக்கான பொது ஆலோசனை:** ஒருங்கிணைந்த பூச்சி மேலாண்மை (IPM) எப்போதும் பரிந்துரைக்கப்படுகிறது. உயிரியல் கட்டுப்பாடு, நோய் எதிர்ப்பு வகைகள் மற்றும் அவசியமானபோது மட்டும் ரசாயன மருந்துகளை பயன்படுத்துவது நல்லது. மாவட்ட வாரியான பூச்சி காலண்டர்களையும் பார்க்கவும்."),
        (r"Crops most at risk: \*\*([^*]+)\*\*\.", lambda m: f"அதிக அபாயத்தில் உள்ள பயிர்கள்: **{m.group(1)}**."),
        (r"Recommended action:", "பரிந்துரைக்கப்படும் நடவடிக்கை:"),
        (r"Let me give you a comprehensive agricultural snapshot of \*\*([^*]+)\*\*\.", lambda m: f"**{_ta_named(m.group(1))}** மாவட்டத்தின் முழுமையான வேளாண்மை சுருக்கம் இதோ."),
        (r"\*\*([^*]+)\*\* covers a total geographical area of \*\*([^*]+)\*\*, with \*\*([^*]+)\*\* under active cultivation\.", lambda m: f"**{_ta_named(m.group(1))}** மாவட்டத்தின் மொத்த புவியியல் பரப்பளவு **{m.group(2)}**; இதில் **{m.group(3)}** செயலில் உள்ள சாகுபடி பரப்பளவு."),
        (r"Of this, \*\*([^*]+)\*\* has irrigation access . giving us a broad picture of the district's farming intensity\.", lambda m: f"இதில் **{m.group(1)}** பாசன வசதி கொண்டது; இது மாவட்டத்தின் சாகுபடி தீவிரத்தை காட்டுகிறது."),
        (r"The (?:main|dominant) soil type is \*\*([^*]+)\*\*, which shapes the crop selection significantly\.", lambda m: f"முக்கிய மண் வகை **{_ta_named(m.group(1))}**; இது பயிர் தேர்வில் பெரிய தாக்கம் செலுத்துகிறது."),
        (r"Alluvial soils are extremely fertile and support a wide range of crops . from rice and sugarcane to banana and vegetables\.", "வண்டல் மண் மிகவும் வளமானது; நெல், கரும்பு, வாழை மற்றும் காய்கறிகள் உள்ளிட்ட பல பயிர்களுக்கு ஏற்றது."),
        (r"Based on \*\*([^*]+)\*\* of records, the highest-yielding crops in ([^ ]+) are (.+?)\.", lambda m: f"**{m.group(1)}** பதிவுகளின் அடிப்படையில், {_ta_named(m.group(2))} மாவட்டத்தில் அதிக மகசூல் தரும் பயிர்கள் {m.group(3)}."),
        (r"These crops have consistently outperformed in yield and area coverage\.", "இந்த பயிர்கள் மகசூல் மற்றும் பரப்பளவு அடிப்படையில் தொடர்ந்து சிறப்பாக செயல்பட்டுள்ளன."),
        (r"The \*\*([^*]+)\*\* season dominates agriculture here in terms of number of crop entries, reflecting the agroclimate's natural alignment with year-round cultivation\.", lambda m: f"**{_ta_named(m.group(1))}** பருவம் பயிர் பதிவுகளின் எண்ணிக்கையில் அதிகமாக உள்ளது; இது ஆண்டு முழுவதும் சாகுபடிக்கு உள்ளூர் காலநிலை ஏற்றதாக இருப்பதை காட்டுகிறது."),
        (r"The \*\*([^*]+)\*\* season dominates agriculture here in terms of number of crop entries, reflecting the agroclimate's natural alignment with the SW monsoon\.", lambda m: f"**{_ta_named(m.group(1))}** பருவம் பயிர் பதிவுகளின் எண்ணிக்கையில் அதிகமாக உள்ளது; இது தென்மேற்கு பருவமழைக்கு உள்ளூர் காலநிலை ஏற்றதாக இருப்பதை காட்டுகிறது."),
        (r"The \*\*([^*]+)\*\* season dominates agriculture here in terms of number of crop entries, reflecting the agroclimate's natural alignment with the NE monsoon and winter cultivation patterns\.", lambda m: f"**{_ta_named(m.group(1))}** பருவம் பயிர் பதிவுகளின் எண்ணிக்கையில் அதிகமாக உள்ளது; இது வடகிழக்கு பருவமழை மற்றும் குளிர்கால சாகுபடிக்கு உள்ளூர் காலநிலை ஏற்றதாக இருப்பதை காட்டுகிறது."),
        (r"Rainfall averages \*\*([^*]+)\*\* .+? ample for water-intensive crops\.", lambda m: f"மழை சராசரி **{m.group(1)}**; நீர் அதிகம் தேவைப்படும் பயிர்களுக்கு இது போதுமானது."),
        (r"Rainfall averages \*\*([^*]+)\*\* .+? sufficient for most crops with proper water management\.", lambda m: f"மழை சராசரி **{m.group(1)}**; சரியான நீர் மேலாண்மையுடன் பெரும்பாலான பயிர்களுக்கு இது போதுமானது."),
        (r"Rainfall averages \*\*([^*]+)\*\* .+? on the lower side, making irrigation and water harvesting critical\.", lambda m: f"மழை சராசரி **{m.group(1)}**; இது குறைவானதால் பாசனமும் நீர் சேகரிப்பும் மிகவும் முக்கியம்."),
        (r"([^ ]+) is an agriculturally rich district with strong yield potential across multiple crop categories\.", lambda m: f"{_ta_named(m.group(1))} வேளாண்மையில் வளமான மாவட்டம்; பல பயிர் வகைகளில் நல்ல மகசூல் திறன் உள்ளது."),
        (r"([^ ]+) is a productive agricultural district with specific strengths in certain crop types\.", lambda m: f"{_ta_named(m.group(1))} உற்பத்தி திறன் கொண்ட வேளாண்மை மாவட்டம்; சில பயிர் வகைகளில் குறிப்பிட்ட பலம் உள்ளது."),
        (r"For detailed farm planning, I'd recommend following up with rainfall queries, irrigation profiles, and specific crop recommendations using the options available\.", "விரிவான பண்ணை திட்டமிடலுக்கு, மழை தகவல், பாசன விவரம் மற்றும் குறிப்பிட்ட பயிர் பரிந்துரைகளை தொடர்ந்து பார்க்கலாம்."),
        (r"([^ ]+) has \*\*excellent irrigation infrastructure\*\*, with \*\*([^*]+)\*\* being irrigated\.", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தில் **மிகச் சிறந்த பாசன வசதி** உள்ளது; **{m.group(2)}** பாசன வசதி கொண்டது."),
        (r"([^ ]+) has \*\*moderate irrigation coverage\*\*, with \*\*([^*]+)\*\* being irrigated\.", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தில் **மிதமான பாசன வசதி** உள்ளது; **{m.group(2)}** பாசன வசதி கொண்டது."),
        (r"([^ ]+) has \*\*limited irrigation coverage\*\*, with \*\*([^*]+)\*\* being irrigated\.", lambda m: f"{_ta_named(m.group(1))} மாவட்டத்தில் **குறைந்த பாசன வசதி** உள்ளது; **{m.group(2)}** பாசன வசதி கொண்டது."),
        (r"Out of ([^,]+) under cultivation, ([^.]+) have assured irrigation access\.", lambda m: f"சாகுபடியில் உள்ள {m.group(1)} பரப்பளவில், {m.group(2)} உறுதியான பாசன வசதி கொண்டது."),
        (r"This district has very good water access and can support intensive double or triple cropping systems\.", "இந்த மாவட்டத்தில் நீர் கிடைப்பாடு நல்லது; தீவிர இரட்டை அல்லது மும்மை பயிரிடல் முறைகளை ஆதரிக்க முடியும்."),
        (r"The primary water source is \*\*([^*]+)\*\* \(([^)]+)\), which is typical for districts with strong canal network from major rivers\.", lambda m: f"முக்கிய நீர் ஆதாரம் **{_ta_named(m.group(1))}** ({m.group(2)}); பெரிய ஆறுகளின் கால்வாய் வலையமைப்பு உள்ள மாவட்டங்களில் இது பொதுவானது."),
        (r"Other sources include (.+?) . reflecting a diversified water access strategy\.", lambda m: f"மற்ற நீர் ஆதாரங்கள்: {m.group(1)}. இது பலவகை நீர் அணுகல் முறையை காட்டுகிறது."),
        (r"Groundwater depth averages \*\*([^*]+)\*\* across the year, indicating deep groundwater levels warranting conservation efforts\.", lambda m: f"ஆண்டு முழுவதும் நிலத்தடி நீர் ஆழம் சராசரியாக **{m.group(1)}**; ஆழமான நிலத்தடி நீரால் நீர் பாதுகாப்பு முயற்சிகள் அவசியம்."),
        (r"Depth of this level increases pumping costs . efficient irrigation methods like drip are increasingly important\.", "இந்த அளவிலான ஆழம் பம்பிங் செலவை அதிகரிக்கும்; சொட்டு பாசனம் போன்ற திறமையான முறைகள் மிகவும் முக்கியம்."),
    ]
    for pattern, replacement in regex_map:
        out = re.sub(pattern, replacement, out, flags=re.I | re.S)

    phrase_map = {
        "What-If Simulation": "என்ன ஆகும்? சோதனை",
        "Scenario Inputs": "சூழ்நிலை உள்ளீடுகள்",
        "Expected Result": "எதிர்பார்க்கப்படும் முடிவு",
        "Why This Happens": "இது ஏன் நடக்கிறது",
        "Recommended Action": "பரிந்துரைக்கப்படும் நடவடிக்கை",
        "Crop Recommendations": "பயிர் பரிந்துரைகள்",
        "Crop Recommendation": "பயிர் பரிந்துரை",
        "Rainfall Summary": "மழை சுருக்கம்",
        "Rainfall Information": "மழை தகவல்",
        "Pest Risk": "பூச்சி அபாயம்",
        "Fertilizer Recommendation": "உர பரிந்துரை",
        "Irrigation Information": "பாசன தகவல்",
        "District Overview": "மாவட்ட சுருக்கம்",
        "Yield Prediction": "மகசூல் கணிப்பு",
        "Yield Trend": "மகசூல் போக்கு",
        "Suitability Score": "பொருத்த மதிப்பெண்",
        "Planting Time": "நடவு காலம்",
        "Best Districts": "சிறந்த மாவட்டங்கள்",
        "Best Crops": "சிறந்த பயிர்கள்",
        "Active Context": "செயலில் உள்ள சூழல்",
        "Total cost": "மொத்த செலவு",
        "Expected yield impact": "எதிர்பார்க்கப்படும் மகசூல் தாக்கம்",
        "Pest risk change": "பூச்சி அபாய மாற்றம்",
        "rainfall change": "மழை மாற்றம்",
        "irrigation change": "பாசன மாற்றம்",
        "fertilizer change": "உர மாற்றம்",
        "temperature change": "வெப்பநிலை மாற்றம்",
        "pest intensity": "பூச்சி தீவிரம்",
        "soil moisture": "மண் ஈரப்பதம்",
        "market price": "சந்தை விலை",
        "cultivation cost": "சாகுபடி செலவு",
        "historical records": "வரலாற்று பதிவுகள்",
        "local conditions": "உள்ளூர் நிலைமைகள்",
        "Annual Rainfall": "ஆண்டு மழை",
        "Avg Yield": "சராசரி மகசூல்",
        "Avg Area": "சராசரி பரப்பளவு",
        "Common Season": "பொதுவான பருவம்",
        "Common Soil": "பொதுவான மண்",
        "Southwest Monsoon": "தென்மேற்கு பருவமழை",
        "Northeast Monsoon": "வடகிழக்கு பருவமழை",
        "very high rainfall": "மிக அதிக மழை",
        "moderate to high rainfall": "மிதமான முதல் அதிக மழை",
        "moderate rainfall": "மிதமான மழை",
        "relatively low rainfall": "குறைந்த மழை",
        "per year": "ஆண்டுக்கு",
        "annually": "ஆண்டுக்கு",
        "soil test": "மண் பரிசோதனை",
        "field monitoring": "வயல் கண்காணிப்பு",
        "integrated pest management": "ஒருங்கிணைந்த பூச்சி மேலாண்மை",
        "Yield may": "மகசூல்",
        "Pest pressure may": "பூச்சி அழுத்தம்",
        "under this scenario": "இந்த சூழ்நிலையில்",
        "stay nearly stable": "கிட்டத்தட்ட நிலையாக இருக்கும்",
        "Water availability is shaped by rainfall and irrigation together.": "நீர் கிடைப்பை மழையும் பாசனமும் சேர்ந்து நிர்ணயிக்கின்றன.",
        "Fertilizer helps only when moisture and pest pressure are manageable.": "ஈரப்பதமும் பூச்சி அழுத்தமும் கட்டுப்பாட்டில் இருந்தால் மட்டுமே உரம் நல்ல பலன் தரும்.",
        "Temperature stress and high pest intensity reduce the likely yield benefit.": "வெப்பநிலை அழுத்தமும் அதிக பூச்சி தீவிரமும் மகசூல் பலனை குறைக்கலாம்.",
        "Soil moisture around the middle range is usually safer than very dry or waterlogged conditions.": "மிக வறண்ட அல்லது நீர் தேங்கிய நிலையை விட நடுத்தர மண் ஈரப்பதம் பொதுவாக பாதுகாப்பானது.",
        "High pest pressure: inspect leaves twice weekly and avoid unnecessary irrigation.": "பூச்சி அழுத்தம் அதிகம்: வாரத்திற்கு இரண்டு முறை இலைகளைச் சரிபார்த்து தேவையற்ற பாசனத்தைத் தவிர்க்கவும்.",
        "Yield may drop: rebalance water, reduce stress, and consider staged fertilizer support.": "மகசூல் குறையலாம்: நீரை சமநிலைப்படுத்தி, அழுத்தத்தை குறைத்து, கட்டுப்படுத்தப்பட்ட கட்டங்களாக உரம் இடவும்.",
        "Scenario looks favorable: keep monitoring moisture and avoid over-fertilizing.": "சூழ்நிலை சாதகமாக உள்ளது: ஈரப்பதத்தை தொடர்ந்து கண்காணித்து அதிக உரமிடுவதைத் தவிர்க்கவும்.",
        "Scenario is stable: maintain current plan and monitor rainfall/pest signs.": "சூழ்நிலை நிலையாக உள்ளது: தற்போதைய திட்டத்தைத் தொடர்ந்தும் மழை மற்றும் பூச்சி அறிகுறிகளை கண்காணிக்கவும்.",
    }
    phrase_map.update({
        "Soil Analysis Result": "மண் பகுப்பாய்வு முடிவு",
        "Detected soil type": "கண்டறியப்பட்ட மண் வகை",
        "Characteristics": "பண்புகள்",
        "Best matching crops": "பொருத்தமான சிறந்த பயிர்கள்",
        "Typical characteristics for this soil type": "இந்த மண் வகைக்கான பொதுவான பண்புகள்",
        "I'll remember this soil type for the rest of this chat.": "இந்த உரையாடலின் மீதம் இந்த மண் வகையை நினைவில் வைத்துக் கொள்கிறேன்.",
        "Suitability Analysis": "பொருத்த மதிப்பீடு",
        "Factor": "காரணி",
        "Max": "அதிகபட்சம்",
        "TOTAL": "மொத்தம்",
        "Yield Performance": "மகசூல் செயல்திறன்",
        "Rainfall Alignment": "மழை பொருத்தம்",
        "Soil Compatibility": "மண் பொருத்தம்",
        "Irrigation Coverage": "பாசன வசதி",
        "Historical Presence": "வரலாற்று இருப்பு",
        "Water Analysis": "நீர் பகுப்பாய்வு",
        "Organic support": "இயற்கை உர ஆதரவு",
        "Important caution": "முக்கிய எச்சரிக்கை",
        "Irrigation Source": "பாசன ஆதாரம்",
        "Area Irrigated": "பாசன பரப்பளவு",
        "Canals": "கால்வாய்கள்",
        "Tube/Bore Wells": "குழாய்/போர் கிணறுகள்",
        "Open Wells": "திறந்த கிணறுகள்",
        "Other Sources": "மற்ற ஆதாரங்கள்",
        "All seasons": "அனைத்து பருவங்களும்",
        "Alluvial soils": "வண்டல் மண்",
        "net sown area": "நிகர விதைப்பு பரப்பளவு",
        "water-intensive": "நீர் அதிகம் தேவைப்படும்",
        "Very Good": "மிக நல்லது",
        "Below Average": "சராசரிக்கு கீழ்",
        "Excellent": "மிகச் சிறந்தது",
        "Moderate": "மிதமானது",
        "Poor": "பலவீனமானது",
        "per acre": "ஏக்கருக்கு",
        "Apply propiconazole fungicide; drain excess water; use resistant varieties.": "ப்ரோபிகோனசோல் பூஞ்சைக்கொல்லி பயன்படுத்தவும்; அதிக நீரை வடிகட்டவும்; நோய் எதிர்ப்பு வகைகளை பயன்படுத்தவும்.",
        "Ensure proper field drainage; apply mancozeb; monitor regularly in Oct-Dec.": "வயலில் நல்ல வடிகால் ஏற்பாடு செய்யவும்; மான்கோசெப் பயன்படுத்தவும்; அக்டோபர் முதல் டிசம்பர் வரை அடிக்கடி கண்காணிக்கவும்.",
        "Ensure proper field drainage; apply mancozeb; monitor regularly in Oct–Dec.": "வயலில் நல்ல வடிகால் ஏற்பாடு செய்யவும்; மான்கோசெப் பயன்படுத்தவும்; அக்டோபர் முதல் டிசம்பர் வரை அடிக்கடி கண்காணிக்கவும்.",
        "Spray neem oil or imidacloprid; maintain adequate soil moisture.": "வேப்பெண்ணெய் அல்லது இமிடாக்ளோபிரிட் தெளிக்கவும்; மண்ணில் போதுமான ஈரப்பதத்தை பராமரிக்கவும்.",
        "Install yellow sticky traps; use spinosad insecticide; irrigate frequently.": "மஞ்சள் ஒட்டும் வலைகளை அமைக்கவும்; ஸ்பைனோசாட் பூச்சிக்கொல்லி பயன்படுத்தவும்; அடிக்கடி பாசனம் செய்யவும்.",
        "Routine monitoring and preventive neem sprays recommended.": "தொடர்ந்து கண்காணிக்கவும்; முன்னெச்சரிக்கையாக வேப்பெண்ணெய் தெளிக்கவும்.",
    })
    for english, tamil in sorted(phrase_map.items(), key=lambda item: len(item[0]), reverse=True):
        out = re.sub(re.escape(english), tamil, out, flags=re.I)

    word_map = {
        "district": "மாவட்டம்",
        "crop": "பயிர்",
        "crops": "பயிர்கள்",
        "soil": "மண்",
        "season": "பருவம்",
        "month": "மாதம்",
        "rainfall": "மழை",
        "rain": "மழை",
        "irrigation": "பாசனம்",
        "fertilizer": "உரம்",
        "temperature": "வெப்பநிலை",
        "moisture": "ஈரப்பதம்",
        "yield": "மகசூல்",
        "profit": "லாபம்",
        "revenue": "வருவாய்",
        "cost": "செலவு",
        "risk": "அபாயம்",
        "pest": "பூச்சி",
        "pests": "பூச்சிகள்",
        "disease": "நோய்",
        "action": "நடவடிக்கை",
        "recommendation": "பரிந்துரை",
        "recommended": "பரிந்துரைக்கப்படும்",
        "suitable": "பொருத்தமான",
        "high": "அதிகம்",
        "medium": "மிதமான",
        "moderate": "மிதமான",
        "low": "குறைவு",
        "increase": "அதிகரிப்பு",
        "decrease": "குறைவு",
        "stable": "நிலையான",
        "good": "நல்ல",
        "poor": "பலவீனமான",
        "excellent": "மிகச் சிறந்த",
        "apply": "பயன்படுத்தவும்",
        "monitor": "கண்காணிக்கவும்",
        "avoid": "தவிர்க்கவும்",
        "use": "பயன்படுத்தவும்",
        "because": "ஏனெனில்",
        "and": "மற்றும்",
        "or": "அல்லது",
        "for": "க்கான",
        "in": "இல்",
        "with": "உடன்",
        "next": "அடுத்த",
        "days": "நாட்கள்",
        "hours": "மணிநேரங்கள்",
        "current": "தற்போதைய",
        "expected": "எதிர்பார்க்கப்படும்",
        "change": "மாற்றம்",
        "scenario": "சூழ்நிலை",
        "input": "உள்ளீடு",
        "result": "முடிவு",
        "happens": "நடக்கிறது",
        "pressure": "அழுத்தம்",
        "benefit": "பலன்",
        "impact": "தாக்கம்",
        "score": "மதிப்பெண்",
        "data": "தரவு",
        "records": "பதிவுகள்",
        "year": "ஆண்டு",
        "years": "ஆண்டுகள்",
        "period": "காலம்",
        "trend": "போக்கு",
        "increasing": "அதிகரிக்கும்",
        "declining": "குறைந்து வரும்",
        "normal": "சாதாரண",
        "dominant": "முக்கிய",
        "significant": "முக்கியமான",
        "minimal": "குறைந்த",
        "supplemental": "கூடுதல்",
        "preparation": "தயாரிப்பு",
        "area": "பரப்பளவு",
        "acres": "ஏக்கர்",
        "price": "விலை",
        "labor": "கூலி",
        "water": "நீர்",
        "summer": "கோடை",
        "winter": "குளிர்காலம்",
        "kharif": "காரிஃப்",
        "rabi": "ரபி",
    }
    word_map.update({
        "year": "ஆண்டு",
        "years": "ஆண்டுகள்",
        "hectares": "ஹெக்டேர்",
        "hectare": "ஹெக்டேர்",
        "tonnes": "டன்",
        "tonne": "டன்",
        "performance": "செயல்திறன்",
        "alignment": "பொருத்தம்",
        "compatibility": "பொருத்தம்",
        "coverage": "வசதி",
        "presence": "இருப்பு",
        "analysis": "பகுப்பாய்வு",
        "considered": "கருதப்பட்டது",
        "infrastructure": "வசதி",
        "primary": "முக்கிய",
        "source": "ஆதாரம்",
        "sources": "ஆதாரங்கள்",
        "cultivation": "சாகுபடி",
        "cultivated": "சாகுபடி செய்யப்பட்டது",
        "commercial": "வணிக",
        "rotation": "சுழற்சி",
        "planning": "திட்டமிடல்",
        "guidance": "வழிகாட்டுதல்",
        "quantity": "அளவு",
        "nitrogen": "நைட்ரஜன்",
        "phosphorus": "பாஸ்பரஸ்",
        "potash": "பொட்டாஷ்",
        "compost": "கம்போஸ்ட்",
        "drainage": "வடிகால்",
        "fungal": "பூஞ்சை",
        "diseases": "நோய்கள்",
        "insect": "பூச்சி",
        "climate": "காலநிலை",
        "profile": "சுயவிவரம்",
        "assessment": "மதிப்பீடு",
        "favourable": "சாதகமான",
        "favorable": "சாதகமான",
        "support": "ஆதரவு",
        "intensive": "தீவிர",
        "double": "இரட்டை",
        "triple": "மும்மை",
        "systems": "முறைகள்",
        "groundwater": "நிலத்தடி நீர்",
        "depth": "ஆழம்",
        "averages": "சராசரியாக உள்ளது",
        "metres": "மீட்டர்",
        "conservation": "பாதுகாப்பு",
        "efforts": "முயற்சிகள்",
        "pumping": "பம்பிங்",
        "efficient": "திறமையான",
        "methods": "முறைகள்",
        "drip": "சொட்டு பாசனம்",
        "vegetables": "காய்கறிகள்",
        "sweet": "சர்க்கரை",
    })
    for english, tamil in sorted(word_map.items(), key=lambda item: len(item[0]), reverse=True):
        out = re.sub(rf"\b{re.escape(english)}\b", tamil, out, flags=re.I)

    value_map = {}
    for value in list(KNOWN_CROPS) + list(CROP_ALIASES.keys()) + list(SOIL_KEYWORDS.keys()) + list(SEASON_KEYWORDS.keys()):
        value_map[value] = _ta(value)
    pest_names = [
        "Rice Blast (Magnaporthe oryzae)", "Brown Plant Hopper", "Stem Borer",
        "Sheath Blight", "Leaf Folder", "Fungal Leaf Spot", "Aphids", "Whitefly",
        "Red Spider Mite", "Thrips", "Leaf Miners", "Pod Borers",
        "General garden pests (minor)",
    ]
    for pest_name in pest_names:
        value_map[pest_name] = _ta_pests([pest_name])
    try:
        for district in getattr(de, "ALL_DISTRICTS", []) or []:
            value_map[str(district)] = _ta(str(district))
    except Exception:
        pass

    for english, tamil in sorted(value_map.items(), key=lambda item: len(item[0]), reverse=True):
        if english and tamil and english.lower() != tamil.lower():
            out = re.sub(rf"\b{re.escape(english)}\b", tamil, out, flags=re.I)

    out = re.sub(r"\btonnes?/ha\b", "டன்/ஹெக்டேர்", out, flags=re.I)
    out = re.sub(r"\btons?/ha\b", "டன்/ஹெக்டேர்", out, flags=re.I)
    out = re.sub(r"\bt/ha\b", "டன்/ஹெக்டேர்", out, flags=re.I)
    out = re.sub(r"\bkg/ha\b", "கிலோ/ஹெக்டேர்", out, flags=re.I)
    out = re.sub(r"\bha\b", "ஹெக்டேர்", out, flags=re.I)
    out = re.sub(r"\bmm\b", "மில்லிமீட்டர்", out, flags=re.I)
    out = re.sub(r"\bkm/h\b", "கி.மீ/மணி", out, flags=re.I)
    out = out.replace("₹", "ரூ.")
    out = out.replace("Rs.", "ரூ.")
    cleanup_map = {
        "receives": "பெறுகிறது",
        "versus": "ஒப்பிடும்போது",
        "need of": "தேவை",
        "well-covered by": "நன்றாக பூர்த்தியாகிறது",
        "of the": "இன்",
        "being irrigated": "பாசன வசதி கொண்டது",
        "under cultivation": "சாகுபடியில்",
        "have assured": "உறுதியான",
        "has irrigation access": "பாசன வசதி உள்ளது",
        "input prices": "உள்ளீட்டு விலைகள்",
        "soil condition": "மண் நிலை",
        "current": "தற்போதைய",
        "Alluvial மண்": "வண்டல் மண்",
        "Black மண்": "கருப்பு மண்",
        "Red மண்": "சிவப்பு மண்",
        "Clay மண்": "களிமண்",
        "நெல் Blast": "நெல் பிளாஸ்ட் நோய்",
        "Blast": "பிளாஸ்ட் நோய்",
        "Brown Plant Hopper": "பழுப்பு தத்துப்பூச்சி",
        "Plant Hopper": "தத்துப்பூச்சி",
        "fungicide": "பூஞ்சைக்கொல்லி",
        "resistant varieties": "நோய் எதிர்ப்பு வகைகள்",
        "access": "வசதி",
        "Whole ஆண்டு": "முழு ஆண்டு",
        "Rank": "வரிசை",
        "Sweet Potato": "சர்க்கரைவள்ளி கிழங்கு",
        "Potato": "உருளைக்கிழங்கு",
    }
    for english, tamil in sorted(cleanup_map.items(), key=lambda item: len(item[0]), reverse=True):
        out = re.sub(re.escape(english), tamil, out, flags=re.I)
    final_regex_map = [
        (r"From a மழை standpoint, ([^ ]+) பெறுகிறது an average of \*\*([^*]+)\*\*, உடன் the ([^*]+?) being the dominant மழை source at \*\*([^*]+)\*\*\.", lambda m: f"மழை அடிப்படையில், {_ta_named(m.group(1))} மாவட்டம் சராசரியாக **{m.group(2)}** பெறுகிறது; முக்கிய மழை ஆதாரம் {_ta_named(m.group(3))}, அதன் அளவு **{m.group(4)}**."),
        (r"From a மழை standpoint, ([^ ]+) பெறுகிறது an average of \*\*([^*]+)\*\*, உடன் the (.+?) being .*? at \*\*([^*]+)\*\*\.", lambda m: f"மழை அடிப்படையில், {_ta_named(m.group(1))} மாவட்டம் சராசரியாக **{m.group(2)}** பெறுகிறது; முக்கிய மழை ஆதாரம் {_ta_named(m.group(3))}, அதன் அளவு **{m.group(4)}**."),
        (r"Out of ([0-9,]+) ஹெக்டேர் under சாகுபடி, ([0-9,]+) ஹெக்டேர் உறுதியான பாசனம் வசதி\.", lambda m: f"சாகுபடியில் உள்ள {m.group(1)} ஹெக்டேர் பரப்பளவில், {m.group(2)} ஹெக்டேர் உறுதியான பாசன வசதி கொண்டது."),
        (r"\*\*([0-9.]+)% இன் நிகர விதைப்பு பரப்பளவு\*\*", lambda m: f"**நிகர விதைப்பு பரப்பளவில் {m.group(1)}%**"),
        (r"### உர பரிந்துரை . ([^ ]+) இல் \*\*([^*]+)\*\*", lambda m: f"### உர பரிந்துரை - **{_ta_named(m.group(2))}** மாவட்டத்தில் {_ta_named(m.group(1))}"),
        (r"\*\*மண்:\*\* ([^.]+)\.", lambda m: f"**மண்:** {_ta_named(m.group(1))}."),
    ]
    for pattern, replacement in final_regex_map:
        out = re.sub(pattern, replacement, out, flags=re.I | re.S)
    out = out.replace("June–September", "ஜூன்-செப்டம்பர்")
    out = out.replace("October–December", "அக்டோபர்-டிசம்பர்")
    out = out.replace("நெல்? பயிருக்கு", "நெல் பயிருக்கு")
    return out


def _tamil_response(result: dict) -> dict:
    result = dict(result)
    if result.get("intent") == "cost_estimate":
        rich_cost = _format_tamil_cost_estimate(result)
        if rich_cost:
            result["text"] = _ensure_tamil_followup_chips(rich_cost, result.get("intent", "general"), result.get("memory") or {})
            return result
    rich_formatters = {
        "wage_info": _format_tamil_wage_info,
        "yield_trend": _format_tamil_yield_trend,
        "best_district_for_crop": _format_tamil_best_districts,
        "whatif": _format_tamil_whatif,
    }
    formatter = rich_formatters.get(result.get("intent"))
    if formatter:
        rich_text = formatter(result)
        if rich_text:
            result["text"] = _ensure_tamil_followup_chips(rich_text, result.get("intent", "general"), result.get("memory") or {})
            return result

    original_text = re.sub(r"\n\n---\n\*\*FOLLOWUP_CHIPS:[\s\S]*?\*\*\s*$", "", result.get("text") or "").strip()
    translated = _translate_same_template_to_tamil(original_text)
    latin_words = re.findall(r"\b[A-Za-z]{4,}\b", translated)
    allowed_latin = {"TNAU", "IPM", "NPK", "AI"}
    leak_count = sum(1 for word in latin_words if word.upper() not in allowed_latin)
    if leak_count > 6 or re.search(r"\b(failed|denied|error|exception|traceback)\b", translated, re.I):
        translated = _strict_tamil_summary(result.get("intent", "general"), result.get("memory") or {}, original_text)
    result["text"] = _ensure_tamil_followup_chips(translated, result.get("intent", "general"), result.get("memory") or {})
    return result

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
    if re.search(r"\bwhat if\b|\bsuppose\b|\bsimulate\b", ql):
        return "whatif"
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
        best_data = de.get_best_districts_for_crop(crop, requested_season, top_n=7)
        text = nlg.describe_best_districts_for_crop(best_data)
        return {"text": _ensure_followup_chips(text, intent, {**ctx, "district": None}), "intent": intent, "district": None, "memory": new_memory, "data": {"best_district_data": best_data}}

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
        response_data["whatif_data"] = de.compute_whatif_simulation(district, crop, soil, season, irr_delta, rain_delta)
        text = nlg.describe_whatif(district, crop, response_data["whatif_data"])
    elif intent == "cost_estimate":
        response_data["cost_data"] = de.estimate_crop_cost(district, crop)
        text = nlg.describe_cost_estimate(district, crop, response_data["cost_data"])
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
        response_data["wage_data"] = de.get_wage_info(district)
        text = nlg.describe_wages(district, response_data["wage_data"])
    elif intent == "irrigation_info":
        text = nlg.describe_irrigation(district, de.get_irrigation_profile(district))
    elif intent == "yield_trend":
        response_data["yield_trend_data"] = de.get_yield_trend(district, crop)
        text = nlg.describe_yield_trend(district, crop, response_data["yield_trend_data"])
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
